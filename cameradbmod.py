# -*- coding: utf-8 -*-
"""
camera setting storage utilities
"""

import logging
import os
import os.path
import sys
import string
from datetime import datetime,date,timedelta
import time
import filestoragemod



# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////




DATAFILENAME="camdata.txt"
DEFDATAFILENAME="default/defcamdata.txt"
CAMERAPARAMETERS=["camname","resolution","position","servo","time","active","vflip"]


global data
data=[]

# read data -----
if not filestoragemod.readfiledata(DATAFILENAME,data): #read watering setting file
	#read from default file
	filestoragemod.readfiledata(DEFDATAFILENAME,data)
	print "Watering writing default calibration data"
	filestoragemod.savefiledata(DATAFILENAME,data)
# end read data -----



# ///////////////// --- END GLOBAL VARIABLES ------



#-- start filestorage utility--------////////////////////////////////////////////////////////////////////////////////////	

# one row is called "default" and include the default data before setting
# {"resolution": "320x240", "fps": "20", "time": "10:30", "name": "default"}
# once the setting is saved, several lines will be produced with name="camera" and "camname" = video1 , video2 , etc
# {"resolution": "320x240", "fps": "20", "time": "10:30", "name": "camera", "camname" : "video1"}


		


	
def restoredefault():
	filestoragemod.deletefile(DATAFILENAME)
	filestoragemod.readfiledata(DEFDATAFILENAME,data)
	savesetting()
	
def savesetting():
	filestoragemod.savefiledata(DATAFILENAME,data)

def changecreatesetting(name,camname,parameter,value):
	for line in data:
		if line["name"]==name:
			if line["camname"]==camname:
				line[parameter]=value #this change the parameter or create one if not existing
				return True
	# need to create append new dictionary line
	newline={}
	newline["name"]=name
	newline["camname"]=camname
	newline[parameter]=value
	data.append(newline)
	return True

def getcameradata(videolist):
	exportdata=[]
	name="camera"
	for video in videolist:
		found=False
		i=0
		while (i<len(data))and(not found):
			line=data[i]
			i=i+1
			if (line["name"]==name)and(line["camname"]==video):
				newline={}
				for param in CAMERAPARAMETERS:
					if param in line:
						newline[param]=line[param]			
					else:
						newline[param]=""
				exportdata.append(newline)
				found=True
		if (not found):
			newline={}
			for param in CAMERAPARAMETERS:
				if param=="camname":
					newline[param]=video
				else:
					newline[param]=searchdata("name","default",param)
			exportdata.append(newline)			
	return exportdata


def getcameraname():
	recordkey="name"
	recordvalue="camera"
	keytosearch="camname"
	return searchdatalist(recordkey,recordvalue,keytosearch)

def getparamlist():
	recordkey="name"
	recordvalue="listparam"
	datalist=[]
	for ln in data:
		if ln[recordkey]==recordvalue:
			ind=0
			for rw in ln:
				if rw!=recordkey:
					ind=ind+1
					datalist.append(ln[str(ind)])	
					
	return datalist



def getrowdata(recordvalue,paramlist):
	recordkey="name"
	datalist=[]
	for ln in data:
		if ln[recordkey]==recordvalue:
			for param in paramlist:
					datalist.append((ln[param]))					
	return datalist

def gettable():
	paramlist=getparamlist()
	elementlist=getelementlist()
	datalist=[]
	for row in elementlist:
		rowdatalist=getrowdata(row,paramlist)
		datalist.append(rowdatalist)	
	return datalist


def replacerow(element,dicttemp):
	searchfield="name"
	searchvalue=element
	for line in data:
		if line[searchfield]==searchvalue:
			for row in line:
				line[row]=dicttemp[row]
			filestoragemod.savefiledata(DATAFILENAME,data)
			return True
	return False



def changesavesetting(name,parameter,value):
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	for line in data:
		if line["name"]==name:
			line[parameter]=value
			savesetting()
			return True
	return False

def searchdata(recordkey,recordvalue,keytosearch):
	for ln in data:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					return ln[keytosearch]	
	return ""

def isCameraActive(video):
	param=searchdata("camname",video,"active")
	if param=="True":
		return True
	else:
		return False


def gettimedata(name):
	# return list with three integer values: hour , minute, second
	timestr=searchdata("name",name,"time")
	returntime=[]
	if not timestr=="":
		timelist=timestr.split(":")
		for timeitem in timelist:
			returntime.append(timeitem)
		if len(timelist)<3:
			returntime.append("00")
		return returntime
	else:
		return ["00","00","00"]
			
		

def searchdatalist(recordkey,recordvalue,keytosearch):
	datalist=[]
	for ln in data:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					datalist.append(ln[keytosearch])	
	return datalist

def getfieldvaluelist(fielditem,valuelist):
	del valuelist[:]
	for line in data:
		valuelist.append(line[fielditem])

def getfieldinstringvalue(fielditem,stringtofind,valuelist):
	del valuelist[:]
	for line in data:
		name=line[fielditem]
		if name.find(stringtofind)>-1:
			valuelist.append(name)


	

def get_path():
    '''Get the path to this script no matter how it's run.'''
    #Determine if the application is a py/pyw or a frozen exe.
    if hasattr(sys, 'frozen'):
        # If run from exe
        dir_path = os.path.dirname(sys.executable)
    elif '__file__' in locals():
        # If run from py
        dir_path = os.path.dirname(__file__)
    else:
        # If run from command line
        dir_path = sys.path[0]
    return dir_path
	
#--end --------////////////////////////////////////////////////////////////////////////////////////		
	
	
if __name__ == '__main__':
	# comment
	a=10
	




