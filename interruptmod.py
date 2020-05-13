from __future__ import print_function
from __future__ import division
from builtins import str
from past.utils import old_div
import logging
from datetime import datetime , time ,timedelta
import _strptime
import hardwaremod
import os
import subprocess
import emailmod
import interruptdbmod
import sensordbmod
import actuatordbmod
import autofertilizermod
import statusdataDBmod
import threading
import time as t




ACTIONPRIORITYLEVEL=5
NONBLOCKINGPRIORITY=0
SAVEBLOCKINGBUSY=False
SAVEBLOCKINGDIFFBUSY=False

NOWTIMELIST=[]

#In hardware, an internal 10K resistor between the input channel and 3.3V (pull-up) or 0V (pull-down) is commonly used. 
#https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/

logger = logging.getLogger("hydrosys4."+__name__)

# status array, required to check the ongoing actions 
elementlist= interruptdbmod.getelementlist()
waitingtime=1200

# ///////////////// -- STATUS VARIABLES  --  ///////////////////////////////

AUTO_data={} # dictionary of dictionary
AUTO_data["default"]={"lasteventtime":datetime.utcnow()- timedelta(minutes=waitingtime),"lastinterrupttime":datetime.utcnow(),"validinterruptcount":0,"eventactivated":False,"lastactiontime":datetime.utcnow()- timedelta(minutes=waitingtime),"actionvalue":0, "alertcounter":0, "infocounter":0, "status":"ok" , "threadID":None , "blockingstate":False}

SENSOR_data={} # used for the associated sensor in a separate hardwareSetting Row 
SENSOR_data["default"]={"Startcounttime":datetime.utcnow(),"InterruptCount":0}

PIN_attributes={}  # to speed up the operation during interurpt
PIN_attributes["default"]={"logic":"pos","refsensor":"","bouncetimeSec":0.001}

BLOCKING_data={}  # to speed up the operation during interurpt
BLOCKING_data["default"]={"BlockingNumbers":0,"BlockingNumbersThreadID":None}



def readstatus(element,item):
	return statusdataDBmod.read_status_data(AUTO_data,element,item)
	
def savedata(sensorname,sensorvalue):
	sensorvalue_str=str(sensorvalue)
	sensorvalue_norm=hardwaremod.normalizesensordata(sensorvalue_str,sensorname)
	sensordbmod.insertdataintable(sensorname,sensorvalue_norm)
	return	

def eventcallback(PIN):
	bouncetimeSec=statusdataDBmod.read_status_data(PIN_attributes,PIN,"bouncetimeSec")
	t.sleep(bouncetimeSec)
	reading=hardwaremod.readinputpin(PIN)
	refsensor=statusdataDBmod.read_status_data(PIN_attributes,PIN,"refsensor")
	logic=statusdataDBmod.read_status_data(PIN_attributes,PIN,"logic")
	#print "reference sensor:" , refsensor, "logic ", logic 
	#print PIN_attributes
	
	# first Edge detection, can have two impleemntations depend on the "logic" setting
	# in case logic=pos we have pull-down resistor, so the normal state is LOW, the first edge will be from LOW to HIGH
	# in case logic<>pos we have pull-up resistor, so the normal state is High, the first edge will be from HIGH to LOW
	if refsensor!="":
		#["First Edge" , "First Edge + Level", "Second Edge" , "Second Edge + Level (inv)", "both Edges"]
		
		#print "Logic " , logic , " reading ", reading , " bouncetimeSec " , bouncetimeSec
		#detecting first edge
		if logic=="pos":
			if reading=="1":      
				#print "*************************  First edge detected on PIN:", PIN  
				mode="First Edge"
			elif reading=="0":      
				#print "*************************  Second edge detected on PIN:", PIN  
				mode="Second Edge"
		else:
			if reading=="0":
				#print "*************************  First edge detected on PIN:", PIN  
				mode="First Edge"
			elif reading=="1":
				#print "*************************  Second edge detected on PIN:", PIN  
				mode="Second Edge"
		
		#print "interrupt --------------------> ", mode
		
		interruptcheck(refsensor,mode,PIN)		
		
	# update status variables for the frequency sensor ----
	sensorinterruptcount=statusdataDBmod.read_status_data(SENSOR_data,PIN,"InterruptCount")	
	sensorinterruptcount=sensorinterruptcount+1
	statusdataDBmod.write_status_data(SENSOR_data,PIN,"InterruptCount",sensorinterruptcount)
	
	#if refsensor!="":
	#	x = threading.Thread(target=savedata, args=(refsensor,reading))
	#	x.start()


