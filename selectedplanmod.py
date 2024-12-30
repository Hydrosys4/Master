# -*- coding: utf-8 -*-
"""
selected plan utility
"""
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import range
from past.utils import old_div
import logging
import os
import os.path
import threading
import string
from datetime import datetime,date,timedelta
import time
import filestoragemod
import sensordbmod
import actuatordbmod
import hardwaremod
import SchedulerMod
import wateringdbmod
from autowatering import autowateringmod
import fertilizerdbmod
import autofertilizermod
import advancedmod
import emailmod
import networkmod
import clockmod
import automationmod
import debuggingmod
import basicSetting
import weatherAPImod
import wateringplansensordbmod
import ActuatorControllermod
import REGandDBmod
import HASScompMatrix

DEBUGMODE=basicSetting.data["DEBUGMODE"]
MASTERSCHEDULERTIME="00:01:00"
STOREPASTDAYS="364"

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

global FASTSCHEDULER
FASTSCHEDULER=True
global ITEMWEEKSROW
ITEMWEEKSROW=2
global HEARTBEATINTERVAL
HEARTBEATINTERVAL=15
global schedulercallback

SETMASTERBUSY=False

# ///////////////// --- END GLOBAL VARIABLES ------

logger = logging.getLogger("hydrosys4."+__name__)
modlogger = logging.getLogger("actuator")

#--start the scheduler call-back part--------////////////////////////////////////////////////////////////////////////////////////

def activateandregister(target,activationseconds): # function to activate the actuators
	print(target, " ",activationseconds, " " , datetime.now())
	logger.info('Activate for Value = %s', activationseconds)
	# start pulse
	#msg,pulseok=hardwaremod.makepulse(target,duration)
	# the above is replaced by a more generic method to activate actuators
	msg , pulseok=ActuatorControllermod.activateactuator(target,activationseconds) # it also save in database
	return msg

def pulsenutrient(target,activationseconds): #scheduled doser activity for fertilizer
	duration=hardwaremod.toint(activationseconds,0)
	workmode = autofertilizermod.getworkmode(target)
	if workmode == "ScheduledTime":
		autofertilizermod.activatedoser(target, duration)
	elif workmode == "BeforeWatering":
		logger.info('Book the %s activation', target)
		autofertilizermod.setActivationDurationDate(target,True,duration,datetime.now())

	return True

def dictionarydataforactuator(actuatorname,data1,data2, description):
	listdict=[]
	dicttemp={}
	dicttemp["date"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	dicttemp["actuator"]=actuatorname
	dicttemp["data1"]= data1
	dicttemp["data2"]= data2
	dicttemp["info"]= description
	listdict.append(dicttemp)
	return listdict

def checksensorcondition(sensornamelist,threshold, MinutesOfAverage, ONOFF=True):

	valid=False	
	passed=False
	thresholdnum=hardwaremod.tonumber(threshold,"NA")
	
	if (thresholdnum!="NA"):	

		if sensornamelist:
			valid=True
			
			sensordata=[]		
			sensorname=sensornamelist[0]  # get first found sensor in the list
			sensordbmod.getsensordbdata(sensorname,sensordata)
			starttimecalc=datetime.now()-timedelta(minutes=int(MinutesOfAverage))
			isok , calclist=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())
			calculation=calclist["average"]
			logger.info('Waterpump Check sensor =%s ', sensorname)
			logger.info('Sensor=%s , Theshold=%s ', str(calculation), str(threshold))
			print('Sensor= ', str(calculation),', Theshold= ', str(threshold))
			
			test="below ON"
			if (calculation<thresholdnum):
				passed=True
			if not ONOFF:
				passed=not passed
				test="above ON"
							
			print('check ', test)
			if passed:		
				logger.info('check %s PASSED, sensor1=%s , Theshold=%s ', test , str(calculation), str(threshold))	
				print('PASSED, sensor1=%s , Theshold=%s ',  str(calculation), str(threshold))		
			else:
				logger.info('check %s FAILED', test)
				print('check FAILED')		
	
	return valid , passed	
	
		
