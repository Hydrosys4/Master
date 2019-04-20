import logging
from datetime import datetime, time ,timedelta
import hardwaremod
import os
import subprocess
import emailmod
import autowateringdbmod
import sensordbmod
import actuatordbmod
import autofertilizermod
import statusdataDBmod

logger = logging.getLogger("hydrosys4."+__name__)

# status array, required to check the ongoing actions within a watering cycle
elementlist= autowateringdbmod.getelementlist()
AUTO_data={} # dictionary of dictionary
AUTO_data["default"]={"cyclestartdate":datetime.now(),"lastwateringtime":datetime.now(),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}
allowwateringplan={} # define the flag that control the waterscheduling activation
# cyclestartdate, datetime of the latest cycle start
# cyclestatus, describe the status of the cycle: lowthreshold, rampup, done
#     "lowthreshold" means that the cycle is just started with lowthreshold activation, if the lowthreshold persists for several checks them alarm should be issued  
#     "rampup", this is in full auto mode, the status in between the lowthreshold and high, not reach yet high. if this status persist then alarm should be issued
#     "done", ready for next start with lowthreshold

# sample of database filed
# {"element": "", "threshold": ["2.0", "4.0"],"workmode": "None","sensor": "","wtstepsec": "100","maxstepnumber": "3","allowedperiod": ["21:00","05:00"],"maxdaysbetweencycles": "10", "pausebetweenwtstepsmin":"45", "mailalerttype":"warningonly" , "sensorminacceptedvalue":"0.5"}


def cyclereset(element):
	global AUTO_data
	waitingtime=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),0)
	AUTO_data[element]={"cyclestartdate":datetime.now(),"lastwateringtime":datetime.now() - timedelta(minutes=waitingtime),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}

def cycleresetall():
	global AUTO_data
	elementlist= autowateringdbmod.getelementlist()
	for element in elementlist:
		AUTO_data[element]={"cyclestartdate":datetime.now(),"lastwateringtime":datetime.now(),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}


def autowateringcheck(refsensor):
	logger.info('Starting Autowatering Evaluation ')
	# iterate among the water actuators
	elementlist= autowateringdbmod.getelementlist()	
	for element in elementlist: 
		autowateringexecute(refsensor,element)
	return
		
		
