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


global DATAFILENAME
DATAFILENAME="emailcred.txt"


# if file does not exist create file
data=[]
if not filestoragemod.readfiledata(DATAFILENAME,data): #read  setting file
	filedata=[{'name':'email', 'address':'','password':'' }]
	filestoragemod.savefiledata(DATAFILENAME,filedata)
	
def savedata(filedata):
	filestoragemod.savefiledata(DATAFILENAME,filedata)


def getelementlist():
	recordkey=hardwaremod.HW_FUNC_USEDFOR
	recordvalue="mailcontrol"
	keytosearch=hardwaremod.HW_INFO_NAME
	datalist=hardwaremod.searchdatalist(recordkey,recordvalue,keytosearch)
	print "elementlist= ",datalist
	return datalist



def getaddress():
	recordkey="name"
	recordvalue="email"
	keytosearch="address"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem

def getpassword():
	recordkey="name"
	recordvalue="email"
	keytosearch="password"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem


def changesavesetting(FTparameter,FTvalue):
	searchfield="name"
	searchvalue="email"
	isok=filestoragemod.savechange(DATAFILENAME,searchfield,searchvalue,FTparameter,FTvalue)
	if not isok:
		print "problem saving paramete"
	return isok
	
def restoredefault():
	filestoragemod.deletefile(DATAFILENAME)
	filedata=[{'name':'email', 'address':'','password':'' }]
	filestoragemod.savefiledata(DATAFILENAME,filedata)

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
	address="hello@mail.com"
	password="haha"
	changesavesetting("address",address)
	changesavesetting("password",password)
	print getaddress()
	print getpassword()