def startpump(target,activationseconds,ThesholdOFFON,ThesholdONOFF):

	logger.info('WateringPlan Startpump evaluation: %s', target)
	check=autowateringmod.getstatus(target,"allowwateringplan")
	if (not check) and (check != None): # None is considered false
		logger.info('WateringPlan: %s pump activation blocked by automation', target)
		pumpit=False
		return False

	duration=hardwaremod.toint(activationseconds,0)
	print(target, " ",duration, " " , datetime.now())

	print("waterpump check")
	logger.info('execute water pump check %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

	# evaluate parameters
	MinutesOfAverage=hardwaremod.toint(wateringplansensordbmod.getselduration(),120) #minutes in which the average data is calculated from sensor sampling

	tsensornamelist, hsensornamelist=wateringplansensordbmod.getactivesensor()

	valid1, passed1 = checksensorcondition(tsensornamelist,ThesholdOFFON, MinutesOfAverage, False)
	valid2, passed2 = checksensorcondition(hsensornamelist,ThesholdONOFF, MinutesOfAverage, True)

	# apply AND or OR condition
	condition=wateringplansensordbmod.getselcondition()  # "AND" , "OR"

	pumpit=True

	if valid1 and valid2:
		if condition=="AND":
			pumpit=passed1 and passed2
		elif condition=="OR":
			pumpit=passed1 or passed2

	else:
		if valid1:
			pumpit=passed1
		if valid2:
			pumpit=passed2

	print('valid1= ' , valid1 , 'valid2= ' , valid2)
	print('passed1= ' , passed1 , 'passed2= ' , passed2)
	print('pumpit= ' , pumpit, 'condition= ' , condition)
	logger.info('Condition for activation =%s ', pumpit)

	# weather Forecast
	sensorname=weatherAPImod.DefaultCounterName()
	sensorlist=sensordbmod.gettablelist()
	if sensorname in sensorlist:
		ActiveActuatorList=weatherAPImod.ActiveActuatorList()
		if target in ActiveActuatorList:
			sensordata=[]
			samplesnumber=1
			sensordbmod.getsensordbdatasamplesN(sensorname,sensordata,samplesnumber)
			MaxPastMinutes=1200
			starttimecalc=datetime.now()-timedelta(minutes=MaxPastMinutes)
			isok , quantitylist=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())
			if isok:
				RainMultipier=quantitylist["average"]
				logger.info('Waterpump weather multiplier =%s ', str(RainMultipier))
			else:
				logger.warning('Waterpump weather multiplier NOT found within 20 Hours apply 100 ')
				RainMultipier=100
			duration=int(duration*RainMultipier/100)
	else:
		logger.warning('Weather Sensor not found, no multpilier applied ')


	if pumpit:
		# activation of the doser before the pump
		doseron=autofertilizermod.checkactivate(target,duration)		
		modlogger.info('Waterpump %s activated for %d sec (fertilize: %r)', target, duration, doseron)
		# watering
		activateandregister(target,duration)
	else:
		modlogger.warning('Waterpump %s activation skipped (sensor1 %r %s sensor2 %r)', target, passed1, condition, passed2)

	return True


