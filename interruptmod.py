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

#In hardware, an internal 10K resistor between the input channel and 3.3V (pull-up) or 0V (pull-down) is commonly used. 
#https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/

logger = logging.getLogger("hydrosys4."+__name__)

# status array, required to check the ongoing actions 
elementlist= interruptdbmod.getelementlist()
waitingtime=1200
AUTO_data={} # dictionary of dictionary
AUTO_data["default"]={"lasteventtime":datetime.utcnow()- timedelta(minutes=waitingtime),"lastinterrupttime":datetime.utcnow(),"validinterruptcount":0,"eventactivated":False,"lastactiontime":datetime.utcnow()- timedelta(minutes=waitingtime),"actionvalue":0, "alertcounter":0, "infocounter":0, "status":"ok" , "threadID":None , "blockingstate":False}

# ///////////////// -- STATUS VARIABLES UTILITY --  ///////////////////////////////
PIN_attributes={}
PIN_attributes["default"]={"logic":"pos","refsensor":""}



def readstatus(element,item):
	return statusdataDBmod.read_status_data(AUTO_data,element,item)
	
def savedata(sensorname,sensorvalue):
	sensorvalue_str=str(sensorvalue)
	sensorvalue_norm=hardwaremod.normalizesensordata(sensorvalue_str,sensorname)
	sensordbmod.insertdataintable(sensorname,sensorvalue_norm)
	return	

def eventcallback(PIN):
	#t.sleep(0.005)
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
		
		interruptcheck(refsensor,mode)		
	
	#if refsensor!="":
	#	x = threading.Thread(target=savedata, args=(refsensor,reading))
	#	x.start()


def setinterruptevents():
	
	hardwaremod.removeallinterruptevents()
	
	print "load interrupt list "
	interruptlist=interruptdbmod.sensorlist()
	print "len interrupt list "	, len(interruptlist)	
	for item in interruptlist:
		print "got into the loop "
		# get PIN number

		recordkey=hardwaremod.HW_INFO_NAME
		recordvalue=item	
		keytosearch=hardwaremod.HW_CTRL_PIN
		PINstr=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)
		print "set event for the PIN ", PINstr		
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
				bouncetimeINT=1000/frequencyINT # this is ok to be trunk of the int. For frequencies higher than 1000 the bouncetime is exactly zero
				
			# RPI.GPIO library does not accept bouncetime=0, it gives runtime error
			if bouncetimeINT<=0:
				bouncetimeINT=1
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
			
			
	return ""


def cyclereset(element):
	global AUTO_data
	waitingtime=hardwaremod.toint(interruptdbmod.searchdata("element",element,"preemptive_period"),0)
	statusdataDBmod.write_status_data(AUTO_data,element,"lastactiontime",datetime.utcnow() - timedelta(minutes=waitingtime))
	statusdataDBmod.write_status_data(AUTO_data,element,"lasteventtime",datetime.utcnow() - timedelta(minutes=waitingtime))
	statusdataDBmod.write_status_data(AUTO_data,element,"status","ok")
	statusdataDBmod.write_status_data(AUTO_data,element,"actionvalue",0)	
	statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)	
	statusdataDBmod.write_status_data(AUTO_data,element,"infocounter",0)
	statusdataDBmod.write_status_data(AUTO_data,element,"validinterruptcount",0)	

def cycleresetall():
	global AUTO_data
	elementlist= interruptdbmod.getelementlist()
	for element in elementlist:
		cyclereset(element)

def interruptcheck(refsensor,mode):
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
		
