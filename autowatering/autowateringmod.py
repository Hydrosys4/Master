import logging
from datetime import datetime, time ,timedelta
import hardwaremod
import emailmod
from autowatering import autowateringdbmod
import sensordbmod
import actuatordbmod
import autofertilizermod
import ActuatorControllermod
import messageboxmod

logger = logging.getLogger("hydrosys4."+__name__)





class ElementAutoBot:

	def __init__(self, element):
		self.status=StatusManager(element)
		self.element=element

	def UpdateStatus(self):
		self.status.ResetStatus()

	def UpdateConfig(self):
		self.status.LoadConfig()

	def ExecuteAutomation(self):
		ExecLogic.Execute(self.status)

	def GetStatus(self, name):
		return self.status.GetStatus(name)



class StatusManager:
	
	def __init__(self,element):
		self.element=element
		self.StatusDataDict={}
		self.ResetStatus()
		self.LoadConfig()


	def GetStatus(self, name):
		if name in self.StatusDataDict:
			return self.StatusDataDict[name]
		return ""


	def ResetStatus(self):
		#self.StatusDataDict={"cyclestartdate":datetime.utcnow(),"lastwateringtime":datetime.utcnow()- timedelta(days=5),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}
		self.StatusDataDict["allowwateringplan"]=True # define the flag that control the waterscheduling activation
		self.StatusDataDict["cyclestartdate"]=datetime.utcnow()
		waitingtime=hardwaremod.toint(autowateringdbmod.searchdata("element",self.element,"pausebetweenwtstepsmin"),0)
		self.StatusDataDict["lastwateringtime"]=datetime.utcnow() - timedelta(minutes=waitingtime)
		self.StatusDataDict["cyclestatus"]="done"
		self.StatusDataDict["currentstatus"]="OK"
		self.StatusDataDict["checkcounter"]=0
		self.StatusDataDict["alertcounter"]=0
		self.StatusDataDict["watercounter"]=0


	def LoadConfig(self):
		element=self.element
		# check if the element is present in the setting file, if not do not laod, the consistency check later will adjust it.
		if autowateringdbmod.recordmatch("element", element):

			self.sensor=autowateringdbmod.searchdata("element",element,"sensor")	
			self.workmode=autowateringdbmod.searchdata("element",element,"workmode")
			print (" threshold Value" , autowateringdbmod.searchdata("element",element,"threshold"))
			self.maxthreshold=hardwaremod.tonumber(autowateringdbmod.searchdata("element",element,"threshold")[1],0)
			self.minthreshold=hardwaremod.tonumber(autowateringdbmod.searchdata("element",element,"threshold")[0],self.maxthreshold)
			self.starttimeh=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"allowedperiod")[0].split(":")[0],0)
			self.starttimem=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"allowedperiod")[0].split(":")[1],0)
			self.endtimeh=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"allowedperiod")[1].split(":")[0],1)
			self.endtimem=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"allowedperiod")[1].split(":")[1],0)
			self.duration=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"wtstepsec"),0)
			self.maxstepnumber=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"maxstepnumber"),0)
			self.maxdays=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"maxdaysbetweencycles"),0)
			self.waitingtime=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),0)
			self.samplesminutes=hardwaremod.tonumber(autowateringdbmod.searchdata("element",element,"samplesminutes"),120) # new addition
			self.mailtype=autowateringdbmod.searchdata("element",element,"mailalerttype")
			self.rangeacceptedstr=autowateringdbmod.searchdata("element",element,"sensorminacceptedvalue")


class Messaging:

	@staticmethod
	def message(msg, status: StatusManager,  console=True, log=True, logseverity = "info", mail=False, mailtype="warningonly" , note=False):
		if console:
			print(msg)
		if log:
			Messaging.writelog(msg, logseverity)
		if mail:
			Messaging.writemail(msg, status, mailtype)
		if note:
			dictitem={'title': "System Message (Alert) - Autowatering", 'content': msg, 'color': "blue" }
			messageboxmod.SaveMessage(dictitem)
			

	@staticmethod
	def writelog(msg, logseverity):
		if logseverity=="info":
			logger.info(msg)
		elif logseverity=="warning":
			logger.warning(msg)
		else:
			logger.error(msg)

	@staticmethod
	def writemail(msg, status : StatusManager, mailtype):
		# invia mail, considered as info, not as alert
		if (status.mailtype==mailtype)and(status.mailtype!="none"):
			if (status.mailtype!="infoandwarning")and(status.StatusDataDict["alertcounter"]<5):
				emailmod.sendallmail("alert", msg)			
				status.StatusDataDict["alertcounter"]+=1
			if (status.mailtype=="infoandwarning"):
				emailmod.sendallmail("alert", msg)	





