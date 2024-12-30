from __future__ import print_function
import logging
from datetime import datetime, date ,timedelta
import time
import hardwaremod
import os
import subprocess
import emailmod
import autofertilizerdbmod
import sensordbmod
import actuatordbmod
import fertilizerdbmod
import statusdataDBmod
import ActuatorControllermod

logger = logging.getLogger("hydrosys4."+__name__)

# status array, required to check the ongoing actions within a watering cycle
elementlist= autofertilizerdbmod.getelementlist()
AUTO_data={} # dictionary of dictionary
#for element in elementlist:
#	AUTO_data[element]={"triggerdate":datetime.utcnow(),"tobeactivated":False, "duration":0, "alertcounter":0}
AUTO_data["default"]={"triggerdate":datetime.utcnow(),"tobeactivated":False, "duration":0, "alertcounter":0}
# triggerdate, datetime when the doser have been triggered to start
# tobeactivated, doser need to be activated in the next opportunity 

def getworkmode(element):
	recordkey="element"
	recordvalue=element
	keytosearch="workmode"
	workmode=autofertilizerdbmod.searchdata(recordkey,recordvalue,keytosearch)
	return workmode

def checkactivate(elementwater,durationwater):  # requires integer input
	result = False
	elementlist=fertilizerdbmod.getelementlist()
	waterok=False

	for doserelement in elementlist: # provided the waterelement, search for corresponding doserelement 
		linkedwaterelement=autofertilizerdbmod.searchdata("element",doserelement,"waterZone")
		if linkedwaterelement==elementwater:
			waterok=True
			element=doserelement
			break

	if waterok: # there is a corresponding doser element
		minwaterduration=hardwaremod.toint(autofertilizerdbmod.searchdata("element",element,"minactivationsec"),0)
		workmode = getworkmode(element)
		if workmode == "BeforeWatering": #setup is not for scheduled time
			print(" Fertilizer " ,element ," set to autowater")
			print(" Check Water duration ", durationwater ,">", minwaterduration)
			if durationwater>minwaterduration: # watering time above the set threshold
				print(" OK Water duration ")
				if statusdataDBmod.read_status_data(AUTO_data,element,"tobeactivated"): #if flag is ON
					print(" Activate ", element)
					durationfer=statusdataDBmod.read_status_data(AUTO_data,element,"duration")
					activatedoser(element,durationfer)
					time.sleep(durationfer) #this blocks the system (and watering activation) for n seconds ... not best practice
					result = True
				else:
					print(" No pending request to activate ", element)

	return result

def activatedoser(element, duration):
	print(element, " ",duration, " " , datetime.now())
	logger.info('Doser Pulse, pulse time for ms = %s', duration)
	msg, pulseok = ActuatorControllermod.activateactuator(element,duration)
	# msg , pulseok=hardwaremod.makepulse(element,duration)

	# salva su database
	actuatordbmod.insertdataintable(element,duration)
	# put flag down
	global AUTO_data
	statusdataDBmod.write_status_data(AUTO_data,element,"tobeactivated",False)
	statusdataDBmod.write_status_data(AUTO_data,element,"duration",0)
	statusdataDBmod.write_status_data(AUTO_data,element,"triggerdate",datetime.now())

def setActivationDurationDate(element,tobeactivated,duration,triggerdate):
	global AUTO_data
	statusdataDBmod.write_status_data(AUTO_data,element,"tobeactivated",tobeactivated) #true or false
	statusdataDBmod.write_status_data(AUTO_data,element,"duration",duration)
	statusdataDBmod.write_status_data(AUTO_data,element,"triggerdate",triggerdate)


def checkworkmode(element):
	return autofertilizerdbmod.searchdata("element",element,"workmode")

def timelist(element):
	workmode = getworkmode(element)
	if workmode == "ScheduledTime":
		fertime=autofertilizerdbmod.searchdata("element",element,"time")
		print("fertime " , fertime)
		timelist=hardwaremod.separatetimestringint(fertime)
	elif workmode == "BeforeWatering":
		print("non scheduler mode ")
		timelist=hardwaremod.separatetimestringint("00:20:00") # get up 0 minutes and check for doseractivation
	else:
		print("Fertilizer is disabled")

	return timelist

if __name__ == '__main__':
	
	"""
	prova functions
	"""

	

