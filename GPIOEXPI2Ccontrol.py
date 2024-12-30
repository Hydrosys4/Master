# -*- coding: utf-8 -*-

# Support for the GPIO expansion board MCP23017
# Possible address setting: 0x20 to 0x27
# GPIOEXPI2Ccontrol

import time
from datetime import datetime,date,timedelta
import threading

import glob
import logging
import statusdataDBmod
import sys, os
import json
basepath=os.getcwd() # get current path


libpath="libraries/MCP/MCP23017" # should be without the backslash at the beginning
sys.path.append(os.path.join(basepath, libpath)) # this adds new import paths to add modules
from MCP23017 import MCP23017


logger = logging.getLogger("hydrosys4."+__name__)

# declare the expansion object 
# INIT the devices ----------------------------------------------------------------------------------############

MCPDEVICES={}
for i in range(0x20,0x28):
	print(hex(i))
	obj = MCP23017(address = i, num_gpios = 16) # MCP23017
	if obj.error:
		print(obj.errormsg)
	else:
		MCPDEVICES[hex(i)]=obj

# Add to the list of possible commands

ISGPIOEXP=False
if MCPDEVICES:
	ISGPIOEXP=True


if ISGPIOEXP:
	HWCONTROLLIST=["pulse/I2CGPIOEXP","stoppulse/I2CGPIOEXP","pinstate/I2CGPIOEXP","hbridge/I2CGPIOEXP","switchoff/I2CGPIOEXP", "switchon/I2CGPIOEXP"]
else:
	HWCONTROLLIST=[]

EXPGPIOPINLIST=["1","2", "3", "4","5","6", "7", "8", "9", "10", "11", "12","13","14", "15", "16"]


# status variables



GPIO_data={}
GPIO_data["default"]={"level":0, "state":None, "threadID":None}

PowerPIN_Status={}
PowerPIN_Status["default"]={"level":0, "state":"off", "pinstate":None, "timeZero":0}



def initMCP23017():
	# INIT the devices ----------------------------------------------------------------------------------############

	global MCPDEVICES
	global ISGPIOEXP
	global HWCONTROLLIST
	global EXPGPIOPINLIST
	
	MCPDEVICES={}
	for i in range(0x20,0x28):
		
		obj = MCP23017(address = i, num_gpios = 16) # MCP23017
		if obj.error:
			print(obj.errormsg)
		else:
			MCPDEVICES[hex(i)]=obj
			print("MCP23017 found at address = ",  hex(i))

	# Add to the list of possible commands
	ISGPIOEXP=False
	if MCPDEVICES:
		ISGPIOEXP=True

	if ISGPIOEXP:
		HWCONTROLLIST=["pulse/I2CGPIOEXP","stoppulse/I2CGPIOEXP","pinstate/I2CGPIOEXP","hbridge/I2CGPIOEXP","switchoff/I2CGPIOEXP", "switchon/I2CGPIOEXP"]
	else:
		HWCONTROLLIST=[]
	EXPGPIOPINLIST=["1","2", "3", "4","5","6", "7", "8", "9", "10", "11", "12","13","14", "15", "16"]


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
	
	print(" WELLCOME TO THE I2CGPIOEXP CONTROL ")
	print("MESSAGE " + message)
	
	if cmd in HWCONTROLLIST:
	
		if cmd==HWCONTROLLIST[0]:	# pulse
			return gpio_pulse(cmd, message, recdata)
			
		elif cmd==HWCONTROLLIST[1]:	# stoppulse
			return gpio_stoppulse(cmd, message, recdata)			
		
		elif cmd==HWCONTROLLIST[2]:	# pinstate
			return gpio_pin_level(cmd, message, recdata)
			
		elif cmd==HWCONTROLLIST[3]: #hbridge	
			return ""	

		elif cmd==HWCONTROLLIST[4]:	# pinstate
			return gpio_switchoff(cmd, message, recdata)

		elif cmd==HWCONTROLLIST[5]:	# pinstate
			return gpio_switchon(cmd, message, recdata)

	else:
		msg="Command not found"
		returnmsg(recdata,cmd,msg,0)
		return False
	return False


def execute_task_fake(cmd, message, recdata):
	
	
	if cmd==HWCONTROLLIST[0]:	
		gpio_pulse(cmd, message, recdata)
		return True;


		
	else:
		msg="no fake command available" + cmd
		returnmsg(recdata,cmd,msg,0)
		return False
		
	return True
	