def interruptexecute(refsensor,element):
	
			
	sensor=refsensor		
	#logger.info('interrupt Pairing OK ---> Actuator: %s , Sensor: %s', element, sensor)

	workmode=checkworkmode(element)

	if (workmode=="None"):
		# None case
		print "No Action required, workmode set to None, element: " , element
		logger.info("No Action required, workmode set to None, element: %s " , element)
		return

	if (workmode==""):
		logger.info("Not able to get the workmode: %s " , element)
		return

	#logger.info('Interrupt, Get all the parameters')
	interrupt_validinterval=hardwaremod.tonumber(interruptdbmod.searchdata("element",element,"interrupt_validinterval"),0)
	#"Counter Only"
	if workmode=="Counter Only":
		 CounterOnly(element,sensor,interrupt_validinterval)
		 return

	interrupt_triggernumber=hardwaremod.tonumber(interruptdbmod.searchdata("element",element,"interrupt_triggernumber"),1)
	actuatoroutput=hardwaremod.tonumber(interruptdbmod.searchdata("element",element,"actuator_output"),0)
	actuatoroutputfollowup=hardwaremod.tonumber(interruptdbmod.searchdata("element",element,"folloup_output"),0)

	# evaluate variables for operational period check
	starttime = datetime.strptime(interruptdbmod.searchdata("element",element,"allowedperiod")[0], '%H:%M').time()
	endtime = datetime.strptime(interruptdbmod.searchdata("element",element,"allowedperiod")[1], '%H:%M').time()
		
	
	# get other parameters
	seonsormode=interruptdbmod.searchdata("element",element,"sensor_mode")
	
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
			#logger.info('inside allowed time')
			CheckActivateNotify(element,sensor,preemptiontime,actuatoroutput,actionmodeafterfirst,actuatoroutputfollowup,mailtype,interrupt_triggernumber,interrupt_validinterval)
				
		else:
			logger.info('out of allowed operational time')

	# implment Critical alert message in case the sensor value is one interval more than Max_threshold

	return


def CounterOnly(element,sensor,interrupt_validinterval):

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





def CheckActivateNotify(element,sensor,preemptiontime,actuatoroutput,actionmodeafterfirst,actuatoroutputfollowup,mailtype,interrupt_triggernumber,interrupt_validinterval):
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
		
		
	#print "********" ,validinterruptcount , "******"	
		
	if not blockingstate: # outside the preemption period , first activation
		#print " outside the preemption period "
		#logger.info('outside the preemption period')	
		# before action, evaluate if trigger number is reached
	
		if validinterruptcount==interrupt_triggernumber:

			# action					
			print "Implement Actuator Value ", value
			logger.info('Procedure to start actuator %s, for value = %s', element, value)		
			isok=activateactuator(element, value)
				
			# invia mail, considered as info, not as alert
			if mailtype!="none":
				if mailtype!="warningonly":
					textmessage="INFO: " + sensor + " event , activating:" + element + " with Value " + str(value)
					emailmod.sendallmail("alert", textmessage)
				if isok:
					statusdataDBmod.write_status_data(AUTO_data,element,"lasteventtime",datetime.utcnow())
					statusdataDBmod.write_status_data(AUTO_data,element,"lastactiontime",datetime.utcnow())
					statusdataDBmod.write_status_data(AUTO_data,element,"actionvalue",value)
				
			# start the blocking state
			print "Start blocking state"
			startblockingstate(element,preemptiontime)

	else:
		# inside blocking state
		#print " inside the preemption period, starting followup actions: " , actionmodeafterfirst
		#logger.info('inside the preemption period, check followup actions %s :', actionmodeafterfirst)
		
		if actionmodeafterfirst=="None":
			return
			
		if actionmodeafterfirst=="Extend blocking state": # extend only the pre-emption blocking period, no action
			print "Extend blocking state"
			startblockingstate(element,preemptiontime)

		if actionmodeafterfirst=="Remove blocking state" or actionmodeafterfirst=="Remove and Follow-up": # remove the pre-emption blocking period, no action
			print "Remove blocking state"
			endblocking(element,preemptiontime)
		

		if actionmodeafterfirst=="Follow-up action" or actionmodeafterfirst=="Remove and Follow-up": # execute the action followup, no variation in the preemption period
			value=actuatoroutputfollowup
			# followup action					
			print "Implement Actuator Value followup", value
			logger.info('Procedure to start actuator followup %s, for value = %s', element, value)		
			isok=activateactuator(element, value)
				
			# invia mail, considered as info, not as alert
			if mailtype!="none":
				if mailtype!="warningonly":
					textmessage="INFO: " + sensor + " event , activating:" + element + " with Value " + str(value)
					emailmod.sendallmail("alert", textmessage)
				if isok:
					statusdataDBmod.write_status_data(AUTO_data,element,"lastactiontime",datetime.utcnow())
					statusdataDBmod.write_status_data(AUTO_data,element,"actionvalue",value)
				
	return isok
		


