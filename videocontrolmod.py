from subprocess import call  
import sys  
import time 
import logindbmod 

videostreamport="5022" #previous setting 5022


################## ------- VLC section
# In case of use of VLC the code below works

#stream = "sudo -u pi cvlc --no-audio v4l2:///dev/video0 --v4l2-width 1920 --v4l2-height 1440 --v4l2-chroma MJPG --v4l2-hflip 1 --v4l2-vflip 1 --sout '#standard{access=http{mime=multipart/x-mixed-replace;boundary=--7b3cc56e5f51db803f790dad720ed50a},mux=mpjpeg,dst=:8554/}' -I dummy &" 
#def streamedit(dictdata):
#	width="1920"
#	height="1440"
#	fps="10"
#	video="video0"
	
#	if "width" in dictdata:
#		width=dictdata["width"]
#	if "height" in dictdata:
#		height=dictdata["height"]
#	if "fps" in dictdata:
#		fps=dictdata["fps"]
#	if "video" in dictdata:
#		video=dictdata["video"]
						
#	stream = "sudo -u pi cvlc --no-audio v4l2:///dev/"+video+" --v4l2-fps "+fps+" --v4l2-width "+width+" --v4l2-height "+height+" --v4l2-chroma MJPG --v4l2-hflip 1 --v4l2-vflip 1 --sout '#standard{access=http{mime=multipart/x-mixed-replace;boundary=--7b3cc56e5f51db803f790dad720ed50a},mux=mpjpeg,dst=:8554/}' -I dummy &" 
#	return stream

################## ------- END

def streamedit(dictdata):
	#./mjpg_streamer -i "./input_uvc.so -d /dev/video1 -r 640x480" -o "./output_http.so -w ./www"
	username=logindbmod.getusername()
	password=logindbmod.getpassword()
	
	
	width="1024"
	height="768"
	fps="15"
	video="video0"
	
	if "width" in dictdata:
		width=dictdata["width"]
	if "height" in dictdata:
		height=dictdata["height"]
	if "fps" in dictdata:
		fps=dictdata["fps"]
	if "video" in dictdata:
		video=dictdata["video"]

	global videostreamport
	if (video=="video0")and(int(width)>1024):

		print "try using the raspicam"
		stream="mjpg_streamer -i '/usr/local/lib/mjpg-streamer/input_raspicam.so -d /dev/"+video+" -x "+width+" -y "+height+" -fps "+fps+"' -o '/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www -p "+videostreamport+"' &"
	
		#stream="mjpg_streamer -i '/usr/local/lib/mjpg-streamer/input_raspicam.so -d /dev/"+video+" -x "+width+" -y "+height+" -fps "+fps+"' -o '/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www -p "+videostreamport+" -c "+username+":"+password+"' &"

	else:
		stream="mjpg_streamer -i '/usr/local/lib/mjpg-streamer/input_uvc.so -d /dev/"+video+" -r "+width+"x"+height+" -f "+fps+"' -o '/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www -p "+videostreamport+"' &"


		#stream="mjpg_streamer -i '/usr/local/lib/mjpg-streamer/input_uvc.so -d /dev/"+video+" -r "+width+"x"+height+" -f "+fps+"' -o '/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www -p "+videostreamport+" -c "+username+":"+password+"' &"

		#mjpg_streamer -i "/usr/local/lib/mjpg-streamer/input_uvc.so -d /dev/video0 -r 1920x1080" -o "/usr/local/lib/mjpg-streamer/output_http.so -w /usr/local/share/mjpg-streamer/www -p 8090"
							
		#stream = "sudo -u pi cvlc --no-audio v4l2:///dev/"+video+" --v4l2-fps "+fps+" --v4l2-width "+width+" --v4l2-height "+height+" --v4l2-chroma MJPG --v4l2-hflip 1 --v4l2-vflip 1 --sout '#standard{access=http{mime=multipart/x-mixed-replace;boundary=--7b3cc56e5f51db803f790dad720ed50a},mux=mpjpeg,dst=:8554/}' -I dummy &" 
			


	return stream


def stream_video(videodev="",resolution={}):
	stop_stream()
	
	resollist=resolution.split("x")
	dictdata={"width":resollist[0], "height":resollist[1], "fps":resollist[2]}
	if videodev:
		dictdata["video"]=videodev
	stream=streamedit(dictdata)
	
	done=False
	try:
		print "starting streaming\n%s" % stream  
		call ([stream], shell=True)  
  
  	except:
		print "Exception error failed to start VLC streaming "
		return "Exception"
	else:
		print "Streaming"
		done="Streaming"
	return done
  
  
def stop_stream_VLC():  
	print "stopping streaming"  
	#call (["pkill raspivid"], shell=True)  
	call (["sudo pkill vlc"], shell=True)
	time.sleep(2)

def stop_stream():  
	print "stopping streaming"  
	#call (["pkill mjpg_streamer"], shell=True)  
	call (["sudo pkill mjpg_streamer"], shell=True)
	time.sleep(2)


	
if __name__ == '__main__':
	# comment
	#a=[]
	#print a
	#connectedssid()
	stream_video()
