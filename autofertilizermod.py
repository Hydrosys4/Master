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

logger = logging.getLogger("hydrosys4."+__name__)

# status array, required to check the ongoing actions within a watering cycle
elementlist= autofertilizerdbmod.getelementlist()
AUTO_data={} # dictionary of dictionary
for element in elementlist:
	AUTO_data[element]={"triggerdate":datetime.utcnow(),"tobeactivated":False, "duration":0, "alertcounter":0}
# triggerdate, datetime when the doser have been triggered to start
# tobeactivated, doser need to be activated in the next opportunity 


def isschedulermode(element):
	recordkey="element"
	recordvalue=element
	keytosearch="workmode"
	workmode=autofertilizerdbmod.searchdata(recordkey,recordvalue,keytosearch)
	if workmode=="SceduledTime":
		return True
	else:
		return False


def checkactivate(elementwater,durationwater):
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
		if not isschedulermode(element): #setup is not for scheduled time
			print " Fertilizer " ,element ," set to autowater"
			print " Check Water duration ", durationwater ,">", minwaterduration
			if durationwater>minwaterduration: # watering time above the set threshold
				print " OK Water duration "
				if AUTO_data[element]["tobeactivated"]: #if flag is ON
					print " Activate ", element
					durationfer=AUTO_data[element]["duration"]
					activatedoser(element,durationfer)
					time.sleep(durationfer) #this blocks the system (and watering activation) for n seconds ... not best practice
				else:
					print " No pending request to activate ", element
			
def activatedoser(target, duration):
	print target, " ",duration, " " , datetime.now() 
	logger.info('Doser Pulse, pulse time for ms = %s', duration)
	pulseok=hardwaremod.makepulse(target,duration)
	# salva su database
	actuatordbmod.insertdataintable(target,duration)
	# put flag down
	global AUTO_data
	AUTO_data[target]["tobeactivated"]=False
	AUTO_data[target]["duration"]=0
	AUTO_data[target]["triggerdate"]=datetime.now()


def checkworkmode(element):
	return autofertilizerdbmod.searchdata("element",element,"workmode")

def timelist(element):
	if isschedulermode(element):
		fertime=autofertilizerdbmod.searchdata("element",element,"time")
		print "fertime " , fertime
		timelist=hardwaremod.separatetimestringint(fertime)
	else:
		print "non scheduler mode "
		timelist=hardwaremod.separatetimestringint("00:20:00") # get up 0 minutes and check for doseractivation
	return timelist

if __name__ == '__main__':
	
	"""
	prova functions
	"""

	

