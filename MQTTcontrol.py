# -*- coding: utf-8 -*-

import time
from datetime import datetime,date,timedelta
import threading
from math import sqrt
#import sys,os
#import serial
#import os
import glob
import logging
import statusdataDBmod
from mqtt import MQTTutils
import sys, os
import json
basepath=os.getcwd() # get current path

logger = logging.getLogger("hydrosys4."+__name__)

ISRPI=MQTTutils.MQTTlib

CLIENTSLIST={}


# in MQTT pin can still be used as subtopic, important for the HBRIDGE configuration

if ISRPI:
	#HWCONTROLLIST=["pulse/MQTT","stoppulse/MQTT","pinstate/MQTT","hbridge/MQTT","hbridgestatus/MQTT"]
	HWCONTROLLIST=["pulse/MQTT","stoppulse/MQTT","readinput/MQTT"]
else:
	HWCONTROLLIST=[]




# status variables

hbridge_data={}
hbridge_data["default"]={'busyflag':False}

GPIO_data={}
GPIO_data["default"]={"level":0, "state":None, "threadID":None}

PowerPIN_Status={}
PowerPIN_Status["default"]={"level":0, "state":"off", "pinstate":None, "timeZero":0}


def Create_connections_and_subscribe():
	global CLIENTSLIST
	MQTTutils.Create_connections_and_subscribe(CLIENTSLIST)
	
def Disconnect_clients():
	global CLIENTSLIST
	MQTTutils.Disconnect_clients(CLIENTSLIST)

def toint(thestring, outwhenfail):
	try:
		f=float(thestring)
		n=int(f)
		return n
	except:
		return outwhenfail

def tonumber(thestring, outwhenfail):
	try:
		n=float(thestring)
		return n
	except:
		return outwhenfail


def execute_task(cmd, message, recdata):
	global hbridge_data
	
	print(" WELLCOME TO THE MQTT CONTROL ")
	print("MESSAGE " + message)
	
	if cmd in HWCONTROLLIST:
	
		if cmd==HWCONTROLLIST[0]:	# pulse
			return MQTT_pulse(cmd, message, recdata)
			
		elif cmd==HWCONTROLLIST[1]:	# stoppulse
			return MQTT_stoppulse(cmd, message, recdata)			

		elif cmd==HWCONTROLLIST[2]:	# readinput
			return readinput_MQTT(cmd, message, recdata)
			
		#elif cmd==HWCONTROLLIST[3]: #hbridge	
		#	return MQTT_set_hbridge(cmd, message, recdata, hbridge_data)	

		#elif cmd==HWCONTROLLIST[4]: #hbridge status	
		#	return get_hbridge_status(cmd, message, recdata, hbridge_data)


	else:
		print("Command not found")
		recdata.append(cmd)
		recdata.append("e")
		recdata.append(0)
		return False;
	return False;


def execute_task_fake(cmd, message, recdata):
	
	
	if cmd==HWCONTROLLIST[0]:	
		gpio_pulse(cmd, message, recdata)
		return True;


		
	else:
		print("no fake command available" , cmd)
		recdata.append(cmd)
		recdata.append("e")
		recdata.append(0)
		return False;
		
	return True
	

def DictPath_SearchReplace(searchpathlist,jsondata,newvalue): # parse for sinlge param item
	# this function work only with wrapper.
	#wrap
	firstkey="firstkey"
	jsondatawarp={firstkey:jsondata}
	searchpathlist.insert(0, firstkey)
	
	isok=False
	gonext=False
	result=""

	subStruct=jsondatawarp			
	for keyword in searchpathlist:
		gonext=False
		# enter the json data structure to search
		if isinstance(subStruct, dict):
			if keyword in subStruct:
				upStruct=subStruct
				lastKey=keyword
				subStruct=subStruct[keyword]		
				gonext=True

		if gonext==False:
			print(" Search Path finished before finding the Object  ........")
			break
	if gonext:
		print(" ========> item found ", 	subStruct)
		result=subStruct			
		upStruct[lastKey]=newvalue
		isok=True

	
	newjsondata=jsondatawarp[firstkey]
	
	
	return isok, result, newjsondata



