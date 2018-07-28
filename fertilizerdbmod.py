# -*- coding: utf-8 -*-
"""
fertilizer UI setting storage utilities
"""

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


global FTDATAFILENAME
FTDATAFILENAME="ftdata.txt"
global DEFFTDATAFILENAME
DEFFTDATAFILENAME="default/defftdata.txt"

global FTdata
FTdata=[]

# read FTdata -----
if not filestoragemod.readfiledata(FTDATAFILENAME,FTdata): #read  setting file
	#read from default file
	filestoragemod.readfiledata(DEFFTDATAFILENAME,FTdata)
	print "Fertilizer writing default calibration data"
	filestoragemod.savefiledata(FTDATAFILENAME,FTdata)
	
# end read IOdata -----



# ///////////////// --- END GLOBAL VARIABLES ------



#-- start filestorage utility--------////////////////////////////////////////////////////////////////////////////////////	

# filestoragemod.readfiledata(filename,filedata)
# filestoragemod.savefiledata(filename,filedata)
# filestoragemod.appendfiledata(filename,filedata)
# filestoragemod.savechange(filename,searchfield,searchvalue,fieldtochange,newvalue)
# filestoragemod.deletefile(filename)


def consitencycheck():
	
	# this routine align the fertilizer table elements with the Hardware available elements "name" labelled with usedfor "fertilizing"
	
	elementlist=getelementlist()
	recordkey="element"
	elementlistfile=[]
	for ln in FTdata:
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
	#print "FTdata ", FTdata
	
	# get the dictionary line with an element as reference (from default file)
	defdata=[]
	filestoragemod.readfiledata(DEFFTDATAFILENAME,defdata)
	for ln in defdata:
		if recordkey in ln:
			referenceln=dict(ln)
			break
			
			
	for tablename in tabletoadd:
		# add copying from element:"1"
		#print "adding table ", tablename
		ln=dict(referenceln)
		ln[recordkey]=tablename
		FTdata.append(ln)



		
	for tablename in tabletoremove:
		for ln in FTdata:
			if recordkey in ln:
				if ln[recordkey]==tablename:
					FTdata.remove(ln)
					
	saveFTsetting()
			
			
def replacewordandsave(oldword,newword):
	filestoragemod.replacewordandsave(FTDATAFILENAME,oldword,newword)
	filestoragemod.readfiledata(FTDATAFILENAME,FTdata)


	
def restoredefault():
	filestoragemod.deletefile(FTDATAFILENAME)
	filestoragemod.readfiledata(DEFFTDATAFILENAME,FTdata)
	consitencycheck()
	
def saveFTsetting():
	filestoragemod.savefiledata(FTDATAFILENAME,FTdata)

def getparamlist():
	recordkey="name"
	recordvalue="listparam"
	datalist=[]
	for ln in FTdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				ind=0
				for rw in ln:
					if rw!=recordkey:
						ind=ind+1
						datalist.append(ln[str(ind)])	
					
	return datalist

def getelementlist():
	recordkey=hardwaremod.HW_FUNC_USEDFOR
	recordvalue="fertilizercontrol"
	keytosearch=hardwaremod.HW_INFO_NAME
	datalist=hardwaremod.searchdatalist(recordkey,recordvalue,keytosearch)
	print "elementlist= ",datalist
	return datalist



def getrowdata(recordvalue,paramlist,index):
	recordkey="element"
	datalist=[]
	for ln in FTdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				for param in paramlist:
						datalist.append(int(ln[param][index]))					
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
	for line in FTdata:
		if searchfield in line:
			if line[searchfield]==searchvalue:
				for row in line:
					line[row]=dicttemp[row]
					filestoragemod.savefiledata(FTDATAFILENAME,FTdata)
				return True
	return False



def changesaveFTsetting(FTname,FTparameter,FTvalue):
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	for line in FTdata:
		if line["name"]==FTname:
			line[FTparameter]=FTvalue
			saveFTsetting()
			return True
	return False

def searchdata(recordkey,recordvalue,keytosearch):
	for ln in FTdata:
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
	for ln in FTdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					datalist.append(ln[keytosearch])	
	return datalist

def getfieldvaluelist(fielditem,valuelist):
	del valuelist[:]
	for line in FTdata:
		valuelist.append(line[fielditem])

def getfieldinstringvalue(fielditem,stringtofind,valuelist):
	del valuelist[:]
	for line in FTdata:
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
	




