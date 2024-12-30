from __future__ import print_function
from __future__ import division
from builtins import str
from builtins import range
from past.utils import old_div
import logging
from datetime import datetime, time ,timedelta
import hardwaremod
import os
import subprocess
import emailmod
import automationdbmod
import sensordbmod
import actuatordbmod
import autofertilizermod
import messageboxmod
import statusdataDBmod
import math
import threading
import ActuatorControllermod


logger = logging.getLogger("hydrosys4."+__name__)

# status array, required to check the ongoing actions 
elementlist= automationdbmod.getelementlist()
AUTO_data={} # dictionary of dictionary
AUTO_data["default"]={"lastactiontime":datetime.utcnow(),"actionvalue":0, "alertcounter":0, "infocounter":0, "status":"ok"}



def cyclereset(element):
	global AUTO_data
	waitingtime=hardwaremod.toint(automationdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),0)
	statusdataDBmod.write_status_data(AUTO_data,element,"lastactiontime",datetime.utcnow() - timedelta(minutes=waitingtime))
	statusdataDBmod.write_status_data(AUTO_data,element,"status","ok")
	statusdataDBmod.write_status_data(AUTO_data,element,"actionvalue",0)	
	statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)	
	statusdataDBmod.write_status_data(AUTO_data,element,"infocounter",0)

def cycleresetall():
	elementlist= automationdbmod.getelementlist()
	for element in elementlist:
		waitingtime=hardwaremod.toint(automationdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),0)
		#print("Cycle reset all ------------------------------------_>", waitingtime , "   ", element)
		cyclereset(element)

def automationcheck(refsensor):
	logger.info('Starting Automation Evaluation, Sensor: %s' , refsensor)
	# iterate among the actuators
	elementlist= automationdbmod.getelementlist()	
	for element in elementlist: 
		automationexecute(refsensor,element)
	return	
		
		
