# -*- coding: utf-8 -*-
"""
Wateringplan sensor selection storage utilities
"""
from __future__ import print_function

import logging
import os
import os.path
import sys
import shutil
import string
from datetime import datetime,date,timedelta
import time
import filestoragemod
import hardwaremod



# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////


global DATAFILENAME
DATAFILENAME="wpsensor.txt"


global WTdata
WTdata={}



# read WTdata -----
WTdata=filestoragemod.readfiledata_full(DATAFILENAME)
if not WTdata:
	print("problem reading the file WTSensor.txt" )
	WTdata={}
#if not WTdata: #read watering setting file
	#read from default file, the below groups should always be present 
	#WTdata={"BasicInfo": {},"QueryGroup": [{"QueryItems":[],"ParseItems":[]}],"CounterInfo": {}, "Wateractuators": {} }

	#print "Watering writing default calibration data"
	#filestoragemod.savefiledata_full(DATAFILENAME,WTdata)


# ///////////////// --- END GLOBAL VARIABLES ------


def consistencycheck():
	# check if the sensors are still present in the sensorlist, if not, remove them
	Sensorlist1, Sensorlist2 = getactivesensor()
	sensors=sensorlist()
	saveit=False
	if Sensorlist1:
		if Sensorlist1[0] not in sensors:
			Sensorlist1=[]
			saveit=True
	if Sensorlist2:
		if Sensorlist2[0] not in sensors:
			Sensorlist2=[]
			saveit=True
	if saveit:	
		saveselsensors(Sensorlist1, Sensorlist2)
		savesetting()
	

def getactivesensor():
	Sensorlist=[]
	Sensorlist2=[]
	if WTdata:
		Sensorlist=WTdata.get("OFFtoON",[])
		Sensorlist2=WTdata.get("ONtoOFF",[])	
	return Sensorlist, Sensorlist2
	
def getselduration():
	selduration="360"
	if WTdata:
		selduration=WTdata.get("durationmin","360")
	return selduration
	
def getselcondition():
	selcondition="AND"
	if WTdata:
		selcondition=WTdata.get("condition","AND")
	return selcondition


def readfromfile():
	global WTdata
	WTdata=filestoragemod.readfiledata_full(DATAFILENAME)
	if not WTdata:
		print("problem reading the file WTSensor.txt" )
		WTdata={}

def saveselsensors(itemlist,itemlist2 ):
	WTdata["OFFtoON"]=itemlist
	WTdata["ONtoOFF"]=itemlist2

def saveselduration(itemlist):
	WTdata["durationmin"]=itemlist

def saveselcondition(itemlist):
	WTdata["condition"]=itemlist
	
def savesetting():
	filestoragemod.savefiledata_full(DATAFILENAME,WTdata)


def getelementlist():
	recordkey=hardwaremod.HW_INFO_IOTYPE
	recordvalue="output"	
	keytosearch=hardwaremod.HW_INFO_NAME
	datalist=hardwaremod.searchdatalist(recordkey,recordvalue,keytosearch)	
	excludewatercontrol=True
	if not excludewatercontrol:
		recordkey=hardwaremod.HW_FUNC_USEDFOR
		recordvalue="watercontrol"
		keytosearch=hardwaremod.HW_INFO_NAME
		removelist=hardwaremod.searchdatalist(recordkey,recordvalue,keytosearch)
		for element in removelist:
			datalist.remove(element)
	
	#print "elementlist= ",datalist
	return datalist



def sensorlist():
	#tablelist=hardwaremod.searchdatalist2keys(hardwaremod.HW_INFO_IOTYPE,"input", hardwaremod.HW_CTRL_CMD, "readinputpin" ,hardwaremod.HW_INFO_NAME)
	tablelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"input",hardwaremod.HW_INFO_NAME)
	return tablelist

def sensorlisttriggertime():
	tablelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"input",hardwaremod.HW_INFO_NAME)
	timetriggerlist=[]
	for item in tablelist:
		timelist=hardwaremod.gettimedata(item)	
		theinterval=timelist[1] # minutes
		timetriggerlist.append(theinterval)
	return timetriggerlist


def gethygrosensorfromactuator(actuatorname):
	recordkey="element"
	recordvalue=actuatorname
	keytosearch="sensor"
	if searchdata(recordkey,recordvalue,"workmode")!="None":
		return searchdata(recordkey,recordvalue,keytosearch)
	else:
		return ""
	
	
	

def getrowdata(recordvalue,paramlist,index): #for parameters with array of integers
	recordkey="element"
	datalist=[]
	for ln in WTdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				for param in paramlist:
					try:					
						datalist.append(int(ln[param][index]))			
					except Exception as e:
						#print 'Failed to load value, set value to zero. Error: '+ str(e)
						datalist.append(0)							

	return datalist

def gettable(index):
	paramlist=getparamlist()
	#print "paramlist" , paramlist
	elementlist=getelementlist()
	datalist=[]
	for row in elementlist:
		rowdatalist=getrowdata(row,paramlist,index)
		datalist.append(rowdatalist)
	#print datalist
	return datalist


def replacerow(element,dicttemp):
	searchfield="element"
	searchvalue=element
	for line in WTdata:
		if searchfield in line:
			if line[searchfield]==searchvalue:
				for row in dicttemp: # modified, in this way it adds the new items is present
					line[row]=dicttemp[row]
					filestoragemod.savefiledata(DATAFILENAME,WTdata)
				return True
	return False


def changesaveWTsetting(WTname,WTparameter,WTvalue):
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	for line in WTdata:
		if line["name"]==WTname:
			line[WTparameter]=WTvalue
			saveWTsetting()
			return True
	return False

def searchdata(recordkey,recordvalue,keytosearch):
	for ln in WTdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					return ln[keytosearch]	
	return ""



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
	for ln in WTdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					datalist.append(ln[keytosearch])	
	return datalist

def getfieldvaluelist(fielditem,valuelist):
	del valuelist[:]
	for line in WTdata:
		valuelist.append(line[fielditem])

def getfieldinstringvalue(fielditem,stringtofind,valuelist):
	del valuelist[:]
	for line in WTdata:
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
	