class ExecLogic:  # stateless

			
	@staticmethod
	def isNowInTimePeriod(status: StatusManager):

		now = datetime.now()
		nowTime = now.time()
		startTime=time(status.starttimeh,status.starttimem)
		endTime=time(status.endtimeh,status.endtimem)
		if startTime < endTime:
			return nowTime >= startTime and nowTime <= endTime
		else: #Over midnight
			return nowTime >= startTime or nowTime <= endTime


	@staticmethod
	def sensorreading(status : StatusManager):
		#MinutesOfAverage=70 #about one hour, 4 samples at 15min samples rate
		if status.sensor:
			# old
			#sensordata=[]		
			#sensordbmod.getsensordbdata(sensorname,sensordata)
			# get number of samples 
			timelist=hardwaremod.gettimedata(status.sensor)	
			theinterval=timelist[1] # minutes
			if theinterval>0:
				samplesnumber=int(status.samplesminutes/theinterval)+1
			else:
				samplesnumber=1	
			# new procedure should be faster on database reading for large amount of data
			sensordata=[]
			sensordbmod.getsensordbdatasamplesN(status.sensor,sensordata,samplesnumber)
			# still necessary to filter the sample based on timestamp, due to the possibility of missing samples
			starttimecalc=datetime.now()-timedelta(minutes=int(status.samplesminutes))
			isok, quantitylist=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())
			quantity=quantitylist["average"]	
		return 	quantity

	@staticmethod
	def lastsensorreading(status : StatusManager):
		if status.sensor:
			sensordata=[]		
			sensordbmod.getsensordbdata(status.sensor,sensordata)
			data=sensordata[-1]
			try:
				number=float(data[1])
			except:
				number=0
		return 	number	

	@staticmethod
	def sensorvalidrange(status : StatusManager, sensorreadingaverage):
		Messaging.message("Accepted range " + status.rangeacceptedstr, status)
		rangelist=status.rangeacceptedstr.split(":")
		sensorrangeok=True
		if len(rangelist)==2:
			try:
				mins=float(rangelist[0])
				maxs=float(rangelist[1])
				if (sensorreadingaverage<mins)or(sensorreadingaverage>maxs):			
					sensorrangeok=False
			except:
				Messaging.message("No valid parameter for sensor range , ignored ",status) 
		return sensorrangeok

	
	@staticmethod
	def checkMinMaxThreshold(status: StatusManager):
		belowthr=False
		abovethr=False
		validity=True		
		# check the hygrometer sensor levels 
		sensorreadingaverage=ExecLogic.sensorreading(status)
		sensorrangeok=ExecLogic.sensorvalidrange(status, sensorreadingaverage)
						
		if sensorrangeok:
			if (sensorreadingaverage<status.minthreshold):
				Messaging.message('Soil moisture check OK, activating watering procedure ',status)
				belowthr=True
			elif(sensorreadingaverage>status.maxthreshold):
				Messaging.message('Soil moisture check OK, activating watering procedure ',status)
				abovethr=True
			else:
				msg="Soil moisture check, Sensor reading=" +str(sensorreadingaverage) + "> Minimum threshold=" + str(status.minthreshold)		
				Messaging.message(msg,status)	

		else:	
			Messaging.message('Sensor reading outside acceptable range ' + str(sensorreadingaverage) + ' no action',status)
			validity=False

		return belowthr,abovethr,validity, sensorreadingaverage

	@staticmethod
	def checkwateringinterval(status: StatusManager):
		# check if time between watering events is larger that the waiting time (minutes)
		lastwateringtime=status.GetStatus("lastwateringtime")
		msg=' Previous watering: ' + str(lastwateringtime.strftime("%m/%d/%Y, %H:%M:%S")) + ' Now: ' + str(datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S"))
		Messaging.message(msg,status)
		timedifference=sensordbmod.timediffinminutes(lastwateringtime,datetime.utcnow())
		msg='Time interval between watering ' + str(timedifference) +'. threshold ' + str(status.waitingtime)
		Messaging.message(msg,status)	
		if timedifference>status.waitingtime:
			Messaging.message(" Sufficient waiting time",status)
			return True
		return False
				

	@staticmethod		
	def Execute(status: StatusManager):	

		# check the watering mode
		workmode=status.workmode


		if workmode=="None": # None case
			msg="No Action required, workmode set to None, element: " + str(status.element)
			Messaging.message(msg,status)
			return msg

		if not(status.sensor in sensordbmod.gettablelist()):
			msg="Sensor does not exist " + str(status.sensor) + ", element: " + str(status.element)
			Messaging.message(msg,status)		
			return msg
		
		# exit condition in case of data inconsistency
		if status.minthreshold>=status.maxthreshold:
			msg = "Data inconsistency Min Threshold higher than Max Threshold , element: " + str(status.element)
			Messaging.message(msg,status, logseverity="error")
			return msg
		
		# check relevant to the normal execution
		ExecuteRoutine=True
		timeok=ExecLogic.isNowInTimePeriod(status)
		if not timeok:
			Messaging.message("Outside allowed day time",status, logseverity="warning")
			ExecuteRoutine=False

		belowthr, abovethr,valid , value =ExecLogic.checkMinMaxThreshold(status)
		if not valid:
			Messaging.message("No valid sensor Value",status ,logseverity="warning", note=True, mail=True , mailtype="warning")
			ExecuteRoutine=False

		WaitOK= ExecLogic.checkwateringinterval(status)
		if not WaitOK:
			Messaging.message("Time from the last watering period too short",status, logseverity="warning")
			ExecuteRoutine=False

		if 	ExecuteRoutine==True:
			if workmode=="Full Auto":
				ExecLogic.ExecFullAuto(status, belowthr)
			elif workmode=="under MIN over MAX":
				ExecLogic.ExecUnderMinOverMax(status, belowthr, abovethr)
			else:
				msg="No Action, workmode set to unknown action, element: " + str(status.element)
				Messaging.message(msg,status)


		# safety procedures
		ExecLogic.ExceedingDaysSafety(status)
		if valid:
			ExecLogic.BelowThresholdSafety(status, value) # send alert message



	@staticmethod
	def ExecFullAuto(status: StatusManager, belowthr):

			Messaging.message("full Auto Mode  -->" + status.element, status)		
			# block the wateringplan activation as by definition of "Full Auto"
			status.StatusDataDict["allowwateringplan"]=False
			# check if inside the allowed time period

			if belowthr:
				Messaging.message('below threshold',status , logseverity="warning" )
				status.StatusDataDict["currentstatus"]="lowthreshold"

				#activate pump		
				ExecLogic.activatewater(status.element, status.duration)
				# invia mail, considered as info, not as alert
				msg="INFO: " + str(status.sensor) + " value below the minimum threshold " + str(status.minthreshold) + ", activating the watering :" + str(status.element)
				Messaging.message(msg, status, mail=True, mailtype="infoandwarning")
				status.StatusDataDict["watercounter"]+=1
				status.StatusDataDict["lastwateringtime"]=datetime.utcnow()

				# send warning in case max step is exceeded				
				if status.maxstepnumber<status.StatusDataDict["watercounter"]:
				# critical, sensor below minimum after maxstep
					msg='critical, sensor below minimum threshold after '+ str(status.StatusDataDict["watercounter"])  + ' watring tiems'
					Messaging.message(msg, status, logseverity="warning", mail=True, mailtype="warning", note=True)
					status.StatusDataDict["alertcounter"]+=1

			else: #above threshold reset the counters
				status.StatusDataDict["alertcounter"]=0
				status.StatusDataDict["watercounter"]=0												
				status.StatusDataDict["checkcounter"]=0
				status.StatusDataDict["currentstatus"]="OK"
													

	@staticmethod
	def ExecUnderMinOverMax(status: StatusManager, belowthr , abovethr):	
	
		Messaging.message('under MIN over MAX', status)
		# normally watering plan is allowed unless over MAX threshold
		status.StatusDataDict["allowwateringplan"]=True
		# check if inside the allow time period
		if belowthr:
			Messaging.message('below threshold', status, logseverity="warning")
			status.StatusDataDict["currentstatus"]="lowthreshold"

			#activate pump		
			ExecLogic.activatewater(status.element, status.duration)
			# invia mail, considered as info, not as alert
			msg="INFO: " + str(status.sensor) + " value below the minimum threshold " + str(status.minthreshold) + ", activating the watering :" + str(status.element)
			Messaging.message(msg, status, mail=True, mailtype="infoandwarning")
			status.StatusDataDict["watercounter"]+=1
			status.StatusDataDict["lastwateringtime"]=datetime.utcnow()

			# send warning in case max step is exceeded				
			if status.maxstepnumber<status.StatusDataDict["watercounter"]:
			# critical, sensor below minimum after maxstep
				msg='ALERT, sensor below minimum threshold after '+ str(status.StatusDataDict["watercounter"])  + ' watring tiems'
				Messaging.message(msg, status,  logseverity="warning", mail=True, mailtype="warning", note=True)
				status.StatusDataDict["alertcounter"]+=1


		else: # above minimum threshold
			status.StatusDataDict["alertcounter"]=0
			status.StatusDataDict["watercounter"]=0												
			status.StatusDataDict["checkcounter"]=0
			status.StatusDataDict["currentstatus"]="OK"		
			
			if abovethr: # sensor reading above max threshold
				msg = 'sensor reading above MAX threshold, deactivate scheduled irrigation'
				Messaging.message(msg, status)
				# do not activate the irrigation scheduled in the time plan
				status.StatusDataDict["allowwateringplan"]=False
							
						

	@staticmethod
	def ExceedingDaysSafety(status: StatusManager):			

		# implment alert message for the cycle exceeding days, and reset the cycle
		if status.workmode!="Full Auto":
			lastwateringtime=status.StatusDataDict["lastwateringtime"]
			timedeltadays=sensordbmod.timediffdays(datetime.utcnow(),lastwateringtime)
			if (timedeltadays > status.maxdays)and(timedeltadays < status.maxdays+2):  #the upper limit is set in case of abrupt time change	
				msg="WARNING "+ str(status.sensor) + " watering cycle is taking too many days, watering system: " + str(status.element) + ". Activate Water + Reset watering cycle"
				Messaging.message(msg, status, logseverity="warning",  note=True , mail=True, mailtype="warning")
				ExecLogic.activatewater(status.element, status.duration)

				status.StatusDataDict["lastwateringtime"]=datetime.utcnow()
				status.StatusDataDict["alertcounter"]=0
				status.StatusDataDict["watercounter"]=0												
				status.StatusDataDict["checkcounter"]=0
				status.StatusDataDict["currentstatus"]="OK"	


	@staticmethod
	def BelowThresholdSafety(status: StatusManager, value):	

		# implment Critical alert message in case the threshold is below the 0.5 of the minimum
		multiplier=50
		if status.workmode!="None":
			if value<(status.minthreshold*multiplier/100):
					msg='CRITICAL: Sensor ' + str(status.sensor) + ' below ' + str(multiplier) + 'percent of the actual set threshold'
					Messaging.message(msg, status,logseverity="warning", note=True, mail=True, mailtype="warning" )
		
	

	@staticmethod
	def activatewater(element, duration):
		# check the activation of the doser before the pump
		doseron=autofertilizermod.checkactivate(element,duration) # this has a blocking sleep command
		#activate pump		
		#msg , pulseok=hardwaremod.makepulse(element,duration)
		msg, pulseok = ActuatorControllermod.activateactuator(element,duration)

		# salva su database
		if pulseok:
			actuatordbmod.insertdataintable(element,duration)
		return msg



class AutoBotManagement:
	
	AutoBotDict={}  # global variable of teh class
	
	def __init__(self):
		# send callback link to the autowateringdbmod
		autowateringdbmod.register_callback("UpdateBots" , self.UpdateBots)
		elementlist= autowateringdbmod.getelementlist()	
		for element in elementlist:
			self.AddElement(element)

	def DeleteAutoBot(self,element):
		if element:
			AutoBotManagement.AutoBotDict.pop(element)

	def AddElement(self,element):
		AutoBotManagement.AutoBotDict[element]=ElementAutoBot(element) # inizialize the ElementBot

	def UpdateBots(self,elementlist,tabletoadd,tabletoremove):
		for element in tabletoadd: 
			self.AddElement(element)
		for element in tabletoremove:
			self.DeleteAutoBot(element)
		for element in elementlist:
			if element in AutoBotManagement.AutoBotDict:
				AutoBotManagement.AutoBotDict[element].UpdateConfig()


# execute this line of code when module is called
AutoBot=AutoBotManagement()

# functionns to be called externally by other modules not belonging to this folder
	
def autowateringcheck(refsensor):
	logger.info('Starting Autowatering Evaluation ')
	# iterate among the water actuators
	elementlist= autowateringdbmod.getelementlist()	
	for element in elementlist: 
		sensor=autowateringdbmod.searchdata("element",element,"sensor")	
		# check the sensor
		if refsensor==sensor:	
			print("auto watering check -----------------------------------------> ", element)
			logger.info('auto watering check --------------------------> %s', element)
			AutoBot.AutoBotDict[element].ExecuteAutomation()
	return

def cycleresetall():
	logger.info('Reset all the Status in the autowatering ')
	for bot in AutoBot.AutoBotDict.values():
		bot.UpdateStatus()

def cyclereset(element):
	AutoBot.AutoBotDict[element].UpdateStatus()

def configupdate(element):
	AutoBot.AutoBotDict[element].UpdateConfig()

def getstatus(element, name):
	if element in AutoBot.AutoBotDict:
		return AutoBot.AutoBotDict[element].GetStatus(name)
	return None



# ----------------------------------------------------










if __name__ == '__main__':
	
	autowateringcheck("Hygro21")
	