def automationexecute(refsensor,element):		
	sensor=automationdbmod.searchdata("element",element,"sensor")
	# check the sensor
	if refsensor==sensor:		
		logger.info('automation Pairing OK ---> Actuator: %s , Sensor: %s', element, sensor)
		# check the watering mode
		modelist=["None", "Full Auto" , "Emergency Activation" , "Alert Only"]
		workmode=checkworkmode(element)

		if (workmode=="None"):
			# None case
			print("No Action required, workmode set to None, element: " , element)
			# logger.info("No Action required, workmode set to None, element: %s " , element)
			return

		if (workmode==""):
			logger.info("Not able to get the workmode: %s " , element)
			return

		logger.info('Automantion, Get all the parameters')
		sensormaxthreshold=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"sensor_threshold")[1],0)
		sensorminthreshold=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"sensor_threshold")[0],sensormaxthreshold)
		actuatormaxthreshold=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"actuator_threshold")[1],0)
		actuatorminthreshold=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"actuator_threshold")[0],actuatormaxthreshold)

		# evaluate variables for operational period check	
		
		starttime = datetime.strptime(automationdbmod.searchdata("element",element,"allowedperiod")[0], '%H:%M').time()
		endtime = datetime.strptime(automationdbmod.searchdata("element",element,"allowedperiod")[1], '%H:%M').time()	
		
		# get other parameters
		maxstepnumber=hardwaremod.toint(automationdbmod.searchdata("element",element,"stepnumber"),1)
		waitingtime=hardwaremod.toint(automationdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),1)
		mailtype=automationdbmod.searchdata("element",element,"mailalerttype")
		averageminutes=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"averagesample"),1)
		mathoperation=automationdbmod.searchdata("element",element,"mathoperation")
		
		# new parameter for the activationdelay
		activationdelay=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"activationdelay"),0)		

		# check sensor timetrigger
		sensorcontrolcommand=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,refsensor,hardwaremod.HW_CTRL_CMD)
		logger.info('Sensor control command: %s , Sensor: %s', sensorcontrolcommand, sensor)
		if sensorcontrolcommand=="returnzero":
			logger.info('Modify parameter for the timetrigger')			
			#adjust the parameters in the way the activation condition is always obtained
			sensormaxthreshold=1
			sensorminthreshold=-1
			maxstepnumber=1
			averageminutes=0

		
		# Calculated Variables
		if maxstepnumber<1:
			# not possible to proceed
			print("No Action required, maxstepnumber <1, element: " , element)
			logger.info("No Action required, maxstepnumber <1, element: %s " , element)
			return
		interval=(sensormaxthreshold-sensorminthreshold)/maxstepnumber
		actuatorinterval=(actuatormaxthreshold-actuatorminthreshold)/maxstepnumber
		P=[]
		for I in range(0, maxstepnumber+1):		# I goes from 0 to maxstepnumber (tihs is how range works) 
			P.append(int(actuatorminthreshold+I*actuatorinterval))
		
		
		
		
		# ------------------------ Automation alghoritm
		if workmode=="Full Auto":
			# check if inside the allowed time period
			print("full Auto Mode")
			logger.info('full auto mode --> %s', element)
			timeok=isNowInTimePeriod(starttime, endtime, datetime.now().time())  # don't use UTC here!
			print("inside allowed time ", timeok , " starttime ", starttime , " endtime ", endtime)
			if timeok:
				logger.info('inside allowed time')
				isok,sensorvalue=sensorreading(sensor,averageminutes,mathoperation) # operation of sensor readings for a number of sample
				if isok:
					print("Sensor Value ", sensorvalue)
					
					if sensorminthreshold<=sensormaxthreshold:
						print("Algorithm , element: " , element)
						logger.info("Forward algorithm  , element: %s " , element)
						
					else: # to be added case of inverse sensor condition, where the sensorminthreshold is higher than the sensormaxthreshold
						print("Reverse Algorithm , element: " , element)
						logger.info("Reverse Algorithm  , element: %s " , element)						

					Inde=math.ceil((sensorvalue-sensorminthreshold)/interval)						
						
						
					if Inde<0:
						status="belowthreshold"
						logger.info('under left threshold')
						Inde=0
					if Inde>maxstepnumber:
						logger.info('beyond right threshold')
						Inde=maxstepnumber
					value=P[Inde]

					# END MAIN ALGORITHM
					logger.info('Activation phase Value=%d',value)
								
					# do relevant stuff	with delay
					argvect=[element,waitingtime,value,mailtype,sensor,sensorvalue]
					t = threading.Timer(activationdelay, CheckActivateNotify, argvect).start()
					#CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue)	
					
					
										
				else:
					logger.error('No valid calculation operation on the stored sensor data')
			else:
				logger.info('Outside allowed Time, Stop')
				
		elif workmode=="Emergency Activation":
			print("Emergency Activation")		
		
		elif workmode=="Alert Only":
			print("Alert Only")					
							


		# implment Critical alert message in case the sensor value is one interval more than Max_threshold

		isok,sensorvalue=sensorreading(sensor,averageminutes,mathoperation) # operation of sensor readings for a number of sample
		if isok:
			if sensorminthreshold<=sensormaxthreshold:
				if sensorvalue>sensormaxthreshold+interval:
					logger.info('sensor %s exceeding limits', sensor)
					textmessage="CRITICAL: "+ sensor + " reading " + str(sensorvalue) + " exceeding threshold limits, need to check the " + element
					print(textmessage)
					#send alert mail notification
					alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
					if alertcounter<2:
						if (mailtype!="none"):
							emailmod.sendallmail("alert", textmessage)

						# Create notification message
						dictitem={'title': "Automation Message (Critical)", 'content': textmessage, 'color': "red" }
						messageboxmod.SaveMessage(dictitem)

						logger.error(textmessage)
						statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)

			else:
				if sensorvalue<sensormaxthreshold+interval:
					logger.info('sensor %s exceeding limits', sensor)
					textmessage="CRITICAL: "+ sensor + " reading " + str(sensorvalue) + " exceeding threshold limits, need to check the " + element
					print(textmessage)
					#send alert mail notification
					alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
					if alertcounter<2:
						if (mailtype!="none"):
							emailmod.sendallmail("alert", textmessage)

						# Create notification message
						dictitem={'title': "Automation Message (Critical)", 'content': textmessage, 'color': "red" }
						messageboxmod.SaveMessage(dictitem)

						logger.error(textmessage)
						statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)

	return


def CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue):
	global AUTO_data
	# check if time between watering events is larger than the waiting time (minutes)
	lastactiontime=statusdataDBmod.read_status_data(AUTO_data,element,"lastactiontime")
	print(' Previous action: ' , lastactiontime , ' Now: ', datetime.utcnow())
	timedifference=sensordbmod.timediffinminutes(lastactiontime,datetime.utcnow())
	print('Time interval between actions', timedifference ,'. threshold', waitingtime)
	logger.info('Time interval between Actions %d threshold %d', timedifference,waitingtime)

	if timedifference>=waitingtime: # sufficient time between actions
		print(" Sufficient waiting time")
		logger.info('Sufficient waiting time')
		# action
		print("Implement Actuator Value ", value)
		logger.info('Procedure to start actuator %s, for value = %s', element, value)
		msg , isok=activateactuator(element, value)

		textmessage="INFO: " + sensor + " value " + str(sensorvalue) + ", activating:" + element + " with Value " + str(value)

		# invia mail, considered as info, not as alert
		if ( mailtype!="warningonly" ) and ( mailtype!="none" ):
			emailmod.sendallmail("alert", textmessage)

		# Create notification message
		dictitem={'title': "Automation Message (Info)", 'content': textmessage, 'color': "primary" }
		messageboxmod.SaveMessage(dictitem)

		if isok:
			statusdataDBmod.write_status_data(AUTO_data,element,"lastactiontime",datetime.utcnow())
			statusdataDBmod.write_status_data(AUTO_data,element,"actionvalue",value)

	else:
		logger.info('Need to wait more time')


def activateactuator(target, value):  # return true in case the state change: activation is >0 or a different position from prevoius position.
	return ActuatorControllermod.activateactuator(target,value)


def isNowInTimePeriod(startTime, endTime, nowTime):
	print(startTime," ",  endTime," " ,  nowTime)
	if startTime < endTime:
		return nowTime >= startTime and nowTime <= endTime
	else: #Over midnight
		return nowTime >= startTime or nowTime <= endTime


def sensorreading(sensorname,MinutesOfAverage,operation):
	isok=False	
	# operation "average", "min" , "max" , "sum"
	if sensorname:
		timelist=hardwaremod.gettimedata(sensorname)	
		theinterval=timelist[1] # minutes
		if theinterval>0:
			samplesnumber=int(old_div(MinutesOfAverage,theinterval)+1)
		else:
			samplesnumber=1
			theinterval=15
		quantity=0
		MinutesOfAverage=samplesnumber*theinterval
		if samplesnumber>0:
			sensordata=[]		
			sensordbmod.getsensordbdatasamplesN(sensorname,sensordata,samplesnumber)
			datenow=datetime.now() # dont put UTC here !!!
			starttimecalc=datenow-timedelta(minutes=(MinutesOfAverage+theinterval)) #if Minutes of average is zero, it allows to have at least one sample
			isok, quantitylist=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datenow)
			quantity=quantitylist[operation]
			# sensor reading value
			logger.info('Sensor reading <%s>=<%s>',sensorname,str(quantity))
			print("sensor Reading ", sensorname, "=" , quantity)	
	return isok , quantity



def lastsensorreading(sensorname):
	if sensorname:
		sensordata=[]		
		sensordbmod.getsensordbdata(sensorname,sensordata)
		data=sensordata[-1]
		try:
			number=float(data[1])
		except:
			number=0
	return 	number	
	
			

def checkworkmode(element):
	return automationdbmod.searchdata("element",element,"workmode")





if __name__ == '__main__':
	
	"""
	prova functions
	"""

	

