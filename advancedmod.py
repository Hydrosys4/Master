# -*- coding: utf-8 -*-
"""
watering UI setting storage utilities
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



DATABASEPATH="database"
DATAFILENAME="addata.txt"
DEFDATAFILENAME="default/defaddata.txt"

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

# filestoragemod.readfiledata(filename,filedata)
# filestoragemod.savefiledata(filename,filedata)
# filestoragemod.appendfiledata(filename,filedata)
# filestoragemod.savechange(filename,searchfield,searchvalue,fieldtochange,newvalue)
# filestoragemod.deletefile(filename)


		


	
def restoredefault():
	filestoragemod.deletefile(DATAFILENAME)
	filestoragemod.readfiledata(DEFDATAFILENAME,data)
	savesetting()
	
def savesetting():
	filestoragemod.savefiledata(DATAFILENAME,data)

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

def getelementlist():
	recordkey="name"
	recordvalue="listelements"
	datalist=[]
	for ln in data:
		if ln[recordkey]==recordvalue:
			ind=0
			for rw in ln:
				if rw!=recordkey:
					ind=ind+1
					datalist.append(ln[str(ind)])	
					
	return datalist

def gettableheaders():
	recordkey="name"
	recordvalue="tableheaders"
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
	




