# -*- coding: utf-8 -*-
"""
Auto watering UI setting storage utilities
"""
from __future__ import print_function

import logging
import os
import os.path
import sys
import string
from datetime import datetime,date,timedelta
import time
import filestoragemod
import hardwaremod



# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////


global WTDATAFILENAME
WTDATAFILENAME="interruptdata.txt"
global DEFWTDATAFILENAME
DEFWTDATAFILENAME="default/definterruptdata.txt"

global WTdata
WTdata=[]



# read WTdata -----
if not filestoragemod.readfiledata(WTDATAFILENAME,WTdata): #read watering setting file
	#read from default file
	filestoragemod.readfiledata(DEFWTDATAFILENAME,WTdata)
	print("Watering writing default calibration data")
	filestoragemod.savefiledata(WTDATAFILENAME,WTdata)
	
# end read IOdata -----



# ///////////////// --- END GLOBAL VARIABLES ------



#-- start filestorage utility--------////////////////////////////////////////////////////////////////////////////////////	

# filestoragemod.readfiledata(filename,filedata)
# filestoragemod.savefiledata(filename,filedata)
# filestoragemod.appendfiledata(filename,filedata)
# filestoragemod.savechange(filename,searchfield,searchvalue,fieldtochange,newvalue)
# filestoragemod.deletefile(filename)

def readfromfile():
	global WTdata
	filestoragemod.readfiledata(WTDATAFILENAME,WTdata)


def consistencycheck():
	
	# this routine align the watering table elements with the Hardware available elements "name" labelled with usedfor "watering"
	
	elementlist=getelementlist()
	recordkey="element"
	elementlistfile=[]
	for ln in WTdata:
		if recordkey in ln:
			elementlistfile.append(ln[recordkey])

	tabletoadd=[]
	for tablename1 in elementlist:
		found=False
		for tablename2 in elementlistfile:
			if tablename1==tablename2 :
				found=True
		if not(found) :
			tabletoadd.append(tablename1)
			
	tabletoremove=[]
	for tablename1 in elementlistfile:
		found=False
		for tablename2 in elementlist:
			if tablename1==tablename2 :
				found=True
		if not(found) :
			tabletoremove.append(tablename1)

	#print " ---------------------------------------------------------------------<----------------<-----------______________"
	#print "to add ", tabletoadd
	#print "to remove " , tabletoremove
	#print "WTdata ", WTdata
	
	# get the dictionary line with an element as reference (from default file)
	defWTdata=[]
	filestoragemod.readfiledata(DEFWTDATAFILENAME,defWTdata)
	for ln in defWTdata:
		if recordkey in ln:
			referenceln=dict(ln)
			break
	# copy the previous taken line and change the element parameter
	for tablename in tabletoadd: 
		# add copying from element:"1"
		#print "adding table ", tablename
		ln=dict(referenceln)
		ln[recordkey]=tablename
		WTdata.append(ln)

	# remove the dictionalry line that are not consistent with element list
	for tablename in tabletoremove:
		for ln in WTdata:
			if recordkey in ln:
				if ln[recordkey]==tablename:
					WTdata.remove(ln)
					
	saveWTsetting()


def replacewordandsave(oldword,newword):
	global WTdata
	filestoragemod.replacewordandsave(WTDATAFILENAME,oldword,newword)
	filestoragemod.readfiledata(WTDATAFILENAME,WTdata)


	
def restoredefault():
	global WTdata
	filestoragemod.deletefile(WTDATAFILENAME)
	filestoragemod.readfiledata(DEFWTDATAFILENAME,WTdata)
	#print "WT data -----------------------------------> ",  WTdata
	consistencycheck()
	
	
def saveWTsetting():
	filestoragemod.savefiledata(WTDATAFILENAME,WTdata)


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
	tablelist=hardwaremod.searchdatalist2keys(hardwaremod.HW_INFO_IOTYPE,"input", hardwaremod.HW_CTRL_CMD, "readinputpin" ,hardwaremod.HW_INFO_NAME)
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
	
	
	
def getparamlist():
	recordkey="name"
	recordvalue="listparam"
	datalist=[]
	for ln in WTdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				ind=0
				for rw in ln:
					if rw!=recordkey:
						ind=ind+1
						datalist.append(ln[str(ind)])	
					
	return datalist

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
					filestoragemod.savefiledata(WTDATAFILENAME,WTdata)
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
	