def autowateringexecute(refsensor,element):	
	global AUTO_data
	sensor=autowateringdbmod.searchdata("element",element,"sensor")	
	# check the sensor
	if refsensor==sensor:	
		print "auto watering check -----------------------------------------> ", element
		logger.info('auto watering check --------------------------> %s', element)
		# check the watering mode
		modelist=["None", "Full Auto" , "Emergency Activation" , "Alert Only"]
		workmode=checkworkmode(element)

		if not(sensor in sensordbmod.gettablelist()):
			print "Sensor does not exist " ,sensor , ", element: " , element
			logger.error("Sensor does not exist %s , element: %s " ,sensor, element)			
			return "sensor not Exist"
		
		maxthreshold=hardwaremod.tonumber(autowateringdbmod.searchdata("element",element,"threshold")[1],0)
		minthreshold=hardwaremod.tonumber(autowateringdbmod.searchdata("element",element,"threshold")[0],maxthreshold)
		# exit condition in case of data inconsistency
		if minthreshold>=maxthreshold:
			print "Data inconsistency , element: " , element
			logger.error("Data inconsistency , element: %s " , element)
			return "data inconsistency"
		
		now = datetime.now()
		nowtime = now.time()
		starttimeh=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"allowedperiod")[0].split(":")[0],0)
		starttimem=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"allowedperiod")[0].split(":")[1],0)
		endtimeh=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"allowedperiod")[1].split(":")[0],1)
		endtimem=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"allowedperiod")[1].split(":")[1],0)
		starttime=time(starttimeh,starttimem)
		endtime=time(endtimeh,endtimem)		
		
		duration=1000*hardwaremod.toint(autowateringdbmod.searchdata("element",element,"wtstepsec"),0)
		maxstepnumber=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"maxstepnumber"),0)
		maxdays=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"maxdaysbetweencycles"),0)
		waitingtime=hardwaremod.toint(autowateringdbmod.searchdata("element",element,"pausebetweenwtstepsmin"),0)
		mailtype=autowateringdbmod.searchdata("element",element,"mailalerttype")
		minaccepted=hardwaremod.tonumber(autowateringdbmod.searchdata("element",element,"sensorminacceptedvalue"),0.1)
		
		# ------------------------ Workmode split
		if workmode=="Full Auto":
			# block the wateringplan activation as by definition of "Full Auto"
			allowwateringplan[element]=False
			# check if inside the allowed time period
			print "full Auto Mode"
			logger.info('full auto mode --> %s', element)
			timeok=isNowInTimePeriod(starttime, endtime, nowtime)
			print "inside allowed time ", timeok , " starttime ", starttime , " endtime ", endtime
			logger.info('full auto mode')
			if timeok:
				logger.info('inside allowed time')
				belowthr,valid=checkminthreshold(sensor,minthreshold,minaccepted)
				if valid:
					if belowthr:
						status="lowthreshold"
						logger.info('below threshold')
						# wait to seek a more stable reading of hygrometer
						# check if time between watering events is larger that the waiting time (minutes)
						lastwateringtime=statusdataDBmod.read_status_data(AUTO_data,element,"lastwateringtime")
						print ' Previous watering: ' , lastwateringtime , ' Now: ', datetime.now()
						timedifference=sensordbmod.timediffinminutes(lastwateringtime,datetime.now())
						print 'Time interval between watering steps', timedifference ,'. threshold', waitingtime
						logger.info('Time interval between watering steps %d threshold %d', timedifference,waitingtime)		
						if timedifference>waitingtime:
							print " Sufficient waiting time"
							logger.info('Sufficient waiting time')	
							# activate watering in case the maxstepnumber is not exceeded	
							watercounter=statusdataDBmod.read_status_data(AUTO_data,element,"watercounter")				
							if maxstepnumber>watercounter:
								#activate pump		
								activatewater(element, duration)
								# invia mail, considered as info, not as alert
								if mailtype!="warningonly":
									textmessage="INFO: " + sensor + " value below the minimum threshold " + str(minthreshold) + ", activating the watering :" + element
									emailmod.sendallmail("alert", textmessage)
								statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",watercounter+1)
								statusdataDBmod.write_status_data(AUTO_data,element,"lastwateringtime",datetime.now())								
							else: # critical, sensor below minimum after all watering activations are done

								logger.info('Number of watering time per cycle has been exceeeded')
								# read hystory data and calculate the slope
								timelist=hardwaremod.gettimedata(sensor)
								cyclestartdate=statusdataDBmod.read_status_data(AUTO_data,element,"cyclestartdate")	
								lastwateringtime=statusdataDBmod.read_status_data(AUTO_data,element,"lastwateringtime")
								startdate=cyclestartdate - timedelta(minutes=timelist[1])
								enddate=lastwateringtime + timedelta(minutes=waitingtime)
								isslopeok=checkinclination(sensor,startdate,enddate) # still to decide if use the enddate 
								
								if isslopeok:
									# invia mail if couner alert is lower than 1
									alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
									if alertcounter<1:
										textmessage="WARNING: Please consider to increase the amount of water per cycle, the "+ sensor + " value below the MINIMUM threshold " + str(minthreshold) + " still after activating the watering :" + element + " for " + str(maxstepnumber) + " times. System will automatically reset the watering cycle to allow more water"
										print textmessage
										#send alert mail notification
										emailmod.sendallmail("alert", textmessage)							
										logger.error(textmessage)
										statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)
										
									# reset watering cycle
									status="done"
									statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
									statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",-1)
									statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)
									statusdataDBmod.write_status_data(AUTO_data,element,"cyclestartdate",datetime.now())
																			
								else: # slope not OK, probable hardware problem
									alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
									if alertcounter<3:
										textmessage="CRITICAL: Possible hardware problem, "+ sensor + " value below the MINIMUM threshold " + str(minthreshold) + " still after activating the watering :" + element + " for " + str(maxstepnumber) + " times"
										print textmessage
										#send alert mail notification
										emailmod.sendallmail("alert", textmessage)							
										logger.error(textmessage)										
										statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)
									
											
						# update the status
						checkcounter=statusdataDBmod.read_status_data(AUTO_data,element,"checkcounter")
						statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus",status)
						statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",checkcounter+1)
						
					# RAMPUP case above threshold but below maxthreshold
					elif sensorreading(sensor)<maxthreshold: # intermediate state where the sensor is above the minthreshold but lower than the max threshold
						# check the status of the automatic cycle
						cyclestatus=statusdataDBmod.read_status_data(AUTO_data,element,"cyclestatus")
						if cyclestatus!="done":
							status="rampup"							
							# wait to seek a more stable reading of hygrometer
							# check if time between watering events is larger that the waiting time (minutes)
							lastwateringtime=statusdataDBmod.read_status_data(AUTO_data,element,"lastwateringtime")			
							if sensordbmod.timediffinminutes(lastwateringtime,datetime.now())>waitingtime:
								watercounter=statusdataDBmod.read_status_data(AUTO_data,element,"watercounter")
								if maxstepnumber>watercounter:
									#activate pump		
									activatewater(element, duration)
									# invia mail, considered as info, not as alert
									if mailtype!="warningonly":
										textmessage="INFO: " + sensor + " value below the Maximum threshold " + str(maxthreshold) + ", activating the watering :" + element
										emailmod.sendallmail("alert", textmessage)
										
									statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",watercounter+1)
									statusdataDBmod.write_status_data(AUTO_data,element,"lastwateringtime",datetime.now())										

								else:
									# give up to reache the maximum threshold, proceed as done, send alert
									logger.info('Number of watering time per cycle has been exceeeded')
									
									# invia mail if couner alert is lower than 1 --------------
									# only if the info is activated
									if mailtype!="warningonly":
										alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")	
										if alertcounter<2:
											textmessage="INFO "+ sensor + " value below the Maximum threshold " + str(maxthreshold) + " still after activating the watering :" + element + " for " + str(maxstepnumber) + " times"
											print textmessage
											#send alert mail notification
											emailmod.sendallmail("alert", textmessage)							
											logger.error(textmessage)	
											statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)								
									
									# reset watering cycle					
									status="done"	
									statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
									statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",-1)
									statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)
									statusdataDBmod.write_status_data(AUTO_data,element,"cyclestartdate",datetime.now())

																	

							# update the status							
							checkcounter=statusdataDBmod.read_status_data(AUTO_data,element,"checkcounter")
							statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus",status)
							statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",checkcounter+1)
					
					else:
						# update the status, reset cycle
						statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus","done")
						statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",0)
						statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
						statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)														
			
			
		elif workmode=="Emergency Activation":
			# check if inside the allow time period
			logger.info('Emergency Mode')
			timeok=isNowInTimePeriod(starttime, endtime, nowtime)
			print "inside allowed time ", timeok , " starttime ", starttime , " endtime ", endtime
			if timeok:			
				belowthr,valid=checkminthreshold(sensor,minthreshold,minaccepted)
				if valid:
					if belowthr:
						# wait to seek a more stable reading of hygrometer
						# check if time between watering events is larger that the waiting time (minutes)
						
						lastwateringtime=statusdataDBmod.read_status_data(AUTO_data,element,"lastwateringtime")			
						if sensordbmod.timediffinminutes(lastwateringtime,datetime.now())>waitingtime:
							# activate watering in case the maxstepnumber is not exceeded			
							watercounter=statusdataDBmod.read_status_data(AUTO_data,element,"watercounter")		
							if maxstepnumber>watercounter:			
								#activate pump		
								activatewater(element, duration)
								# invia mail, considered as info, not as alert
								if mailtype!="warningonly":
									textmessage="INFO: " + sensor + " value below the minimum threshold " + str(minthreshold) + ", activating the watering :" + element
									emailmod.sendallmail("alert", textmessage)

								statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",watercounter+1)
								statusdataDBmod.write_status_data(AUTO_data,element,"lastwateringtime",datetime.now())									
								
								
							else:

								logger.info('Number of watering time per cycle has been exceeeded')
								# read hystory data and calculate the slope
								timelist=hardwaremod.gettimedata(sensor)
								cyclestartdate=statusdataDBmod.read_status_data(AUTO_data,element,"cyclestartdate")	
								lastwateringtime=statusdataDBmod.read_status_data(AUTO_data,element,"lastwateringtime")	
								startdate=cyclestartdate - timedelta(minutes=timelist[1])
								enddate=lastwateringtime + timedelta(minutes=waitingtime)
								isslopeok=checkinclination(sensor,startdate,enddate)
								
								if isslopeok:
									# invia mail if couner alert is lower than 1
									alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
									if alertcounter<1:
										textmessage="WARNING: Please consider to increase the amount of water per cycle, the "+ sensor + " value below the MINIMUM threshold " + str(minthreshold) + " still after activating the watering :" + element + " for " + str(maxstepnumber) + " times. System will automatically reset the watering cycle to allow more water"
										print textmessage
										#send alert mail notification alertcounter
										emailmod.sendallmail("alert", textmessage)							
										logger.error(textmessage)
										statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)
										
									# reset watering cycle
									status="done"
									statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
									statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",-1)
									statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)
									statusdataDBmod.write_status_data(AUTO_data,element,"cyclestartdate",datetime.now())
																			
								else: # slope not OK, probable hardware problem
									alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
									if alertcounter<3:
										textmessage="CRITICAL: Possible hardware problem, "+ sensor + " value below the MINIMUM threshold " + str(minthreshold) + " still after activating the watering :" + element + " for " + str(maxstepnumber) + " times"
										print textmessage
										#send alert mail notification
										emailmod.sendallmail("alert", textmessage)							
										logger.error(textmessage)
										statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)			
		
									
						# update the status
						checkcounter=statusdataDBmod.read_status_data(AUTO_data,element,"checkcounter")
						statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus","lowthreshold")
						statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",checkcounter+1)
					else:
						# update the status		
						statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus","done")
						statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",0)
						statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
						statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)		
	
			
		elif workmode=="under MIN over MAX":
			logger.info('under MIN over MAX')
			# normally watering plan is allowed unless over MAX threshold
			allowwateringplan[element]=True
			# check if inside the allow time period
			timeok=isNowInTimePeriod(starttime, endtime, nowtime)
			print "inside allowed time ", timeok , " starttime ", starttime , " endtime ", endtime
			if timeok:			
				logger.info('Insede operative time')
				belowthr,valid=checkminthreshold(sensor,minthreshold,minaccepted)
				if valid:
					logger.info('valid sensor reading')
					if belowthr:
						logger.info('sensor reading below threshold')
						# wait to seek a more stable reading of hygrometer
						# check if time between watering events is larger that the waiting time (minutes)			

						lastwateringtime=statusdataDBmod.read_status_data(AUTO_data,element,"lastwateringtime")			
						if sensordbmod.timediffinminutes(lastwateringtime,datetime.now())>waitingtime:
							# activate watering in case the maxstepnumber is not exceeded			
							watercounter=statusdataDBmod.read_status_data(AUTO_data,element,"watercounter")		
							if maxstepnumber>watercounter:
								logger.info('water Count not exceeded')			
								#activate pump		
								activatewater(element, duration)
								# invia mail, considered as info, not as alert
								if mailtype!="warningonly":
									textmessage="INFO: " + sensor + " value below the minimum threshold " + str(minthreshold) + ", activating the watering :" + element
									emailmod.sendallmail("alert", textmessage)								
								statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",watercounter+1)
								statusdataDBmod.write_status_data(AUTO_data,element,"lastwateringtime",datetime.now())	
								
								
							else:

								logger.info('Number of watering time per cycle has been exceeeded')
								# read hystory data and calculate the slope
								timelist=hardwaremod.gettimedata(sensor)
								
								cyclestartdate=statusdataDBmod.read_status_data(AUTO_data,element,"cyclestartdate")	
								lastwateringtime=statusdataDBmod.read_status_data(AUTO_data,element,"lastwateringtime")
								startdate=cyclestartdate - timedelta(minutes=timelist[1])
								enddate=lastwateringtime + timedelta(minutes=waitingtime)
								isslopeok=checkinclination(sensor,startdate,enddate)
								
								if isslopeok:
									# invia mail if couner alert is lower than 1
									alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
									if alertcounter<1:
										textmessage="WARNING: Please consider to increase the amount of water per cycle, the "+ sensor + " value below the MINIMUM threshold " + str(minthreshold) + " still after activating the watering :" + element + " for " + str(maxstepnumber) + " times. System will automatically reset the watering cycle to allow more water"
										print textmessage
										#send alert mail notification
										emailmod.sendallmail("alert", textmessage)							
										logger.error(textmessage)
										statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)
										
									# reset watering cycle
									status="done"
									statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
									statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",-1)
									statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)
									statusdataDBmod.write_status_data(AUTO_data,element,"cyclestartdate",datetime.now())
																			
								else: # slope not OK, probable hardware problem
									alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
									if alertcounter<3:
										textmessage="CRITICAL: Possible hardware problem, "+ sensor + " value below the MINIMUM threshold " + str(minthreshold) + " still after activating the watering :" + element + " for " + str(maxstepnumber) + " times"
										print textmessage
										#send alert mail notification
										emailmod.sendallmail("alert", textmessage)							
										logger.error(textmessage)
										statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)			
		
									
						# update the status
						checkcounter=statusdataDBmod.read_status_data(AUTO_data,element,"checkcounter")
						statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus","lowthreshold")
						statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",checkcounter+1)
						
					else: # above minimum threshold
						logger.info('sensor reading above min threshold')
						# update the status
						statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus","done")
						statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",0)
						statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
						statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)		
						
						if sensorreading(sensor)>maxthreshold:
							logger.info('sensor reading above MAX threshold, deactivate scheduled irrigation')
							# do not activate the irrigation scheduled in the time plan
							allowwateringplan[element]=False
							
						

		elif workmode=="Alert Only":
			belowthr,valid=checkminthreshold(sensor,minthreshold,minaccepted)
			if valid:
				if belowthr:
					# invia mail if couter alert is lower than
					alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")	
					if alertcounter<2:
						textmessage="WARNING "+ sensor + " value below the minimum threshold " + str(minthreshold) + " watering system: " + element
						print textmessage
						#send alert mail notification
						emailmod.sendallmail("alert", textmessage)							
						logger.error(textmessage)
						statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)
					# update the status
					checkcounter=statusdataDBmod.read_status_data(AUTO_data,element,"checkcounter")
					statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus","lowthreshold")
					statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",checkcounter+1)
				else:
					# update the status	
					statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus","done")
					statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",0)
					statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
					statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)						
							
			
		else: # None case
			print "No Action required, workmode set to None, element: " , element
			logger.info("No Action required, workmode set to None, element: %s " , element)

		cyclestatus=statusdataDBmod.read_status_data(AUTO_data,element,"cyclestatus")
		if cyclestatus=="lowthreshold":
			checkcounter=statusdataDBmod.read_status_data(AUTO_data,element,"checkcounter")
			if checkcounter==1:			
				statusdataDBmod.write_status_data(AUTO_data,element,"cyclestartdate",datetime.now())

		# implment alert message for the cycle exceeding days, and reset the cycle
		if workmode!="None":
			cyclestartdate=statusdataDBmod.read_status_data(AUTO_data,element,"cyclestartdate")
			timedeltadays=sensordbmod.timediffdays(datetime.now(),cyclestartdate)
			if (timedeltadays > maxdays): #the upper limit is set in case of abrupt time change
				textmessage="WARNING "+ sensor + " watering cycle is taking too many days, watering system: " + element + ". Reset watering cycle"
				print textmessage
				# in case of full Auto, activate pump for minimum pulse period
				if workmode=="Full Auto":
					if (timedeltadays < maxdays+2): #the upper limit is set in case of abrupt time change					
						textmessage="WARNING "+ sensor + " watering cycle is taking too many days, watering system: " + element + ". Activate Min pulse + Reset watering cycle"					
						activatewater(element, duration)
				#send alert mail notification
				if mailtype!="warningonly":
					emailmod.sendallmail("alert", textmessage)							
				logger.error(textmessage)
				logger.error("Cycle started %s, Now is %s ", cyclestartdate.strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))			
				# reset cycle
				statusdataDBmod.write_status_data(AUTO_data,element,"cyclestatus","done")
				statusdataDBmod.write_status_data(AUTO_data,element,"checkcounter",0)
				statusdataDBmod.write_status_data(AUTO_data,element,"watercounter",0)
				statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",0)	
				statusdataDBmod.write_status_data(AUTO_data,element,"cyclestartdate",datetime.now())

		# implment Critical alert message in case the threshold is below the 0.5 of the minimum
		if workmode!="None":
			belowthr,valid=checkminthreshold(sensor,minthreshold*0.5,minaccepted)
			if valid:
				if belowthr:
					logger.info('sensor %s below half of the actual set threshold', sensor)
					textmessage="CRITICAL: Plant is dying, "+ sensor + " reading below half of the minimum threshold, need to check the " + element
					print textmessage
					#send alert mail notification
					alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
					if alertcounter<5:
						emailmod.sendallmail("alert", textmessage)							
						logger.error(textmessage)
						statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)
			else:
				logger.info('sensor %s below valid data', sensor)
				textmessage="WARNING: "+ sensor + " below valid data range, need to check sensor"
				print textmessage
				#send alert mail notification
				alertcounter=statusdataDBmod.read_status_data(AUTO_data,element,"alertcounter")
				if alertcounter<3:
					emailmod.sendallmail("alert", textmessage)							
					logger.error(textmessage)
					statusdataDBmod.write_status_data(AUTO_data,element,"alertcounter",alertcounter+1)		
	return