def powerPIN_start(address, POWERPIN,logic,waittime):
	if POWERPIN!="":
		PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,address+POWERPIN,"level")
		statusdataDBmod.write_status_data(PowerPIN_Status,address+POWERPIN,"level",PowerPINlevel+1)
		#PowerPIN_Status[POWERPIN]["level"]+=1
		#start power pin
		PowerPINstate=statusdataDBmod.read_status_data(PowerPIN_Status,address+POWERPIN,"state")
		if PowerPINstate=="off":
			GPIO_setup(address, POWERPIN, "out")
			if logic=="pos": 
				GPIO_output(address, POWERPIN, 1)
				statusdataDBmod.write_status_data(PowerPIN_Status,address+POWERPIN,"pinstate","1")
				#PowerPIN_Status[POWERPIN]["pinstate"]="1"
			else:
				GPIO_output(address, POWERPIN, 0)
				statusdataDBmod.write_status_data(PowerPIN_Status,address+POWERPIN,"pinstate","0")
				#PowerPIN_Status[POWERPIN]["pinstate"]="0"
				
			statusdataDBmod.write_status_data(PowerPIN_Status,address+POWERPIN,"state","on")	
			#PowerPIN_Status[POWERPIN]["state"]="on"
			#print "PowerPin activated ", POWERPIN
			time.sleep(waittime)
	return True	

		
def powerPIN_stop(address, POWERPIN,waittime):
	if POWERPIN!="":
		#set powerpin to zero again in case this is the last thread
		PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,address+POWERPIN,"level")
		statusdataDBmod.write_status_data(PowerPIN_Status,address+POWERPIN,"level",PowerPINlevel-1)
		#PowerPIN_Status[POWERPIN]["level"]-=1		
		#stop power pin	
		if (PowerPINlevel-1)<=0:
			PowerPINstate=statusdataDBmod.read_status_data(PowerPIN_Status,address+POWERPIN,"state")
			if PowerPINstate=="on":
				time.sleep(waittime)
				PowerPINpinstate=statusdataDBmod.read_status_data(PowerPIN_Status,address+POWERPIN,"pinstate")
				if PowerPINpinstate=="1": 
					GPIO_output(address,POWERPIN, 0)
					statusdataDBmod.write_status_data(PowerPIN_Status,address+POWERPIN,"pinstate","0")
					#PowerPIN_Status[POWERPIN]["pinstate"]="0"
				elif PowerPINpinstate=="0":
					GPIO_output(address,POWERPIN, 1)
					statusdataDBmod.write_status_data(PowerPIN_Status,address+POWERPIN,"pinstate","1")
					#PowerPIN_Status[POWERPIN]["pinstate"]="1"
				statusdataDBmod.write_status_data(PowerPIN_Status,address+POWERPIN,"state","off")
				#PowerPIN_Status[POWERPIN]["state"]="off"

	return True	

def CheckRealHWpin(PIN=""):
	if ISGPIOEXP:
		if PIN in EXPGPIOPINLIST:
			try:
				PINint=int(PIN)
				return True, PINint
			except:
				return False, 0	
	return False, 0		

def GPIO_output(address , PINstr, level ):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		if address in MCPDEVICES:
			mcp=MCPDEVICES[address]
		else:
			msg= "Address =" + address + " not available for this Hardware"
			logger.error(msg)
			print(msg)
			return False
		PIN=PIN-1
		if level==0:
			mcp.output(PIN, mcp.LOW)
		else:
			mcp.output(PIN, mcp.HIGH)
		statusdataDBmod.write_status_data(GPIO_data, address + PINstr, "level", level)
		logger.info("Set PIN=%s to State=%s", PINstr, str(level))
		return True
	else:
		if PINstr != "N/A":
			msg= "PIN=" + PINstr + " not Valid for this Hardware (" + address + ")"
			logger.error(msg)
			print(msg)

	return False

def GPIO_setup(address, PINstr, state, pull_up_down=""):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		if address in MCPDEVICES:
			mcp=MCPDEVICES[address]
		else:
			return False
		PIN=PIN-1
		if state=="out":
			mcp.pinMode(PIN, mcp.OUTPUT)

		else:
			if pull_up_down=="pull_down":
				mcp.pinMode(PIN, mcp.INPUT)
				mcp.pullUp(PIN, 0)
				
			elif pull_up_down=="pull_up":
				mcp.pinMode(PIN, mcp.INPUT)
				mcp.pullUp(PIN, 1)
				
			else:
				mcp.pinMode(PIN, mcp.INPUT)
	
	#GPIO_data[PIN]["state"]=state
	statusdataDBmod.write_status_data(GPIO_data,PINstr,"state",state)
	return True



