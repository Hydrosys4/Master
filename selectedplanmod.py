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
import fertilizerdbmod
import advancedmod
import emailmod
import networkmod
import clockmod

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

global FASTSCHEDULER
FASTSCHEDULER=True
global DATABASEPATH
DATABASEPATH="database"
global ITEMWEEKSROW
ITEMWEEKSROW=2
global HEARTBEATINTERVAL
HEARTBEATINTERVAL=15
global schedulercallback
global PRESETFILENAME
PRESETFILENAME='presetsettings.txt'

# ///////////////// --- END GLOBAL VARIABLES ------


#-- start filestorage utility--------////////////////////////////////////////////////////////////////////////////////////	
def dbpath(filename):
	return os.path.join(DATABASEPATH, filename)	

# filestoragemod.readfiledata(filename,filedata)
# filestoragemod.savefiledata(filename,filedata)
# filestoragemod.appendfiledata(filename,filedata)
# filestoragemod.savechange(filename,searchfield,searchvalue,fieldtochange,newvalue)
# filestoragemod.deletefile(filename)


	
#--start the scheduler call-back part--------////////////////////////////////////////////////////////////////////////////////////	

def pulsenutrient(target,activationseconds):
	duration=1000*hardwaremod.toint(activationseconds,0)
	print target, " ",duration, " " , datetime.now() 
	logging.info('Doser Pulse, pulse time for ms = %s', duration)
	hardwaremod.makepulse(target,duration)
	# salva su database
	actuatordbmod.insertdataintable(target,duration)


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
	duration=1000*hardwaremod.toint(activationseconds,0)
	print target, " ",duration, " " , datetime.now() 
	logging.info('Startpump evaluation')
	# evaluate parameters
	#MinAverageLight=500 not used now
	MinutesOfAverage=120 #minutes in which the average data is calculated from sensor sampling

	print "waterpump check"
	logging.info('execute water pump check %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

	# then check the temperature and Humidity

	print "Check Humidity and Temperature"
	
	hsensornamelist=hardwaremod.getsensornamebymeasure(hardwaremod.MEASURELIST[1])
	if hsensornamelist:
		sensordata=[]		
		hsensorname=hsensornamelist[0]  # get first found sensor in the list
		sensordbmod.getsensordbdata(hsensorname,sensordata)
		starttimecalc=datetime.now()-timedelta(minutes=int(MinutesOfAverage))
		humquantity=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())["average"]	
		logging.info('Waterpump Check parameter if humquantity=%s < MaxAverageHumid=%s ', str(humquantity), str(MaxAverageHumid))
		print 'Waterpump Check parameter if humquantity=',humquantity,' < MaxAverageHumid=' ,MaxAverageHumid
	
	tsensornamelist=hardwaremod.getsensornamebymeasure(hardwaremod.MEASURELIST[0])
	if tsensornamelist:
		sensordata=[]		
		tsensorname=tsensornamelist[0]  # get first found sensor in the list
		sensordbmod.getsensordbdata(tsensorname,sensordata)
		starttimecalc=datetime.now()-timedelta(minutes=int(MinutesOfAverage))
		tempquantity=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())["average"]	
		logging.info('Waterpump Check parameter if tempquantity=%s > MinAveragetemp=%s ', str(tempquantity), str(MinAveragetemp))
		print 'Waterpump Check parameter if tempquantity=',tempquantity,' > MinAveragetemp=' ,MinAveragetemp
	
	MinAveragetempnum=hardwaremod.tonumber(MinAveragetemp,"NA")
	MaxAverageHumidnum=hardwaremod.tonumber(MaxAverageHumid,"NA")
	
	# all the below conditions should be verified to start the PUMP
	pumpit=True
	
	if (MinAveragetempnum!="NA"):
		if (tempquantity>MinAveragetempnum):		
			logging.info('Temperature check PASSED, tempquantity=%s > MinAveragetemp=%s ', str(tempquantity), str(MinAveragetemp))			
		else:
			logging.info('Temperature check FAILED')
			print 'Temperature check FAILED'
			pumpit=False	
			
	if (MaxAverageHumidnum!="NA"):
		if (humquantity<MaxAverageHumidnum):		
			logging.info('Humidity check PASSED, humquantity=%s < MaxAverageHumid=%s ', str(humquantity), str(MaxAverageHumid))			
		else:
			logging.info('Humidity check FAILED')
			print 'Humidity check FAILED'
			pumpit=False			
		
	if pumpit:
		hardwaremod.makepulse(target,duration)
		# salva su database
		logging.info('Pump ON, optional time for sec = %s', duration)
		print 'Pump ON, optional time for sec =', duration
		actuatordbmod.insertdataintable(target,duration)
		


	