def isNowInTimePeriod(startTime, endTime, nowTime):
    if startTime < endTime:
        return nowTime >= startTime and nowTime <= endTime
    else: #Over midnight
        return nowTime >= startTime or nowTime <= endTime

	

def checkminthreshold(sensor,minthreshold,minaccepted):
	belowthr=False
	validity=True		
	# check the hygrometer sensor levels 
	sensorreadingaverage=sensorreading(sensor)
	# if the average level after 4 measure (15 min each) is below threshold apply emergency 
	print " Min accepted threshold " , minaccepted
	if (sensorreadingaverage>minaccepted):
		if (sensorreadingaverage>minthreshold):		
			logger.info('Soil moisture check, Sensor reading=%s > Minimum threshold=%s ', str(sensorreadingaverage), str(minthreshold))			
			print 'Soil moisture check, Sensor reading=%s > Minimum threshold=%s '
		else:
			logger.warning('Soil moisture check, Sensor reading=%s < Minimum threshold=%s ', str(sensorreadingaverage), str(minthreshold))			
			logger.info('Start watering procedure ')			
			print 'Soil moisture check, activating watering procedure '
			belowthr=True
	else:	
		logger.warning('Sensor reading lower than acceptable values %s no action', str(sensorreadingaverage))
		print 'Sensor reading lower than acceptable values ', sensorreadingaverage ,' no action'
		validity=False

	return belowthr, validity


