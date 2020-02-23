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



global DATAFILENAME
DATAFILENAME="network.txt"
global DEFDATAFILENAME
DEFDATAFILENAME="" # not neded, default read from the hpstapd config file

BASICDATAFILENAME="/etc/hostapd/hostapd.conf"
MESSAGEFILENAME="database/networkmessage.txt"


	
# read data -----
data=[]
#read data from BASICDATAFILENAME file
done=filestoragemod.readfiledata_spec(BASICDATAFILENAME,"# HERE->",data)
if done:
	print "writing default network data"
	filestoragemod.savefiledata(DATAFILENAME,data)
	logger.info('Basic network data acquired')
else:
	print "ERROR ----------------------------- not able to get network data"
	logger.error('Not able to get basic network data ---------------------')
# end read IOdata -----



# START part relevant to Message file

def getstoredmessage():
	filedata=[]
	isok=filestoragemod.readfiledata_plaintext(MESSAGEFILENAME,filedata)
	outstring=""
	for line in filedata:
		outstring=outstring+line+'\n'
	return outstring

	
def storemessage(message):
	messagelist=[]
	messagelist.append(message)
	filestoragemod.savefiledata_plaintext(MESSAGEFILENAME,messagelist)


# END part relevant to Message file


	
def savedata(filedata):
	filestoragemod.savefiledata(DATAFILENAME,filedata)

def readdata(filedata):
	filestoragemod.readfiledata(DATAFILENAME,filedata)



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

def getWAITTOCONNECT():
	recordkey="name"
	recordvalue="IPsetting"
	keytosearch="APtime"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem
	
def getCUSTOMURL():
	recordkey="name"
	recordvalue="IPsetting"
	keytosearch="customURL"
	dataitem=filestoragemod.searchdata(DATAFILENAME,recordkey,recordvalue,keytosearch)
	return dataitem
	
	
def changesavesetting(FTparameter,FTvalue):
	searchfield="name"
	searchvalue="IPsetting"
	isok=filestoragemod.savechange(DATAFILENAME,searchfield,searchvalue,FTparameter,FTvalue)
	if not isok:
		print "problem saving parameters"
	return isok



	
def restoredefault():
	filestoragemod.deletefile(DATAFILENAME)
	filedata=[{"name": "IPsetting", "LocalIPaddress": "192.168.1.172", "LocalPORT": "5172", "LocalAPSSID" : "Hydrosys4", "APtime" : "180"}]
	filestoragemod.savefiledata(DATAFILENAME,filedata)


	
#--end --------////////////////////////////////////////////////////////////////////////////////////		
	
	
if __name__ == '__main__':
	# comment
	address="hello@mail.com"
	password="haha"
	#changesavesetting("address",address)
	#changesavesetting("password",password)
	#print getaddress()
	#print getpassword()
	
	message="hello"
	storemessage(message)
	getstoredmessage()




