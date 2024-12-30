# -*- coding: utf-8 -*-
"""
fertilizer UI setting storage utilities
"""
from __future__ import print_function

import logging
import os
import os.path
import sys
import string
from datetime import datetime,date,timedelta
import time
import hashlib
import filestoragemod
import hardwaremod



# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////


global DATAFILENAME
DATAFILENAME="logincred.txt"


# if file does not exist create file
data=[]
if not filestoragemod.readfiledata(DATAFILENAME,data): #read  setting file
	restoredefault()
	
def restoredefault():
	filestoragemod.deletefile(DATAFILENAME)
	m = hashlib.sha256()
	m.update(b"default")
	hashedpw = m.hexdigest()
	filedata=[{'name':'login', 'username':'admin', 'password':hashedpw }]
	#iledata=[{'name':'login', 'username':'admin','password':'default' }]
	filestoragemod.savefiledata(DATAFILENAME,filedata)
	
def savedata(filedata):
	filestoragemod.savefiledata(DATAFILENAME,filedata)

def getusername():
	recordkey="name"
	recordvalue="login"
	keytosearch="username"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem

def getpassword():
	recordkey="name"
	recordvalue="login"
	keytosearch="password"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem

def changesavesetting(FTparameter,FTvalue):
	searchfield="name"
	searchvalue="login"
	isok=filestoragemod.savechange(DATAFILENAME,searchfield,searchvalue,FTparameter,FTvalue)
	if not isok:
		print("problem saving parameter")
	return isok

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
	print("Hello there ")