def checkinclination(sensorname,startdate,enddate):
	# startdate is UTC now, need to be evaluated
	print "Check inclination of the hygrometer curve after watering done " , sensorname
	logger.info('Check inclination of the hygrometer curve after watering done: %s', sensorname)
	logger.info('Start eveluation from %s to %s', startdate.strftime("%Y-%m-%d %H:%M:%S") , enddate.strftime("%Y-%m-%d %H:%M:%S"))
	print "Start eveluation from " , startdate.strftime("%Y-%m-%d %H:%M:%S") , " to " , enddate.strftime("%Y-%m-%d %H:%M:%S")
	datax=[]
	datay=[]
	if sensorname:
		lenght=sensordbmod.getSensorDataPeriodXminutes(sensorname,datax,datay,startdate,enddate)

	print "datax ", datax
	print "datay ", datay
	if lenght>0:
		avex=sum(datax)/float(lenght)
		avey=sum(datay)/float(lenght)
		print " Average: " , avex, "  " ,  avey
		num=0
		den=0				
		for inde in range(len(datax)):
			x2=(datax[inde]-avex)*(datax[inde]-avex)
			xy=(datax[inde]-avex)*(datay[inde]-avey)
			num=num+xy
			den=den+x2
		print " ----> Lenght " ,lenght , " num: ", num , " Den: ", den
		if den>0.0001: # this is to avoid problem with division
			slope=num/den
			logger.info('Inclination value: %.4f', slope)
			print " Slope Value" , slope
			# here an arbitray min slope that should be reasonable for a working system 
			yvolt=0.2
			xminute=2*60
			minslope=yvolt/xminute # 0.2 volt per 2 hours
			if slope>minslope:
				logger.info('Inclination value %.4f above the min reference %.4f (0.2 volt per 2 hours), restaring watering cycle',slope,minslope)
				return True
	return False
	