def readinput_MQTT(cmd, message, recdata):
	
	print("MQTT inputs ..............................")
	
	# This provides the latest reading of the MQTT device, the reading is passive, it means that the system is not sendig command to get the reading , 
	# it just record the latest value send by the sensor
	


	msgarray=message.split(":")

	PIN_str=""
	if len(msgarray)>1:
		PIN_str=msgarray[1]	


	measureUnit=""
	if len(msgarray)>4:
		measureUnit=msgarray[4]

	SensorAddress=""
	if len(msgarray)>6:
		SensorAddress=msgarray[6]	

	PIN2_str=""
	if len(msgarray)>7:
		PIN2_str=msgarray[7]	

	Topic=""
	if len(msgarray)>8:
		Topic=msgarray[8]

	Timeperiodstr=""
	if len(msgarray)>9:
		Timeperiodstr=msgarray[9]
	Timeperiodsec=tonumber(Timeperiodstr,0) # zero is a special case , never expire

	print(" Timeperiodsec  " , msgarray[9], "   "  , Timeperiodsec)

	PIN=toint(PIN_str,-1)
	PIN2=toint(PIN2_str,-1)



	if (Topic==""):
		print("Error, MQTT reading no topic defined", Topic)
		# address not correct
		logger.error("MQTT reading no topic defined %s", Topic)
		recdata.append(cmd)
		recdata.append("Topic not configured ")
		recdata.append(0)
		return True
	
	# Get the last value pubished for this topic. 
	reading=0

	stinglist=Topic.split("//")
	subtopic=stinglist[0]
	if len(stinglist)>1:
		searchpathlist=stinglist[1].split("/")


	jsonstring=statusdataDBmod.read_status_data(MQTTutils.SubscriptionLog,subtopic,"jsonstring")
	timestamp=statusdataDBmod.read_status_data(MQTTutils.SubscriptionLog,subtopic,"timestamp")	
	
	
	
	if jsonstring=="":
		print("Error, MQTT reading no Reading for the topic ", subtopic)
		# address not correct
		logger.error("MQTT reading no Reading for the topic %s", subtopic)
		recdata.append(cmd)
		recdata.append("Error, MQTT no Reading for the topic " + subtopic)
		recdata.append(0)
		return True
	
	deltaseconds=(datetime.utcnow()-timestamp).total_seconds()
	
	print(" deltaseconds  " , deltaseconds)
	
	if deltaseconds<0:
		#MQTT reading happenend in the future .... somethign wrong, issue error
		print("Error, MQTT reading in the future ")
		# address not correct
		logger.error("MQTT reading in the future")
		recdata.append(cmd)
		recdata.append("Error, MQTT reading in the future ...")
		recdata.append(0)
		return True		
	

	# extract value
	jsondata = json.loads(jsonstring)
	isok, result, jsondata = DictPath_SearchReplace(searchpathlist,jsondata,"")
	jsonstring = json.dumps(jsondata)  
	print ("MQTT sensor ", isok, "  " , result, "   " , jsonstring)	
	
	
	if Timeperiodsec>0:
		if ((deltaseconds+1)>Timeperiodsec):
			# value not valid, replace with empty string
			# remove the number from the string so a second reading will not get the value.
			statusdataDBmod.write_status_data(MQTTutils.SubscriptionLog,subtopic,"jsonstring",jsonstring) 
			result=""	

	
	if isok:
		if result=="":
			print("Error, MQTT no updates from the sensor since ", str(deltaseconds) , " (sec)")
			# address not correct
			logger.error("MQTT no updates from the sensor %s (sec)", str(deltaseconds))
			recdata.append(cmd)
			recdata.append("Error, MQTT no updates from the sensor")
			recdata.append(0)
			return True

		else:
			reading=result
			successflag=1	
			logger.info("MQTT input reading: %s", reading)
			print("MQTT input reading ", reading)
			recdata.append(cmd)
			recdata.append(reading)
			recdata.append(successflag)
			statusmsg="MQTT last update " + '{:.1f}'.format(deltaseconds) + " seconds "
			recdata.append(statusmsg)
			return True
		

	print("Error, MQTT reading ", jsonstring)
	logger.error("MQTT reading %s", jsonstring)
	recdata.append(cmd)
	recdata.append("Generic Error, MQTT reading")
	recdata.append(0)
		
	return True