def setinterruptevents():
	
	hardwaremod.removeallinterruptevents()
	
	print("load interrupt list ")
	interruptlist=interruptdbmod.sensorlist()
	print("len interrupt list "	, len(interruptlist))	
	for item in interruptlist:
		print("got into the loop ")
		# get PIN number

		recordkey=hardwaremod.HW_INFO_NAME
		recordvalue=item
		keytosearch=hardwaremod.HW_CTRL_PIN
		PINstr=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)
		print("set event for the PIN ", PINstr)		
		if not PINstr=="":	

			keytosearch=hardwaremod.HW_CTRL_LOGIC
			logic=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)
			# set Sw pull up / down mode
		
			if logic=="pos":
				hardwaremod.GPIO_setup(PINstr, "in", "pull_down")
				evenslopetype="both"
			else:
				hardwaremod.GPIO_setup(PINstr, "in" , "pull_up")
				evenslopetype="both"

			#GPIO.RISING, GPIO.FALLING or GPIO.BOTH.
			# link to the callback function
			
			# the bouncetime is set by the frequency parameter, if this parameter is empty, the default bouncetime would be 200
			
			keytosearch=hardwaremod.HW_CTRL_FREQ
			frequency=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)
			if frequency=="":
				bouncetimeINT=200
			else:
				frequencyINT=hardwaremod.toint(frequency,5)
				bouncetimeINT=old_div(1000,frequencyINT) # in ms. this is ok to be trunk of the int. For frequencies higher than 1000 the bouncetime is exactly zero
				
			# RPI.GPIO library does not accept bouncetime=0, it gives runtime error
			if bouncetimeINT<=0:
				bouncetimeINT=1 #ms
			hardwaremod.GPIO_add_event_detect(PINstr, evenslopetype, eventcallback, bouncetimeINT)
			
			# set fast reference call indexed with the PIN number which is the variable used when interrupt is called:
			# search now to avoid searching later
			
			global PIN_attributes
			
			PIN=hardwaremod.toint(PINstr,0)
			
			statusdataDBmod.write_status_data(PIN_attributes,PIN,"logic",logic)
			
			recordkey=hardwaremod.HW_CTRL_PIN
			recordvalue=PINstr	
			keytosearch=hardwaremod.HW_INFO_NAME
			refsensor=hardwaremod.searchdata(recordkey,recordvalue,keytosearch) # return first occurence
			
			statusdataDBmod.write_status_data(PIN_attributes,PIN,"refsensor",refsensor)
			statusdataDBmod.write_status_data(PIN_attributes,PIN,"bouncetimeSec",0.4*float(bouncetimeINT)/1000)
			
	
	# code below to enable blocking for N sec, it is necessary to trigger the bloccking status in case of levels already present when starting.
	elementlist= interruptdbmod.getelementlist()	
	#print elementlist
	for element in elementlist: 
		workmode=checkworkmode(element)
		if (workmode!="None")and(workmode!=""):
			sensor=interruptdbmod.searchdata("element",element,"sensor")
			#saveblockingdiff(sensor)
			print(" what a sensor ", sensor)
			if sensor!="":
				startblockingstate(element,10,False)
			
			
	return ""