def sensorreading(sensorname):
	MinutesOfAverage=70 #about one hour, 4 samples at 15min samples rate
	if sensorname:
		# old
		#sensordata=[]		
		#sensordbmod.getsensordbdata(sensorname,sensordata)
		# get number of samples 
		timelist=hardwaremod.gettimedata(sensorname)	
		theinterval=timelist[1] # minutes
		if theinterval>0:
			samplesnumber=int(MinutesOfAverage/theinterval+1)
		else:
			samplesnumber=1	
		# new procedure should be faster on database reading for large amount of data
		sensordata=[]
		sensordbmod.getsensordbdatasamplesN(sensorname,sensordata,samplesnumber)
		# still necessary to filter the sample based on timestamp, due to the possibility of missing samples
		starttimecalc=datetime.now()-timedelta(minutes=int(MinutesOfAverage))
		quantity=sensordbmod.EvaluateDataPeriod(sensordata,starttimecalc,datetime.now())["max"]	
	return 	quantity

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
	return autowateringdbmod.searchdata("element",element,"workmode")


def activatewater(element, duration):
	# check the activation of the doser before the pump
	doseron=autofertilizermod.checkactivate(element,duration)
	#activate pump		
	hardwaremod.makepulse(element,duration)
	# salva su database
	logger.info('%s Pump ON, optional time for msec = %s', element, duration)
	print 'Pump ON, optional time for msec =', duration
	actuatordbmod.insertdataintable(element,duration)



if __name__ == '__main__':
	
	"""
	prova functions
	"""

	

