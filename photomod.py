from __future__ import print_function
import time
from time import sleep
import datetime
import os
import sys
import subprocess
import logging
from PIL import Image # to make thumbnail
from subprocess import call
from shutil import copyfile

logger = logging.getLogger("hydrosys4."+__name__)

def videodevlist():
	folderpath="/dev"
	videolist=[]
	filelist=os.listdir(folderpath)
	for filename in filelist:
		if "video" in filename:

			# following code was necessary starting from raspbian buster, by default there are video10,video11,video12 devices created
			#get the video number
			videonumberstr=get_digits(filename)
			try:
				videonumber=int(videonumberstr)
			except:
				videonumber=-1
				print("not able to convert the video number")
			if videonumber>-1:
				if (videonumber<10):
					print("check video " , filename)
					# following code was necessary starting from raspbian buster, linux kernel v4l2 was updated, now one single webcam can show more than one videoXX dev
					if checkvideoformatexist(videonumberstr):
						print("OK video " , filename)
						videolist.append(filename)
	return videolist # item1 (path) item2 (name) item3 (datetime)

def get_digits(x):
    return ''.join(ele for ele in x if ele.isdigit())

def checkvideoformatexist(videonumberstr):
	# v4l2-ctl -d /dev/video0 -D
	DeviceType="Video Capture"
	formats=['YU12','YUYV','RGB3','JPEG','H264','MJPG','YVYU','VYUY','UYVY','NV12','BGR3','YV12','NV21','BGR4']

	# v4l2-ctl --list-formats -d 1
	cmd = ['v4l2-ctl', '--list-formats' , '-d', videonumberstr]
	try:
		scanoutput = subprocess.check_output(cmd).decode('utf-8')
	except:
		print("error execute the command ", cmd)
		logger.error("error execute the command %s",cmd)
		return False

	if 	not DeviceType in scanoutput:
		print("not a video capture device =" , videonumberstr)
		return False

	# check if one of the format is inside the output string
	for formatitem in formats:
		if formatitem in scanoutput:
			print("At least a format = ", formatitem ," for video capture device =" , videonumberstr)
			return True
	return False

def checkPIcam(device):
	cmd = ['v4l2-ctl', '-d', '/dev/'+device, '-D']
	wordtofind="bm2835"
	isfound=executeandsearch(cmd,wordtofind)
	return isfound

def findPIcam():
	result = ""

	devicelist=videodevlist()
	for device in devicelist:
		cmd = ['v4l2-ctl', '-d', '/dev/'+device, '-D']
		wordtofind="bm2835"
		isfound=executeandsearch(cmd,wordtofind)
		if isfound:
			result = device
	return result

def executeandsearch(cmd,wordtofind):
	try:
		scanoutput = subprocess.check_output(cmd).decode('utf-8')
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return False

	for line in scanoutput.split('\n'):
		#print " line ",line
		strstart=line.find(wordtofind)
		if strstart>-1:
			#found
			return True
	return False

def saveshot(filepath, video, realshot, resolution, positionvalue, vdirection):
	shottaken=False
	print("take photo")

	if vdirection=="neg":
		rotdeg="180"
	else:
		rotdeg="0"

	currentdate=datetime.datetime.now().strftime("%y-%m-%d,%H:%M")
	print("Current date and time: " , currentdate)
	if realshot:
		filenamenopath=currentdate+"@"+video+"@"+positionvalue+".jpg"
		filenamenopath2=currentdate+"@"+video+"@"+positionvalue+"F.jpg"
		filenamenopath3=currentdate+"@"+video+"@"+positionvalue+"R.jpg"
	else:
		filenamenopath="testimage.jpg"
		filenamenopath2=filenamenopath
		filenamenopath3=filenamenopath

	filename=os.path.join(filepath, filenamenopath)
	print("Start Photo procedure: ", video , " ************************************************")
	print("FILE : ", filename)

	cam_list = "/dev/" + video
	if not (video==""):


		filexist=os.path.isfile(filename)
		print("file already exist = ", filexist)

		if (filexist)and(not realshot):
			os.rename(filename, filename + ".bak")

		shottaken=False
		#w=resolution.split("x")[0]
		#h=resolution.split("x")[1]

		#filenamebase=filenamenopath.split(".")[0]
		#extension=filename.split(".")[1]

		# capture image using V4l2
		# http://www.geeetech.com/wiki/index.php/Raspberry_Pi_Camera_Module
		# v4l2-ctl --set-fmt-video=width=2592,height=1944,pixelformat=3
		# v4l2-ctl --stream-mmap=3 --stream-count=1 --stream-to=somefile.jpg
		# https://www.raspberrypi.org/forums/viewtopic.php?f=43&t=62364&start=450

		# check the v4l2 setting: v4l2-ctl -d /dev/video0 --list-ctrls
		# setting
		# v4l2-ctl --set-ctrl=gain=00
		# sudo v4l2-ctl -d /dev/video0 --set-ctrl=auto_exposure=1
		# (auto exposure=0 ->auto; exposure=1 ->manual, each camera has its own name of the parameter, auto_exposure, exposure_auto)
		# v4l2-ctl --set-ctrl=exposure_absolute=10

		# raspistill provides way better photo than the fswebcam when using the raspbery camera
		# raspberry camera is on video0 only
		# there is no reliable way to detect the raspicam, then just try to get a picture first with raspistill

		if checkPIcam(video):
			print("The video device should be PI camera")
			shottaken=takeshotandsave_raspistill(filepath, filenamenopath3, video, resolution, rotdeg)
			if not shottaken: # gives it a second chance :)
				shottaken=takeshotandsave_fswebcam(filepath, filenamenopath2, video, resolution, rotdeg)
		else:
			print(" The video device should be USB camera")
			shottaken=takeshotandsave_fswebcam(filepath, filenamenopath2, video, resolution, rotdeg)

		#shottaken=takeshotandsave_mjpg_streamer(filepath,filenamenopath, video, resolution)

		if (not shottaken)and(not realshot):
			if filexist:
				os.rename(filename + ".bak", filename)

		print("Picture acknowledge return = " ,shottaken)

	else:
		print("camera not connected")
	return shottaken