def cyclereset(element):
	

	#AUTO_data["default"]={"lasteventtime":datetime.utcnow()- timedelta(minutes=waitingtime),"lastinterrupttime":datetime.utcnow(),
	#"validinterruptcount":0,"eventactivated":False,"lastactiontime":datetime.utcnow()- timedelta(minutes=waitingtime),
	#"actionvalue":0, "alertcounter":0, "infocounter":0, "status":"ok" , "threadID":None , "blockingstate":False}
	#SENSOR_data["default"]={"Startcounttime":datetime.utcnow(),"InterruptCount":0} # this is for the actual frequency sensor
	#PIN_attributes["default"]={"logic":"pos","refsensor":"","bouncetimeSec":0.001} # this is relebant to the PINs
	#BLOCKING_data["default"]={"BlockingNumbers":0,"BlockingNumbersThreadID":None} # tihs is relenat to the Interrupt trigger


	global AUTO_data
	waitingtime=hardwaremod.toint(interruptdbmod.searchdata("element",element,"preemptive_period"),0)
	statusdataDBmod.write_status_data(AUTO_data,element,"lastactiontime",datetime.utcnow() - timedelta(minutes=waitingtime))
	statusdataDBmod.write_status_data(AUTO_data,element,"lasteventtime",datetime.utcnow() - timedelta(minutes=waitingtime))
	statusdataDBmod.write_status_data(AUTO_data,element,"status","ok")
	statusdataDBmod.write_status_data(AUTO_data,element,"actionvalue",0)	
	statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)	
	statusdataDBmod.write_status_data(AUTO_data,element,"infocounter",0)
	statusdataDBmod.write_status_data(AUTO_data,element,"validinterruptcount",0)
	# start procedure to stop blocking on this element
	endblocking(element)	
	
	
	# reassess all the interrupt sensor related shit
	elementlist= interruptdbmod.getelementlist()
	sensorblockingcounter={}
	#print "elementlist" , elementlist
	#print elementlist
	for element in elementlist: 
		#print " ELEMENT " , element
		workmode=checkworkmode(element)
		if (workmode!="None")and(workmode!=""):
			sensor=interruptdbmod.searchdata("element",element,"sensor")
			#print " SENSOR " , sensor
			if sensor!="":
				#print "Blocking starte " , statusdataDBmod.read_status_data(AUTO_data,element,"blockingstate")
				if statusdataDBmod.read_status_data(AUTO_data,element,"blockingstate"): # blocking state is TRUE
					#print " TRUE ------------------------------------------------------- " , element
					if sensor in sensorblockingcounter:
						sensorblockingcounter[sensor]=sensorblockingcounter[sensor]+1
					else:
						sensorblockingcounter[sensor]=1
					
	print(sensorblockingcounter)
	global BLOCKING_data
	for sensor in sensorblockingcounter:
		statusdataDBmod.write_status_data(BLOCKING_data,sensor,"BlockingNumbers",sensorblockingcounter[sensor])
	
	

def cycleresetall():
	global AUTO_data
	elementlist= interruptdbmod.getelementlist()
	for element in elementlist:
		cyclereset(element)

def interruptcheck(refsensor,mode, PIN):
	#logger.info('Starting Interrupt Evaluation, Sensor: %s' , refsensor)
	# iterate among the actuators
	elementlist= interruptdbmod.getelementlist()	
	#print elementlist
	for element in elementlist: 
		sensor=interruptdbmod.searchdata("element",element,"sensor")
		#print sensor
		if sensor==refsensor:
			sensormode=interruptdbmod.searchdata("element",element,"sensor_mode")		
			#print "mode ", mode , "sensormode ", 	sensormode
			if (mode in sensormode) or ("both" in sensormode):
				interruptexecute(refsensor,element)
				
	
	return	
		

def ReadInterruptFrequency(PIN):
	sensorinterruptcount=statusdataDBmod.read_status_data(SENSOR_data,PIN,"InterruptCount")	
	Startcounttime=statusdataDBmod.read_status_data(SENSOR_data,PIN,"Startcounttime")	
	nowtime=datetime.utcnow()
	diffseconds=(nowtime-Startcounttime).total_seconds()
	if diffseconds>0:
		Frequency=old_div(sensorinterruptcount,diffseconds)
	else:
		Frequency = 0
	# azzera timer e counter
	statusdataDBmod.write_status_data(SENSOR_data,PIN,"InterruptCount",0)
	statusdataDBmod.write_status_data(SENSOR_data,PIN,"Startcounttime",nowtime)
	return Frequency