def powerPIN_start(REGID,CMD,address,pulsesecond,ignorepowerpincount=False): # powerpin will work only with same address and same topic/"powerpin number"
	if REGID!="":
		PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"level")
		#start power pin
		if PowerPINlevel<1: 
			PowerPINlevel==0
		if not ignorepowerpincount:
			statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"level",PowerPINlevel+1)			
			
		
		# complication below is necessary.
		timeZero=int(time.time())+pulsesecond
		Lasttimezero=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"timeZero")
		if Lasttimezero:
			if timeZero>Lasttimezero:
				statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"timeZero",timeZero)
				MQTT_output(CMD, address)				
		else:
			statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"timeZero",timeZero)

		
		if PowerPINlevel==0:
			time.sleep(0.2)			
	return True	

		
def powerPIN_stop(CMD_PWR,waittime,address):
	REGID=CMD_PWR["ID"]
	if REGID!="":
		PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"level")
		statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"level",PowerPINlevel-1)

		#stop power pin	if level less or equal to zero
		if (PowerPINlevel-1)<=0:

			time.sleep(waittime)
			
			MQTT_output(CMD_PWR["STOP"], address)


	return True	



def MQTT_output(CMD_LIST,address):


	found=False
	if address in CLIENTSLIST:
		clientobj=CLIENTSLIST[address]["clientobj"]
		for CMD in CMD_LIST:
			topic=CMD["topic"]
			payload=CMD["value"]
			print("Publish: " + "  " + address + "   " + topic + "   "  + str(payload))
			clientobj.publish(topic=topic, payload=str(payload), qos=2)
			time.sleep(0.1)
	
	return True


def MQTT_output_all_stats():

	for client in CLIENTSLIST:
		clientinfo=CLIENTSLIST[client]
		clientobj=clientinfo["clientobj"]

		topic=clientinfo["cmdtopicstat5"]
		payload=5
		print("Publish: " + "  " + client + "   " + topic + "   "  + str(payload))
		clientobj.publish(topic=topic, payload=str(payload), qos=2)
		time.sleep(0.1)
	
	return True

def MQTT_get_all_stats():
	
	print(" MQTT STATS  ***********************************") 
	retdict={}
	
	for client in CLIENTSLIST:
		clientinfo=CLIENTSLIST[client]
		clientobj=clientinfo["clientobj"]
		subtopic=clientinfo["subtopicstat5"]
		
		jsonstring=statusdataDBmod.read_status_data(MQTTutils.SubscriptionLog,subtopic,"jsonstring")
		timestamp=statusdataDBmod.read_status_data(MQTTutils.SubscriptionLog,subtopic,"timestamp")
		
		print("Json Status : " , jsonstring)
		
		if jsonstring!="":
			jsondata = json.loads(jsonstring)
			StatusNET=jsondata["StatusNET"]
			IPAddress=StatusNET["IPAddress"]
			WifiPower=StatusNET["WifiPower"]
		else:
			IPAddress="N/A"
			WifiPower="N/A"
		
		infodict={"IPAddress":IPAddress,"WifiPower":WifiPower}
		
		"""
		{"StatusNET":{"Hostname":"esp-01s-1383","IPAddress":"192.168.0.103","Gateway":"192.168.0.1","Subnetmask":"255.255.255.0","DNSServer":"192.168.0.1","Mac":"DC:4F:22:BC:C5:67","Webserver":2,"WifiConfig":4,"WifiPower":17.0}}
		"""
		
		retdict[client]=infodict
		
		
	
	return retdict	