def takeshotandsave_raspistill(filepath,filenamenopath, video, resolution, rotdeg):
	shottaken=False

	if rotdeg=="180":
		vflip="-vf -hf"
	else:
		vflip=""

	print("flip ", vflip)

	cam_list = "/dev/" + video

	i=0
	while (not shottaken)and(i<3):
		i=i+1
		filename=os.path.join(filepath, filenamenopath)
		print("FILE : ", filename)

		shottaken=False
		w=resolution.split("x")[0]
		h=resolution.split("x")[1]

		print("try raspistill")

		filenamebase=filenamenopath.split(".")[0]
		extension=filename.split(".")[1]

		# create the picture files
		isok=False
		try:
			myproc = subprocess.check_output("raspistill "+vflip+" -w "+w+" -h "+h+" -q 95 -a 12 -a \"%Y-%m-%d %X (UTC)\" -o " + filename, shell=True, stderr=subprocess.STDOUT)
			isok=True
		except:
			print("problem to execute command")


		newfilexist=os.path.isfile(filename)
		print("file was created = ", newfilexist)

		if (isok)and(newfilexist):
			print("raspistill got picture")
			shottaken=True
			# make thumbnail
			ExistandThumb(filepath,filenamenopath,shottaken)

		else:
			print("raspistill not able to get picture")
			shottaken=False


		print("RASPISTILL Picture take = " ,shottaken, "  Attempt ", i)

	return shottaken

def takeshotandsave_fswebcam(filepath, filenamenopath, video, resolution, rotdeg):
	shottaken=False

	if not (video==""):
		cam_list = "/dev/" + video

		i=0
		while (not shottaken)and(i<3):
			i=i+1
			filename=os.path.join(filepath, filenamenopath)
			print("FILE : ", filename)

			shottaken=False
			w=resolution.split("x")[0]
			h=resolution.split("x")[1]

			print("try fswebcam")

			filenamebase=filenamenopath.split(".")[0]
			extension=filename.split(".")[1]

			# create the picture files
			isok=False
			try:
				myproc = subprocess.check_output("fswebcam -q -d "+ cam_list +" -r "+resolution+" --fps 15 -S 60 --rotate " + rotdeg + " -s brightness=50% -s Contrast=50% --jpeg -1 --font luxisr:14 " + filename, shell=True, stderr=subprocess.STDOUT)
				isok=True
			except:
				print("problem to execute fswebcam command")

			# -R use read() method -- NOT WORKING ---
			# -D delay before taking frames
			# -S skip the first frames
			# -q quiet output mode
			# -d device
			# -r resoltion
			# -F takes frames

			print("output from subprocess: " , myproc)

			newfilexist=os.path.isfile(filename)
			print("file was created = ", newfilexist)

			if (isok)and(newfilexist):
				print("fswebcam got picture")
				shottaken=True
				# make thumbnail
				ExistandThumb(filepath,filenamenopath,shottaken)
			else:
				print("fswebcam not able to get picture")
				shottaken=False

			print("FSWEBCAM Picture take = " ,shottaken, "  Attempt ", i)

	else:
		print("camera not connected")

	return shottaken

