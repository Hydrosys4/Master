# -*- coding: utf-8 -*-
"""
selected plan utility
"""

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
import autowateringmod
import fertilizerdbmod
import autofertilizermod
import advancedmod
import emailmod
import networkmod
import clockmod
import automationmod
import debuggingmod
import basicSetting

DEBUGMODE=basicSetting.data["DEBUGMODE"]

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

	
#--start the scheduler call-back part--------////////////////////////////////////////////////////////////////////////////////////	

def activateandregister(target,activationseconds): # function to activate the actuators
	duration=hardwaremod.toint(activationseconds,0)
	print target, " ",duration, " " , datetime.now() 
	logger.info('Doser Pulse, pulse time for ms = %s', duration)
	# start pulse
	pulseok=hardwaremod.makepulse(target,duration)
	# salva su database
	if "Started" in pulseok:
		actuatordbmod.insertdataintable(target,duration)
	return pulseok

def pulsenutrient(target,activationseconds): #scheduled doser activity for fertilizer
	duration=hardwaremod.toint(activationseconds,0)
	if autofertilizermod.isschedulermode(target):
		autofertilizermod.activatedoser(target, duration)
	else:
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


def startpump(target,activationseconds,MinAveragetemp,MaxAverageHumid):

	logger.info('WateringPlan Startpump evaluation: %s', target)	
	#workmode=autowateringmod.checkworkmode(target)
	#if workmode=="Full Auto":
	if target in autowateringmod.allowwateringplan:
		if not autowateringmod.allowwateringplan[target]:
			logger.info('WateringPlan: %s pump activation blocked by automation', target)
			pumpit=False
			return False
	
	duration=hardwaremod.toint(activationseconds,0)
	print target, " ",duration, " " , datetime.now() 

	# evaluate parameters
	#MinAverageLight=500 not used now
	MinutesOfAverage=120 #minutes in which the average data is calculated from sensor sampling

	print "waterpump check"
	logger.info('execute water pump check %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

	# then check the temperature and Humidity

	print "Check Humidity and Temperature"
	
	MinAveragetempnum=hardwaremod.tonumber(MinAveragetemp,"NA")
	MaxAverageHumidnum=hardwaremod.tonumber(MaxAverageHumid,"NA")
	
	# all the below conditions should be verified to start the PUMP
	pumpit=True	
	
	hsensornamelist=hardwaremod.getsensornamebymeasure(hardwaremod.MEASURELIST[1])
	if hsensornamelist:
		sensordata=[]		
		hsensorname=hsensornamelist[0]  # get first found sensor in the list
		sensordbmod.getsensordbdata(hsensorname,sensordata)
		starttimecalc=datetime.now()-timedelta(minutes=int(MinutesOfAverage))
		isok , quantitylist=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())
		humquantity=quantitylist["average"]

		logger.info('Waterpump Check parameter if humquantity=%s < MaxAverageHumid=%s ', str(humquantity), str(MaxAverageHumid))
		print 'Waterpump Check parameter if humquantity=',humquantity,' < MaxAverageHumid=' ,MaxAverageHumid
		
		if (MaxAverageHumidnum!="NA"):
			if (humquantity<MaxAverageHumidnum):		
				logger.info('Humidity check PASSED, humquantity=%s < MaxAverageHumid=%s ', str(humquantity), str(MaxAverageHumid))			
			else:
				logger.info('Humidity check FAILED')
				print 'Humidity check FAILED'
				pumpit=False			
		
	
	tsensornamelist=hardwaremod.getsensornamebymeasure(hardwaremod.MEASURELIST[0])
	if tsensornamelist:
		sensordata=[]		
		tsensorname=tsensornamelist[0]  # get first found sensor in the list
		sensordbmod.getsensordbdata(tsensorname,sensordata)
		starttimecalc=datetime.now()-timedelta(minutes=int(MinutesOfAverage))
		isok , quantitylist=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())
		tempquantity=quantitylist["average"]
		logger.info('Waterpump Check parameter if tempquantity=%s > MinAveragetemp=%s ', str(tempquantity), str(MinAveragetemp))
		print 'Waterpump Check parameter if tempquantity=',tempquantity,' > MinAveragetemp=' ,MinAveragetemp
		
		if (MinAveragetempnum!="NA"):
			if (tempquantity>MinAveragetempnum):		
				logger.info('Temperature check PASSED, tempquantity=%s > MinAveragetemp=%s ', str(tempquantity), str(MinAveragetemp))			
			else:
				logger.info('Temperature check FAILED')
				print 'Temperature check FAILED'
				pumpit=False	
				

	if pumpit:
		# activation of the doser before the pump
		doseron=autofertilizermod.checkactivate(target,duration)	
		# watering
		hardwaremod.makepulse(target,duration)
		# salva su database
		logger.info('Switch Pump %s ON, optional time for sec = %s', target, duration)
		print 'Pump ON, optional time for sec =', duration
		actuatordbmod.insertdataintable(target,duration)
		
	return True

	
