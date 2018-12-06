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


logger = logging.getLogger("hydrosys4."+__name__)

# status array, required to check the ongoing actions 
elementlist= automationdbmod.getelementlist()
AUTO_data={} # dictionary of dictionary
for element in elementlist:
	AUTO_data[element]={"lastactiontime":datetime.now(),"actionvalue":0, "alertcounter":0, "infocounter":0, "status":"ok"}



def cyclereset(element):
	global AUTO_data
	waitingtime=hardwaremod.toint(automationdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),0)
	AUTO_data[element]={"lastactiontime":datetime.now() - timedelta(minutes=waitingtime),"status":"ok","actionvalue":0, "alertcounter":0, "infocounter":0}

def cycleresetall():
	global AUTO_data
	elementlist= automationdbmod.getelementlist()
	for element in elementlist:
		waitingtime=hardwaremod.toint(automationdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),0)
		AUTO_data[element]={"lastactiontime":datetime.now() - timedelta(minutes=waitingtime),"status":"ok","actionvalue":0, "alertcounter":0, "infocounter":0}


def automationcheck(refsensor):
	global AUTO_data
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
		print AUTO_data[element]
		# check the watering mode
		modelist=["None", "Full Auto" , "Emergency Activation" , "Alert Only"]
		workmode=checkworkmode(element)

		if workmode=="None":
			# None case
			print "No Action required, workmode set to None, element: " , element
			logger.info("No Action required, workmode set to None, element: %s " , element)
			return

		sensormaxthreshold=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"sensor_threshold")[1],0)
		sensorminthreshold=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"sensor_threshold")[0],sensormaxthreshold)
		actuatormaxthreshold=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"actuator_threshold")[1],0)
		actuatorminthreshold=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"actuator_threshold")[0],actuatormaxthreshold)

		# evaluate variables for operational period check
		now = datetime.now()
		nowtime = now.time()
		starttimeh=hardwaremod.toint(automationdbmod.searchdata("element",element,"allowedperiod")[0].split(":")[0],0)
		starttimem=hardwaremod.toint(automationdbmod.searchdata("element",element,"allowedperiod")[0].split(":")[1],0)
		endtimeh=hardwaremod.toint(automationdbmod.searchdata("element",element,"allowedperiod")[1].split(":")[0],1)
		endtimem=hardwaremod.toint(automationdbmod.searchdata("element",element,"allowedperiod")[1].split(":")[1],0)
		starttime=time(starttimeh,starttimem)
		endtime=time(endtimeh,endtimem)		
		
		# get other parameters
		maxstepnumber=hardwaremod.toint(automationdbmod.searchdata("element",element,"stepnumber"),1)
		waitingtime=hardwaremod.toint(automationdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),1)
		mailtype=automationdbmod.searchdata("element",element,"mailalerttype")
		averagesample=hardwaremod.tonumber(automationdbmod.searchdata("element",element,"averagesample"),1)
		
		# Calculated Variables
		if maxstepnumber<1:
			# not possible to proceed
			print "No Action required, maxstepnumber <1, element: " , element
			logger.info("No Action required, maxstepnumber <1, element: %s " , element)
			return
		interval=(sensormaxthreshold-sensorminthreshold)/maxstepnumber
		actuatorinterval=(actuatormaxthreshold-actuatorminthreshold)/maxstepnumber
		P=[]
		for I in range(0, maxstepnumber+1):
			P.append(actuatorminthreshold+I*actuatorinterval)
		
		
		
		
		
		# ------------------------ Automation alghoritm
		if workmode=="Full Auto":
			# check if inside the allowed time period
			print "full Auto Mode"
			logger.info('full auto mode --> %s', element)
			timeok=isNowInTimePeriod(starttime, endtime, nowtime)
			print "inside allowed time ", timeok , " starttime ", starttime , " endtime ", endtime
			if timeok:
				logger.info('inside allowed time')
				sensorvalue=sensorreading(sensor,averagesample) # average of sensor readings for a number of sample
				print "Sensor Value ", sensorvalue
				
				if sensorminthreshold<=sensormaxthreshold:
					print "Algorithm , element: " , element
					logger.info("Forward algorithm  , element: %s " , element)
				
					Inde=0
					maxs=sensorminthreshold+Inde*interval
					if sensorvalue<=maxs:
						status="belowthreshold"
						logger.info('below Minthreshold')
						value=P[Inde]
						# do relevant stuff	
						CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue)
					
					Inde=Inde+1
					for I in range(Inde, maxstepnumber):
						mins=sensorminthreshold+(I-1)*interval
						maxs=sensorminthreshold+I*interval
						if mins<sensorvalue<=maxs:
							value=P[I]					
							# do relevant stuff	
							CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue)		
					
					Inde=maxstepnumber
					mins=sensorminthreshold+(Inde-1)*interval										
					if mins<sensorvalue:
						print "INDE:",Inde
						value=P[Inde]
						# do relevant stuff	
						CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue)
					# END MAIN ALGORITHM
					
				else: # to be added case of inverse sensor condition, where the sensorminthreshold is higher than the sensormaxthreshold
					print "Reverse Algorithm , element: " , element
					logger.info("Reverse Algorithm  , element: %s " , element)						
								
					Inde=0
					maxs=sensorminthreshold+Inde*interval
					if sensorvalue>=maxs:
						status="belowthreshold"
						logger.info('Above MAXthreshold')
						value=P[Inde]
						# do relevant stuff	
						CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue)
					
					Inde=Inde+1
					for I in range(Inde, maxstepnumber):
						mins=sensorminthreshold+(I-1)*interval
						maxs=sensorminthreshold+I*interval
						if mins>sensorvalue>=maxs:
							value=P[I]					
							# do relevant stuff	
							CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue)		
					
					Inde=maxstepnumber
					mins=sensorminthreshold+(Inde-1)*interval										
					if mins>sensorvalue:
						print "INDE:",Inde
						value=P[Inde]
						# do relevant stuff	
						CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue)
					# END MAIN ALGORITHM - Reverse				
			
		elif workmode=="Emergency Activation":
			print "Emergency Activation"		
		
		elif workmode=="Alert Only":
			print "Alert Only"					
							


		# implment Critical alert message in case the sensor value is one interval more than Max_threshold

		sensorvalue=sensorreading(sensor,averagesample) # average of sensor readings for a number of sample
		if sensorminthreshold<=sensormaxthreshold:
			if sensorvalue>sensormaxthreshold+interval:
				logger.info('sensor %s exceeding limits', sensor)
				textmessage="CRITICAL: "+ sensor + " reading " + str(sensorvalue) + " exceeding threshold limits, need to check the " + element
				print textmessage
				#send alert mail notification
				if AUTO_data[element]["alertcounter"]<2:
					emailmod.sendallmail("alert", textmessage)							
					logger.error(textmessage)
					AUTO_data[element]["alertcounter"]=AUTO_data[element]["alertcounter"]+1
		else:
			if sensorvalue<sensormaxthreshold+interval:
				logger.info('sensor %s exceeding limits', sensor)
				textmessage="CRITICAL: "+ sensor + " reading " + str(sensorvalue) + " exceeding threshold limits, need to check the " + element
				print textmessage
				#send alert mail notification
				if AUTO_data[element]["alertcounter"]<2:
					emailmod.sendallmail("alert", textmessage)							
					logger.error(textmessage)
					AUTO_data[element]["alertcounter"]=AUTO_data[element]["alertcounter"]+1			

	return


