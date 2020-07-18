# -*- coding: utf-8 -*-

import time
import datetime
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
basepath=os.getcwd() # get current path

logger = logging.getLogger("hydrosys4."+__name__)

ISRPI=MQTTutils.MQTTlib

CLIENTSLIST={}



# in MQTT pin can still be used as subtopic, important for the HBRIDGE configuration

if ISRPI:
	#HWCONTROLLIST=["pulse/MQTT","stoppulse/MQTT","pinstate/MQTT","hbridge/MQTT","hbridgestatus/MQTT"]
	HWCONTROLLIST=["pulse/MQTT"]
else:
	HWCONTROLLIST=[]

# status variables

hbridge_data={}
hbridge_data["default"]={'busyflag':False}

GPIO_data={}
GPIO_data["default"]={"level":0, "state":None, "threadID":None}

PowerPIN_Status={}
PowerPIN_Status["default"]={"level":0, "state":"off", "pinstate":None}


def Create_connections_and_subscribe():
	global CLIENTSLIST
	MQTTutils.Create_connections_and_subscribe(CLIENTSLIST)
	


def toint(thestring, outwhenfail):
	try:
		f=float(thestring)
		n=int(f)
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

		elif cmd==HWCONTROLLIST[2]:	# status
			return MQTT_pin_level(cmd, message, recdata)
			
		elif cmd==HWCONTROLLIST[3]: #hbridge	
			return MQTT_set_hbridge(cmd, message, recdata, hbridge_data)	

		elif cmd==HWCONTROLLIST[4]: #hbridge status	
			return get_hbridge_status(cmd, message, recdata, hbridge_data)


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




def powerPIN_start(POWERPIN,logic,waittime,address,durationsec): # powerpin will work only with same address and same topic/"powerpin number"
	if POWERPIN!="":
		PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,POWERPIN,"level")
		statusdataDBmod.write_status_data(PowerPIN_Status,POWERPIN,"level",PowerPINlevel+1)
		#PowerPIN_Status[POWERPIN]["level"]+=1
		#start power pin
		PowerPINstate=statusdataDBmod.read_status_data(PowerPIN_Status,POWERPIN,"state")
		if PowerPINstate=="off": 
			MQTT_output(POWERPIN, durationsec+waittime*2, address)
			statusdataDBmod.write_status_data(PowerPIN_Status,POWERPIN,"pinstate","1")
			#PowerPIN_Status[POWERPIN]["pinstate"]="1"
			statusdataDBmod.write_status_data(PowerPIN_Status,POWERPIN,"state","on")	
			#PowerPIN_Status[POWERPIN]["state"]="on"
			#print "PowerPin activated ", POWERPIN
			time.sleep(waittime)
	return True	

		
def powerPIN_stop(POWERPIN,waittime,address):
	if POWERPIN!="":
		#set powerpin to zero again in case this is the last thread
		PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,POWERPIN,"level")
		statusdataDBmod.write_status_data(PowerPIN_Status,POWERPIN,"level",PowerPINlevel-1)
		#PowerPIN_Status[POWERPIN]["level"]-=1		
		#stop power pin	
		if (PowerPINlevel-1)<=0:
			PowerPINstate=statusdataDBmod.read_status_data(PowerPIN_Status,POWERPIN,"state")
			if PowerPINstate=="on":
				time.sleep(waittime)
				PowerPINpinstate=statusdataDBmod.read_status_data(PowerPIN_Status,POWERPIN,"pinstate")

				MQTT_output(POWERPIN, 0, address)
				statusdataDBmod.write_status_data(PowerPIN_Status,POWERPIN,"pinstate","0")


				statusdataDBmod.write_status_data(PowerPIN_Status,POWERPIN,"state","off")
				#PowerPIN_Status[POWERPIN]["state"]="off"

	return True	