def interruptexecute(refsensor,element):
	
	sensor=refsensor		
	#logger.info('interrupt Pairing OK ---> Actuator: %s , Sensor: %s', element, sensor)

	workmode=checkworkmode(element)

	if (workmode=="None"):
		# None case
		print("No Action required, workmode set to None, element: " , element)
		logger.info("No Action required, workmode set to None, element: %s " , element)
		return

	if (workmode==""):
		logger.info("Not able to get the workmode: %s " , element)
		return

	#logger.info('Interrupt, Get all the parameters')
	interrupt_validinterval=hardwaremod.tonumber(interruptdbmod.searchdata("element",element,"interrupt_validinterval"),0)
	#"Counter Only"
	if workmode=="Counter Only":
		 CounterOnlyNew(element,sensor,interrupt_validinterval)
		 return

	interrupt_triggernumber=hardwaremod.tonumber(interruptdbmod.searchdata("element",element,"interrupt_triggernumber"),1)
	actuatoroutput=hardwaremod.tonumber(interruptdbmod.searchdata("element",element,"actuator_output"),0)
	actuatoroutputfollowup=hardwaremod.tonumber(interruptdbmod.searchdata("element",element,"folloup_output"),0)

	# evaluate variables for operational period check
	starttime = datetime.strptime(interruptdbmod.searchdata("element",element,"allowedperiod")[0], '%H:%M').time()
	endtime = datetime.strptime(interruptdbmod.searchdata("element",element,"allowedperiod")[1], '%H:%M').time()
		
	
	# get other parameters
	seonsormode=interruptdbmod.searchdata("element",element,"sensor_mode")

	triggermode=interruptdbmod.searchdata("element",element,"trigger_mode")	
	
	preemptiontimemin=hardwaremod.toint(interruptdbmod.searchdata("element",element,"preemptive_period"),0)
	
	if preemptiontimemin==0:
		# if relay, meaning cmd = pulse
		actuatortype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_CTRL_CMD)
		if actuatortype=="pulse":
			preemptiontime=actuatoroutput # if set to zero then get the time as the actuator (in case of relay)
		else:
			preemptiontime=0
	else:
		preemptiontime=preemptiontimemin*60
	
	mailtype=interruptdbmod.searchdata("element",element,"mailalerttype")
	
	actionmodeafterfirst=interruptdbmod.searchdata("element",element,"actionmode_afterfirst")
		
	# time check

	
	# ------------------------ interrupt alghoritm
	
	if workmode=="Pre-emptive Blocking":
		# check if inside the allowed time period
		#print "Pre-emptive Blocking Mode"
		#logger.info('Pre-emptive Blocking mode --> %s', element) 
		timeok=isNowInTimePeriod(starttime, endtime, datetime.now().time()) # don't use UTC here!
		#print "inside allowed time ", timeok , " starttime ", starttime , " endtime ", endtime
		if timeok:

			CheckActivateNotify(element,sensor,preemptiontime,actuatoroutput,actionmodeafterfirst,actuatoroutputfollowup,mailtype,interrupt_triggernumber,interrupt_validinterval,triggermode)
				
		else:
			logger.info('out of allowed operational time')

	# implment Critical alert message in case the sensor value is one interval more than Max_threshold

	return


def CounterOnly(element,sensor,interrupt_validinterval):  # this one should be dismissed, anyway it works

	isok=False
	global AUTO_data
	
	lastinterrupttime=statusdataDBmod.read_status_data(AUTO_data,element,"lastinterrupttime")
	nowtime=datetime.utcnow()
	#print ' Previous interrupt: ' , lastinterrupttime , ' Now: ', nowtime	

	diffseconds=(nowtime-lastinterrupttime).total_seconds()

	statusdataDBmod.write_status_data(AUTO_data,element,"lastinterrupttime",nowtime)	
	validinterruptcount=statusdataDBmod.read_status_data(AUTO_data,element,"validinterruptcount")	

	
	if diffseconds<=interrupt_validinterval: #valid interval between interrupt, increase counter
		validinterruptcount=validinterruptcount+1
		statusdataDBmod.write_status_data(AUTO_data,element,"validinterruptcount",validinterruptcount)
	else: # time between interrupt too long, restart counter
		# save on database 
		#x = threading.Thread(target=savedata, args=(sensor,validinterruptcount))
		#x.start()			
		#reset counter and events
		validinterruptcount=1
		statusdataDBmod.write_status_data(AUTO_data,element,"validinterruptcount",validinterruptcount)	
		
	WaitandRegister(element, sensor,  interrupt_validinterval, validinterruptcount)	
				
	return isok


