# -*- coding: utf-8 -*-
"""
selected plan utility
"""

import logging
import os
import os.path
import string
from datetime import datetime,date,timedelta
import time
import filestoragemod
import plandbmod
import sensordbmod
import actuatordbmod
import hardwaremod
import SchedulerMod
import wateringdbmod
import advancedmod
import databasemod




def separatetimestringintdict(timestr):
	outdict={}
	timelist=timestr.split(":")
	paramlist=["hour", "minute", "second"]
	for i in range(3):
		if i<len(timelist):
			outdict[paramlist[i]]=int(timelist[i])
		else:
			outdict[paramlist[i]]=0
	return outdict

def separatetimestringint(timestr):
	outlist=[]
	timelist=timestr.split(":")
	for i in range(3):
		if i<len(timelist):
			if timelist[i]!="":
				outlist.append(int(timelist[i]))
			else:
				outlist.append(0)	
		else:
			outlist.append(0)
	return outlist
	
def removepastdata():
	#----------------
	pastdays=2

	sensordbmod.RemoveSensorDataPeriod(pastdays)
	actuatordbmod.RemoveActuatorDataPeriod(pastdays)

	
if __name__ == '__main__':
	
	#timestr="1:2:3"
	#timelist=separatetimestringint(timestr)
	#print timelist
	#todaydate=date(datetime.now().year, datetime.now().month, datetime.now().day)
	#print date.today()
	#for i in range(1,3):
	#	print i

	print actuatordbmod.gettablenameapprox("temp")

			
