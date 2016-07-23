import time
from time import sleep
import datetime
import os
import sys

try:
	__import__("picamera")
except ImportError:
	ISRPI=False
else:
	import picamera
	ISRPI=True

 
def saveshot(filepath,realshot=True):
	shottaken=False
	currentdate=datetime.datetime.now().strftime("%y-%m-%d,%H:%M")
	print "Current date and time: " , currentdate
	cam_list = "/dev/video0"
	if ISRPI:
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
			
			# TAKE shot

			try:			
				with picamera.PiCamera() as camera:
					camera.resolution = (2592,1944)
					# Camera warm-up time
					sleep(2)
					camera.capture(filepath)
					shottaken=True
			except:
				shottaken=False
				
			# shot taken
			
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
