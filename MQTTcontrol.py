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
	HWCONTROLLIST=["pulse/MQTT","stoppulse/MQTT","readinput/MQTT","pinstate/MQTT","hbridge/MQTT", "switchoff/MQTT" , "switchon/MQTT"]
else:
	HWCONTROLLIST=[]




# status variables

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

def returnmsg(recdata,cmd,msg,successful):
    recdata.clear()
    print(msg)
    recdata.append(cmd)
    recdata.append(msg)
    recdata.append(successful)
    if not successful:
        logger.error("Error: %s" ,msg)
    return True

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
		
		elif cmd==HWCONTROLLIST[3]:	# pinstate
			return MQTT_pin_level(cmd, message, recdata)
			
		elif cmd==HWCONTROLLIST[4]: #hbridge	
			return ""	

		elif cmd==HWCONTROLLIST[5]:	# pinstate
			return MQTT_switchoff(cmd, message, recdata)

		elif cmd==HWCONTROLLIST[6]:	# pinstate
			return MQTT_switchon(cmd, message, recdata)



	else:
		returnmsg(recdata,cmd,"Command not Found",0)
		return False
	return False


def execute_task_fake(cmd, message, recdata):
	
	
	if cmd==HWCONTROLLIST[0]:	
		print("fake command")
		return True


		
	else:
		msg="no fake command available" + cmd
		returnmsg(recdata,cmd,msg,0)
		return False
		
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
		msg="Error, MQTT reading no topic defined " +Topic
		returnmsg(recdata,cmd,msg,0)
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
		msg="Error, MQTT reading no Reading for the topic "+ subtopic
		returnmsg(recdata,cmd,msg,0)
		return True
	
	deltaseconds=(datetime.utcnow()-timestamp).total_seconds()
	
	print(" deltaseconds  " , deltaseconds)
	
	if deltaseconds<0:
		#MQTT reading happenend in the future .... somethign wrong, issue error
		msg="Error, MQTT reading in the future "
		returnmsg(recdata,cmd,msg,0)
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
			msg="Error, MQTT no updates from the sensor since "+ str(deltaseconds) + "(sec)"
			returnmsg(recdata,cmd,msg,0)
			return True

		else:
			reading=result
			successflag=1	
			logger.info("MQTT input reading: %s", reading)
			print("MQTT input reading ", reading)
			returnmsg(recdata,cmd,reading,successflag)
			statusmsg="MQTT last update " + '{:.1f}'.format(deltaseconds) + " seconds "
			recdata.append(statusmsg)
			return True
		

	print("Error, MQTT reading ", jsonstring)
	logger.error("MQTT reading %s", jsonstring)
	msg="Generic Error, MQTT reading"
	returnmsg(recdata,cmd,msg,0)
	return True



def powerPIN_status(REGID,CMD,address,pulsesecond,pwr_level_increase=1): # powerpin will work only with same address and same topic/"powerpin number"
	power_pulse_needed=False
	pulsesecond=toint(pulsesecond,0)

	if REGID!="":
		PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"level")
		#start power pin
		if PowerPINlevel<1: 
			PowerPINlevel==0
		statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"level",PowerPINlevel+pwr_level_increase)			
			
		
		# complication below is necessary.
		timeZero=int(time.time())+pulsesecond
		Lasttimezero=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"timeZero")
		if not Lasttimezero:
			Lasttimezero=0

		if timeZero>Lasttimezero:
			statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"timeZero",timeZero)
			#MQTT_output(CMD, address)	# here send the command		
			power_pulse_needed=True	
				
	return power_pulse_needed	

		
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
			print("Publish to Tasmota: " + "  " + address + "   " + topic + "   "  + str(payload))
			clientobj.publish(topic=topic, payload=str(payload), qos=2)
			time.sleep(0.1)
		return True, ""
	
	return False, "Generic Error"


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
	
	isok, msg = MQTT_output(PIN_CMD["STOP"], address)
	
	endwaittime=0
	powerPIN_stop(POWERPIN_CMD,endwaittime,address)

	#print "pulse ended", time.ctime() , " PIN=", PINstr , " Logic=", logic , " Level=", level
	return  isok, msg