def takeshotandsave_mjpg_streamer(filepath,filenamenopath, video, resolution , rotdeg):
	shottaken=False

	filename=os.path.join(filepath, filenamenopath)
	print("FILE : ", filename)

	if not (video==""):
		cam_list = "/dev/" + video

		shottaken=False
		w=resolution.split("x")[0]
		h=resolution.split("x")[1]

		print("try mjpg_streamer")

		filenamebase=filenamenopath.split(".")[0]
		extension=filename.split(".")[1]

		pathmjpg=os.path.join(filepath,"mjpg")
		if not os.path.exists(pathmjpg):
			# fi folder do not exist, create it
			os.makedirs(pathmjpg)
		else:
			#remove all files in folder
			for the_file in os.listdir(pathmjpg):
				file_path = os.path.join(pathmjpg, the_file)
				try:
					if os.path.isfile(file_path):
						os.unlink(file_path)
				except Exception as e:
					print(e)

		# create the picture files
		fps="20"

		if (video=="video0")and(int(w)>1024):
			print("mjpg_streamer using the raspicam")
			stream="mjpg_streamer -i '/usr/local/lib/mjpg-streamer/input_raspicam.so -d /dev/"+video+" -x "+w+" -y "+h+" -fps "+fps+" -rot "+rotdeg+"' -o '/usr/local/lib/mjpg-streamer/output_file.so -f "+pathmjpg+" -d 100' &"
		else:
			stream="mjpg_streamer -i '/usr/local/lib/mjpg-streamer/input_uvc.so -d /dev/"+video+" -r "+w+"x"+h+" -f "+fps+" -rot "+rotdeg+"' -o '/usr/local/lib/mjpg-streamer/output_file.so -f "+pathmjpg+" -d 100' &"
		call ([stream], shell=True)
		time.sleep(2)
		call (["sudo pkill mjpg_streamer"], shell=True)

		# take last saved file in the folder
		folderpath=pathmjpg

		filenamelist=[]
		sortedlist=sorted([f for f in os.listdir(folderpath) if os.path.isfile(os.path.join(folderpath, f))])
		sortedlist.reverse()
		lastfile=""
		for files in sortedlist:
			if (files.endswith(".jpg") or files.endswith(".png")):
				lastfile=files
				break

		#copy lastfile to filepath
		if not (lastfile==""):
			shottaken=True
			#copy file to the right folder and right name
			src=os.path.join(pathmjpg, lastfile)
			dst=filename
			copyfile(src, dst)
			# make thumbnail
			ExistandThumb(filepath,filenamenopath,shottaken)
		else:
			print("mjpg_streame not able to get picture")
			shottaken=False

		print("MJPG_STREAMER Picture take = " ,shottaken)

	else:
		print("camera not connected")

	return shottaken

def ExistandThumb(filepath,filenamenopath,shottaken):
	filename=os.path.join(filepath, filenamenopath)
	newfilexist=os.path.isfile(filename)
	# make thumbnail
	if (shottaken and newfilexist):
		paththumb=os.path.join(filepath,"thumb")
		if not os.path.exists(paththumb):
			os.makedirs(paththumb)
		try:
			image = Image.open(filename)
			image.thumbnail((350, 350))
			thumbname=os.path.join(paththumb,filenamenopath)
			image.save(thumbname)
		except:
			print("not able to make thumbnail")
	return newfilexist

def thumbconsistency(apprunningpath):
	"""
	Check if there is a thumbnail without corresponding image and delete it.
	Recreate missing thumbnails.
	"""

	# control if the folder hydropicture exist otherwise create it
	filepath=os.path.join(apprunningpath, "static", "hydropicture")
	if not os.path.exists(filepath):
		os.makedirs(filepath)
		print("Hydropicture folder has been created")

	paththumb=os.path.join(filepath,"thumb")
	if not os.path.exists(paththumb):
		os.makedirs(paththumb)
		print("Hydropicture thumbnail folder has been created")

	filenamelist=os.listdir(filepath)
	thumbnamelist=os.listdir(paththumb)

	for thumbnail in thumbnamelist:
		if thumbnail not in filenamelist:
			print("thumbnail has no corresponding image, delete")
			os.remove(os.path.join(paththumb, thumbnail))

	# create thumbnail in case picture has no coresponding thumbnail
	for fileimage in filenamelist:
		if os.path.isfile(os.path.join(filepath, fileimage)):
			if fileimage not in thumbnamelist:
				print("image has no corresponding thumbnail, create")
				#create thumbnail
				try:
					image = Image.open(os.path.join(filepath,fileimage))
					image.thumbnail((350, 350))
					thumbname=os.path.join(paththumb,os.path.basename(fileimage))
					image.save(thumbname)
				except:
					print("Create thumbnail failed")

	return True

if __name__ == '__main__':
	"""
	prova funzioni di camera
	"""
	print("PI cam device :" , findPIcam())
	#saveshot()