def WaitandRegister(element, sensor, periodsecond, counter):  # this one should be dismissed, working with previous procedure
	if periodsecond>0:
		global AUTO_data
		t.sleep(0.05)
		# in case another timer is active on this element, cancel it 
		threadID=statusdataDBmod.read_status_data(AUTO_data,element+sensor,"RegisterID")
		if threadID!=None and threadID!="":
			threadID.cancel()
		# activate a new time, in cas this is not cancelled then the data will be saved callin the savedata procedure
		threadID = threading.Timer(periodsecond, savedata, [sensor , counter])
		threadID.start()
		statusdataDBmod.write_status_data(AUTO_data,element+sensor,"RegisterID",threadID)
	else:
		x = threading.Thread(target=savedata, args=(sensor,counter))
		x.start()

def CounterOnlyNew(element,sensor,periodsecond):  # this one should be dismissed

	isok=False
	global AUTO_data
	if periodsecond>0:
		# in case another timer is active on this element, cancel it 
		threadID=statusdataDBmod.read_status_data(AUTO_data,element+sensor,"RegisterID")
		if threadID!=None and threadID!="":
			threadID.cancel()
			validinterruptcount=statusdataDBmod.read_status_data(AUTO_data,element,"validinterruptcount")
			validinterruptcount=validinterruptcount+1
			statusdataDBmod.write_status_data(AUTO_data,element,"validinterruptcount",validinterruptcount)
		else: # time between interrupt exceeded, restart counter
			validinterruptcount=1
			statusdataDBmod.write_status_data(AUTO_data,element,"validinterruptcount",validinterruptcount)			
			
			
		# activate a new time, in cas this is not cancelled then the data will be saved callin the savedata procedure	
		threadID = threading.Timer(periodsecond, WaitandRegisterNew, [element , sensor , validinterruptcount])
		threadID.start()
		statusdataDBmod.write_status_data(AUTO_data,element+sensor,"RegisterID",threadID)
				
	return isok
	
def WaitandRegisterNew(element, sensor, counter):
	global AUTO_data
	savedata(sensor , counter)
	statusdataDBmod.write_status_data(AUTO_data,element+sensor,"RegisterID",None)
	#t.sleep(0.1)
	#savedata(sensor , 0)

	