def periodicdatarequest(sensorname):
	print("Read sensors request: ", sensorname , " " , datetime.now())
	logger.info('Read sensor data: %s - %s', sensorname, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	isok, sensorvalue, errmsg = hardwaremod.getsensordata(sensorname,3)
	if sensorvalue!="":
		REGandDBmod.register_input_value(sensorname,sensorvalue)
		# Automation algoritm 
		automationmod.automationcheck(sensorname)
		# call to automatic algorithms for watering
		autowateringmod.autowateringcheck(sensorname)
		
	return True	
	
def CheckNTPandAdjustClockandResetSched(timediffsec=60):
	# try to get the clock from network
	print("check system clock")
	logger.info('Check system clock vs NTP (Network Time Protocol)')
	networktime=clockmod.getNTPTime()
	logger.info('Network time NTP: %s ', networktime)
	systemtime=clockmod.readsystemdatetime()
	logger.info('System time NTP: %s ', systemtime)
	if not networktime=='':
		diffsec=clockmod.timediffinsec(networktime, systemtime)
		logger.info('Difference between system time and network time, diffsec =  %d ', diffsec)
		if diffsec>timediffsec:
			print("Warning difference between system time and network time >",timediffsec ," sec, diffsec = " , diffsec)
			logger.warning('Warning difference between system time and network time >%d sec, diffsec =  %d ', timediffsec , diffsec)
			print("Apply network datetime to system")
			logger.warning('Apply network datetime to system ')
			clockmod.setHWclock(networktime)
			clockmod.setsystemclock(networktime)
			# reset scheduling 
			logger.warning('Reset master Scheduler due to time change')
			resetmastercallback()
			return True
		else:
			print("Clock OK")
			logger.info('Clock OK')
	else:
		print("not able to get network time")
		logger.warning('Not able to get network time')
	return False

def heartbeat():
	print("start heartbeat check", " " , datetime.now())
	logger.info('Start heartbeat routine %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	# check wifi connection
	connectedssid = networkmod.connectedssid()
	connected = False
	if len(connectedssid) == 0:

		if not networkmod.WIFIENDIS == "Disabled":
			logger.warning('Heartbeat check , no network connected -------------- try to connect')
			print('Heartbeat check , no network connected -------------- try to connect')
			connected = networkmod.connect_network()
		else:
			logger.info('Heartbeat check , wifi disabled')
			connected = True
	else:
		logger.info('Heartbeat check , Connected Wifi Network: %s ', connectedssid[0])
		if connectedssid[0] == networkmod.localwifisystem:
			logger.info('Heartbeat check , Configured as wifi access point, check if possible to connect to wifi network')
			connected = networkmod.connect_network()
			networkmod.DHCP_COUNTER = 0
		else: # Connected to wifi network
			reachgoogle=networkmod.check_internet_connection(1)

			if not reachgoogle:
				logger.warning('Heartbeat check wifi SSID ok, but test ping not able to reach Google')
				print('Heartbeat check , no IP connection')
				#connected=networkmod.connect_network() # use this in case you require the system to try connect wifi again in case no internet is reached
				#logger.warning('Heartbeat check , DHCP reset counter %s' , str(networkmod.DHCP_COUNTER))
				# DHCP reset
				#if (networkmod.DHCP_COUNTER % 16)==0: # try to reset every 16x15min =4 hours
					# try to reset DHCP
					#logger.warning('Heartbeat check , reset DHCP')
					#print 'Heartbeat check , reset DHCP'
					#networkmod.resetDHCP()

				#networkmod.DHCP_COUNTER=networkmod.DHCP_COUNTER+1

				goON, GWipaddr = networkmod.checkGWsubnet("wlan0")
				if GWipaddr == "":
					logger.info('Gateway IP address NOT found, back to AP mode')
					# back to AP mode! kind of risky business
					networkmod.connect_AP()

				else:
					logger.info('Gateway IP address found %s', GWipaddr)

				connected = False
			else:
				logger.info('Heartbeat check , wifi connection OK')
				print('Heartbeat check , wifi connection OK')
				#networkmod.DHCP_COUNTER=0
				connected = True

	if connected:
		# Check if remote IP address is changed compared to previous communication and in such case resend the mail
		ipext = networkmod.get_external_ip()
		logger.info('Heartbeat check , Check IP address change -%s- and previously sent -%s-', ipext , emailmod.IPEXTERNALSENT)
		if (ipext != ""):
			if (emailmod.IPEXTERNALSENT != ""):
				if ipext != emailmod.IPEXTERNALSENT:
					print("Heartbeat check, IP address change detected. Send email with updated IP address")
					logger.info('Heartbeat check, IP address change detected. Send email with updated IP address')
					emailmod.sendallmail("alert","System detected IP address change, below the updated links")
				else:
					logger.info('Heartbeat check, IP address unchanged')
			else:
				# first mail has not been sent succesfully of IPEXTERNALSENT was not available by the time
				print("System has been reconnected")
				logger.info("System has been reconnected, IPEXTERNALSENT was empty")
				emailmod.sendallmail("alert","System has been reconnected", localmessage=False)

	else:
		print("not able to establish an internet connection")
		logger.warning("not able to establish an internet connection")

	# check clock with NTP and reset master scheduler in case of clock change
	if CheckNTPandAdjustClockandResetSched():
		return True

	# check MQTT connection is UP
	HASScompMatrix.HASSIOintegr.check_loop_and_connect()

	if not networkmod.WIFIENDIS == "Disabled":
		#check the static IP address
		currentipaddr = networkmod.get_local_ip_raw()
		logger.info('Target IP address= %s. Current access point IP addresses= %s', networkmod.IPADDRESS,currentipaddr)
		if networkmod.IPADDRESS not in currentipaddr:
			#set IP address
			logger.warning('Local Static IP address not in the list, Set Target IP address')
			networkmod.addIP("wlan0")
		else:
			logger.info('Local Statip IP address OK')

	# check master job has a next run"
	isok, datenextrun = SchedulerMod.get_next_run_time("master")
	if isok:
		datenow = datetime.utcnow()
		datenextrun = datenextrun.replace(tzinfo=None)
		print("Master Scheduler Next run " , datenextrun , " Now (UTC) ", datenow)
		if datenextrun > datenow:
			print("Masterschedule next RUN confirmed")
			logger.info('Heartbeat check , Master Scheduler OK')
		else:
			isok=False

	if not isok:
		print("No next run for master scheduler")
		logger.warning('Heartbeat check , Master Scheduler Interrupted')
		#emailmod.sendallmail("alert","Master Scheduler has been interrupted, try to restart scheduler")
		resetmastercallback()
		return True

	# check if there have been errors in Syslog
	if DEBUGMODE:
		logger.info('Heartbeat check , check errors in Syslog file')
		Errortextlist = debuggingmod.searchsyslogkeyword("error")
		if Errortextlist:
			print("found error in syslog")
			logger.warning("ERROR: found error in syslog -------------------------")
			#send notification mail 
			if debuggingmod.SENTERRORTEXT != Errortextlist[0]:
				emailmod.sendallmail("alert","Error found in Syslog",Errortextlist)
				debuggingmod.SENTERRORTEXT = Errortextlist[0]
		else:
			print("No error found in syslog")
			logger.info('Heartbeat check , SYSLOG ok')

	# check if there have been errors in Schedulerlog
	if DEBUGMODE:
		logger.info('Heartbeat check , check errors in Sched log file')
		filename = "logfiles/apscheduler_hydrosystem.log"
		MYPATH = hardwaremod.get_path()
		filenameandpath = os.path.join(MYPATH, filename)
		Errortextlist = debuggingmod.searchLOGkeyword(filenameandpath,"error")
		if Errortextlist:
			print("found error in LOG ",filename)
			logger.warning("ERROR: found error in LOG , %s -------------------------",filename)
			#send notification mail
			if debuggingmod.SENTERRORTEXT != Errortextlist[0]:
				emailmod.sendallmail("alert","Error found in LOG",Errortextlist)
				debuggingmod.SENTERRORTEXT = Errortextlist[0]
		else:
			print("No error found in LOG", filename)
			logger.info('Heartbeat check , LOG ok')

	return True

def sendmail(target):
	logger.info('send Mail %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	# save action in database
	issent=emailmod.sendmail(target,"report","Periodic system report generated automatically")
	if issent:
		actuatordbmod.insertdataintable(target,1)
		print("Action", target , " " , datetime.now())
		
	return True	
	
def takephoto(target):
	logger.info('take picture %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	isok=hardwaremod.takephoto()
	# save action in database
	if isok:
		actuatordbmod.insertdataintable(target,1)
	print("Action", target ," " , datetime.now())	
	return True
	
def setlight(MinimumLightinde,MaximumLightONinde):
	# removed because obsolete
	return True


"""
callback list should be defined after the function is defined
"""

schedulercallback={"heartbeat":heartbeat,"doser":pulsenutrient,"waterpump":startpump,"sensor":periodicdatarequest,"mail":sendmail,"photo":takephoto,"light":setlight}




# Master callback is scheduled each day at midnight

def setmastercallback():
	logger.info('Master Scheduler - Setup daily jobs')
	#set daily call for mastercallback at midnight
	thedateloc=datetime.now()+timedelta(days=1)
	timelist=hardwaremod.separatetimestringint(MASTERSCHEDULERTIME)
	starttimeloc=thedateloc.replace(hour=timelist[0], minute=timelist[1], second=timelist[2])
	print(timelist)
	#convert to UTC time
	starttime=clockmod.convertLOCtoUTC_datetime(starttimeloc)
	print("setup master job")
	argument=[True]
	try:
		SchedulerMod.sched.add_job(mastercallback, 'interval', days=1, start_date=starttime, args=argument, misfire_grace_time=120, name="master")
		logger.info('Master Scheduler - Started without errors')
	except ValueError:
		print('Date value for job scheduler not valid')
		logger.warning('Heartbeat check , Master Scheduler not Started properly')
	mastercallback()
		
	return True


def waitandsetmastercallback(pulsesecond, offset):

	try:
		f=float(pulsesecond)
		secondint=int(f)+offset
	except:
		secondint=200
	print("try to setmastercallback after " , secondint , " seconds")		
	t = threading.Timer(secondint, resetmastercallback ).start()

def resetmastercallback():
	global SETMASTERBUSY	
	#check Busy flag
	if SETMASTERBUSY:
		return True
	# busy flag up
	SETMASTERBUSY=True
	logger.info('Reset Master Scheduler')
	# remove all the current jobs
	print("Reset scheduler, List existing jobs to be removed:")
	SchedulerMod.sched.print_jobs()
	SchedulerMod.removealljobs()
	print("list of jobs after removal:")
	SchedulerMod.sched.print_jobs()
	setmastercallback()	
	print("new jobs to be set in scheduler")
	SchedulerMod.sched.print_jobs()		
	SETMASTERBUSY=False	
	return True


def checkheartbeat():
	# check heartbeat job has a next run"
	logger.info('Check of the heartbeat routine schedule')
	isok, datenextrun = SchedulerMod.get_next_run_time("heartbeat")
	if isok:
		datenow=datetime.utcnow()
		datenextrun = datenextrun.replace(tzinfo=None)
		print("Master heartbeat Next run " , datenextrun , " Now (UTC) ", datenow)
		datenowplusone = datenow + timedelta(days=2)
		if (datenextrun>datenow)and(datenextrun<datenowplusone):
			print("heartbeat next RUN confirmed")
			logger.info('After connection heartbeat Scheduler OK')
		else:
			isok=False
			
	if not isok:
		print("No next run for heartbeat job")
		logger.warning('heartbeat job Interrupted, restarting the overall scheduler ')
		resetmastercallback()
	return isok

def waitandcheckheartbeat(pulsesecond):
	print("wait " , pulsesecond , " seconds")
	try:
		f=float(pulsesecond)
		secondint=int(f)
	except:
		secondint=180
	t = threading.Timer(secondint, checkheartbeat).start()

def mastercallback(fromscheduledtime=False):
	print("master callback")
	if fromscheduledtime: # check if the time this function is called is the same as the expected time it should be called (solar/legal time might mess with it)
		logger.info('Master scheduler call at scheduled local time, expected time %s', MASTERSCHEDULERTIME )		
		thedateloc=datetime.now()
		timelist=hardwaremod.separatetimestringint(MASTERSCHEDULERTIME)
		masterschedtime=thedateloc.replace(hour=timelist[0], minute=timelist[1], second=timelist[2])
		secondsdifference=abs((thedateloc-masterschedtime).total_seconds())
		logger.info('Master scheduler, difference between expected time and local time %d', secondsdifference )
		if secondsdifference>300: # more than 5 minutes
			logger.warning('Master scheduler, difference between expected time and local time greater than 5 minutes, RESET MASTER SCHEDULER' )			
			resetmastercallback()
			return
		# clean old data of the database (pastdays)
		logger.info('Remove data exceeding one year')
		pastdays=hardwaremod.toint(STOREPASTDAYS,364)
		logger.info('Sensor Remove data exceeding one year')	
		sensordbmod.RemoveSensorDataPeriod(pastdays)
		logger.info('Actuator Remove data exceeding one year')	
		actuatordbmod.RemoveActuatorDataPeriod(pastdays)
		logger.info('Photo Remove data exceeding one year')
		hardwaremod.removephotodataperiod(pastdays)
	else:
		logger.info('Master scheduler call not coming from scheduler')
		

	logger.info('Scheduling main activities')
	
	# remove all jobs except masterscheduler
	#for job in SchedulerMod.sched.get_jobs():
	#	if job.name != "master":
	#		try:
	#			job.remove()	
	#		except:
	#			logger.error('Not able to remove Job %s', job.name)

	# set the individual callback of the day
	
	logger.info('Start other scheduler activities - heartbeat')

	# info file dedicate call-back --------------------------------------------- (heartbeat)	
	
	#this callback is used only for system status periodic check 
	
	calltype="periodic"
	global HEARTBEATINTERVAL
	interval=HEARTBEATINTERVAL
	timelist=[0,interval,900] # 20 indicates to start after 15 minutes
	callback="heartbeat"
	argument=[]
	
	setschedulercallback(calltype,timelist,argument,callback,callback)
	
	logger.info('Start other scheduler activities - sensor')
	
	# info file dedicate call-back --------------------------------------------- (sensor)
	

	hwnamelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"input",hardwaremod.HW_INFO_NAME)
	
	# GPIO input can be considered at all the aspects a binary input, therefor their stat collection are possible as any other input
	# the input should be time periodic and time should be more than one minute
	
	
	callback="sensor"
	timeshift=300  # after wifi activation because of possible clock adjustment
	shiftstep=7 #seconds	
	# IMPORTANT
	# the shiftstep is necessary to avoid thread collision which brings to sqlite3 db failure "database is locked" 
	# this number is giving a limit to the sensor reading that should be higher than 1min
	for hwname in hwnamelist:
		calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,hwname,hardwaremod.HW_FUNC_SCHEDTYPE)
		if calltype=="periodic": #check the input to be periodic
			timelist=hardwaremod.gettimedata(hwname)
			timelist[2]=timeshift # avoid all the sensor thread to be called in the same time
			argument=[]
			argument.append(hwname)
			setschedulercallback(calltype,timelist,argument,callback,hwname)
			timeshift=timeshift+shiftstep
		else:
			logger.warning('The scheduler for the input %s is not set to PERIODIC, no log record of this input will be taken',hwname)

	logger.info('Start other scheduler activities - photo')

	#<------>
	# info file dedicate quinto call-back ----------------------------------(takephoto)
	usedfor="photocontrol"
	callback="photo"	
	hwnamelist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_NAME)
	for hwname in hwnamelist:
		calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,hwname,hardwaremod.HW_FUNC_SCHEDTYPE)
		timelist=hardwaremod.gettimedata(hwname)
		argument=[]
		argument.append(hwname)
		setschedulercallback(calltype,timelist,argument,callback,hwname)

	logger.info('Start other scheduler activities - mail')

	# info ne file dedicate quarto call-back ---------------------------------------(sendmail)
	
	usedfor="mailcontrol"
	callback="mail"	
	hwnamelist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_NAME)
	for hwname in hwnamelist:
		calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,hwname,hardwaremod.HW_FUNC_SCHEDTYPE)
		timelist=hardwaremod.gettimedata(hwname)
		argument=[]
		argument.append(hwname)
		setschedulercallback(calltype,timelist,argument,callback,hwname)



	# info ne file dedicate quinto call-back ---------------------------------------(lightcheck)

	# empty
	#<---->
	
	logger.info('Start other scheduler activities - pump')
	
	# info file dedicate call-back ------------------------------------------------ (waterpump)
	

	callback="waterpump"
	
	#water schedule table
	paramlist= wateringdbmod.getparamlist()  # name of the months ordered
	elementlist= wateringdbmod.getelementlist()  # pump ordered (based on "watercontrol" field)
	table=wateringdbmod.gettable(1)# table, each row is a pump, each column is a month, value is watering time multiplieer
	table1=wateringdbmod.gettable(0)# table, each row is a pump, each column is a month, value is watering scheme
	table2=wateringdbmod.gettable(2)# table, each row is a pump, each column is a month, value is time delay 	
	
	#print paramlist
	#print elementlistly
	#print table

	waterSchemaList=advancedmod.getelementlist()
	tabledrop=advancedmod.gettable() # table, each row is a schema number (drop number), each column is a weekday, return ofject is list with Time and duration

	for pumpnumber in range(len(elementlist)):
		#print "number =",pumpnumber
		pumpname=elementlist[pumpnumber]
		todaydate = date.today()
		# Monday is 0 and Sunday is 6
		weekday = todaydate.weekday()
		month = todaydate.month	
		
		try:					
			waterschemanumber=table1[pumpnumber][month-1]
			waterdropnumber=hardwaremod.toint(table[pumpnumber][month-1],0)
			watertimedelaysec=hardwaremod.toint(table2[pumpnumber][month-1],0)
		except IndexError:
			print("EXCEPTION: index out of range") 		
			waterdropnumber=0
			watertimedelaysec=0		
		
		if waterdropnumber>0:			
			#print " month  " , month, " drop  " , waterdropnumber
			calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,pumpname,hardwaremod.HW_FUNC_SCHEDTYPE)
			
			# have to verify if the Schema is relevant to Weekly cycle or daily cycle.
			
			waterschema=waterSchemaList[int(waterschemanumber-1)]
			cycledatalist=advancedmod.getrowdata(waterschema,["cycleOption","dayCycle","startDate"])
			rightDay=True
			if len(cycledatalist)>2:
				if cycledatalist[0]=="Daily Setting":
					rightDay=False
					# now it is required to understand if the event can be triggered using the start date adn daycycle
					# the weekday to be used is the day=0 (Monday)
					startdate=datetime.strptime(cycledatalist[2], "%d/%m/%Y")
					today=datetime.now()
					deltadays = (today - startdate).days
					if deltadays<0:
						print("Scheduler for Daily wayering, current time before the setting time, proceeding anyway")
						logger.warning("Scheduler for Daily wayering, current time before the setting time, proceeding anyway")
					modulo=deltadays % hardwaremod.toint(cycledatalist[1],1)
					print ("Element ", pumpname , "Schema ", waterschema , " Modulo " , modulo)
					if modulo==0:
						weekday=0 # choose the first table
						rightDay=True

			if rightDay:
				for todayevent in tabledrop[waterschemanumber-1][weekday]: # given schema and weekday, provide the list of actions
					# check if the time ofthe event is not 00:00
					if not todayevent[0]=="00:00":
						timelist=hardwaremod.separatetimestringint(todayevent[0])
						timelist[2]=timelist[2]+watertimedelaysec*waterdropnumber
						argument=[]
						argument.append(pumpname)
						durationinseconds=hardwaremod.toint(todayevent[1],0)*waterdropnumber
						argument.append(durationinseconds)				
						for i in range(2,len(todayevent)):
								argument.append(todayevent[i])
						#if durationinseconds>0: #check if the duration in second is >0 this check has been removed because of more general use with hbridge in which this value represent the position
						setschedulercallback(calltype,timelist,argument,callback,pumpname)


	logger.info('Start other scheduler activities - doser')
	# info file dedicate call-back ------------------------------------------------ (pulsenutrient)
	

	callback="doser"

	
	#fertilizer schedule table
	paramlist= fertilizerdbmod.getparamlist()  # name of the months ordered
	elementlist= fertilizerdbmod.getelementlist()  # element with "fertilizercontrol field" ordered 
	table=fertilizerdbmod.gettable(1)# table, each row is a doser, each column is a month, value is number of times in a month	
	table1=fertilizerdbmod.gettable(0)# table, each row is a doser, each column is a month, value is pulse seconds	

	for dosernumber in range(len(elementlist)):
		#print "number =",dosernumber
		dosername=elementlist[dosernumber]
		calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,dosername,hardwaremod.HW_FUNC_SCHEDTYPE)
		todaydate = date.today()
		# Monday is 0 and Sunday is 6
		year = todaydate.year
		month = todaydate.month	
		day = todaydate.day
		fertilizerpulsenumber=hardwaremod.toint(table[dosernumber][month-1],0)
		fertilizerpulsesecond=hardwaremod.toint(table1[dosernumber][month-1],0)
		if (fertilizerpulsenumber>0) and (fertilizerpulsesecond>0):			
			themonthdays=30 #approximate number of days in a month
			dayinterval=old_div(themonthdays,fertilizerpulsenumber)
			halfinterval=old_div((dayinterval+1),2)
			print("day=" , day , " dayinterval=", dayinterval, " half=", halfinterval)		
			if ((day+int(halfinterval)) % int(dayinterval)) == 0:				
				#timelist=hardwaremod.gettimedata("06:00:00")
				timelist=autofertilizermod.timelist(dosername)
				argument=[]
				argument.append(dosername)
				argument.append(fertilizerpulsesecond)
				if (fertilizerpulsesecond)>0: #check if the duration in second is >0
					setschedulercallback(calltype,timelist,argument,callback,dosername)

	logger.info('Start other scheduler activities - finish')
	return True