def endpulse(PIN_CMD,POWERPIN_CMD,address):
	REGID=PIN_CMD["ID"]
	statusdataDBmod.write_status_data(GPIO_data,REGID,"threadID",None)
	
	MQTT_output(PIN_CMD["STOP"], address)
	
	endwaittime=0
	powerPIN_stop(POWERPIN_CMD,endwaittime,address)

	#print "pulse ended", time.ctime() , " PIN=", PINstr , " Logic=", logic , " Level=", level
	return True

def create_pulse_CMD_list(PIN,POWERPIN,title,pulsesecond):
	
	# this is coming from the strange way the pulse is calculated in tasmota
	Durationperiod=0
	if pulsesecond<12:
		Durationperiod=pulsesecond*10
	else:
		Durationperiod=pulsesecond+100
	
	PINnum=toint(PIN,0)
	PINstr=""
	if not PINnum==0:
		PINstr=PIN 	
	# MQTT publish commands	
	MQTT_CMD={"ID":title+PINstr}
	CMD={"topic":title+"/PulseTime"+PINstr,"value":str(Durationperiod)}
	CMD_list=[]	
	CMD_list.append(CMD)
	MQTT_CMD["EXTEND"]=CMD_list	
	
	CMD={"topic":title+"/Power"+PINstr,"value":"ON"}
	CMD_list.append(CMD)		
	MQTT_CMD["START"]=CMD_list

	CMD={"topic":title+"/Power"+PINstr,"value":"OFF"}	
	CMD_list=[]
	CMD_list.append(CMD)		
	MQTT_CMD["STOP"]=CMD_list
	
	
	MQTT_CMD_PWR={"ID":"","START":"","STOP":"","EXTEND":""}
	POWERPINstr=""	
	POWERPINnum=toint(POWERPIN,0)
	if not POWERPINnum==0:  # commands are filled only if the PWRPIN is a number
		POWERPINstr=POWERPIN
		
		waittime=0.2
		
		# MQTT publish commands	PWR
		ID=title+POWERPINstr
		MQTT_CMD_PWR={"ID":ID}
		CMD={"topic":title+"/PulseTime"+POWERPINstr,"value":str(Durationperiod+waittime*2)}
		CMD_list=[]	
		CMD_list.append(CMD)
		MQTT_CMD_PWR["EXTEND"]=CMD_list	
		
		CMD={"topic":title+"/Power"+POWERPINstr,"value":"ON"}
		CMD_list.append(CMD)		
		MQTT_CMD_PWR["START"]=CMD_list

		CMD={"topic":title+"/Power"+POWERPINstr,"value":"OFF"}	
		CMD_list=[]
		CMD_list.append(CMD)		
		MQTT_CMD_PWR["STOP"]=CMD_list

	return MQTT_CMD, MQTT_CMD_PWR


