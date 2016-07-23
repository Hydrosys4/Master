import time
from time import sleep
import datetime
import os
import sys

from subprocess import Popen, PIPE

 
def saveshot(filepath,realshot=True):
	shottaken=False
	currentdate=datetime.datetime.now().strftime("%y-%m-%d,%H:%M")
	print "Current date and time: " , currentdate
	cam_list = "/dev/video0"
	if cam_list:
		gonext=True
		if gonext:
			if realshot:
				filepath=os.path.join(filepath, currentdate+".jpg")
			else:
				filepath=os.path.join(filepath, "testimage.jpg")
			print filepath
			
			filexist=os.path.isfile(filepath)
			print "file already exist = ", filexist
			
			if filexist:
				os.rename(filepath, filepath + ".bak")
			
			#p = sub.Popen("fswebcam -d "+ cam_list +" -r 1280x1024 -S 35 --jpeg 95 " + filepath, stdout=sub.PIPE, stderr=sub.PIPE)
			#p = os.popen("fswebcam -d "+ cam_list +" -r 1280x1024 -S 35 --jpeg 95 " + filepath)

			myproc = Popen("fswebcam -d "+ cam_list +" -r 1280x1024 -S 35 --jpeg 95 " + filepath, shell=True, stdout=PIPE, stderr=PIPE)
			#sleep(10)
			print myproc.stdout.readline()
			print 'Return code was ', myproc.returncode
			sleep(2)
			
			newfilexist=os.path.isfile(filepath)
			print "file was created = ", newfilexist
			shottaken=True
			
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
	filepath=os.path.join(dir_path, "static")
	filepath=os.path.join(filepath, "cameratest")
	print filepath 
	saveshot(filepath,False)
	#saveshot()