def periodicdatarequest(sensorname):
	print "Read sensors request: ", sensorname , " " , datetime.now()
	logger.info('Read sensor data: %s - %s', sensorname, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	sensorvalue=hardwaremod.getsensordata(sensorname,3)
	if sensorvalue!="":
		sensordbmod.insertdataintable(sensorname,sensorvalue)
		# Automation algoritm 
		automationmod.automationcheck(sensorname)
		# call to automatic algorithms for watering
		autowateringmod.autowateringcheck(sensorname)
		
	return True	
	
	
def heartbeat():
	print "start heartbeat check", " " , datetime.now()
	logger.info('Start heartbeat routine %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	connectedssid=networkmod.connectedssid()
	connected=False
	if len(connectedssid)==0:
		logger.warning('Heartbeat check , no network connected -------------- try to connect')
		print 'Heartbeat check , no network connected -------------- try to connect'
		connected=networkmod.connect_network()
	else:
		logger.info('Heartbeat check , Connected Wifi Network: %s ', connectedssid[0])
		if connectedssid[0]==networkmod.localwifisystem:
			logger.info('Heartbeat check , Configured as wifi access point, check if possible to connect to wifi network')
			connected=networkmod.connect_network()
		else:		
			reachgoogle=networkmod.check_internet_connection(1)

			if not reachgoogle:
				logger.warning('Heartbeat check , test ping not able to reach Google -------------- No action')
				print 'Heartbeat check , no IP connection-------------- No action'
				#connected=networkmod.connect_network() # use this in case you require the system to try connect wifi again in case no internet is reached
				connected=False
			else:
				logger.info('Heartbeat check , wifi connection OK')
				print 'Heartbeat check , wifi connection OK'
				connected=True			

	if connected:
		# Check if remote IP address is changed compared to previous communication and in such case resend the mail	
		ipext=networkmod.get_external_ip()
		logger.info('Heartbeat check , Check IP address change -%s- and previously sent -%s-', ipext , emailmod.IPEXTERNALSENT)
		if (ipext!=""):
			if (emailmod.IPEXTERNALSENT!=""):
				if ipext!=emailmod.IPEXTERNALSENT:
					print "Heartbeat check, IP address change detected. Send email with updated IP address"
					logger.info('Heartbeat check, IP address change detected. Send email with updated IP address')
					emailmod.sendallmail("alert","System detected IP address change, below the updated links")
				else:
					logger.info('Heartbeat check, IP address unchanged')	
			else:
				# first mail has not been sent succesfully of IPEXTERNALSENT was not available by the time
				print "System has been reconnected"
				logger.info("System has been reconnected, IPEXTERNALSENT was empty")
				emailmod.sendallmail("alert","System has been reconnected")							

		# Check current time is less than 60 second different from NTP information
		# try to get the clock from network
		print "check system clock"
		logger.info('Heartbeat check, check clock')
		networktime=clockmod.getNTPTime()
		logger.info('Heartbeat check , Network time NTP: %s ', networktime)
		systemtime=clockmod.readsystemdatetime()
		logger.info('Heartbeat check , System time NTP: %s ', systemtime)
		if not networktime=='':
			diffsec=clockmod.timediffinsec(networktime, systemtime)
			logger.info('Heartbeat check , difference between system time and network time, diffsec =  %d ', diffsec)
			if diffsec>60:
				print "Heartbeat check , warning difference between system time and network time >60 sec, diffsec = " , diffsec
				logger.warning('Heartbeat check , warning difference between system time and network time >60 sec, diffsec =  %d ', diffsec)
				print "Heartbeat check , Apply network datetime to system"
				logger.warning('Heartbeat check , Apply network datetime to system ')
				clockmod.setHWclock(networktime)
				clockmod.setsystemclock(networktime)
			else:
				print "Heartbeat check , Clock OK"
				logger.info('Heartbeat check , Clock OK')
		else:
			print "not able to get network time"
			logger.warning('Heartbeat check , not able to get network time')
	else:
		print "not able to establish an internet connection"
		logger.warning("not able to establish an internet connection")			
	
	# check master job has a next run"
	isok, datenextrun = SchedulerMod.get_next_run_time("master")
	if isok:
		datenow=datetime.utcnow()
		datenextrun = datenextrun.replace(tzinfo=None)
		print "Master Scheduler Next run " , datenextrun , " Now (UTC) ", datenow
		if datenextrun>datenow:
			print "Masterschedule next RUN confirmed"
			logger.info('Heartbeat check , Master Scheduler OK')
		else:
			isok=False
			
	if not isok:
		print "No next run for master scheduler"
		logger.warning('Heartbeat check , Master Scheduler Interrupted')
		emailmod.sendallmail("alert","Master Scheduler has been interrupted, try to restart scheduler")
		resetmastercallback()
	
	# check if there have been errors in Syslog
	if DEBUGMODE:
		logger.info('Heartbeat check , check errors in Syslog file')
		Errortextlist=debuggingmod.searchsyslogkeyword("error")
		if Errortextlist:
			print "found error in syslog"
			logger.warning("ERROR: found error in syslog -------------------------")	
			#send notification mail 
			if debuggingmod.SENTERRORTEXT!=Errortextlist[0]:
				emailmod.sendallmail("alert","Error found in Syslog",Errortextlist)
				debuggingmod.SENTERRORTEXT=Errortextlist[0]
		else:
			print "No error found in syslog"
			logger.info('Heartbeat check , SYSLOG ok')		
			
	# check if there have been errors in Schedulerlog
	if DEBUGMODE:
		logger.info('Heartbeat check , check errors in Sched log file')
		filename="logfiles/apscheduler_hydrosystem.log"
		MYPATH=hardwaremod.get_path()
		filenameandpath=os.path.join(MYPATH, filename)
		Errortextlist=debuggingmod.searchLOGkeyword(filenameandpath,"error")
		if Errortextlist:
			print "found error in LOG ",filename
			logger.warning("ERROR: found error in LOG , %s -------------------------",filename)	
			#send notification mail 
			if debuggingmod.SENTERRORTEXT!=Errortextlist[0]:
				emailmod.sendallmail("alert","Error found in LOG",Errortextlist)
				debuggingmod.SENTERRORTEXT=Errortextlist[0]
		else:
			print "No error found in LOG", filename
			logger.info('Heartbeat check , LOG ok')					
				
				
		
	return True
	
def sendmail(target):
	logger.info('send Mail %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	# save action in database
	issent=emailmod.sendmail(target,"report","Periodic system report generated automatically")
	if issent:
		actuatordbmod.insertdataintable(target,1)
		print "Action", target , " " , datetime.now()
		
	return True	
	
def takephoto(target):
	logger.info('take picture %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	isok=hardwaremod.takephoto()
	# save action in database
	if isok:
		actuatordbmod.insertdataintable(target,1)
	print "Action", target ," " , datetime.now()	
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
	starttimeloc=thedateloc.replace(hour=0, minute=5, second=0)
	#convert to UTC time
	starttime=clockmod.convertLOCtoUTC_datetime(starttimeloc)
	print "setup master job"
	try:
		SchedulerMod.sched.add_job(mastercallback, 'interval', days=1, start_date=starttime, misfire_grace_time=120, name="master")
		logger.info('Master Scheduler - Started without errors')
	except ValueError:
		print 'Date value for job scheduler not valid'
		logger.warning('Heartbeat check , Master Scheduler not Started properly')
	mastercallback()
		
	return True


def waitandsetmastercallback(pulsesecond, offset):

	try:
		f=float(pulsesecond)
		secondint=int(f)+offset
	except:
		secondint=200
	print "try to setmastercallback after " , secondint , " seconds"		
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
	print "Reset scheduler, List existing jobs to be removed:"
	SchedulerMod.sched.print_jobs()
	SchedulerMod.removealljobs()
	print "list of jobs after removal:"
	SchedulerMod.sched.print_jobs()
	setmastercallback()	
	print "new jobs to be set in scheduler"
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
		print "Master heartbeat Next run " , datenextrun , " Now (UTC) ", datenow
		datenowplusone = datenow + timedelta(days=2)
		if (datenextrun>datenow)and(datenextrun<datenowplusone):
			print "heartbeat next RUN confirmed"
			logger.info('After connection heartbeat Scheduler OK')
		else:
			isok=False
			
	if not isok:
		print "No next run for heartbeat job"
		logger.warning('heartbeat job Interrupted, restarting the overall scheduler ')
		resetmastercallback()
	return isok

def waitandcheckheartbeat(pulsesecond):
	print "wait " , pulsesecond , " seconds"
	try:
		f=float(pulsesecond)
		secondint=int(f)
	except:
		secondint=180
	t = threading.Timer(secondint, checkheartbeat).start()

def mastercallback():
	
	# clean old data of the database (pastdays)
	logger.info('Remove data in exceed of one year')

	
	pastdays=364
	#sensordbmod.RemoveSensorDataPeriod(pastdays)
	logger.info('Sensor Remove data in exceed of one year')	
	#actuatordbmod.RemoveActuatorDataPeriod(pastdays)
	logger.info('Actuator Remove data in exceed of one year')
	#hardwaremod.removephotodataperiod(364)
	logger.info('Photo Remove data in exceed of one year')

	logger.info('Start other scheduler activities')
	
	# remove all jobs except masterscheduler
	#for job in SchedulerMod.sched.get_jobs():
	#	if job.name != "master":
	#		try:
	#			job.remove()	
	#		except:
	#			logger.error('Not able to remove Job %s', job.name)

	# set the individual callback of the day
	
	# info file dedicate call-back --------------------------------------------- (heartbeat)	
	
	#this callback is used only for system status periodic check 
	
	calltype="periodic"
	global HEARTBEATINTERVAL
	interval=HEARTBEATINTERVAL
	timelist=[0,interval,900] # 900 indicates to start after 15 minutes
	callback="heartbeat"
	argument=[]
	
	setschedulercallback(calltype,timelist,argument,callback,callback)
	
	logger.info('Start other scheduler activities - sensor')
	
	# info file dedicate call-back --------------------------------------------- (sensor)
	
	hwnamelist=sensordbmod.gettablelist()
	callback="sensor"
	timeshift=300
	shiftstep=5 #seconds	
	# IMPORTANT
	# the shiftstep is necessary to avoid thread collision which brings to sqlite3 db failure "database is locked" 
	# this number is giving a limit to the sensor reading that should be higher than 1min
	for hwname in hwnamelist:
		calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,hwname,hardwaremod.HW_FUNC_SCHEDTYPE)
		timelist=hardwaremod.gettimedata(hwname)
		timelist[2]=timeshift # avoid all the sensor thread to be called in the same time
		argument=[]
		argument.append(hwname)
		setschedulercallback(calltype,timelist,argument,callback,hwname)
		timeshift=timeshift+shiftstep

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
	paramlistdrop= advancedmod.getparamlist() # day of the week
	elementlistdrop= advancedmod.getelementlist() # drops ordered
	tabledrop=advancedmod.gettable() # table, each row is a schema number (drop number), each column is a weekday

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
			print "EXCEPTION: index out of range" 		
			waterdropnumber=0
			watertimedelaysec=0		
		
		if waterdropnumber>0:			
			#print " month  " , month, " drop  " , waterdropnumber
			calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,pumpname,hardwaremod.HW_FUNC_SCHEDTYPE)
			for todayevent in tabledrop[waterschemanumber-1][weekday]:
				
				timelist=hardwaremod.separatetimestringint(todayevent[0])
				timelist[2]=timelist[2]+watertimedelaysec
				argument=[]
				argument.append(pumpname)
				durationinseconds=hardwaremod.toint(todayevent[1],0)*waterdropnumber
				argument.append(durationinseconds)				
				for i in range(2,len(todayevent)):
						argument.append(todayevent[i])
				if durationinseconds>0: #check if the duration in second is >0
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
			dayinterval=themonthdays/fertilizerpulsenumber
			halfinterval=(dayinterval+1)/2
			print "day=" , day , " dayinterval=", dayinterval, " half=", halfinterval		
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
		try:
			theinterval=timelist[1]
			randomsecond=timelist[2]
			thedateloc=datetime.now()+timedelta(seconds=randomsecond)
			enddateloc=thedateloc.replace(hour=23, minute=59, second=59)
			#convert to UTC time
			thedate=clockmod.convertLOCtoUTC_datetime(thedateloc)
			#define end date for trigger
			enddate=clockmod.convertLOCtoUTC_datetime(enddateloc)

			try:
				if not FASTSCHEDULER:
					SchedulerMod.sched.add_job(callback, 'interval', minutes=theinterval, start_date=thedate, end_date=enddate ,args=argument, misfire_grace_time=120, name=jobname)
				else:
					SchedulerMod.sched.add_job(callback, 'interval', seconds=theinterval, start_date=thedate, end_date=enddate ,args=argument, misfire_grace_time=120, name=jobname)
			except ValueError:
				iserror=True
				print 'Date value for job scheduler not valid'
		except ValueError as e:
			iserror=True
			print 'Error: ', e
	else: # one shot type
		tday = date.today()
		todaydate = datetime(tday.year, tday.month, tday.day, 0, 0, 0)
		thedateloc=todaydate+timedelta(hours=timelist[0],minutes=timelist[1],seconds=timelist[2])
		#convert to UTC time
		thedate=clockmod.convertLOCtoUTC_datetime(thedateloc)
		
		if len(argument)>0:
			print "date ", thedate , " callbackname " , callbackname , " Pump line ", argument[0]
		else:
			print "date ", thedate , " callbackname " , callbackname 
		try:
			#print argument
			job = SchedulerMod.sched.add_job(callback, 'date', run_date=thedate, args=argument, misfire_grace_time=120, name=jobname)
		except ValueError as e:
			iserror=True
			print 'Error: ', e
	
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
	

	
	SchedulerMod.start_scheduler()
	setmastercallback()
	SchedulerMod.print_job()
	time.sleep(9999)
	print "close"
	SchedulerMod.stop_scheduler()
	
	






