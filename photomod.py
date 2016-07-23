import time
from time import sleep
import datetime
import os
import sys

import subprocess 

def videodevlist():
	folderpath="/dev"
	videolist=[]
	filelist=os.listdir(folderpath)
	for files in filelist:
		if "video" in files:
			videolist.append(files)
	return videolist # item1 (path) item2 (name) item3 (datetime)
 
def saveshot(filepath, video, realshot=True):
	shottaken=False
	i=0
	currentdate=datetime.datetime.now().strftime("%y-%m-%d,%H:%M")
	print "Current date and time: " , currentdate
	if realshot:
		filepath=os.path.join(filepath, currentdate+"@"+video+".jpg")
	else:
		filepath=os.path.join(filepath, "testimage.jpg")
	print "FILE : ", filepath		

	
	cam_list = "/dev/" + video
	if not (video==""):
			
		while (not shottaken)and(i<10):
			i=i+1
			print " ATTEMPT: ", i , " device : ", cam_list
			filexist=os.path.isfile(filepath)
			print "file already exist = ", filexist
			
			if (filexist)and(not realshot):
				os.rename(filepath, filepath + ".bak")
			

			#myproc = subprocess.check_output("fswebcam -d "+ cam_list +" -r 1280x720 -S 15 --jpeg 95" + filepath, shell=True)
			if i==1:
				myproc = subprocess.check_output("fswebcam -q -d "+ cam_list +" -r 1280x720 -S 35 --jpeg 95 " + filepath, shell=True, stderr=subprocess.STDOUT)				
			else:
				myproc = subprocess.check_output("fswebcam -q -d "+ cam_list +" -r 1280x720 -S 5 --jpeg 95 " + filepath, shell=True, stderr=subprocess.STDOUT)
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

			
			newfilexist=os.path.isfile(filepath)
			print "file was created = ", newfilexist
			
			if not newfilexist:
				shottaken=False
				if filexist:
					os.rename(filepath + ".bak", filepath)
			print "Picture take = " ,shottaken
			

	else:
		print "camera not connected"	
	return shottaken


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