def MQTT_pulse(cmd, message, recdata):
	successflag=0
	msgarray=message.split(":")
	messagelen=len(msgarray)	
	PIN=msgarray[1]

	testpulsetime=msgarray[2] # in seconds
	pulsesecond=int(testpulsetime)
	
	
	POWERPIN=""	
	if messagelen>4:	
		POWERPIN=msgarray[4]	

	MIN=0	
	if messagelen>5:	
		MIN=int(msgarray[5])	
		
	MAX=0	
	if messagelen>6:	
		MAX=int(msgarray[6])	
		
	MAX=0	
	if messagelen>6:	
		MAX=int(msgarray[6])
		
	activationmode=""	
	if messagelen>7:	
		activationmode=msgarray[7]		
		
	address=""	# this is the MQTT client ID
	if messagelen>8:	
		address=msgarray[8]

	title=""	
	if messagelen>9:	
		title=msgarray[9]
	

	if title=="":
		print("missing topic") 
		logger.error("No topic specified, please insert it in the Title field")
		successflag=0
		recdata.append("e")
		recdata.append(successflag)
		recdata.append("Missing MQTT topic")
		return recdata
		

	MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,pulsesecond)

	# start pulse activation logic

	REGID=MQTT_CMD["ID"]
	ignorepowerpincount=False
	# in case another timer is active on this TOPIC ID it means that the PIN is activated 
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
	if not PINthreadID==None:
		
		# pin already active
		if activationmode=="NOADD": # no action needed
			successflag=1
			recdata.append(cmd)
			recdata.append(PIN)
			recdata.append(successflag)
			return True		
		
		PINthreadID.cancel() # cancel thread 

		ignorepowerpincount=True # do not add levels to the powerpin
	
	

	powerPIN_start(MQTT_CMD_PWR["ID"],MQTT_CMD_PWR["START"],address,pulsesecond,ignorepowerpincount)


	level=1
	statusdataDBmod.write_status_data(GPIO_data,REGID,"level",level)
	logger.info("Set PIN=%s to State=%s", REGID, str(level))
	print (REGID + " *********************************************** " , level)
	
	MQTT_output(MQTT_CMD["START"],address)
	
	NewPINthreadID=threading.Timer(pulsesecond, endpulse, [MQTT_CMD, MQTT_CMD_PWR, address])
	NewPINthreadID.start()
	statusdataDBmod.write_status_data(GPIO_data,REGID,"threadID",NewPINthreadID)



	successflag=1
	recdata.append(cmd)
	recdata.append(PIN)
	recdata.append(successflag)
	return True	

def MQTT_stoppulse(cmd, message, recdata):   # when ON send MQTT message with the duration in seconds of the activation, and when OFF send zero.
	print(" Don't stop me now ")
	
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN=msgarray[1]
	
	logic="pos"
	if messagelen>3:
		logic=msgarray[3]
	
	POWERPIN=""
	if messagelen>4:	
		POWERPIN=msgarray[4]
		
	MIN=0	
	if messagelen>5:	
		MIN=int(msgarray[5])	
		
	MAX=0	
	if messagelen>6:	
		MAX=int(msgarray[6])	
	
	address=""	# this is the MQTT client ID
	if messagelen>7:	
		address=msgarray[7]

	
	title=""
	if messagelen>8:	
		title=msgarray[8]	
	
	if title=="":
		print("missing topic") 
		logger.error("No topic specified, please insert it in the Title field")
		successflag=0
		recdata.append("e")
		recdata.append(successflag)	
		return recdata
	
	MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,0)
	
	REGID=MQTT_CMD["ID"]	
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
		
	endpulse(MQTT_CMD, MQTT_CMD_PWR,address)	#this also put powerpin off		
	recdata.append(cmd)
	recdata.append(PIN)
	return True	


def MQTT_pin_level(cmd, message, recdata):
	msgarray=message.split(":")
	PIN=msgarray[1]
	recdata.append(msgarray[0])
	PINlevel=statusdataDBmod.read_status_data(GPIO_data,PIN,"level")
	if PINlevel is not None:
		recdata.append(str(PINlevel))
		return True
	else:
		recdata.append("e")
		return False	


def read_input_pin(cmd, message, recdata):
	
	# this is useful for the real time reading. Suggest to put in oneshot for the hardware configuration because the database record timing is given by the interrupts
	successflag=1
	msgarray=message.split(":")
	#print " read pin input ", message
	PINstr=msgarray[1]
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	recdata.append(cmd)		
	if isRealPIN:
		if GPIO.input(PIN):
			reading="1"
		else:
			reading="0"
		recdata.append(reading)
		recdata.append(successflag)	
	else:
		successflag=0
		recdata.append("e")
		recdata.append(successflag)	
	return True
	
	

def isPinActive(PIN):
	PINlevel=statusdataDBmod.read_status_data(GPIO_data,PIN,"level")
	#print " pin Level" , PINlevel
	if PINlevel is not None:
		return PINlevel		
	else:
		return False



