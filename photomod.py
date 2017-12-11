import time
from time import sleep
import datetime
import os
import sys
import subprocess 
from PIL import Image # to make thumbnail



def videodevlist():
	folderpath="/dev"
	videolist=[]
	filelist=os.listdir(folderpath)
	for files in filelist:
		if "video" in files:
			videolist.append(files)
	return videolist # item1 (path) item2 (name) item3 (datetime)
 
def saveshot(filepath, video, realshot, resolution, positionvalue):
	shottaken=False
	i=0
	currentdate=datetime.datetime.now().strftime("%y-%m-%d,%H:%M")
	print "Current date and time: " , currentdate
	if realshot:
		filenamenopath=currentdate+"@"+video+"@"+positionvalue+".jpg"
	else:
		filenamenopath="testimage.jpg"
	
	filename=os.path.join(filepath, filenamenopath)
	print "FILE : ", filename		

	
	cam_list = "/dev/" + video
	if not (video==""):
			
		while (not shottaken)and(i<10):
			i=i+1
			print " ATTEMPT: ", i , " device : ", cam_list
			filexist=os.path.isfile(filename)
			print "file already exist = ", filexist
			
			if (filexist)and(not realshot):
				os.rename(filename, filename + ".bak")
			

			#myproc = subprocess.check_output("fswebcam -d "+ cam_list +" -r 1280x720 -S 15 --jpeg 95" + filename, shell=True)




			shottaken=False
			w=resolution.split("x")[0]
			h=resolution.split("x")[1]			

			print "try fswebcam"
			if i==1:
				S="35"
			else:
				S="5"
			# Raspistill option
			# raspistill -w 1024 -h 768 -q 95 -o "picture.jpg"			
			#myproc = subprocess.check_output("raspistill -w "+w+" -h "+h+" -q 95 -o " + filename, shell=True, stderr=subprocess.STDOUT)

			#fswebcam option
			myproc = subprocess.check_output("fswebcam -q -d "+ cam_list +" -r "+resolution+" -S "+S+" --jpeg 95 " + filename, shell=True, stderr=subprocess.STDOUT)
			# -R use read() method -- NOT WORKING ---
			# -D delay before taking frames
			# -S skip the first frames
			# -q quiet output mode
			# -d device
			# -r resoltion

			if myproc=="":
				print " No error reported "
				shottaken=True
			else:
				print 'Error code was ', myproc
				shottaken=False

			
			newfilexist=os.path.isfile(filename)
			print "file was created = ", newfilexist
			
			if not newfilexist:
				shottaken=False
				if filexist:
					os.rename(filename + ".bak", filename)
			print "Picture take = " ,shottaken
			
			# make thumbnail
			if shottaken:
				paththumb=os.path.join(filepath,"thumb")
				if not os.path.exists(paththumb):
					os.makedirs(paththumb)
				image = Image.open(filename)
				image.thumbnail((300, 300))
				thumbname=os.path.join(paththumb,filenamenopath)
				image.save(thumbname)
				

	else:
		print "camera not connected"	
	return shottaken



def thumbconsistency(apprunningpath):
	# check if there is a thumbnail without corresponding image
	
	filepath=os.path.join(apprunningpath, "static")
	filepath=os.path.join(filepath, "hydropicture")
	# control if the folder hydropicture exist otherwise create it
	if not os.path.exists(filepath):
		os.makedirs(filepath)
		print "Hydropicture folder has been created"
	paththumb=os.path.join(filepath,"thumb")
	if not os.path.exists(paththumb):
		os.makedirs(paththumb)
		print "Hydropicture thumbnail folder has been created"
	
	filenamelist=os.listdir(filepath)

	thumbnamelist=os.listdir(paththumb)
	
	for thumbnail in thumbnamelist:
		if thumbnail not in filenamelist:
			print "thumbnail has no corresponding image, delete"
			os.remove(os.path.join(paththumb, thumbnail))
	
	# create thumbnail in case picture has no coresponding thumbnail
	
	
	for fileimage in filenamelist:
		if os.path.isfile(os.path.join(filepath, fileimage)):
			if fileimage not in thumbnamelist:
				print "image has no corresponding thumbnail, create"
				#create thumbnail
				image = Image.open(os.path.join(filepath,fileimage))
				image.thumbnail((300, 300))
				thumbname=os.path.join(paththumb,os.path.basename(fileimage))
				image.save(thumbname)
			
	return True







if __name__ == '__main__':
	
	"""
	prova funzioni di camera
	"""
	#Determine if the application is a py/pyw or a frozen exe.
	if hasattr(sys, 'frozen'):
		# If run from exe
		dir_path = os.path.dirname(sys.executable)
	elif '__file__' in locals():
		# If run from py
		dir_path =  os.path.dirname(os.path.realpath(__file__))
	else:
		# If run from command line
		dir_path = sys.path[0]
	
	print dir_path

	saveshot(dir_path,False)
	#saveshot()