def CheckActivateNotify(element,waitingtime,value,mailtype,sensor,sensorvalue):
	global AUTO_data
	# check if time between watering events is larger that the waiting time (minutes)
	print ' Previous action: ' , AUTO_data[element]["lastactiontime"] , ' Now: ', datetime.now()
	timedifference=sensordbmod.timediffinminutes(AUTO_data[element]["lastactiontime"],datetime.now())
	print 'Time interval between actions', timedifference ,'. threshold', waitingtime
	logger.info('Time interval between Actions %d threshold %d', timedifference,waitingtime)		
	if timedifference>=waitingtime: # sufficient time between actions
		print " Sufficient waiting time"
		logger.info('Sufficient waiting time')	
		# action					
		print "Implement Actuator Value ", value
		logger.info('Procedure to start actuator %s, for value = %s', element, value)		
		activateactuator(element, value)
			
		# invia mail, considered as info, not as alert
		if mailtype!="warningonly":
			textmessage="INFO: " + sensor + " value " + str(sensorvalue) + ", activating:" + element + " with Value " + str(value)
			emailmod.sendallmail("alert", textmessage)
		AUTO_data[element]["lastactiontime"]=datetime.now()
		AUTO_data[element]["actionvalue"]=value

def activateactuator(target, value):
	# check the actuator type
	actuatortype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,target,hardwaremod.HW_CTRL_CMD)
	supportedactuators=["pulse","servo","stepper"]
	# stepper motor
	if actuatortype=="stepper":
		out, isok = hardwaremod.GO_stepper_position(target,value)
		if isok:
			actuatordbmod.insertdataintable(target,value)
	
	# pulse
	if actuatortype=="pulse":
		duration=1000*hardwaremod.toint(value,0)
		# start pulse
		pulseok=hardwaremod.makepulse(target,duration)
		# salva su database
		if "Started" in pulseok:
			actuatordbmod.insertdataintable(target,duration)
		
	# servo motor 
	if actuatortype=="servo":
		out, isok = hardwaremod.servoangle(target,value,0.5)
		if isok:
			actuatordbmod.insertdataintable(target,value)


def isNowInTimePeriod(startTime, endTime, nowTime):
    if startTime < endTime:
        return nowTime >= startTime and nowTime <= endTime
    else: #Over midnight
        return nowTime >= startTime or nowTime <= endTime


def sensorreading(sensorname,samplenumber):
	quantity=0
	if samplenumber>0:
		timelist=hardwaremod.gettimedata(sensorname)	
		theinterval=timelist[1] # minutes
		MinutesOfAverage=theinterval*samplenumber+theinterval/2
		if sensorname:
			sensordata=[]		
			sensordbmod.getsensordbdatasamplesN(sensorname,sensordata,samplenumber)
			starttimecalc=datetime.now()-timedelta(minutes=MinutesOfAverage)
			quantity=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())["average"]	
	return quantity

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

	

