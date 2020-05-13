# -*- coding: utf-8 -*-
"""
file storage utility
"""
from __future__ import print_function
from builtins import range
import basicSetting
import logging
import os
import os.path
import shutil
import string
from datetime import datetime,date,timedelta
import json

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

global DATABASEPATH
DATABASEPATH=basicSetting.data["DATABASEPATH"]

# ///////////////// --- END GLOBAL VARIABLES ------







#-- start DB utility--------////////////////////////////////////////////////////////////////////////////////////	
def dbpath(filename):
	return os.path.join(DATABASEPATH, filename)	

def readfiledata(filename,filedata): 
	if os.path.isfile(dbpath(filename)): #file is there
		# read the selected table file
		in_file = open(dbpath(filename),"r")
		lines = in_file.readlines()
		in_file.close()
		del filedata[:]
		#print " ln " , lines
		for ln in lines:
			filedata.append(json.loads(ln))
		#print IOdata[0]["name"]
		return True
	else:
		print("----------------------------------------------------------------------> warning no file ", filename) 
		return False


def readfiledata_full(filename): 
	if os.path.isfile(dbpath(filename)): #file is there
		# read the selected table file	
		#in_file = open(dbpath(filename),"r")
		with open(dbpath(filename)) as json_file:
			try:
				data = json.load(json_file)
			except:
				print("not able to parse Json file")
				return False
		json_file.close()
		return data
	else:
		print("----------------------------------------------------------------------> warning no file ", filename) 
		return False
		


def savefiledata_full(filename,filedata):
# questo possibile lista di dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	out_file = open(dbpath(filename),"w")
	jsonStr=json.dumps(filedata, sort_keys=True, indent=4)
	out_file.write(jsonStr)
	out_file.close()



# START Plain text file functions ---------------------------------------- Used for generic file manipulation


def readfiledata_plaintext(pathfilename,filedata): #return list with row of the file
	if os.path.isfile(pathfilename): #file is there
		# read the selected table file
		in_file = open(pathfilename,"r")
		lines = in_file.readlines()
		in_file.close()
		del filedata[:]
		for ln in lines:
			filedata.append(ln.strip("\n"))
		return True
	else:
		print("-----------------------------------------> warning no file ", pathfilename) 
		return False

def savefiledata_plaintext(pathfilename,filedata):
	#print "save file ", filedata
	out_file = open(pathfilename,"w")
	for line in filedata:
		out_file.write(line)
		out_file.write("\n")
	out_file.close()

def readfiledata_spec(pathfilename,identifier,filedata): # used also in networkdbmod
	if os.path.isfile(pathfilename): #file is there
		# read the selected table file
		in_file = open(pathfilename,"r")
		lines = in_file.readlines()
		in_file.close()
		del filedata[:]
		#print " ln " , lines
		for ln in lines:
			if identifier in ln:
				theline=ln[ln.find("{"):ln.find("}")+1]
				filedata.append(json.loads(theline))
				return True
		#print IOdata[0]["name"]
		return False
	else:
		print("------------------------------------------> warning no file ", pathfilename) 
		return False
		

def savechangerow_plaintext(pathfilename,searchvalue,newrow): # used to replace row in file giving one string
	filedata=[]
	readfiledata_plaintext(pathfilename,filedata)
	#print "text File /n" , filedata
	for i in range(len(filedata)):
		line=filedata[i]
		if searchvalue in line:
			print(" row found ------------ !!!!!!!!! " , line)
			filedata[i]=newrow
			print(" new row  ------------ !!!!!!!!! " , newrow)
			savefiledata_plaintext(pathfilename,filedata)
			return True
	return False


def readvalue_plaintext(pathfilename,key,separation): # used to get data from text file
	#format of the row "key:value"
	filedata=[]
	readfiledata_plaintext(pathfilename,filedata)
	for line in filedata:
		if key in line:
			substr=line.split(separation)
			if len(substr)>1:
				value=substr[1].strip()
				return value
	return False


# END Plain text file functions ---------------------------------------- Used for generic file manipulation

def disct2text(dictdata):
	return json.dumps(dictdata, sort_keys=True)


def savefiledata(filename,filedata):
# questo possibile lista di dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	out_file = open(dbpath(filename),"w")
	for line in filedata:
		#jsonStr=json.dumps(line, sort_keys=True, indent=14)
		jsonStr=json.dumps(line, sort_keys=True)
		out_file.write(jsonStr)
		out_file.write("\n")
	out_file.close()

def appendfiledata(filename,filedata):
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	out_file = open(dbpath(filename),"a")
	for line in filedata:
		jsonStr=json.dumps(line)
		out_file.write(jsonStr)
		out_file.write("\n")
	out_file.close()
	
def savechange(filename,searchfield,searchvalue,fieldtochange,newvalue):
	filedata=[]
	readfiledata(filename,filedata)
	# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	for line in filedata:
		if searchfield in line:
			if line[searchfield]==searchvalue:
				line[fieldtochange]=newvalue
				savefiledata(filename,filedata)
				return True
	return False



def replacewordandsave(filename,oldvalue,newvalue): #oldvalue and newvalue are lists
	filedata=[]
	readfiledata(filename,filedata)
	# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario

	for line in filedata:
		for key in line:
			for i in range(len(newvalue)): #iterate in the lists
				if newvalue[i]!=oldvalue[i]:					
					if line[key]==oldvalue[i]:
						line[key]=newvalue[i]

	savefiledata(filename,filedata)
	return True


	
def deletefile(filename):
	try:
		os.remove(dbpath(filename))
		return True
	except OSError:
		return False

def copydbfileto(filename,dst):
	try:
		copyfile(dbpath(filename), dst)
		return True
	except OSError:
		return False
	
# utility functions --------------------------------------
	
def searchdata(filename,recordkey,recordvalue,keytosearch):
	IOdata=[]
	readfiledata(filename,IOdata)
	for ln in IOdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					return ln[keytosearch]	
	return ""


def searchdatalist(filename,recordkey,recordvalue,keytosearch):
	IOdata=[]
	readfiledata(filename,IOdata)
	datalist=[]
	for ln in IOdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					datalist.append(ln[keytosearch])	
	return datalist



def getfieldinstringvalue(filename,fielditem,stringtofind,valuelist):
	IOdata=[]
	readfiledata(filename,IOdata)
	del valuelist[:]
	for line in IOdata:
		name=line[fielditem]
		if name.find(stringtofind)>-1:
			valuelist.append(name)	
	
	
	
#--end --------////////////////////////////////////////////////////////////////////////////////////		
	
	
if __name__ == '__main__':

	FILENAME='dummy.txt'
	data=[
	{"lastupdate": "", "name": "ECsensor1", "pin": 7, "m": 1.0, "controllercmd": "", "q": 0.0, "IOtype": "di"},
	{"lastupdate": "", "name": "ECsensor1enable", "pin": 4, "m": 1.0, "controllercmd": "", "q": 0.0, "IOtype": "do"},
	{"lastupdate": "", "name": "PHsensor1", "pin": 0, "m": 1.0, "controllercmd": "5", "q": 0.0, "IOtype": "ai"}
	]
	savefiledata(FILENAME,data)
	savechange(FILENAME,"name","ECsensor1","q",2.0)
	filedata=[]
	readfiledata(FILENAME,filedata)
	print(filedata)