def CheckActivateNotify(element,sensor,preemptiontime,actuatoroutput,actionmodeafterfirst,actuatoroutputfollowup,mailtype,interrupt_triggernumber,interrupt_validinterval,triggermode):
	value=actuatoroutput
	isok=False
	global AUTO_data
	# check if in blocking state
	lasteventtime=statusdataDBmod.read_status_data(AUTO_data,element,"lasteventtime")
	blockingstate=statusdataDBmod.read_status_data(AUTO_data,element,"blockingstate")	
	#print ' Previous event: ' , lasteventtime , ' Now: ', datetime.utcnow()
	#timedifference=sensordbmod.timediffinminutes(lasteventtime,datetime.utcnow())
	#print 'Time interval between actions', timedifference ,'. threshold', preemptiontime
	#logger.info('Time interval between Actions %d threshold %d', timedifference,preemptiontime)	
	
	# count the interrupt that are fast enough to stay in the valid interrupt period
	
	#print "autodata" ,AUTO_data[element]
	lastinterrupttime=statusdataDBmod.read_status_data(AUTO_data,element,"lastinterrupttime")
	nowtime=datetime.utcnow()
	
	# ------------  Frequency
	if triggermode=="Frequency":  # triggermode=="Frequency":	
		NOWTIMELIST.append(nowtime)
		validinterruptcount=statusdataDBmod.read_status_data(AUTO_data,element,"validinterruptcount")	

		diffseconds=(nowtime-NOWTIMELIST[0]).total_seconds()

		if diffseconds<=interrupt_validinterval: #valid interval between interrupt, increase counter
			validinterruptcount=validinterruptcount+1
		else:
			while (diffseconds>interrupt_validinterval)and(len(NOWTIMELIST)>1):
				validinterruptcount=validinterruptcount-1
				diffseconds=(nowtime-NOWTIMELIST.pop(0)).total_seconds()
		validinterruptcount=len(NOWTIMELIST)
		
		statusdataDBmod.write_status_data(AUTO_data,element,"validinterruptcount",validinterruptcount)	
		
	
	#-------------Counter

	else: # triggermode=="Counter":	
	
		#print ' Previous interrupt: ' , lastinterrupttime , ' Now: ', nowtime	
		diffseconds=(nowtime-lastinterrupttime).total_seconds()

	

		statusdataDBmod.write_status_data(AUTO_data,element,"lastinterrupttime",nowtime)	
		validinterruptcount=statusdataDBmod.read_status_data(AUTO_data,element,"validinterruptcount")	

		
		if diffseconds<=interrupt_validinterval: #valid interval between interrupt, increase counter
			validinterruptcount=validinterruptcount+1

		else: # time between interrupt too long, restart counter
			# save on database 
			#x = threading.Thread(target=savedata, args=(sensor,validinterruptcount))
			#x.start()			
			#reset counter and events
			validinterruptcount=1
		
		statusdataDBmod.write_status_data(AUTO_data,element,"validinterruptcount",validinterruptcount)	
			

	#print(" validinterruptcount --------------------->", validinterruptcount) 	

	#print "********" ,validinterruptcount , "******"	
		
	if not blockingstate: # outside the preemption period , first activation
		#print " outside the preemption period "
		#logger.info('outside the preemption period')	
		# before action, evaluate if trigger number is reached
	
		if validinterruptcount>=interrupt_triggernumber:

					
			print("Implement Actuator Value ", value)
			logger.info('Procedure to start actuator %s, for value = %s', element, value)		
			isok=activateactuator(element, value)
				
			# invia mail, considered as info, not as alert
			if mailtype!="none":
				if mailtype!="warningonly":
					textmessage="INFO: " + sensor + " event , activating:" + element + " with Value " + str(value)
					#send mail using thread to avoid blocking
					x = threading.Thread(target=emailmod.sendallmail, args=("alert", textmessage))
					x.start()	
					#emailmod.sendallmail("alert", textmessage)
				if isok:
					statusdataDBmod.write_status_data(AUTO_data,element,"lasteventtime",datetime.utcnow())
					statusdataDBmod.write_status_data(AUTO_data,element,"lastactiontime",datetime.utcnow())
					statusdataDBmod.write_status_data(AUTO_data,element,"actionvalue",value)
				
			
			#save data
			print("first save in database")
			saveblockingdiff(sensor)
			#--				
			# start the blocking state
			print("Start blocking state")
			startblockingstate(element,preemptiontime)
			
			#save data
			saveblockingdiff(sensor)
			#--					

					

		
			

	else:
		# inside blocking state
		#print " inside the preemption period, starting followup actions: " , actionmodeafterfirst
		#logger.info('inside the preemption period, check followup actions %s :', actionmodeafterfirst)
		
		if actionmodeafterfirst=="None":
			return
			
		if actionmodeafterfirst=="Extend blocking state": # extend only the pre-emption blocking period, no action
			print("Extend blocking state")
			startblockingstate(element,preemptiontime)

		if actionmodeafterfirst=="Remove blocking state" or actionmodeafterfirst=="Remove and Follow-up": # remove the pre-emption blocking period, no action
			print("Remove blocking state")
			endblocking(element)
		

		if actionmodeafterfirst=="Follow-up action" or actionmodeafterfirst=="Remove and Follow-up": # execute the action followup, no variation in the preemption period
			value=actuatoroutputfollowup
			# followup action					
			print("Implement Actuator Value followup", value)
			logger.info('Procedure to start actuator followup %s, for value = %s', element, value)		
			isok=activateactuator(element, value)
				
			# invia mail, considered as info, not as alert
			if mailtype!="none":
				if mailtype!="warningonly":
					textmessage="INFO: " + sensor + " event , activating:" + element + " with Value " + str(value)
					x = threading.Thread(target=emailmod.sendallmail, args=("alert", textmessage))
					x.start()
					#emailmod.sendallmail("alert", textmessage)
				if isok:
					statusdataDBmod.write_status_data(AUTO_data,element,"lastactiontime",datetime.utcnow())
					statusdataDBmod.write_status_data(AUTO_data,element,"actionvalue",value)
				
	return isok
		