def endpulse(address, PINstr,logic,POWERPIN):
	#GPIO_data[PIN]["threadID"]=None
	statusdataDBmod.write_status_data(GPIO_data,address+PINstr,"threadID",None)
	if logic=="pos":
		level=0
	else:
		level=1
	

	GPIO_output(address, PINstr, level)
	
	powerPIN_stop(address, POWERPIN,0)

	#print "pulse ended", time.ctime() , " PIN=", PINstr , " Logic=", logic , " Level=", level
	return True

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



def gpio_pulse(cmd, message, recdata):
	successflag=0
	msgarray=message.split(":")
	messagelen=len(msgarray)	
	PIN=msgarray[1]

	pulsetime_str=msgarray[2]

	isvalid, pulsestr , pulsesecond = pulse_value(pulsetime_str)
	if not isvalid:
		msg="Wrong value for pulse" + pulsetime_str
		logger.error(msg)
		successflag=0
		returnmsg(recdata,cmd,msg,successflag)
		return True	

	logic="pos"
	if messagelen>3:
		logic=msgarray[3]
	
	POWERPIN=""	
	if messagelen>4:	
		POWERPIN=msgarray[4]	
	
		
	address=""	# this is the default address of the MCP 23017
	if messagelen>5:	
		address=msgarray[5]
	if address=="":
		address="0x20"
			

	activationmode=""
	if messagelen>7:	
		activationmode=msgarray[7]
		
		


	if isPinActive(address,PIN,logic):
		if activationmode=="NOADD": # no action needed
			print("No Action, pulse activated when PIN already active and activationmode is NOADD")
			logger.warning("No Action, pulse activated when PIN already active and activationmode is NOADD")
			successflag=1
			returnmsg(recdata,cmd,PIN,successflag)
			return True



	# in case another timer is active on this PIN, cancel it 
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,address+PIN,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
	
	else:
		if not pulsetime_str=="ON": # exclude powerpin functiopn in case of ON
			powerPIN_start(address, POWERPIN,logic,0.2) # it is assumed that the logic (pos,neg) of the powerpin is the same of the pin to pulse, in the future it might be useful to specify the powerpin logic separately
		GPIO_setup(address, PIN, "out")
		if logic=="pos":
			level=1
		else:
			level=0
		pulseok=GPIO_output(address, PIN, level)
		if not pulseok:
			msg="Not able to activate the pulse in GPIO Expansion, Address I2C: " + address + " PIN: "+ PIN
			returnmsg(recdata,cmd,msg,0)
			return True	


	if not pulsetime_str=="ON": # in case is ON, do not call the callback to end the pulse
		NewPINthreadID=threading.Timer(pulsesecond, endpulse, [address, PIN , logic , POWERPIN ])
		NewPINthreadID.start()
		statusdataDBmod.write_status_data(GPIO_data,address+PIN,"threadID",NewPINthreadID)

	#print "pulse started", time.ctime() , " PIN=", PIN , " Logic=", logic 
	successflag=1
	returnmsg(recdata,cmd,PIN,successflag)
	return True	

def gpio_stoppulse(cmd, message, recdata):
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN=msgarray[1]
	
	logic="pos"
	if messagelen>3:
		logic=msgarray[3]
	
	POWERPIN=""
	if messagelen>4:	
		POWERPIN=msgarray[4]
	
			
	address=""	# this is the default address of the MCP 23017
	if messagelen>5:	
		address=msgarray[5]
	if address=="":
		address="0x20"
	
	
	if not isPinActive(address,PIN,logic):
		print("No Action, Already OFF")
		logger.warning("No Action, Already OFF")
		successflag=1
		returnmsg(recdata,cmd,PIN,successflag)
		return True	

	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,address+PIN,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
		
	endpulse(address, PIN,logic,POWERPIN)	#this also put powerpin off		

	returnmsg(recdata,cmd,PIN,1)
	return True	