def setschedulercallback(calltype,timelist,argument,callbackname,jobname):
	# jobname is used as unique identifier of the job
	iserror=False
	callback=schedulercallback[callbackname]
	if calltype=="periodic":
		theintervalminutes=timelist[1]
		theintervalhours=timelist[0]
		startdelaysec=timelist[2]
		if (theintervalminutes+theintervalhours==0): # the time interval is too short, no action
			iserror=True
			logger.warning('The scheduler interval for the input %s is Zero, no log record of this input will be taken',jobname)
			return iserror
		try:
			print("add job ", jobname)

			thedateloc=datetime.now()+timedelta(seconds=startdelaysec)

			mastertimelist=hardwaremod.separatetimestringint(MASTERSCHEDULERTIME)
			date1=datetime.now()+timedelta(days=1)
			date2=date1.replace(hour=mastertimelist[0], minute=mastertimelist[1], second=mastertimelist[2])
			enddateloc=date2-timedelta(minutes=10) # stop 10 minutes before the start of new masterscheduler
			#enddateloc=thedateloc.replace(hour=23, minute=59, second=59)
			#convert to UTC time
			thedate=clockmod.convertLOCtoUTC_datetime(thedateloc)
			#define end date for trigger
			enddate=clockmod.convertLOCtoUTC_datetime(enddateloc)

			try:
				if not FASTSCHEDULER:
					SchedulerMod.sched.add_job(callback, 'interval', hours=theintervalhours, minutes=theintervalminutes, start_date=thedate, end_date=enddate ,args=argument, misfire_grace_time=5, name=jobname)
				else:
					SchedulerMod.sched.add_job(callback, 'interval', seconds=theintervalminutes, start_date=thedate, end_date=enddate ,args=argument, misfire_grace_time=5, name=jobname)
			except ValueError:
				iserror=True
				print('Date value for job scheduler not valid')
		except ValueError as e:
			iserror=True
			print('Error: ', e)
	else: # one shot type
		tday = date.today()
		todaydate = datetime(tday.year, tday.month, tday.day, 0, 0, 0)
		thedateloc=todaydate+timedelta(hours=timelist[0],minutes=timelist[1],seconds=timelist[2])
		#convert to UTC time
		thedate=clockmod.convertLOCtoUTC_datetime(thedateloc)

		if len(argument)>0:
			print("date ", thedate , " callbackname " , callbackname , " Element ", argument[0])
		else:
			print("date ", thedate , " callbackname " , callbackname)
		try:
			#print argument
			job = SchedulerMod.sched.add_job(callback, 'date', run_date=thedate, args=argument, misfire_grace_time=120, name=jobname)
		except ValueError as e:
			iserror=True
			print('Error: ', e)

	return iserror



def start_scheduler():
	SchedulerMod.start_scheduler()
	return True

def stop_scheduler():
	SchedulerMod.stop_scheduler()
	return True


def readselectedmaininfo(maininfo):
	maininfo.append("GrowingCycle")
	maininfo.append("Start")
	maininfo.append("Status")
	return True


def removeallscheduledjobs():
	SchedulerMod.removealljobs()
	return True

#--end --------////////////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':
	#SchedulerMod.start_scheduler()
	#setmastercallback()
	#SchedulerMod.print_job()
	#time.sleep(9999)
	#print("close")
	#SchedulerMod.stop_scheduler()

	REGandDBmod.register_input_value("RPItemperature","12")

