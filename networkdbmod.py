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

logger = logging.getLogger("hydrosys4."+__name__)

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////


global DATABASEPATH
DATABASEPATH="database"
global DATAFILENAME
DATAFILENAME="network.txt"
global DEFDATAFILENAME
DEFDATAFILENAME="" # not neded, default read from the hpstapd config file

BASICDATAFILENAME="/etc/hostapd/hostapd.conf"


	
# read data -----
data=[]
#read data from BASICDATAFILENAME file
done=filestoragemod.readfiledata_spec(BASICDATAFILENAME,data)
if done:
	print "writing default network data"
	filestoragemod.savefiledata(DATAFILENAME,data)
	logger.info('Basic network data acquired')
else:
	print "ERROR ----------------------------- not able to get network data"
	logger.error('Not able to get basic network data ---------------------')
# end read IOdata -----


	
	
def savedata(filedata):
	filestoragemod.savefiledata(DATAFILENAME,filedata)


def getIPaddress():
	recordkey="name"
	recordvalue="IPsetting"
	keytosearch="LocalIPaddress"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem

def getPORT():
	recordkey="name"
	recordvalue="IPsetting"
	keytosearch="LocalPORT"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem

def getAPSSID():
	recordkey="name"
	recordvalue="IPsetting"
	keytosearch="LocalAPSSID"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem


def changesavesetting(FTparameter,FTvalue):
	searchfield="name"
	searchvalue="IPsetting"
	isok=filestoragemod.savechange(DATAFILENAME,searchfield,searchvalue,FTparameter,FTvalue)
	if not isok:
		print "problem saving paramete"
	return isok
	
def restoredefault():
	filestoragemod.deletefile(DATAFILENAME)
	filedata=[{"name": "IPsetting", "LocalIPaddress": "192.168.0.172", "LocalPORT": "5012", "LocalAPSSID" : "Hydrosys4"}]
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