def startblockingstate(element,periodsecond,saveend=True):
	#logger.warning("StartBOLCKINGSTATE Started ---> Period %d", periodsecond)
	global BLOCKING_data
	if periodsecond>0:
		global AUTO_data
		# in case another timer is active on this element, cancel it 
		threadID=statusdataDBmod.read_status_data(AUTO_data,element,"threadID")
		if threadID!=None and threadID!="":
			#print "cancel the Thread of element=",element
			threadID.cancel()
		else:
			sensor=interruptdbmod.searchdata("element",element,"sensor")
			# change blocking counter
			BlockingNumbers=statusdataDBmod.read_status_data(BLOCKING_data,sensor,"BlockingNumbers")	
			BlockingNumbers=BlockingNumbers+1
			statusdataDBmod.write_status_data(BLOCKING_data,sensor,"BlockingNumbers",BlockingNumbers)
			#--
		
		statusdataDBmod.write_status_data(AUTO_data,element,"blockingstate",True)
		statusdataDBmod.write_status_data(hardwaremod.Blocking_Status,element,"priority",ACTIONPRIORITYLEVEL) #increse the priority to execute a command
		
		nonblockingpriority=0
		#logger.warning("Trigger EndblockingStart ---> Period %d", periodsecond)
		threadID = threading.Timer(periodsecond, endblocking, [element , saveend])
		threadID.start()
		statusdataDBmod.write_status_data(AUTO_data,element,"threadID",threadID)


def endblocking(element, saveend=True):

	sensor=interruptdbmod.searchdata("element",element,"sensor")
	#save data
	if saveend:
		saveblockingdiff(sensor)
	#--		
	if checkstopcondition(element):
		global AUTO_data
		threadID=statusdataDBmod.read_status_data(AUTO_data,element,"threadID")
		if threadID!=None and threadID!="":
			#print "cancel the Thread of element=",element
			threadID.cancel()
			global BLOCKING_data
			# change blocking counter
			BlockingNumbers=statusdataDBmod.read_status_data(BLOCKING_data,sensor,"BlockingNumbers")	
			BlockingNumbers=BlockingNumbers-1
			statusdataDBmod.write_status_data(BLOCKING_data,sensor,"BlockingNumbers",BlockingNumbers)
			#--
			#save data
			saveblockingdiff(sensor)
			#--		

		#print "Start removing blocking status"
		statusdataDBmod.write_status_data(hardwaremod.Blocking_Status,element,"priority",NONBLOCKINGPRIORITY) #put the priority to lower levels
		statusdataDBmod.write_status_data(AUTO_data,element,"threadID",None)
		statusdataDBmod.write_status_data(AUTO_data,element,"blockingstate",False)
	else: # renew the blocking status
		print("Interrupt LEVEL High, Do not stop blocking period, Extend it")
		# reload the period in case this is chnaged
		preemptiontimemin=hardwaremod.toint(interruptdbmod.searchdata("element",element,"preemptive_period"),0)
		period=preemptiontimemin*60
		if period>0:
			startblockingstate(element,period)
	


def checkstopcondition(element):
	#print "Evaluating End of Blocking period ++++++++++++"
	actionmodeafterfirst=interruptdbmod.searchdata("element",element,"actionmode_afterfirst")
	#print "actionafter " , actionmodeafterfirst
	sensor=interruptdbmod.searchdata("element",element,"sensor")


	
	if actionmodeafterfirst=="Extend blocking state" or actionmodeafterfirst=="Extend and Follo-up": # extend only the pre-emption blocking period, no action
		seonsormode=interruptdbmod.searchdata("element",element,"sensor_mode")
		#print "SENSORMODE" , seonsormode
		recordkey=hardwaremod.HW_INFO_NAME
		recordvalue=sensor	
		keytosearch=hardwaremod.HW_CTRL_PIN
		PIN=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)
		reading=hardwaremod.readinputpin(PIN)		

		if seonsormode=="First Edge + Level":	
			keytosearch=hardwaremod.HW_CTRL_LOGIC
			logic=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)			
			# pin high according to the set logic
			#print "logic:", logic , " reading:"  ,reading
			if (logic=="pos" and reading=="1")or(logic=="neg" and reading=="0"):
				return False

		elif seonsormode=="Second Edge + Level (inv)":
			keytosearch=hardwaremod.HW_CTRL_LOGIC
			logic=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)			
			#pin LOW according to the set logic
			#print "logic:", logic , " reading:"  ,reading
			if (logic=="pos" and reading=="0")or(logic=="neg" and reading=="1"):
				return False


	return True		