def WaitandRegister(element, sensor, periodsecond, counter):
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


def startblockingstate(element,periodsecond):
	
	if periodsecond>0:
		global AUTO_data
		# in case another timer is active on this element, cancel it 
		threadID=statusdataDBmod.read_status_data(AUTO_data,element,"threadID")
		if threadID!=None and threadID!="":
			#print "cancel the Thread of element=",element
			threadID.cancel()
		
		statusdataDBmod.write_status_data(AUTO_data,element,"blockingstate",True)
		statusdataDBmod.write_status_data(hardwaremod.Blocking_Status,element,"priority",ACTIONPRIORITYLEVEL) #increse the priority to execute a command
		
		nonblockingpriority=0
		threadID = threading.Timer(periodsecond, endblocking, [element , periodsecond])
		threadID.start()
		statusdataDBmod.write_status_data(AUTO_data,element,"threadID",threadID)

		




def endblocking(element,  period):
	if checkstopcondition(element):
		global AUTO_data
		threadID=statusdataDBmod.read_status_data(AUTO_data,element,"threadID")
		if threadID!=None and threadID!="":
			#print "cancel the Thread of element=",element
			threadID.cancel()

		#print "Start removing blocking status"
		statusdataDBmod.write_status_data(hardwaremod.Blocking_Status,element,"priority",NONBLOCKINGPRIORITY) #put the priority to lower levels
		statusdataDBmod.write_status_data(AUTO_data,element,"threadID",None)
		statusdataDBmod.write_status_data(AUTO_data,element,"blockingstate",False)
	else:
		print "Interrupt LEVEL High, Do not stop blocking period, Extend it"
		startblockingstate(element,period)
	

def checkstopcondition(element):
	#print "Evaluating End of Blocking period ++++++++++++"
	actionmodeafterfirst=interruptdbmod.searchdata("element",element,"actionmode_afterfirst")
	#print "actionafter " , actionmodeafterfirst
	if actionmodeafterfirst=="Extend blocking state" or actionmodeafterfirst=="Extend and Follo-up": # extend only the pre-emption blocking period, no action
		seonsormode=interruptdbmod.searchdata("element",element,"sensor_mode")
		#print "SENSORMODE" , seonsormode
		if seonsormode=="First Edge + Level":
			sensor=interruptdbmod.searchdata("element",element,"sensor")
			recordkey=hardwaremod.HW_INFO_NAME
			recordvalue=sensor	
			keytosearch=hardwaremod.HW_CTRL_PIN
			PIN=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)
			reading=hardwaremod.readinputpin(PIN)				
			keytosearch=hardwaremod.HW_CTRL_LOGIC
			logic=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)			
			# pin high according to the set logic
			#print "logic:", logic , " reading:"  ,reading
			if logic=="pos" and reading=="1":
				return False
			if logic=="neg" and reading=="0":
				return False

		elif seonsormode=="Second Edge + Level (inv)":
			sensor=interruptdbmod.searchdata("element",element,"sensor")
			recordkey=hardwaremod.HW_INFO_NAME
			recordvalue=sensor	
			keytosearch=hardwaremod.HW_CTRL_PIN
			PIN=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)
			reading=hardwaremod.readinputpin(PIN)				
			keytosearch=hardwaremod.HW_CTRL_LOGIC
			logic=hardwaremod.searchdata(recordkey,recordvalue,keytosearch)			
			#pin LOW according to the set logic
			#print "logic:", logic , " reading:"  ,reading
			if logic=="pos" and reading=="0":
				return False
			if logic=="neg" and reading=="1":
				return False

	return True		

	
					
		

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

	