def create_pulse_CMD_list(PIN,POWERPIN,title,pulsesecond_srt):
	
	# this is coming from the strange way the pulse is calculated in tasmota
	pulsesecond=toint(pulsesecond_srt,0)
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

	CMD_list=[]	

	MQTT_CMD["EXTEND"]=CMD_list	
	CMD={"topic":title+"/Power"+PINstr,"value":"ON"}
	CMD_list.append(CMD)		
	MQTT_CMD["START"]=CMD_list


	CMD_list=[]	
	CMD={"topic":title+"/PulseTime"+PINstr,"value":"OFF"} # disable pulsetime for this topic.
	CMD_list.append(CMD)
	CMD={"topic":title+"/Power"+PINstr,"value":"ON"}
	CMD_list.append(CMD)		
	MQTT_CMD["ON"]=CMD_list

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



def pulse_value(value): #Input the string and output 3 value, valid, str, number
	isvalid=False
	value_str=""
	value_num=0
	possible_str=["ON", "OFF"]
	if value in possible_str:
		isvalid=True
		value_str=value
	else: # check if it is an int number
		try:
			value_num=int(value)
			isvalid=True
			value_str=""
		except:
			isvalid=False
			value_str=""
			value_num=0
	return isvalid , value_str, value_num



def MQTT_pulse(cmd, message, recdata):
	successflag=0
	msgarray=message.split(":")
	messagelen=len(msgarray)	
	PIN=msgarray[1]

	pulsetime_str=msgarray[2] # in seconds
	isvalid, pulsestr , pulsesecond = pulse_value(pulsetime_str)
	if not isvalid:
		msg="Wrong value for pulse" + pulsetime_str
		logger.error(msg)
		successflag=0
		returnmsg(recdata,cmd,msg,successflag)
		return True	

	print("-------------> pulsetime_str ", pulsetime_str)
    
	POWERPIN=""	
	if messagelen>4:	
		POWERPIN=msgarray[4]
		if not toint(POWERPIN,0):
			POWERPIN=""		

		
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
		successflag=0
		msg="Missing MQTT topic in setting"
		returnmsg(recdata,cmd,msg,successflag)
		return recdata
		

	MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,pulsesecond)

	REGID=MQTT_CMD["ID"]  # this is made by the string "topic"+"PIN"
	pwr_level_increase=1 # determine how many levels to add to the power pin (power pin level are used to OFF the power when level is Zero or below)
	# in case another timer is active on this TOPIC ID it means that the PIN is activated 
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
	if not PINthreadID==None:
		# pin already active
		if activationmode=="NOADD": # no action needed
			successflag=1
			returnmsg(recdata,cmd,PIN,successflag)
			return True		
		PINthreadID.cancel() # cancel thread 
		pwr_level_increase=pwr_level_increase-1 # do not add levels to the powerpin, pin is already active and is already counted
	
	level=1
	statusdataDBmod.write_status_data(GPIO_data,REGID,"level",level)
	logger.info("Set PIN=%s to State=%s", REGID, str(level))
	print (REGID + " *********************************************** " , level)
		
	if pulsetime_str=="ON":
		pwr_level_increase=pwr_level_increase-1 # do not add levels to the powerpin
	
	need_power_pulse=powerPIN_status(MQTT_CMD_PWR["ID"],MQTT_CMD_PWR["START"],address,pulsesecond,pwr_level_increase)
	print("need_power_pulse " , need_power_pulse)
	if (not pulsetime_str=="ON")and(need_power_pulse): # exclude powerpin functiopn in case of ON
		isok , msg = MQTT_output(MQTT_CMD_PWR["START"],address)
		isok , msg = MQTT_output(MQTT_CMD["START"],address)	
	else:
		if pulsetime_str=="ON":
			isok , msg = MQTT_output(MQTT_CMD["ON"],address)	 # try two times # starts the PIN 
		else:
			isok , msg = MQTT_output(MQTT_CMD["START"],address)  # try two times # starts the PIN 
		
	if not pulsetime_str=="ON": # exclude powerpin functiopn in case of ON
		NewPINthreadID=threading.Timer(pulsesecond, endpulse, [MQTT_CMD, MQTT_CMD_PWR, address])
		NewPINthreadID.start()
		statusdataDBmod.write_status_data(GPIO_data,REGID,"threadID",NewPINthreadID)

	if isok:
		successflag=1
		returnmsg(recdata,cmd,PIN,successflag) 
	else:
		successflag=0
		returnmsg(recdata,cmd,msg,successflag) 
  
	return True	