def saveblockingdiff(sensor): # this function minimize the writing over the database, keep them at 1 sec distance and provides a visual pleasant graph :) 
	global BLOCKING_data
	global SAVEBLOCKINGDIFFBUSY		
	if not SAVEBLOCKINGDIFFBUSY:
		SAVEBLOCKINGDIFFBUSY=True
		threadID=statusdataDBmod.read_status_data(BLOCKING_data,sensor,"BlockingNumbersThreadID")
		print(" threadID ", threadID) 
		if (threadID!=None) and (threadID!=""): # thread already present
			print("thread present already, remove it")
			threadID.cancel()
		else:
			# no thread present already		
			print("no thread present already	")
			x = threading.Thread(target=saveblocking, args=(sensor,False))
			x.start()			
		
		#logger.warning("SaveBlockDIFF ---> Sensor %s", sensor)
		threadID = threading.Timer(1, saveblocking, [sensor])
		threadID.start()
		statusdataDBmod.write_status_data(BLOCKING_data,sensor,"BlockingNumbersThreadID",threadID)
		SAVEBLOCKINGDIFFBUSY=False
	else:
		print(" BUSYYYYY")
			
def saveblocking(sensor,cleanThreadID=True):
	global SAVEBLOCKINGBUSY		
	global BLOCKING_data	
	if not SAVEBLOCKINGBUSY:
		SAVEBLOCKINGBUSY=True		
		BlockingNumbers=statusdataDBmod.read_status_data(BLOCKING_data,sensor,"BlockingNumbers")
		print("SAVING :::::: sensor ",sensor," BlockingNumbers " ,BlockingNumbers)
		savedata(sensor,BlockingNumbers)
		if cleanThreadID:
			statusdataDBmod.write_status_data(BLOCKING_data,sensor,"BlockingNumbersThreadID",None)
	
		SAVEBLOCKINGBUSY=False
		

def activateactuator(target, value):  # return true in case the state change: activation is >0 or a different position from prevoius position.
	# check the actuator 
	isok=False
	actuatortype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,target,hardwaremod.HW_CTRL_CMD)
	supportedactuators=["pulse","servo","stepper"]
	# stepper motor
	if actuatortype=="stepper":
		out, isok = hardwaremod.GO_stepper_position(target,value,priority=ACTIONPRIORITYLEVEL)
		if isok:
			actuatordbmod.insertdataintable(target,value)
	
	# hbridge motor
	if actuatortype=="hbridge":
		out, isok = hardwaremod.GO_hbridge_position(target,value)
		if isok:
			actuatordbmod.insertdataintable(target,value)
	
	# pulse
	if actuatortype=="pulse":
		duration=hardwaremod.toint(value,0)
		if duration>0:
			# check the fertilizer doser flag before activating the pulse
			doseron=autofertilizermod.checkactivate(target,duration)
			# start pulse
			pulseok=hardwaremod.makepulse(target,duration,priority=ACTIONPRIORITYLEVEL)	
			# salva su database
			if "Started" in pulseok:
				actuatordbmod.insertdataintable(target,duration)
				isok=True
		else:
			pulseok=hardwaremod.stoppulse(target)
		
	# servo motor 
	if actuatortype=="servo":
		out, isok = hardwaremod.servoangle(target,value,0.5,priority=ACTIONPRIORITYLEVEL)
		if isok:
			actuatordbmod.insertdataintable(target,value)

	# photo 
	if actuatortype=="photo":
		duration=hardwaremod.toint(value,0)
		if duration>0:
			isok=hardwaremod.takephoto(True) # True override the daily activation
			# save action in database
			if isok:
				actuatordbmod.insertdataintable(target,1)	
				
	# mail 
	if (actuatortype=="mail+info+link")or(actuatortype=="mail+info"):
		if value>0:
			mailtext=str(value)	
			isok=emailmod.sendmail(target,"info","Interrupt Value:" + mailtext)
			# save action in database
			if isok:
				actuatordbmod.insertdataintable(target,1)

			
	return isok


def isNowInTimePeriod(startTime, endTime, nowTime):
	#print "iNSIDE pERIOD" ,startTime," ",  endTime," " ,  nowTime
	if startTime < endTime:
		return nowTime >= startTime and nowTime <= endTime
	else: #Over midnight
		return nowTime >= startTime or nowTime <= endTime

			

def checkworkmode(element):
	return interruptdbmod.searchdata("element",element,"workmode")





if __name__ == '__main__':
	
	"""
	prova functions
	"""

	