def periodicdatarequest(sensorname):
	print "Read sensors request: ", sensorname , " " , datetime.now()
	logging.info('Read sensor data: %s - %s', sensorname, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	sensorvalue=hardwaremod.getsensordata(sensorname,3)
	if sensorvalue!="":
		sensordbmod.insertdataintable(sensorname,sensorvalue)
	
def heartbeat():
	print "start heartbeat check", " " , datetime.now()
	logging.info('Start heartbeat routine %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	connectedssid=networkmod.connectedssid()
	if len(connectedssid)==0:
		logging.warning('Heartbeat check , no network connected -------------- try to connect')
		print 'Heartbeat check , no network connected -------------- try to connect'
		networkmod.connect_network()
	else:
		logging.info('Heartbeat check , Connected Wifi Network: %s ', connectedssid[0])
		if connectedssid[0]==networkmod.localwifisystem:
			logging.info('Heartbeat check , Configured as wifi access point, check if possible to connect to wifi network')
			networkmod.connect_network()
		else:		
			reachgoogle=networkmod.check_internet_connection(3)

			if not reachgoogle:
				logging.warning('Heartbeat check , test ping not able to reach Google -------------- try to connect')
				print 'Heartbeat check , no IP connection-------------- try to connect'
				networkmod.connect_network()
			else:
				logging.info('Heartbeat check , wifi connection OK')
				print 'Heartbeat check , wifi connection OK'				

	# Check if remote IP address is changed compared to previous communication and in such case resend the mail	
	ipext=networkmod.get_external_ip()
	if ipext!="":
		if ipext!=emailmod.IPEXTERNALSENT:
			print "Heartbeat check, IP address change detected. Send email with updated IP address"
			logging.info('Heartbeat check, IP address change detected. Send email with updated IP address')
			emailmod.sendallmail()

	# Check current time is less than 60 second different from NTP information
	# try to get the clock from network
	networktime=clockmod.getNTPTime()
	logging.info('Heartbeat check , Network time NTP: %s ', networktime)
	systemtime=clockmod.readsystemdatetime()
	logging.info('Heartbeat check , System time NTP: %s ', systemtime)
	if not networktime=='':
		diffsec=clockmod.timediffinsec(networktime, systemtime)
		if diffsec>60:
			print "Heartbeat check , warning difference between system time and network time >60 sec, diffsec = " , diffsec
			logging.warning('Heartbeat check , warning difference between system time and network time >60 sec, diffsec =  %d ', diffsec)
			print "Heartbeat check , Apply network datetime to system"
			logging.warning('Heartbeat check , Apply network datetime to system ')
			clockmod.setHWclock(networktime)
			clockmod.setsystemclock(networktime)
		else:
			print "Heartbeat check , Clock OK"
			logging.warning('Heartbeat check , Clock OK')
	else:
		print "not able to get network time"
		logging.warning('Heartbeat check , not able to get network time')

		
	return True
	
def sendmail(target):
	logging.info('send Mail %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	# save action in database
	issent=emailmod.sendmail(target)
	if issent:
		actuatordbmod.insertdataintable(target,1)
		print "Action", target , " " , datetime.now()
	
	
def takephoto(target):
	logging.info('take picture %s', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	hardwaremod.takephoto()
	# save action in database
	actuatordbmod.insertdataintable(target,1)
	print "Action", target ," " , datetime.now()

def setlight(MinimumLightinde,MaximumLightONinde):
	# removed because obsolete
	return True


"""
callback list should be defined after the function is defined
"""

schedulercallback={"heartbeat":heartbeat,"doser":pulsenutrient,"waterpump":startpump,"sensor":periodicdatarequest,"mail":sendmail,"photo":takephoto,"light":setlight}




# Master callback is scheduled each day at midnight

def setmastercallback():
	#set daily call for mastercallback at midnight
	starttime=datetime(datetime.now().year, datetime.now().month, datetime.now().day, 0, 0, 0)
	starttimeloc=starttime + timedelta(seconds=1)
	#convert to UTC time
	starttime=clockmod.convertLOCtoUTC_datetime(starttimeloc)
	print "setup master job"
	try:
		SchedulerMod.sched.add_job(mastercallback, 'interval', days=1, start_date=starttime, misfire_grace_time=120, name="master")
	except ValueError:
		print 'Date value for job scheduler not valid'
	mastercallback()

#add_job(func, trigger=None, args=None, kwargs=None, id=None, name=None, misfire_grace_time=undefined, coalesce=undefined, max_instances=undefined, next_run_time=undefined, jobstore='default', executor='default', replace_existing=False, **trigger_args)


def mastercallback():
	
	# clean old data of the database (pastdays)
	
	pastdays=364
	sensordbmod.RemoveSensorDataPeriod(pastdays)
	actuatordbmod.RemoveActuatorDataPeriod(pastdays)
	hardwaremod.removephotodataperiod(364)
	
	# Reset log file and back it up
	
	hardwaremod.resetandbackuplog()

	
	# remove all jobs except masterscheduler
	for job in SchedulerMod.sched.get_jobs():
		if job.name != "master":
			job.remove()	

	# set the individual callback of the day
	
	# info file dedicate call-back --------------------------------------------- (heartbeat)	
	
	#this callback is used only for system status periodic check 
	
	calltype="periodic"
	global HEARTBEATINTERVAL
	interval=HEARTBEATINTERVAL
	timelist=[0,interval,300] # 300 indicates to start after 5 minutes
	callback="heartbeat"
	argument=[]
	
	setschedulercallback(calltype,timelist,argument,callback,callback)
	
	
	
	# info file dedicate call-back --------------------------------------------- (sensor)
	
	hwnamelist=sensordbmod.gettablelist()
	callback="sensor"	
	for hwname in hwnamelist:
		calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,hwname,hardwaremod.HW_FUNC_SCHEDTYPE)
		timelist=hardwaremod.gettimedata(hwname)
		argument=[]
		argument.append(hwname)
		setschedulercallback(calltype,timelist,argument,callback,hwname)

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
	
	# info file dedicate call-back ------------------------------------------------ (waterpump)
	

	callback="waterpump"
	
	#water schedule table
	paramlist= wateringdbmod.getparamlist()  # name of the months ordered
	elementlist= wateringdbmod.getelementlist()  # pump ordered (based on "watercontrol" field)
	table=wateringdbmod.gettable(1)# table, each row is a pump, each column is a month, value is watering time multiplieer
	table1=wateringdbmod.gettable(0)# table, each row is a pump, each column is a month, value is watering scheme
	
	
	#print paramlist
	#print elementlistly
	#print table
	paramlistdrop= advancedmod.getparamlist() # day of the week
	elementlistdrop= advancedmod.getelementlist() # drops ordered
	tabledrop=advancedmod.gettable() # table, each row is a schema number (drop number), each column is a weekday

	for pumpnumber in range(len(elementlist)):
		print "number =",pumpnumber
		pumpname=elementlist[pumpnumber]
		todaydate = date.today()
		# Monday is 0 and Sunday is 6
		weekday = todaydate.weekday()
		month = todaydate.month	
		waterschemanumber=table1[pumpnumber][month-1]
		waterdropnumber=hardwaremod.toint(table[pumpnumber][month-1],0)
		if waterdropnumber>0:			
			#print " month  " , month, " drop  " , waterdropnumber
			calltype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,pumpname,hardwaremod.HW_FUNC_SCHEDTYPE)
			for todayevent in tabledrop[waterschemanumber-1][weekday]:
				
				timelist=hardwaremod.separatetimestringint(todayevent[0])
				
				argument=[]
				argument.append(pumpname)
				durationinseconds=hardwaremod.toint(todayevent[1],0)*waterdropnumber
				argument.append(durationinseconds)				
				for i in range(2,len(todayevent)):
						argument.append(todayevent[i])
				if durationinseconds>0: #check if the duration in second is >0
					setschedulercallback(calltype,timelist,argument,callback,pumpname)



	# info file dedicate call-back ------------------------------------------------ (pulsenutrient)
	

	callback="doser"

	
	#fertilizer schedule table
	paramlist= fertilizerdbmod.getparamlist()  # name of the months ordered
	elementlist= fertilizerdbmod.getelementlist()  # element with "fertilizercontrol field" ordered 
	table=fertilizerdbmod.gettable(1)# table, each row is a doser, each column is a month, value is number of times in a month	
	table1=fertilizerdbmod.gettable(0)# table, each row is a doser, each column is a month, value is pulse seconds	

	for dosernumber in range(len(elementlist)):
		print "number =",dosernumber
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
				timelist=hardwaremod.gettimedata("06:00:00")
				argument=[]
				argument.append(dosername)
				argument.append(fertilizerpulsesecond)
				if (fertilizerpulsesecond)>0: #check if the duration in second is >0
					setschedulercallback(calltype,timelist,argument,callback,dosername)



	
	
	
def setschedulercallback(calltype,timelist,argument,callbackname,jobname):
	# jobname is used as unique identifier of the job
	iserror=False	
	callback=schedulercallback[callbackname]
	if calltype=="periodic":
		try:
			theinterval=timelist[1]
			randomsecond=timelist[2]+1
			thedateloc=datetime.now()+timedelta(seconds=randomsecond)
			#convert to UTC time
			thedate=clockmod.convertLOCtoUTC_datetime(thedateloc)
			try:
				if not FASTSCHEDULER:
					SchedulerMod.sched.add_job(callback, 'interval', minutes=theinterval, start_date=thedate, args=argument, misfire_grace_time=120, name=jobname)
				else:
					SchedulerMod.sched.add_job(callback, 'interval', seconds=theinterval, start_date=thedate, args=argument, misfire_grace_time=120, name=jobname)
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



def start():
	SchedulerMod.start_scheduler()
	
def stop():
	SchedulerMod.stop_scheduler()


def readselectedmaininfo(maininfo):
	maininfo.append("GrowingCycle")
	maininfo.append("Start")
	maininfo.append("Status")
	return True

def startnewselectionplan():
	print "selected new table"
	SchedulerMod.removealljobs()
	print "are still jobs there"
	SchedulerMod.sched.print_jobs()
	setmastercallback()
	print "new jobs there"
	SchedulerMod.sched.print_jobs()	


	
	
#--end --------////////////////////////////////////////////////////////////////////////////////////		

	
if __name__ == '__main__':
	
	logging.basicConfig(filename="selectedplan.log", filemode='w', level=logging.INFO)
	logging.basicConfig(format='%(asctime)s %(message)s')
	#logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
	logging.info('Start logging --------------------------------------------')


	planname=plandbmod.getplanlist()[1]
	print planname
	table=[]
	table=plandbmod.getplantable(planname)
	#selplansave(table,planname)
	
	SchedulerMod.start_scheduler()
	setmastercallback()
	SchedulerMod.print_job()
	time.sleep(9999)
	print "close"
	SchedulerMod.stop_scheduler()
	
	