def MQTT_switchon(cmd, message, recdata):
	successflag=0
	msgarray=message.split(":")
	messagelen=len(msgarray)	
	PIN=msgarray[1]

	pulsetime_str=msgarray[2] # in seconds
	pulsesecond=0    

	POWERPIN=""	
	if messagelen>4:	
		POWERPIN=msgarray[4]
		if not toint(POWERPIN,0):
			POWERPIN=""		

		
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
		successflag=0
		msg="Missing MQTT topic in setting"
		returnmsg(recdata,cmd,msg,successflag)
		return recdata
		

	MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,pulsesecond)

	REGID=MQTT_CMD["ID"]  # this is made by the string "topic"+"PIN"
	pwr_level_increase=1 # determine how many levels to add to the power pin (power pin level are used to OFF the power when level is Zero or below)
	# in case another timer is active on this TOPIC ID it means that the PIN is activated 
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
	if not PINthreadID==None:
		# pin already active
		if activationmode=="NOADD": # no action needed
			successflag=1
			returnmsg(recdata,cmd,PIN,successflag)
			return True		
		PINthreadID.cancel() # cancel thread 
		pwr_level_increase=pwr_level_increase-1 # do not add levels to the powerpin, pin is already active and is already counted
	
	level=1
	statusdataDBmod.write_status_data(GPIO_data,REGID,"level",level)
	logger.info("Set PIN=%s to State=%s", REGID, str(level))
	print (REGID + " *********************************************** " , level)
		

	if pulsetime_str=="ON":
		isok , msg = MQTT_output(MQTT_CMD["ON"],address)	 # try two times # starts the PIN 


	if isok:
		successflag=1
		returnmsg(recdata,cmd,PIN,successflag) 
	else:
		successflag=0
		returnmsg(recdata,cmd,msg,successflag) 
  
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
		
	
	address=""	# this is the MQTT client ID
	if messagelen>7:	
		address=msgarray[7]

	
	title=""
	if messagelen>8:	
		title=msgarray[8]	
	
	if title=="":
		msg="missing topic in Title field"
		logger.error("No topic specified, please insert it in the Title field")
		successflag=0
		returnmsg(recdata,cmd,msg,successflag)
		return recdata
	
	MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,0)
	
	REGID=MQTT_CMD["ID"]	
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
		
	endpulse(MQTT_CMD, MQTT_CMD_PWR,address)	#this also put powerpin off		
	returnmsg(recdata,cmd,PIN,1)
	return True	



def MQTT_switchoff(cmd, message, recdata):   # when ON send MQTT message with the duration in seconds of the activation, and when OFF send zero.
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
		
	
	address=""	# this is the MQTT client ID
	if messagelen>7:	
		address=msgarray[7]

	
	title=""
	if messagelen>8:	
		title=msgarray[8]	
	
	if title=="":
		msg="missing topic in Title field"
		logger.error("No topic specified, please insert it in the Title field")
		successflag=0
		returnmsg(recdata,cmd,msg,successflag)
		return recdata
	
	MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,0)
	
	REGID=MQTT_CMD["ID"]	
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
		
	isok, msg = endpulse(MQTT_CMD, MQTT_CMD_PWR,address)	#this also put powerpin off		
	if isok:
		returnmsg(recdata,cmd,PIN,1) 
	else:
		returnmsg(recdata,cmd,msg,0) 
	return True	


def MQTT_pin_level(cmd, message, recdata):
	msgarray=message.split(":")
	PIN=msgarray[1]
	PINlevel=statusdataDBmod.read_status_data(GPIO_data,PIN,"level")
	if PINlevel is not None:
		returnmsg(recdata,cmd,str(PINlevel),1)
		return True
	else:
		returnmsg(recdata,cmd,"error",0)
		return False	


	

def isPinActive(PIN):
	PINlevel=statusdataDBmod.read_status_data(GPIO_data,PIN,"level")
	#print " pin Level" , PINlevel
	if PINlevel is not None:
		return PINlevel		
	else:
		return False





def sendcommand(cmd, message, recdata):
	# as future upgrade this function might be run asincronously using "import threading"

	if ISRPI:
		ack=execute_task(cmd, message, recdata)
	else:
		print(" Client to support MQTT not installed")
		ack=execute_task_fake(cmd, message, recdata)
	return ack
	

def connecttobroker(address,port,timeout=180):
	client = MQTTutils.Client()
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

