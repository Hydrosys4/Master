# -*- coding: utf-8 -*-
"""
fertilizer UI setting storage utilities
"""
from __future__ import print_function

#import logging
import os
import os.path
import sys
import string
from datetime import datetime,date,timedelta
import time
import filestoragemod




# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////


global DATAFILENAME
DATAFILENAME="clocktimezone.txt"


# if file does not exist create file
data=[]
if not filestoragemod.readfiledata(DATAFILENAME,data): #read  setting file
	filedata=[{'name':'clock', 'timezone':'UTC'}]
	filestoragemod.savefiledata(DATAFILENAME,filedata)
	
def savedata(filedata):
	filestoragemod.savefiledata(DATAFILENAME,filedata)



def gettimezone():
	recordkey="name"
	recordvalue="clock"
	keytosearch="timezone"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem

def changesavesetting(FTparameter,FTvalue):
	searchfield="name"
	searchvalue="clock"
	isok=filestoragemod.savechange(DATAFILENAME,searchfield,searchvalue,FTparameter,FTvalue)
	if not isok:
		print("problem saving parameter")
	return isok
	
def restoredefault():
	filestoragemod.deletefile(DATAFILENAME)
	filedata=[{'name':'clock', 'timezone':'UTC'}]
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
	timezone="Europe/Rome"

	changesavesetting("timezone",timezone)

	print(gettimezone())