# START hbridge section

	
def MQTT_set_hbridge(cmd, message, recdata , hbridge_data ):
			
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN1=msgarray[1]
	PIN2=msgarray[2]
	direction=msgarray[3]
	durationsecondsstr=msgarray[4]
	logic=msgarray[5]
	
	#print "hbridge ", PIN1, "  ",  PIN2, "  ",  direction, "  ",  durationsecondsstr,  "  ", logic

	# check that both pins are at logic low state, so Hbridge is off
	PIN1active=isPinActive(PIN1, logic)
	PIN2active=isPinActive(PIN2, logic)
	hbridgebusy=PIN1active or PIN2active


	if hbridgebusy:
		print("hbridge motor busy ")
		logger.warning("hbridge motor Busy, not proceeding ")
		recdata.append(cmd)
		recdata.append("e")
		recdata.append("busy")
		return False
	
	#  no busy, proceed	


	try:
		POWERPIN="N/A"

		if direction=="FORWARD":
			sendstring="pulse:"+PIN1+":"+durationsecondsstr+":"+logic+":"+POWERPIN		
		else:
			sendstring="pulse:"+PIN2+":"+durationsecondsstr+":"+logic+":"+POWERPIN	
		#Send pulse to one of the Hbridge port
		#print "logic " , logic , " sendstring " , sendstring
		isok=False	
		if float(durationsecondsstr)>0:
			#print "Sendstring  ", sendstring	
			isok=False
			recdatapulse=[]
			ack = gpio_pulse("pulse",sendstring,recdatapulse)
			#print "returned hbridge data " , recdatapulse
			# recdata[0]=command (string), recdata[1]=data (string) , recdata[2]=successflag (0,1)
			if ack and recdatapulse[2]:
				#print "Hbridge correctly activated"
				isok=True


	except:

		print("problem hbridge execution")
		logger.error("problem hbridge execution")
		recdata.append(cmd)
		recdata.append("e")
		return False

		
	#print "Hbridge: PIN1=", PIN1 , " PIN2=", PIN2 , " direction=", direction , " duration=", durationsecondsstr , " logic=", logic 

	recdata.append(cmd)
	recdata.append(PIN1+PIN2)
	
	return True	

def get_hbridge_status(cmd, message, recdata , hbridge_data):
	#print "get hbridge status"
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN1=msgarray[1]
	PIN2=msgarray[2]
	returndata=read_status_dict(hbridge_data,PIN1+PIN2)
	recdata.append(cmd)
	recdata.append(returndata)
	return True

	
def get_hbridge_status(cmd, message, recdata , hbridge_data):
	#print "get hbridge status"
	msgarray=message.split(":")
	messagelen=len(msgarray)
	Interface=msgarray[1]
	returndata=read_status_dict(hbridge_data,Interface)
	recdata.append(cmd)
	recdata.append(returndata)
	return True


def sendcommand(cmd, message, recdata):
	# as future upgrade this function might be run asincronously using "import threading"

	if ISRPI:
		ack=execute_task(cmd, message, recdata)
	else:
		print(" Client to support MQTT not installed")
		ack=execute_task_fake(cmd, message, recdata)
	return ack
	

def connecttobroker(address,port,timeout=180):
	client = mqtt.Client()
	client.connect(address, port, timeout)	
	client.loop_forever()
	



if __name__ == '__main__':
	
	"""
	to be acknowledge a message should include the command and a message to identyfy it "identifier" (example "temp"), 
	if arduino answer including the same identifier then the message is acknowledged (return true) command is "1"
	the data answer "recdata" is a vector. the [0] field is the identifier, from [1] start the received data
	"""
	searchpathlist=['BH1750',"Illuminance"]
	#searchpathlist=['BH1750']
	jsondata={"Time":"2020-08-11T16:38:26","BH1750":{"Illuminance":164}}
	#jsondata="10"

	print("search path ", searchpathlist)
	print("before replace ", jsondata)


	isok, result, jsondata = DictPath_SearchReplace(searchpathlist,jsondata,"bobo")


	print (isok, "  " , result)
	print("after replace ", jsondata)