def MQTT_output(PINstr, level,address):
	# PINstr in reality is the topic
	# address is the MQTT clientid
	# level is the time in seconds for activation is specaking about pulses
	statusdataDBmod.write_status_data(GPIO_data,PINstr,"level",level)
	logger.info("Set PIN=%s to State=%s", PINstr, str(level))
	print (PINstr + " *********************************************** " , level)
	# get object from clientID
	#print(CLIENTSLIST)
	found=False
	if address in CLIENTSLIST:
		clientobj=CLIENTSLIST[address]["clientobj"]
		print("Publish: " + "  " + address + "   " + PINstr + "   "  + str(level))
		clientobj.publish(topic=PINstr, payload=str(level), qos=2)
	
	
	return True





def endpulse(PINstr,logic,POWERPIN,address):
	#GPIO_data[PIN]["threadID"]=None
	statusdataDBmod.write_status_data(GPIO_data,PINstr,"threadID",None)
	if logic=="pos":
		level=0
	else:
		level=1
	
	MQTT_output(PINstr, level, address)
	
	powerPIN_stop(POWERPIN,0,address)

	#print "pulse ended", time.ctime() , " PIN=", PINstr , " Logic=", logic , " Level=", level
	return True


def MQTT_pulse(cmd, message, recdata):
	successflag=0
	msgarray=message.split(":")
	messagelen=len(msgarray)	
	PIN=msgarray[1]

	testpulsetime=msgarray[2] # in seconds
	pulsesecond=int(testpulsetime)
	
	logic="pos"  # in MQTT logic is always pos, logic has no sense in MQTT
	#if messagelen>3:
	#	logic=msgarray[3]
	
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
	
	PINnum=toint(PIN,0)
	if not PINnum==0:
		PIN=title+"/"+PIN
		POWERPINnum=toint(POWERPIN,0)
		if not POWERPINnum==0:
			POWERPIN=title+"/"+POWERPIN	
		else:
			POWERPIN=""

	else:
		PIN=title
		POWERPIN=""
		
	if isPinActive(PIN,logic):
		if activationmode=="NOADD": # no action needed
			successflag=1
			recdata.append(cmd)
			recdata.append(PIN)
			recdata.append(successflag)
			return True
		

	# in case another timer is active on this TOPIC, cancel it 
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,PIN,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
	
	else:
		powerPIN_start(POWERPIN,logic,0.2,address,pulsesecond) # For MQTT logic is always POS

		if logic=="pos":
			level=pulsesecond
		else:
			level=0
		MQTT_output(PIN, level, address)

	NewPINthreadID=threading.Timer(pulsesecond, endpulse, [PIN , logic , POWERPIN , address])
	NewPINthreadID.start()
	statusdataDBmod.write_status_data(GPIO_data,PIN,"threadID",NewPINthreadID)

	#print "pulse started", time.ctime() , " PIN=", PIN , " Logic=", logic 
	successflag=1
	recdata.append(cmd)
	recdata.append(PIN)
	recdata.append(successflag)
	return True	

def MQTT_stoppulse(cmd, message, recdata):   # when ON send MQTT message with the duration in seconds of the activation, and when OFF send zero.
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
	
	address="localhost"	
	if messagelen>7:	
		address=msgarray[7]
	if address=="":
		address="localhost"	
	
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
	
	PINnum=toint(PIN,0)
	if not PINnum==0:
		PIN=title+"/"+PIN
		POWERPINnum=toint(POWERPIN,0)
		if not POWERPINnum==0:
			POWERPIN=title+"/"+POWERPIN	
		else:
			POWERPIN=""

	else:
		PIN=title
		POWERPIN=""
	
	
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,PIN,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
		
	endpulse(PIN,logic,POWERPIN,address)	#this also put powerpin off		
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
	
	

def isPinActive(PIN, logic):
	PINlevel=statusdataDBmod.read_status_data(GPIO_data,PIN,"level")
	#print " pin Level" , PINlevel
	if PINlevel is not None:
		isok=True
	else:
		return False
	if isok:
		if logic=="neg":
			if PINlevel: # pinlevel is integer 1 or zero
				activated=False
			else:
				activated=True
		elif logic=="pos":
			if PINlevel:
				activated=True
			else:
				activated=False
	return activated

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
	recdata=[]
	for i in range(0,30):
		get_DHT22_temperature_fake("tempsensor1", "" , recdata , DHT22_data )
		time.sleep(0.4)
		print(DHT22_data['lastupdate'])