def gpio_switchon(cmd, message, recdata):
	successflag=0
	msgarray=message.split(":")
	messagelen=len(msgarray)	
	PIN=msgarray[1]

	onoffcmd=msgarray[2]

	logic="pos"
	if messagelen>3:
		logic=msgarray[3]
	
	POWERPIN=""	
	if messagelen>4:	
		POWERPIN=msgarray[4]	
	
		
	address=""	# this is the default address of the MCP 23017
	if messagelen>5:	
		address=msgarray[5]
	if address=="":
		address="0x20"
			

	activationmode=""
	if messagelen>7:	
		activationmode=msgarray[7]
		
	if isPinActive(address,PIN,logic):
		if activationmode=="NOADD": # no action needed
			print("No Action, pulse activated when PIN already active and activationmode is NOADD")
			logger.warning("No Action, pulse activated when PIN already active and activationmode is NOADD")
			successflag=1
			returnmsg(recdata,cmd,PIN,successflag)
			return True

	# in case another timer is active on this PIN, cancel it 
	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,address+PIN,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
	
	else:
		GPIO_setup(address, PIN, "out")
		if logic=="pos":
			level=1
		else:
			level=0
		pulseok=GPIO_output(address, PIN, level)
		if not pulseok:
			msg="Not able to activate the pulse in GPIO Expansion, Address I2C: " + address + " PIN: "+ PIN
			returnmsg(recdata,cmd,msg,0)
			return True	

	#print "pulse started", time.ctime() , " PIN=", PIN , " Logic=", logic 
	successflag=1
	returnmsg(recdata,cmd,PIN,successflag)
	return True	




def gpio_switchoff(cmd, message, recdata):
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN=msgarray[1]
	
	logic="pos"
	if messagelen>3:
		logic=msgarray[3]
	
	POWERPIN=""
	if messagelen>4:	
		POWERPIN=msgarray[4]
	
			
	address=""	# this is the default address of the MCP 23017
	if messagelen>5:	
		address=msgarray[5]
	if address=="":
		address="0x20"
	
	if not isPinActive(address,PIN,logic):
		print("No Action, Already OFF")
		logger.warning("No Action, Already OFF")
		successflag=1
		returnmsg(recdata,cmd,PIN,successflag)
		return True	

	PINthreadID=statusdataDBmod.read_status_data(GPIO_data,address+PIN,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
		
	endpulse(address, PIN,logic,POWERPIN)	#this also put powerpin off		

	returnmsg(recdata,cmd,PIN,1)
	return True	


def gpio_pin_level(cmd, message, recdata):
	msgarray=message.split(":")
	PIN=msgarray[1]	
	address=msgarray[2]
	if address=="":
		address="0x20"

	PINlevel=statusdataDBmod.read_status_data(GPIO_data,address+PIN,"level")
	if PINlevel is not None:
		returnmsg(recdata,cmd,str(PINlevel),1)
		return True
	else:
		returnmsg(recdata,cmd,"error",0)
		return False	



def read_input_pin(cmd, message, recdata):
	
	# this is useful for the real time reading. Suggest to put in oneshot for the hardware configuration because the database record timing is given by the interrupts
	successflag=1
	msgarray=message.split(":")
	#print " read pin input ", message
	PINstr=msgarray[1]
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		if GPIO.input(PIN):
			reading="1"
		else:
			reading="0"
		returnmsg(recdata,cmd,reading,successflag)
	else:
		successflag=0
		returnmsg(recdata,cmd,"error",successflag)
	return True

def isPinActive(address, PIN, logic):
	PINlevel=statusdataDBmod.read_status_data(GPIO_data,address+PIN,"level")
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



def sendcommand(cmd, message, recdata):
	# as future upgrade this function might be run asincronously using "import threading"

	ack=execute_task(cmd, message, recdata)

	return ack



if __name__ == '__main__':
	

	import random
	
	mcpdevices={}
	for i in range(0x20,0x28):
		print(hex(i))
		obj = MCP23017(address = i, num_gpios = 16) # MCP23017
		if obj.error:
			print(obj.errormsg)
		else:
			mcpdevices[hex(i)]=obj

	print (mcpdevices)

	address="0x20"
	mcp=mcpdevices[address]

	for pin in range(9,15):
		mcp.pinMode(pin, mcp.OUTPUT)
		mcp.output(pin, mcp.HIGH)
	while (True):
		pin = random.randint(9,14)
		
		mcp.output(pin, mcp.LOW)  # Pin 0 High
		print(pin)
		time.sleep(0.1)
		mcp.output(pin, mcp.HIGH)  # Pin 0 Low


