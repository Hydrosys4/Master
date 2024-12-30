# -*- coding: utf-8 -*-
"""
selected plan utility
"""
from __future__ import print_function
from __future__ import division
from builtins import str
from builtins import range
from past.utils import old_div
import shutil
import logging
import re
import os
import os.path
import sys
import string
import random
from datetime import datetime,date,timedelta
import time
import filestoragemod
import HWcontrol
import MQTTcontrol
import HC12control
import GPIOEXPI2Ccontrol
import photomod
import cameradbmod
import struct
import imghdr
import copy
import messageboxmod
import statusdataDBmod




# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////


global DATABASEPATH
DATABASEPATH=filestoragemod.DATABASEPATH
global HWDATAFILENAME
HWDATAFILENAME="hwdata.txt"
global DEFHWDATAFILENAME
DEFHWDATAFILENAME="default/defhwdata.txt"

logger = logging.getLogger("hydrosys4."+__name__)
modlogger = logging.getLogger("actuator")

# ///////////////// -- Hawrware data structure Setting --  ///////////////////////////////
#important this data is used almost everywhere

HWdataRECORDKEY=[]
HWdataKEYWORDS={}

# HW_INFO group includes info for the UI and identification of the item
HW_INFO_IOTYPE="IOtype" # info group, needed, specify if input or output 
HW_INFO_NAME="name" # info group , mandatory, identifier of the item  (shown in the UI)
HW_INFO_MEASUREUNIT="unit"  # info group , mandatory, measurement unit of info parameter
HW_INFO_MEASURE="measure"  # info group , mandatory, measurement type of info parameter

# HW_CTRL group includes info hardware to speak with HWcontrol module
HW_CTRL_CMD="controllercmd" # HW control group , mandatory, command sent to the HWControl section to specify the function to select -> HW
HW_CTRL_PIN="pin" # HW control group,optional, specify the PIN board for the HWControl if needed -> gpiopin
HW_CTRL_PIN2="pin2" # HW control group,optional, specify the PIN board for the HWControl if needed -> gpiopin (new item in rel 1.08)
HW_CTRL_ADCCH="ADCchannel" # HW control group, optional, specify the arg1 board for the HWControl if needed -> "ADCchannel"
HW_CTRL_PWRPIN="powerpin"  # HW control group, optional, specify PIN that is set ON before starting tasks relevant to ADC convert, Actuator pulse, then is set OFF when the task is finished -> "ADCpowerpin"
HW_CTRL_LOGIC="logic"  # HW control group, optional, in case the relay works in negative logic
#"settingaction", # HW control group, use the controllercmd instead -> to be removed
HW_CTRL_ADDR="address" # HW control group, optional, specify this info for the HWControl if needed -> mailaddress, I2C address
HW_CTRL_TITLE="title" # HW control group, optional, specify this info for the HWControl if needed (mail title) -> "mailtitle"

#servo/stepper/sensors
HW_CTRL_FREQ="frequency" # HW control group , optional, working frequency of the servo
HW_CTRL_MIN="min"  # HW control group, optional, minimum of the duty cycle, for sensor this is the min corresponding to zero
HW_CTRL_MAX="max"  # HW control group, optional, maximum of the duty cycle, for sensor this is the max corresponding to scale

HW_CTRL_SCALE="scale"  # HW control group, optional, for sensor this is the scale (new item in rel 1.08)
HW_CTRL_OFFSET="offset"  # HW control group, optional, for sensor not clear how to use TBD (new item in rel 1.08)
HW_CTRL_DIR="direction"  # HW control group, optional, invert the data min/max (new item in rel 1.08)

HW_CTRL_DIVIDE="divide" # HW control group, optional, divide the data after scaling
HW_CTRL_SUBTRACT="subtract" # HW control group, optional, subtract from data prior scaling

HW_FUNC_USEDFOR="usefor" # function group , optional, description of main usage of the item and the actions associated with the plan "selectedplanmod"
HW_FUNC_SCHEDTYPE="schedulingtype" # function group , optional, between "oneshot" and "periodic" 
HW_FUNC_TIME="time"  #function group , optional, description of time or interval to activate the item depending on the "schedulingtype" item, in case of interval information the minutes are used for the period, seconds are used for start offset

USAGELIST=["sensorquery", "watercontrol", "fertilizercontrol", "lightcontrol", "temperaturecontrol", "humiditycontrol", "photocontrol", "mailcontrol", "powercontrol", "N/A", "Other"]
MEASURELIST=["Temperature", "Humidity" , "Light" , "Pressure" , "Time", "Quantity", "Moisture","Percentage","Events"]
MEASUREUNITLIST=["C", "%" , "Lum" , "hPa" , "Sec", "Pcs", "Volt","F"]


HWdataKEYWORDS[HW_INFO_IOTYPE]=["input"  , "output" ]
HWdataKEYWORDS[HW_INFO_NAME]=[]
HWdataKEYWORDS[HW_INFO_MEASUREUNIT]=MEASUREUNITLIST
HWdataKEYWORDS[HW_INFO_MEASURE]=MEASURELIST
HWdataKEYWORDS[HW_CTRL_CMD]=HWcontrol.HWCONTROLLIST+MQTTcontrol.HWCONTROLLIST+HC12control.HWCONTROLLIST+GPIOEXPI2Ccontrol.HWCONTROLLIST
HWdataKEYWORDS[HW_CTRL_PIN]=HWcontrol.RPIMODBGPIOPINLISTPLUS
HWdataKEYWORDS[HW_CTRL_PIN2]=HWcontrol.RPIMODBGPIOPINLISTPLUS

HWdataKEYWORDS[HW_CTRL_ADCCH]=HWcontrol.ADCCHANNELLIST
HWdataKEYWORDS[HW_CTRL_PWRPIN]=HWcontrol.RPIMODBGPIOPINLISTNA
HWdataKEYWORDS[HW_CTRL_LOGIC]=["pos","neg"]
HWdataKEYWORDS[HW_CTRL_ADDR]=[]
HWdataKEYWORDS[HW_CTRL_TITLE]=[]
HWdataKEYWORDS[HW_FUNC_USEDFOR]=USAGELIST #used for
HWdataKEYWORDS[HW_FUNC_SCHEDTYPE]=["oneshot", "periodic"] #scheduling type
HWdataKEYWORDS[HW_FUNC_TIME]=[] #time in format hh:mm:ss

HWdataKEYWORDS[HW_CTRL_FREQ]=[]
HWdataKEYWORDS[HW_CTRL_MIN]=[]
HWdataKEYWORDS[HW_CTRL_MAX]=[]

HWdataKEYWORDS[HW_CTRL_SCALE]=[]
HWdataKEYWORDS[HW_CTRL_OFFSET]=[]
HWdataKEYWORDS[HW_CTRL_DIR]=["dir","inv"]

HWdataKEYWORDS[HW_CTRL_DIVIDE]=[]
HWdataKEYWORDS[HW_CTRL_SUBTRACT]=[]

# ///////////////// -- Hawrware data structure Setting --  ///////////////////////////////

IOdata=[]
# read IOdata -----
if not filestoragemod.readfiledata(HWDATAFILENAME,IOdata): #read calibration file
	print("warning hwdata file not found -------------------------------------------------------")
	#read from default file
	filestoragemod.readfiledata(DEFHWDATAFILENAME,IOdata)
	print("writing default calibration data")
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
# end read IOdata -----
IOdatatemp=copy.deepcopy(IOdata)
IOdatarow={}

# ///////////////// --- END GLOBAL VARIABLES ------


# ///////////////// -- STATUS VARIABLES UTILITY --  ///////////////////////////////
Servo_Status={}
Servo_Status["default"]={'duty':"3"}

Stepper_Status={}
Stepper_Status["default"]={'position':"0"}

Hbridge_Status={}
Hbridge_Status["default"]={'position':"0"}

Blocking_Status={}
Blocking_Status["default"]={'priority':0} # priority level, the commands are executed only if the command priority is higher or equlal to the blocking status priority

Actuator_Enable_Status={}
Actuator_Enable_Status["default"]={'Enabled':"enable"}

Data_Visible_Status={}
Data_Visible_Status["default"]={'Visible':"True"}

def UpdateCMDcontrol():
	global HWdataKEYWORDS
	HWdataKEYWORDS[HW_CTRL_CMD]=HWcontrol.HWCONTROLLIST+MQTTcontrol.HWCONTROLLIST+HC12control.HWCONTROLLIST+GPIOEXPI2Ccontrol.HWCONTROLLIST


# ///////////////// --- END STATUS VARIABLES ------

# procedures for the Enable/Disable

# Status variable  --> Actuator_Enable_Status

def ReadActuatorEnabled(Target):
	return statusdataDBmod.read_status_data(Actuator_Enable_Status,Target,'Enabled',True,"Actuator_Enable_Status")

def WriteActuatorEnabled(Target, status):
	global Actuator_Enable_Status
	statusdataDBmod.write_status_data(Actuator_Enable_Status,Target,'Enabled',status,True,"Actuator_Enable_Status")
	
# Status variable  --> Data_Visible_Status

def ReadVisibleStatus(Target):
	return statusdataDBmod.read_status_data(Data_Visible_Status,Target,'Visible',True,"Data_Visible_Status")

def WriteVisibleStatus(Target, status):
	global Data_Visible_Status
	statusdataDBmod.write_status_data(Data_Visible_Status,Target,'Visible',status,True,"Data_Visible_Status")




#-- start filestorage utility--------////////////////////////////////////////////////////////////////////////////////////	

# filestoragemod.readfiledata(filename,filedata)
# filestoragemod.savefiledata(filename,filedata)
# filestoragemod.appendfiledata(filename,filedata)
# filestoragemod.savechange(filename,searchfield,searchvalue,fieldtochange,newvalue)
# filestoragemod.deletefile(filename)

def readfromfile():
	global IOdata
	filestoragemod.readfiledata(HWDATAFILENAME,IOdata)


def IOdatatempalign():
	global IOdatatemp
	IOdatatemp=copy.deepcopy(IOdata)

def	IOdatafromtemp():
	global IOdata
	IOdata=copy.deepcopy(IOdatatemp)
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)

def	SaveData():
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)

	
def checkdata(fieldtocheck,dictdata,temp=True): # check if basic info in the fields are correct
# name is the unique key indicating the row of the list, dictdata contains the datato be verified
	# check the "name" field
	fieldname=HW_INFO_NAME
	if (fieldtocheck==fieldname)or(fieldtocheck==""):
		if fieldname in dictdata:
			fieldvalue=dictdata[fieldname]	
			if fieldvalue=="":
				message="Name is empty"
				return False, message
			elif not re.match("^[A-Za-z0-9_-]*$", fieldvalue):
				message="Name should not contains alphanumeric caracters or spaces"
				return False, message		
			else:
				#check same name already present in IOdatatemp
				if searchmatch(fieldname,fieldvalue,temp):
					message="Same name is already present"
					return False, message
					
	
	fieldname=HW_FUNC_TIME
	correlatedfield=HW_INFO_IOTYPE	
	if (fieldtocheck==fieldname)or(fieldtocheck==""):
		if (correlatedfield in dictdata)and(fieldname in dictdata):
			fieldvalue=dictdata[fieldname]	
			if fieldvalue!="":
				#check format is correct
				if len(fieldvalue.split(":"))<3:
					message="Please enter correct time format hh:mm:ss"
					return False, message
			else:

				if dictdata[correlatedfield]=="input":
					message="Time cannot be empty for item belonging to input"
					return False, message	
	
	
	# check select field dependencies
	#dictdata[HW_INFO_IOTYPE]=["input"  , "output" ]
	#dictdata[HW_INFO_MEASUREUNIT]=MEASUREUNITLIST
	#dictdata[HW_INFO_MEASURE]=MEASURELIST
	#dictdata[HW_CTRL_CMD]=HWcontrol.HWCONTROLLIST

	# check if the PIN is same when using the "pulse"
	fieldname=HW_CTRL_PIN	
	correlatedfield=HW_CTRL_CMD
	if (fieldtocheck==fieldname)or(fieldtocheck==""):
		if (correlatedfield in dictdata)and(fieldname in dictdata):
			if "pulse"==dictdata[correlatedfield]:

				fieldvalue=dictdata[fieldname]	
				if fieldvalue!="N/A":
					listkeyvalue=[{"key":fieldname , "value":fieldvalue},{"key":correlatedfield , "value":dictdata[correlatedfield]}]
					if searchmatchN(listkeyvalue,temp):
						message="Same PIN already used"
						return False, message

	# check if the PIN is same when using the "pulse/I2CGPIOEXP"
	fieldname=HW_CTRL_PIN	
	correlatedfield=HW_CTRL_CMD
	if (fieldtocheck==fieldname)or(fieldtocheck==""):
		correlatedfieldvalue=dictdata.get(correlatedfield)
		if "pulse/I2CGPIOEXP"==correlatedfieldvalue:
			fieldvalue=dictdata.get(fieldname)	
			if fieldvalue!="N/A":
				listkeyvalue=[{"key":fieldname , "value":fieldvalue},{"key":correlatedfield , "value":correlatedfieldvalue},{"key":HW_CTRL_ADDR , "value":dictdata.get(HW_CTRL_ADDR)}]
				if searchmatchN(listkeyvalue,temp):
					message="Same PIN already used"
					return False, message


		
	#dictdata[HW_CTRL_ADCCH]=HWcontrol.ADCCHANNELLIST
	#dictdata[HW_CTRL_PWRPIN]=HWcontrol.RPIMODBGPIOPINLIST
	#dictdata[HW_CTRL_LOGIC]=["pos","neg"]
	#dictdata[HW_FUNC_USEDFOR]=USAGELIST #used for
	#dictdata[HW_FUNC_SCHEDTYPE]=["oneshot", "periodic"] #scheduling type
	return True, ""

def sendcommand(cmd,sendstring,recdata,target="", priority=0):
	if target!="":
		if ReadActuatorEnabled(target)=="enable":
			prioritystatus=statusdataDBmod.read_status_data(Blocking_Status,target,'priority')
			#print " Target output ", target , "priority status: ", prioritystatus , " Command Priority: ", priority
			#check if the actions are blocked
			if priority>=prioritystatus:
				if cmd in HWcontrol.HWCONTROLLIST:
					return HWcontrol.sendcommand(cmd,sendstring,recdata)
				elif cmd in MQTTcontrol.HWCONTROLLIST:
					return MQTTcontrol.sendcommand(cmd,sendstring,recdata)
				elif cmd in HC12control.HWCONTROLLIST:
					return HC12control.sendcommand(cmd,sendstring,recdata)
				elif cmd in GPIOEXPI2Ccontrol.HWCONTROLLIST:
					return GPIOEXPI2Ccontrol.sendcommand(cmd,sendstring,recdata)
				else:
					message = "Device '" + target + "' not found. cmd: " + cmd
					dictitem={'title': "Hardware Message (Error)", 'content': message, 'color': "red" }
					messageboxmod.SaveMessage(dictitem)

					modlogger.error(message)

					successflag=0
					recdata.append(cmd)
					recdata.append("Device not found")
					recdata.append(successflag)
					return True
			else:
				message = "Device '" + target + "' blocked. cmd: " + cmd
				dictitem={'title': "Hardware Message (Warning)", 'content': message, 'color': "yellow" }
				messageboxmod.SaveMessage(dictitem)

				modlogger.warning(message)

				successflag=0
				recdata.append(cmd)
				recdata.append("blocked")
				recdata.append(successflag)
				return True
		else:
			message = "Device '" + target + "' disabled. cmd: " + cmd
			dictitem={'title': "Hardware Message (Info)", 'content': message, 'color': "primary" }
			messageboxmod.SaveMessage(dictitem)

			modlogger.info(message)

			successflag=0
			recdata.append(cmd)
			recdata.append("Disabled")
			recdata.append(successflag)
			return True

	else:
		if cmd in HWcontrol.HWCONTROLLIST:
			return HWcontrol.sendcommand(cmd,sendstring,recdata)
		elif cmd in MQTTcontrol.HWCONTROLLIST:
			return MQTTcontrol.sendcommand(cmd,sendstring,recdata)
		elif cmd in HC12control.HWCONTROLLIST:
			return HC12control.sendcommand(cmd,sendstring,recdata)
		elif cmd in GPIOEXPI2Ccontrol.HWCONTROLLIST:
			return GPIOEXPI2Ccontrol.sendcommand(cmd,sendstring,recdata)

def normalizesensordata(reading_str,sensorname):	
	# get the normalization data
	Minimum=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_MIN)) # if not found searchdata return ""
	Maximum=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_MAX))
	Direction=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_DIR)) # can be two values "inv" , "dir"
	Scale=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_SCALE))
	Offset=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_OFFSET))					
	Divide=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_DIVIDE))					
	Subtract=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_SUBTRACT))					
	
	# transform all values to numbers
	Minvalue=tonumber(Minimum, 0)
	Maxvalue=tonumber(Maximum, 0)
	Scalevalue=tonumber(Scale, 1)
	Offsetvalue=tonumber(Offset, 0)
	Dividevalue=tonumber(Divide, 1)
	Subtractvalue=tonumber(Subtract, 0)
	readingvalue=tonumber(reading_str, 0)

	if abs(Minvalue-Maxvalue)>0.01: # in case values are zero or not consistent, stops here
		if Direction!="inv":
			den=Maxvalue-Minvalue
			readingvalue=old_div((readingvalue-Minvalue),den)
		else:
			den=Maxvalue-Minvalue
			readingvalue=1-old_div((readingvalue-Minvalue),den)

	# apply subtraction
	if Subtractvalue>0:
		readingvalue=readingvalue-Subtractvalue

	# apply scale
	if Scalevalue>0:
		readingvalue=readingvalue*Scalevalue

	# apply division
	if Dividevalue != 1:
		readingvalue=readingvalue/Dividevalue

	# apply offset
	readingvalue=readingvalue+Offsetvalue

	# transform to string and adjust the format
	reading_str=str('%.2f' % readingvalue)

	return reading_str

def getsensordata(sensorname,attemptnumber): #needed
	# this procedure was initially built to communicate using the serial interface with a module in charge of HW control (e.g. Arduino)
	# To lower the costs, I used the PI hardware itself but I still like the way to communicate with the HWcontrol module that is now a SW module not hardware
	isok=False
	statusmessage=""
	
	cmd=searchdata(HW_INFO_NAME,sensorname,HW_CTRL_CMD)
	Thereading=""	
	if not cmd=="":
		pin=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_PIN))
		arg1=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_ADCCH))
		arg2=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_PWRPIN))
		arg3=str(searchdata(HW_INFO_NAME,sensorname,HW_INFO_MEASUREUNIT))
		arg4=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_LOGIC))
		arg5=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_ADDR))
		arg6=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_PIN2))
		arg7=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_TITLE))
		
		timestr=searchdata(HW_INFO_NAME,sensorname,HW_FUNC_TIME)
		mastertimelist=separatetimestringint(timestr)
		timeperiodsec=mastertimelist[0]*3600+mastertimelist[1]*60+mastertimelist[0]
		
		arg8=str(timeperiodsec)
				
		sendstring=sensorname+":"+pin+":"+arg1+":"+arg2+":"+arg3+":"+arg4+":"+arg5+":"+arg6+":"+arg7+":"+arg8
		recdata=[]
		ack=False
		i=0
		while (not ack)and(i<attemptnumber): # old check when the serial interface was used, in this case ack only indicates that the trasmission was correct, not the sensor value
			ack=sendcommand(cmd,sendstring,recdata,sensorname,0)
			i=i+1
		if ack:
			if recdata[0]==cmd: # this was used to check the response and command consistency when serial comm was used
				if recdata[2]>0: # this is the flag that indicates if the measurement is correct
					#print " Sensor " , sensorname  , "reading ",recdata[1]	
					isok=True

					Thereading=normalizesensordata(recdata[1],sensorname)  # output is a string

					print(" Sensor " , sensorname  , "Normalized reading ",Thereading)
					logger.info("Sensor %s reading: %s", sensorname,Thereading)
					if len(recdata)>3:
						statusmessage=recdata[3]
				else:
					message = "Problem with sensor reading " + sensorname
					dictitem={'title': "Sensor Message (Warning)", 'content': message, 'color': "yellow" }
					messageboxmod.SaveMessage(dictitem)
					print(message)
					logger.error(message)
					statusmessage=recdata[1]
			else:
				message = "Problem with response consistency " + sensorname + " cmd " + cmd
				dictitem={'title': "Sensor Message (Warning)", 'content': message, 'color': "yellow" }
				messageboxmod.SaveMessage(dictitem)
				print(message)
				logger.error(message)
		else:
			message = "no answer from Hardware control module" + sensorname
			dictitem={'title': "Sensor Message (Warning)", 'content': message, 'color': "yellow" }
			messageboxmod.SaveMessage(dictitem)
			print(message)
			logger.error(message)
	else:
		print("sensor name not found in list of sensors ", sensorname)
		logger.error("sensor name not found in list of sensors : %s", sensorname)

	return isok, Thereading, statusmessage

def makepulse(target,duration,addtime=True, priority=0): # pulse in seconds , addtime=True extend the pulse time with new time , addtime=False let the current pulse finish , 
	
	if addtime:
		activationmode="ADD"
	else:
		activationmode="NOADD"
	
	
	#search the data in IOdata

	command=searchdata(HW_INFO_NAME,target,HW_CTRL_CMD)	
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	

	print( " MakePulse ")
	
	return activatepulse(command,PIN,duration,activationmode,target,priority)
	
	

	
def activatepulse(command,PIN,duration,activationmode,target,priority):	
	
	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	POWERPIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PWRPIN)	
	address=searchdata(HW_INFO_NAME,target,HW_CTRL_ADDR)	
	title=searchdata(HW_INFO_NAME,target,HW_CTRL_TITLE)		
	
	testpulsetime=duration
	
	# normal pulse
	sendstring=command+":"+PIN+":"+testpulsetime+":"+logic+":"+POWERPIN+":"+ address +":0"+":"+activationmode+":"+target+":"+title


	isok=False
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack = sendcommand(command,sendstring,recdata,target,priority)
		#print "returned data " , recdata
		# recdata[0]=command (string), recdata[1]=data (string) , recdata[2]=successflag (0,1)
		successflag=0
		if len(recdata)>2:
			successflag=recdata[2]
		msg=""
		if len(recdata)>1:
			msg=recdata[1]

		if ack and successflag:
			isok=True
			recdata.append("Pulse Started")
			return "Pulse Started", True
		else:
			if not successflag:
				print ( " Return Status ", msg)
				return msg , False
			
			
	return "Generic error", False
	
	
def switchon(target,addtime=True, priority=0): # pulse in seconds , addtime=True extend the pulse time with new time , addtime=False let the current pulse finish , 
	

	print ("### Switch ON ###")
	if addtime:
		activationmode="ADD"
	else:
		activationmode="NOADD"
	
	
	cmd=searchdata(HW_INFO_NAME,target,HW_CTRL_CMD)
	cmdlist=cmd.split("/")
	command="switchon"
	if len(cmdlist)>1:
		command=command+"/"+cmdlist[1]

	

	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	
	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	POWERPIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PWRPIN)	
	address=searchdata(HW_INFO_NAME,target,HW_CTRL_ADDR)	
	title=searchdata(HW_INFO_NAME,target,HW_CTRL_TITLE)		
	
	testpulsetime=""
	
	# normal pulse
	sendstring=command+":"+PIN+":"+testpulsetime+":"+logic+":"+POWERPIN+":"+ address +":0"+":"+activationmode+":"+target+":"+title
	print (sendstring)

	isok=False
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack = sendcommand(command,sendstring,recdata,target,priority)
		#print "returned data " , recdata
		# recdata[0]=command (string), recdata[1]=data (string) , recdata[2]=successflag (0,1)
		successflag=0
		if len(recdata)>2:
			successflag=recdata[2]
		msg=""
		if len(recdata)>1:
			msg=recdata[1]

		if ack and successflag:
			isok=True
			recdata.append("Pulse Started")
			return "Pulse Started", True
		else:
			if not successflag:
				print ( " Return Status ", msg)
				return msg , False
			
			
	return "Generic error", False


def stoppulse(target):
	#search the data in IOdata

	#print "Stop Pulse - ", target
	cmd=searchdata(HW_INFO_NAME,target,HW_CTRL_CMD)
	cmdlist=cmd.split("/")
	stopcmd="stoppulse"
	if len(cmdlist)>1:
		stopcmd=stopcmd+"/"+cmdlist[1]
	
	
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	
	
	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	POWERPIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PWRPIN)

		
	address=searchdata(HW_INFO_NAME,target,HW_CTRL_ADDR)	
	title=searchdata(HW_INFO_NAME,target,HW_CTRL_TITLE)	
			
	# normal pulse
	sendstring=stopcmd+":"+PIN+":"+"0"+":"+logic+":"+POWERPIN+":"+address+":0"+":"+target+":"+title

	#print "logic " , logic , " sendstring " , sendstring

	isok=False
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand(stopcmd,sendstring,recdata,target,5)
		#print "returned data " , recdata
		if ack and recdata[1]!="e":
			#print target, "correctly activated"
			isok=True
			return "Stopped" , True
			
	return "error" , False


def switchOFF(target):
	#search the data in IOdata
	print ("### Switch Off ####")

	cmd=searchdata(HW_INFO_NAME,target,HW_CTRL_CMD)
	cmdlist=cmd.split("/")
	cmd="switchoff"
	if len(cmdlist)>1:
		cmd=cmd+"/"+cmdlist[1]
	
	
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	
	
	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	#POWERPIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PWRPIN)
	POWERPIN=""

		
	address=searchdata(HW_INFO_NAME,target,HW_CTRL_ADDR)	
	title=searchdata(HW_INFO_NAME,target,HW_CTRL_TITLE)	
			
	# normal pulse
	sendstring=cmd+":"+PIN+":"+"0"+":"+logic+":"+POWERPIN+":"+address+":0"+":"+target+":"+title

	#print "logic " , logic , " sendstring " , sendstring

	isok=False
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand(cmd,sendstring,recdata,target,5)
		successflag=0
		if len(recdata)>2:
			successflag=recdata[2]
		msg=""
		if len(recdata)>1:
			msg=recdata[1]

		if ack and successflag:
			isok=True
			recdata.append("Switch OFF")
			return "Pulse Stop", True
		else:
			if not successflag:
				print ( " Return Status ", msg)
				return msg , False
			
			
	return "Generic error", False


def servoangle(target,percentage,delay,priority=0): #percentage go from zeo to 100 and is the percentage between min and max duty cycle
	
	global Servo_Status
	#search the data in IOdata
	isok=False
	
	print("Move Servo - ", target) #normally is servo1
	
	# check if servo is belonging to servolist
	servolist=searchdatalist(HW_CTRL_CMD,"servo",HW_INFO_NAME)
	
	if target in servolist:
	
		PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	

		try:

			FREQ=searchdata(HW_INFO_NAME,target,HW_CTRL_FREQ)	
			MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
			MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	

			previousduty=getservoduty(target) 
			dutycycle= str(int(MIN)+(int(MAX)-int(MIN))*int(percentage)/float(100))
			stepsnumber="40" # this should be a string
			
			difference=float(previousduty)-float(dutycycle)
			percentagediff=abs(float(100)*difference/(int(MAX)-int(MIN)))
			
			if percentagediff<1: # one percent difference
				print(" No difference with prevoius position ", target , " percentage difference ", percentagediff)
				return "same" , isok				
			
			if 0<=int(percentage)<=100:
				print("range OK")
			else:
				print(" No valid data for Servo ", target , " out of Range")
				return "Out of Range" , isok

		except ValueError:
			print(" No valid data for Servo", target)
			return "error" , isok


		sendstring="servo:"+PIN+":"+FREQ+":"+dutycycle+":"+str(delay)+":"+previousduty+":"+stepsnumber
		print(" sendstring " , sendstring)

		i=0
		while (not(isok))and(i<2):
			i=i+1
			recdata=[]
			ack= sendcommand("servo",sendstring,recdata,target,priority)
			print("returned data " , recdata)
			if ack and recdata[1]!="e":
				print(target, "correctly activated")
				# save duty as new status
				statusdataDBmod.write_status_data(Servo_Status,target,'duty',dutycycle)
				isok=True
				return percentage , isok
			
	return "error" , isok

def getservopercentage(target):
	percentage="50"
	MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
	MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	
	
	if (not MIN=="")and(not MAX==""):
		#print " MIN ", MIN , " MAX ", MAX
		try:
			den=(int(MAX)-int(MIN))
			percentage_num=int(old_div((100*(float(getservoduty(target))-int(MIN))),den))
			if percentage_num<0:
				percentage_num=0
			if percentage_num>100:
				percentage_num=100
			percentage=str(percentage_num)
		except:
			print(" No valid data for Servo", target)

	print("servo percntage " , percentage)
	return percentage

def getservoduty(element):
	return statusdataDBmod.read_status_data(Servo_Status,element,'duty')


# stepper section

def GO_stepper_position(target,position,priority=0):
	position=toint(position,0)
	prev_position_string=getstepperposition(target)
	prev_position=toint(prev_position_string,position)
	steps=position-prev_position
	isdone=False
	if steps>0:
		out , isdone=GO_stepper(target,steps,"FORWARD",priority)
	else:
		steps=abs(steps)	
		out , isdone=GO_stepper(target,steps,"BACKWARD",priority)
		
	return out , isdone


def get_stepper_busystatus(target): 
	tempdict , isok=get_stepper_HWstatus(target)
	if isok:
		if "busyflag" in tempdict:
			return tempdict["busyflag"]
	return ""
	
	
	
def get_stepper_HWstatus(target): 
	#search the data in IOdata
	isok=False
	
	try:
		Interface_Number=searchdata(HW_INFO_NAME,target,HW_CTRL_ADCCH)
	except ValueError:
		return "error" , isok
		
	sendstring="stepperstatus:"+Interface_Number
	print(" sendstring " , sendstring)
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("stepperstatus",sendstring,recdata,target,0) 
		print("returned data " , recdata)
		if ack:
			print(target, "correctly activated")	
			print("get stepper status : " , recdata[1])
			isok=True
			return recdata[1], isok
			
	return "Error" , isok



def GO_stepper(target,steps,direction,priority=0): 
	global Stepper_Status
	#search the data in IOdata
	isok=False
	print("Move Stepper - ", target) #only supported the I2C default address, the module supports 2 stepper interfaces: 1,2
	
	position_string=getstepperposition(target)
	
	print(" position " , position_string)
 
	try:
		Interface_Number=searchdata(HW_INFO_NAME,target,HW_CTRL_ADCCH)	
		FREQ=searchdata(HW_INFO_NAME,target,HW_CTRL_FREQ)	
		MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
		MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	

		steps=int(steps)
		
		if steps<=0:
			print(" No valid range for Stepper ", target)
			return "Out of Range" , isok
		
		# simulate endpoints
		position=int(position_string)
		
		if direction=="FORWARD":
			position=position+steps
		elif direction=="BACKWARD":
			position=position-steps

		if int(MIN)<=(position)<=int(MAX):
			print("range OK")
		else:
			print(" No valid range for Stepper ", target)
			return "Out of Range" , isok

	except ValueError:
		print(" No valid data for Servo", target)
		return "error" , isok


	sendstring="stepper:"+Interface_Number+":"+direction+":"+FREQ+":"+str(steps)
	print(" sendstring " , sendstring)

	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("stepper",sendstring,recdata,target,priority) 
		print("returned data " , recdata)
		if ack and recdata[1]!="e":
			print(target, "correctly activated")
			# save position as new status
			statusdataDBmod.write_status_data(Stepper_Status,target,'position',str(position),True,"Stepper_Status")
			
			isok=True
			return str(position) , isok
			
	return "Error" , isok

def getstepperposition(element):
	return statusdataDBmod.read_status_data(Stepper_Status,element,'position',True,"Stepper_Status")

def setstepperposition(element, position):
	global Stepper_Status
	return statusdataDBmod.write_status_data(Stepper_Status,element,'position',position,True,"Stepper_Status")


# END stepper section

# START hbridge section

def GO_hbridge_position(target,position_str,priority=0):

	prev_position_string=gethbridgeposition(target) # in range value
	prev_position=toint(prev_position_string,0)
	position=toint(position_str,prev_position)
	
	MINstr=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)
	MIN=toint(MINstr,0)
	MAXstr=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)
	MAX=toint(MAXstr,0)


	zerooffset=0
	steps=position-prev_position # in range values
	absolutesteps=abs(steps)
	if position<=MIN: # the final position is intended to be the minimum
		zerooffsetstr=searchdata(HW_INFO_NAME,target,HW_CTRL_OFFSET)
		zerooffset=toint(zerooffsetstr,0)		

	out=""
	isdone=False
	if steps>0:
		out , isdone=GO_hbridge(target,absolutesteps,zerooffset,"FORWARD",priority)
	elif steps<0:	
		out , isdone=GO_hbridge(target,absolutesteps,zerooffset,"BACKWARD",priority)
	
	return out , isdone




def GO_hbridge(target,steps_str,zerooffset,direction,priority=0): 
	global Hbridge_Status
	#search the data in IOdata
	isok=False
	print("Move Hbridge - ", target) 
	
	try:

		command=searchdata(HW_INFO_NAME,target,HW_CTRL_CMD)
		PIN1=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)
		PIN2=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN2)	
		logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)	
		MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
		MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	
		address=searchdata(HW_INFO_NAME,target,HW_CTRL_ADDR)	

		position_string=gethbridgeposition(target)
		
		print(" position " , position_string)


		steps=int(steps_str)
		
		print("PIN1 ", PIN1 , "PIN2 ", PIN2 , "steps ", steps , " direction " , direction, " MIN ", MIN , " MAX ", MAX)
		
		if steps<=0:
			print(" No valid range (ore Zero) for pulse steps", target)
			return "Out of Range" , isok
		
		print(" position " , position_string)
		# simulate endpoints
		position=int(position_string)
		
		print(" position int " , position)
		
		if direction=="FORWARD":
			position=position+steps
		elif direction=="BACKWARD":
			position=position-steps
			
		print(" position int " , position)
		
		if int(MIN)<=(position)<=int(MAX):
			print("range OK")
		else:
			print(" No valid range for hbridge ", target)
			return "Out of Range" , isok




	except ValueError:
		print(" No valid data for hbridge, please check the HardwareTable parameters ", target)
		return "error" , isok

	# here apply the offset
	steps=steps+zerooffset
	
	
	sendstring=command+":"+PIN1+":"+PIN2+":"+direction+":"+str(steps)+":"+logic+":"+address
	print(" sendstring " , sendstring)

	errorcode="error"
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= gpio_set_hbridge(command,sendstring,recdata,target,priority) 
		print("returned data " , recdata)
		if ack and recdata[1]!="e":
			print(target, "correctly activated")
			# save position as new status
			sethbridgeposition(target, str(position))
			#statusdataDBmod.write_status_data(Hbridge_Status,target,'position',str(position),True,"Hbridge_Status") # save in persistent mode
			isok=True
			return str(position) , isok
		else:
			errorcode="error"
			if len(recdata)>2:
				errorcode=recdata[2]
				
	return errorcode , isok



	
def gpio_set_hbridge(cmd, message, recdata, target, priority ):
			
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN1=msgarray[1]
	PIN2=msgarray[2]
	direction=msgarray[3]
	durationsecondsstr=msgarray[4]
	logic=msgarray[5]
	address=msgarray[6]
	
	#print "hbridge ", PIN1, "  ",  PIN2, "  ",  direction, "  ",  durationsecondsstr,  "  ", logic

	# check that both pins are at logic low state, so Hbridge is off
	PIN1active=getpinstate(target, address,  PIN1, logic)
	PIN2active=getpinstate(target, address,  PIN2, logic)
	
	hbridgebusy=PIN1active or PIN2active

	# Make the command suitable for other devices
	cmdlist=cmd.split("/")
	basecmd="pulse"
	cmd=basecmd
	if len(cmdlist)>1:
		cmd=basecmd+"/"+cmdlist[1]


	if hbridgebusy:
		print("hbridge motor busy ")
		logger.warning("hbridge motor Busy, not proceeding ")
		recdata.append(cmd)
		recdata.append("e")
		recdata.append("busy")
		return False
	

	POWERPIN="N/A"
	activationmode="NOADD"

	if direction=="FORWARD":
		#sendstring=cmd+":"+PIN1+":"+durationsecondsstr+":"+logic+":"+POWERPIN		
		statusmsg=activatepulse(cmd,PIN1,durationsecondsstr,activationmode,target,priority)
	else:
		#sendstring=cmd+":"+PIN2+":"+durationsecondsstr+":"+logic+":"+POWERPIN	
		statusmsg=activatepulse(cmd,PIN2,durationsecondsstr,activationmode,target,priority)
	
	startHbridgetimer(target) # here starts to count the seconds


	if statusmsg=="error":

		print("problem hbridge execution")
		logger.error("problem hbridge execution")
		recdata.append(cmd)
		recdata.append("e")
		return False


	recdata.append(cmd)
	recdata.append(PIN1+PIN2)
	
	return True	


def gpio_stop_hbridge(target):
			

	cmd=searchdata(HW_INFO_NAME,target,HW_CTRL_CMD)
	PIN1=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)
	PIN2=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN2)	
	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)	
	MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
	MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	
	address=searchdata(HW_INFO_NAME,target,HW_CTRL_ADDR)	
	title=searchdata(HW_INFO_NAME,target,HW_CTRL_TITLE)

	# check that both pins are at logic low state, so Hbridge is off
	PIN1active=getpinstate(target, address,  PIN1, logic)
	PIN2active=getpinstate(target, address,  PIN2, logic)
	
	hbridgebusy=PIN1active or PIN2active

	if hbridgebusy:
		# proceed to stop the Hbridge 
		if PIN1active:
			PIN = PIN1
			direction="FORWARD"
		if PIN2active:
			PIN = PIN2
			direction="BACKWARD"
	
		POWERPIN="N/A"
		activationmode="NOADD"

		#search the data in IOdata

		#print "Stop Pulse - ", target
		cmdlist=cmd.split("/")
		stopcmd="stoppulse"
		if len(cmdlist)>1:
			stopcmd=stopcmd+"/"+cmdlist[1]
					
		# normal stop pulse
		sendstring=stopcmd+":"+PIN+":"+"0"+":"+logic+":"+POWERPIN+":"+address+":0"+":"+target+":"+title

		isok=False
		i=0
		while (not(isok))and(i<2):
			i=i+1
			recdata=[]
			ack= sendcommand(stopcmd,sendstring,recdata,target,5)
			#print "returned data " , recdata
			if ack and recdata[1]!="e":
				steps = stopHbridgetimer(target)
				position=toint(gethbridgeposition(target,previous=True),0) # problem this includes already the STEPS
				print (" Position ", position, " Steps ", steps , "<------------------")
				if direction=="FORWARD":
					position=position+steps
				if direction=="BACKWARD":
					position=position-steps
				#print target, "correctly stopped"
				sethbridgeposition(target,position)
				isok=True
				return str(position), True
			
	return "error" , False
	





def gethbridgeposition(element, previous=False):
	if not previous:
		return statusdataDBmod.read_status_data(Hbridge_Status,element,'position',True,"Hbridge_Status")
	else:
		return statusdataDBmod.read_status_data(Hbridge_Status,element,'prev_position',True,"Hbridge_Status")

def sethbridgeposition(element, position):
	global Hbridge_Status
	prev_position=statusdataDBmod.read_status_data(Hbridge_Status,element,'position',True,"Hbridge_Status")
	statusdataDBmod.write_status_data(Hbridge_Status,element,'prev_position',prev_position,True,"Hbridge_Status")
	return statusdataDBmod.write_status_data(Hbridge_Status,element,'position',position,True,"Hbridge_Status")

def stopHbridgetimer(element):
	timestop= time.time()
	timestart=statusdataDBmod.read_status_data(Hbridge_Status,element,'timer')
	return round(timestop-timestart)


def startHbridgetimer(element):
	global Hbridge_Status
	timestart= time.time()
	return statusdataDBmod.write_status_data(Hbridge_Status,element,'timer',timestart)





# END hbridge section


def getpinstate(target, address, PIN, logic, priority=0):
	#search the data in IOdata
	print("Check PIN state ", target)
	cmd=searchdata(HW_INFO_NAME,target,HW_CTRL_CMD)
	cmdlist=cmd.split("/")
	basecmd="pinstate"
	cmd=basecmd
	if len(cmdlist)>1:
		cmd=basecmd+"/"+cmdlist[1]
	return getpinstate_pin(cmd, address, PIN, logic, priority)


def getpinstate_pin(cmd, address, PIN, logic, priority=0):
	
	print("cmd " , cmd, "logic ", logic)

	sendstring=cmd+":"+PIN+":"+address
	print (sendstring)
	isok=False
	value=0
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand(cmd,sendstring,recdata)
		print("returned data " , recdata)
		if ack and recdata[1]!="e":
			value=recdata[1]
			isok=True
		else:
			activated="error"
			
	if isok:
		if logic=="neg":
			if value=="0":
				activated=True
			else:
				activated=False
		elif logic=="pos":
			if value=="1":
				activated=True
			else:
				activated=False		

				
	return activated





def readinputpin(PIN):
	#search the data in IOdata
	
	#print "Read input PIN ", PIN
	sendstring="inputpin:"+str(PIN)

	isok=False
	value=0
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("readinputpin",sendstring,recdata,target="")
		#print "returned data " , recdata
		if ack and recdata[2]:
			value=recdata[1]
			isok=True
		else:
			value="error"
			
	return value # either "0" or "1"
	
	
	

def getsensornamebymeasure(measure):
	# MEASURELIST is the list with valid values for the "measure" parameter
	sensorlist=searchdatalist(HW_INFO_MEASURE,measure,HW_INFO_NAME)
	return sensorlist

			
def readallsensors():
	# read from serial the values for arduino
	sensorlist=searchdatalist(HW_INFO_IOTYPE,"input",HW_INFO_NAME)
	sensorvalues={}
	for sensorname in sensorlist:
		isok, sensorvalues[sensorname], errmsg =getsensordata(sensorname,3)
	return sensorvalues



			
def checkallsensors():
	# check if the sensor respond properly according to sensor list in HWdata file
	print(" check sensor list ")
	sensorlist=searchdatalist(HW_INFO_IOTYPE,"input",HW_INFO_NAME)
	sensorvalues={}
	for sensorname in sensorlist:
		isok, sensorvalues[sensorname], errmsg = getsensordata(sensorname,3)
	return sensorvalues

		
def initallGPIOpins():	
	removeallinterruptevents()
	checkGPIOconsistency()
	initallGPIOinput()
	initallGPIOoutput()
	initallGPIOoutputEXP()
	return True



def initGPIOEXP():
	GPIOEXPI2Ccontrol.initMCP23017()

def initHC12():
	# check if the pins for the HC12 connection are not already used
	ProblemFound=False
	pinlist=HC12control.pinlist
	for hc12pin in pinlist:
		itemname=searchdatalist(HW_CTRL_PIN,hc12pin,HW_INFO_NAME)
		if itemname:
			cmd=searchdatalist(HW_INFO_NAME,itemname,HW_CTRL_CMD)
			if not ("/" in cmd):
				ProblemFound=True
				logger.warning("Not possible to connect for the HC-12, require pins already used for other purposes PIN= %s", hc12pin)
				print("Not possible to connect for the HC-12, require pins already used for other purposes", hc12pin)
				break
	if ProblemFound:
		HC12control.ISRPI=False
		if HC12control.HC12mod.HC12radionet: 
			HC12control.HC12mod.HC12radionet.mediumconnected=False
		HC12control.HWCONTROLLIST=[]
	else:
		HC12control.initHC12()


def initMQTT():

	MQTTcontrol.Disconnect_clients()
	MQTTcontrol.CLIENTSLIST={}
	# define the list of parameters for the initialization
	MQTTitemlist=searchdatalistinstr(HW_CTRL_CMD,"/mqtt",HW_INFO_NAME)

	for items in MQTTitemlist:
		client={}		
		client["broker"]= searchdata(HW_INFO_NAME,items,HW_CTRL_ADDR)
		client["port"]=1883 # for non encrypted operations
		client["username"]=""
		client["password"]=""
		client["pubtopic"]="" # this will be provided during operations
		fulltopic=searchdata(HW_INFO_NAME,items,HW_CTRL_TITLE)
		if searchdata(HW_INFO_NAME,items,HW_INFO_IOTYPE)=="output":
			# read on "stat"
			stattopic = fulltopic.replace("cmnd", "stat")
			subtopic=stattopic+"/RESULT" 
			client["subtopic"]=subtopic
			# subscribe topic for IP stats
			client["subtopicstat5"]=stattopic+"/STATUS5"

			
		else:
			# the initial part of the fulltopic is the MQTT topic, then after the "//" double back slash, there are the Json fiels to look for.
			# Json fields are separated by "/"
			stinglist=fulltopic.split("//")
			subtopic=stinglist[0]
			client["subtopic"]=subtopic
			if len(stinglist)>1:
				jsonlist=stinglist[1].split("/")
			client["jsonlist"]=jsonlist			
			# subscribe topic for IP stats
			stattopic = subtopic.replace("tele", "stat")
			stattopicstatus5=stattopic.replace("SENSOR", "STATUS5")
			client["subtopicstat5"]=stattopicstatus5

			
		# subscribe topic for IP stats command
		cmdtopicstat5=client["subtopicstat5"].replace("stat", "cmnd")
		cmdtopicstat5=cmdtopicstat5.replace("STATUS5", "STATUS")
		client["cmdtopicstat5"]=cmdtopicstat5
			
		MQTTcontrol.CLIENTSLIST[items]=client
		
		
		
	print(MQTTcontrol.CLIENTSLIST)
	MQTTcontrol.Create_connections_and_subscribe()

	return True

def SendSTATcmdtoall():
	MQTTcontrol.MQTT_output_all_stats()
	return True
		
def getSTATfromall():
	return MQTTcontrol.MQTT_get_all_stats()	



def setallGPIOinputs():	# this function sets all GPIO to input, actually it disable I2C and SPI as this functions are set using the PIN special mode Alt0
	for pinstr in HWcontrol.RPIMODBGPIOPINLIST:
		HWcontrol.GPIO_setup(pinstr, "in")
	return True
	
def checkGPIOconsistency():	
	# chek PIN in input and output cannot be the same
	inputpinlist=[]
	outputpinlist=[]	
	for ln in IOdata:
		if (HW_INFO_IOTYPE in ln) and (HW_CTRL_PIN in ln):
			iotype=ln[HW_INFO_IOTYPE]
			PIN=ln[HW_CTRL_PIN]
			if (iotype=="input"):
				if PIN in inputpinlist:
					print("Warning input PIN duplicated", PIN)
					logger.warning('Warning, input PIN duplicated PIN=%s', PIN)					
				inputpinlist.append(PIN)
			if (iotype=="output"):
				if (PIN in outputpinlist)and(PIN in HWcontrol.RPIMODBGPIOPINLIST):
					print("Warning output PIN duplicated", PIN)
					logger.warning('Warning, output PIN duplicated PIN=%s', PIN)
				else:
					outputpinlist.append(PIN)
				if (HW_CTRL_PWRPIN in ln):
					PWRPIN=ln[HW_CTRL_PWRPIN]
					if (PWRPIN in outputpinlist)and(PWRPIN in HWcontrol.RPIMODBGPIOPINLIST):
						print("Warning output PWRPIN overlapping", PWRPIN)
						logger.warning('Warning, output PWRPIN overlapping PIN=%s', PWRPIN)
					else:
						outputpinlist.append(PWRPIN)
				if (HW_CTRL_PIN2 in ln):
					PIN2=ln[HW_CTRL_PIN2]
					if (PIN2 in outputpinlist)and(PIN2 in HWcontrol.RPIMODBGPIOPINLIST):
						print("Warning output PIN2 overlapping", PIN2)
						logger.warning('Warning, output PIN2 overlapping PIN=%s', PIN2)
					else:
						outputpinlist.append(PIN2)
				

		if (HW_CTRL_PWRPIN in ln):
			PWRPIN=ln[HW_CTRL_PWRPIN]
			outputpinlist.append(PWRPIN)
				
	#print inputpinlist
	#print outputpinlist
				
	for inputpin in inputpinlist:
		if inputpin in outputpinlist:
			if inputpin in HWcontrol.RPIMODBGPIOPINLIST:
				print("error output PIN and Input PIN are the same", inputpin)
				logger.error('Error, output PIN and Input PIN are the same PIN=%s', inputpin)

	return True

def setPinOutput(PIN,level):
	HWcontrol.GPIO_setup(PIN, "out")
	HWcontrol.GPIO_output(PIN, level)

def initallGPIOinput():
	for ln in IOdata:
		iotype=ln[HW_INFO_IOTYPE]
		
		# input: set gpio status
		if (iotype=="input") :
			if (ln[HW_CTRL_CMD]=="readinputpin"):
				PINstr=ln[HW_CTRL_PIN]
				print("set event for the PIN ", PINstr)		
				if not PINstr=="":	
					logic=ln[HW_CTRL_LOGIC]
					# set Sw pull up / down mode
					if logic=="pos":
						GPIO_setup(PINstr, "in", "pull_down")
					else:
						GPIO_setup(PINstr, "in" , "pull_up")


		
def initallGPIOoutput():	
	for ln in IOdata:
		iotype=ln[HW_INFO_IOTYPE]
		
		# output: set gpio status
		if (iotype=="output") :
			if (ln[HW_CTRL_CMD]=="pulse"):
				# safe code in case of non int input
				PIN=ln[HW_CTRL_PIN]
				HWcontrol.GPIO_setup(PIN, "out")
				if ln[HW_CTRL_LOGIC]=="pos":
					HWcontrol.GPIO_output(PIN, 0)
				else:
					HWcontrol.GPIO_output(PIN, 1)
			elif (ln[HW_CTRL_CMD]=="hbridge"):
				PIN1=ln[HW_CTRL_PIN]
				PIN2=ln[HW_CTRL_PIN2]
				HWcontrol.GPIO_setup(PIN1, "out")
				HWcontrol.GPIO_setup(PIN2, "out")
				if ln[HW_CTRL_LOGIC]=="pos":
					HWcontrol.GPIO_output(PIN1, 0)
					HWcontrol.GPIO_output(PIN2, 0)
				else:
					HWcontrol.GPIO_output(PIN1, 1)
					HWcontrol.GPIO_output(PIN2, 1)				
			
		# powerpin
		# check if there is an extension of the command after "/"
		cmd=ln[HW_CTRL_CMD]
		cmdlist=cmd.split("/")
		cmdext=""
		if len(cmdlist)>1:
			cmdext=cmdlist[1]
		
		if cmdext=="":
			if (HW_CTRL_PWRPIN in ln):
				PWRPIN=ln[HW_CTRL_PWRPIN] 
				HWcontrol.GPIO_setup(PWRPIN, "out")
				if (HW_CTRL_LOGIC in ln):
					if (ln[HW_CTRL_LOGIC]=="pos") or (ln[HW_CTRL_LOGIC]==""):
						HWcontrol.GPIO_output(PWRPIN, 0)
						#print "power PIN ", ln[HW_CTRL_PWRPIN] , " set to 0 " 
					else:
						HWcontrol.GPIO_output(PWRPIN, 1)
						#print "power PIN ", ln[HW_CTRL_PWRPIN] , " set to 1 " 					
				else:			
					HWcontrol.GPIO_output(PWRPIN, 0) # assume logic is positive
					print("power PIN ", ln[HW_CTRL_PWRPIN] , " set to 0, No logic information available ") 	

			# Input: enable one wire
			if (iotype=="input") :
				if (ln[HW_CTRL_CMD]=="DS18B20"):
					# safe code in case of non int input
					PIN=ln[HW_CTRL_PIN]
					logic=ln[HW_CTRL_LOGIC]
					Set_1wire_Pin(PIN,logic)


	#print HWcontrol.GPIO_data
	return True



def initallGPIOoutputEXP():	
	for ln in IOdata:
		time.sleep(0.02)
		iotype=ln[HW_INFO_IOTYPE]
		address=""
		if HW_CTRL_ADDR in ln:
			address=ln[HW_CTRL_ADDR]
		if address=="":
			address="0x20"
		
		# output: set gpio status
		if (iotype=="output") :
			if (ln[HW_CTRL_CMD]=="pulse/I2CGPIOEXP"):
				# safe code in case of non int input
				PIN=ln[HW_CTRL_PIN]
				GPIOEXPI2Ccontrol.GPIO_setup(address, PIN, "out")
				if ln[HW_CTRL_LOGIC]=="pos":
					GPIOEXPI2Ccontrol.GPIO_output(address, PIN, 0)
				else:
					GPIOEXPI2Ccontrol.GPIO_output(address, PIN, 1)
			elif (ln[HW_CTRL_CMD]=="hbridge/I2CGPIOEXP"):
				PIN1=ln[HW_CTRL_PIN]
				PIN2=ln[HW_CTRL_PIN2]
				GPIOEXPI2Ccontrol.GPIO_setup(address, PIN1, "out")
				GPIOEXPI2Ccontrol.GPIO_setup(address, PIN2, "out")
				if ln[HW_CTRL_LOGIC]=="pos":
					GPIOEXPI2Ccontrol.GPIO_output(address, PIN1, 0)
					GPIOEXPI2Ccontrol.GPIO_output(address, PIN2, 0)
				else:
					GPIOEXPI2Ccontrol.GPIO_output(address, PIN1, 1)
					GPIOEXPI2Ccontrol.GPIO_output(address, PIN2, 1)				
			
		# powerpin		
		# check if there is an extension of the command after "/"
		cmd=ln[HW_CTRL_CMD]
		cmdlist=cmd.split("/")
		cmdext=""
		if len(cmdlist)>1:
			cmdext=cmdlist[1]
		
		if cmdext=="I2CGPIOEXP":
			if (HW_CTRL_PWRPIN in ln):
				PWRPIN=ln[HW_CTRL_PWRPIN] 
				GPIOEXPI2Ccontrol.GPIO_setup(address, PWRPIN, "out")
				if (HW_CTRL_LOGIC in ln):
					if (ln[HW_CTRL_LOGIC]=="pos") or (ln[HW_CTRL_LOGIC]==""):
						GPIOEXPI2Ccontrol.GPIO_output(address, PWRPIN, 0)
						#print "power PIN ", ln[HW_CTRL_PWRPIN] , " set to 0 " 
					else:
						GPIOEXPI2Ccontrol.GPIO_output(address, PWRPIN, 1)
						#print "power PIN ", ln[HW_CTRL_PWRPIN] , " set to 1 " 					
				else:			
					GPIOEXPI2Ccontrol.GPIO_output(address, PWRPIN, 0) # assume logic is positive
					print("power PIN ", ln[HW_CTRL_PWRPIN] , " set to 0, No logic information available ") 	


	return True






def Set_1wire_Pin(PIN,logic):
	#Newer kernels (4.9.28 and later) allow you to use dynamic overlay loading, 
	#including creating multiple 1-Wire busses to be used at the same time:

	#sudo dtoverlay w1-gpio gpiopin=4 pullup=0 pull-up does not seem to work
	
	try:
		# These tow lines mount the device, anyway seems not to be needed
		cmdstring="dtoverlay w1-gpio gpiopin="+PIN
		os.system(cmdstring)
		os.system('modprobe w1-gpio')
		os.system('modprobe w1-therm')
		if logic=="pos":
			HWcontrol.GPIO_setup(PIN, "in", "pull_up")
		else:
			HWcontrol.GPIO_setup(PIN, "in")
		
		# dtoverlay w1-gpio gpiopin=4 pullup=0		
		#cmd = ['dtoverlay', 'w1-gpio' , 'gpiopin='+ PIN, 'pullup=0']		
		#ifup_output = subprocess.check_output(cmd).decode('utf-8')
		return True
	except:
		print("Fail to set the One Wire driver")
		logger.error('Fail to set the One Wire driver')
		return False

def get_devices_list():
	outlist=[]
	devtype="One Wire"
	devicelist=HWcontrol.get_1wire_devices_list()
	
	for item in devicelist:
		outlist.append({"address":item , "type":devtype})
		
	devtype="I2C"
	devicelist=HWcontrol.get_I2C_devices_list()
	for item in devicelist:
		outlist.append({"address":item , "type":devtype})
		
	return outlist
		
def get_device_list_address_property():
	addresslist=get_devices_list()
	#print "before=",  addresslist
	for item in addresslist:
		if item["type"]=="I2C":
			recordkey=HW_CTRL_PIN
			recordvalue="I2C"
			recordkey1=HW_CTRL_ADDR
			recordvalue1=item["address"]
			keytosearch=HW_INFO_NAME
			namelist=searchdatalist2keys(recordkey,recordvalue,recordkey1,recordvalue1,keytosearch)
			item["message"]=""
			item["name"]=""
			item["cmd"]=""			
			if len(namelist)==1:
				# found only one item corresponding to the search
				item["name"]=namelist[0]
				# find the associated command
				recordkey=HW_INFO_NAME
				recordvalue=item["name"]				
				keytosearch=HW_CTRL_CMD
				item["cmd"]=searchdata(recordkey,recordvalue,keytosearch)								
			elif len(namelist)==0:
				item["message"]="Unknown"
			elif len(namelist)>1:
				item["message"]="Duplicated!!"


			# flag to enable the change address button
			# currently only one hardware support this option
			item["changeaddressflag"]=""
			if item["cmd"]=="Hygro24_I2C":
				item["changeaddressflag"]="1"
		else:
			item["message"]=""
			item["name"]=""
			item["cmd"]=""
			item["changeaddressflag"]=0
			
	print("after=",  addresslist)
	return addresslist



def GPIO_setup(PIN, state, pull_up_down):
	HWcontrol.GPIO_setup(PIN, state, pull_up_down)

def GPIO_add_event_detect(PIN, evenslopetype, eventcallback , bouncetimeINT=200):
	HWcontrol.GPIO_add_event_detect(PIN, evenslopetype, eventcallback , bouncetimeINT)

def GPIO_remove_event_detect(PIN):
	HWcontrol.GPIO_remove_event_detect(PIN)

def removeallinterruptevents():
	for channel in HWcontrol.RPIMODBGPIOPINLIST: 
		try:
			#print "try to remove event detect ", channel
			GPIO_remove_event_detect(channel)
		except:
			#print "Warning, not able to remove the event detect"
			a=1
		
	return ""


def removeinterruptevents():
	print("load interrupt list ")
	interruptlist=searchdatalist2keys(HW_INFO_IOTYPE,"input", HW_CTRL_CMD, "readinputpin" ,HW_INFO_NAME)
	print("len interrupt list "	, len(interruptlist))	
	for item in interruptlist:
		print("got into the loop ")
		# get PIN number

		recordkey=HW_INFO_NAME
		recordvalue=item	
		keytosearch=HW_CTRL_PIN
		PINstr=searchdata(recordkey,recordvalue,keytosearch)
		print("set event for the PIN ", PINstr)

		try:
			HWcontrol.GPIO_remove_event_detect(PINstr)
		except:
			print("Warning, not able to remove the event detect")
			logger.info('Warning, not able to remove the event detect')
		
	return ""





def restoredefault():
	filestoragemod.deletefile(HWDATAFILENAME)
	filestoragemod.readfiledata(DEFHWDATAFILENAME,IOdata)
	savecalibartion()
	
def savecalibartion():
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)

def changesavecalibartion(IOname,IOparameter,IOvalue):  #needed
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	for line in IOdata:
		if line[HW_INFO_NAME]==IOname:
			line[IOparameter]=IOvalue
			savecalibartion()
			return True
	return False

def changeIOdatatemp(IOname,IOparameter,IOvalue):  #needed
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	global IOdatatemp
	for line in IOdatatemp:
		if line[HW_INFO_NAME]==IOname:
			line[IOparameter]=IOvalue
			return True
	return False




def searchdata(recordkey,recordvalue,keytosearch):
	for ln in IOdata:
		if recordkey in ln:			
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					return ln[keytosearch]	
	return ""


def deepcopydict(dictin):
	return copy.deepcopy(dictin)

def searchrowtemp(recordkey,recordvalue):
	for ln in IOdatatemp:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				return copy.deepcopy(ln)
	return {}

def searchrowtempbyname(recordvalue):
	recordkey=HW_INFO_NAME
	return searchrowtemp(recordkey,recordvalue)


def AddUpdateRowByName(datarow):
	global IOdata
	recordkey=HW_INFO_NAME
	if recordkey in datarow:
		name=datarow[recordkey]
	else:
		return False
	
	# search row by name
	for ln in IOdata:
		if recordkey in ln:
			if ln[recordkey]==name:
				# found
				for key in datarow: #update all fileds present in the row
					ln[key]=datarow[key] 
				SaveData()
				return True	
	#add row to the bottom
	IOdata.append(datarow)
	SaveData()


def searchmatch(recordkey,recordvalue,temp):
	if temp:
		for ln in IOdatatemp:
			if recordkey in ln:
				if ln[recordkey]==recordvalue:
					return True	
		return False
	else:
		for ln in IOdata:
			if recordkey in ln:
				if ln[recordkey]==recordvalue:
					return True	
		return False


def searchmatchN(listkeyvalue,temp):
	# listkeyvalue is a list of dictionaries key , value
	if temp:
		reflist=IOdatatemp
	else:
		reflist=IOdata		
		
	for ln in reflist:
		alltrue=True
		for serachitem in listkeyvalue:
			recordkey=serachitem["key"]
			recordvalue=serachitem["value"]
			if recordkey in ln:
				if ln[recordkey]!=recordvalue:
					alltrue=False
					break
		if alltrue:
			return True
					
	return False


def gettimedata(name):
	# return list with three integer values: hour , minute, second
	timestr=searchdata(HW_INFO_NAME,name,HW_FUNC_TIME)
	return separatetimestringint(timestr)


def separatetimestringint(timestr): # given the string input "hh:mm:ss" output a list with  Hour, min, sec in integer format 
	outlist=[]
	timelist=timestr.split(":")
	for i in range(3):
		value=0		
		if i<len(timelist):
			if timelist[i]!="":
				value=toint(timelist[i],0)
		outlist.append(value)		
	# check the range of Minutes and Hours and seconds
	#Seconds:
	seconds=outlist[2]%60
	# // is the floor division operator
	minutes=(int(outlist[2]//60)+outlist[1])%60
	hours=(int(outlist[1]//60)+outlist[0])%24
	returnlist=[hours,minutes,seconds]
	#print " time string " , timestr , " time return list ", returnlist
	return returnlist

		
def tonumber(thestring, outwhenfail):
	try:
		n=float(thestring)
		return n
	except:
		return outwhenfail

def toint(thestring, outwhenfail):
	try:
		f=float(thestring)
		n=int(f)
		return n
	except:
		return outwhenfail


def searchdatalist(recordkey,recordvalue,keytosearch):
	datalist=[]
	for ln in IOdata:
		if recordkey in ln:
			if "*"==recordvalue[-1]:  # last character of the string is "*"
				pos=ln[recordkey].find(recordvalue[:-1])
				if pos==0:
					if keytosearch in ln:
						datalist.append(str(ln[keytosearch]))
				
			else:
				if ln[recordkey]==recordvalue:
					if keytosearch in ln:
						datalist.append(str(ln[keytosearch]))	
	return datalist


def searchdatalistinstr(recordkey,recordvalue,keytosearch):
	datalist=[]
	for ln in IOdata:
		if recordkey in ln:
			if recordvalue.upper() in ln[recordkey].upper():
				if keytosearch in ln:
					datalist.append(str(ln[keytosearch]))	
	return datalist


def searchdatalist2keys(recordkey,recordvalue,recordkey1,recordvalue1,keytosearch):
	datalist=[]
	for ln in IOdata:
		if (recordkey in ln)and(recordkey1 in ln):
			if (ln[recordkey]==recordvalue)and(ln[recordkey1]==recordvalue1):
				if keytosearch in ln:
					datalist.append(str(ln[keytosearch]))	
	return datalist


def getItemlist(fielditem):
	valuelist=[]
	for line in IOdata:
		if fielditem in line:
			valuelist.append(line[fielditem])
	return valuelist


def getfieldvaluelist(fielditem,valuelist):
	del valuelist[:]
	for line in IOdata:
		valuelist.append(line[fielditem])

def getfieldvaluelisttemp(fielditem,valuelist):
	del valuelist[:]
	for line in IOdatatemp:
		valuelist.append(line[fielditem])


def getfieldinstringvalue(fielditem,stringtofind,valuelist):
	del valuelist[:]
	for line in IOdata:
		name=line[fielditem]
		if name.find(stringtofind)>-1:
			valuelist.append(name)

def photolist(apprunningpath, withindays=0):

	folderpath=os.path.join(apprunningpath, "static")
	folderpath=os.path.join(folderpath, "hydropicture")
	# control if the folder hydropicture exist otherwise create it
	if not os.path.exists(folderpath):
		os.makedirs(folderpath)
		print("Hydropicture folder has been created")
	
	filenamelist=[]
	sortedlist=sorted([f for f in os.listdir(folderpath) if os.path.isfile(os.path.join(folderpath, f))])
	sortedlist.reverse()
	for files in sortedlist:
		if (files.endswith(".jpg") or files.endswith(".png")):
			isok=False
			if "@" in files:
				datestr=files.split("@")[0]
			else:
				datestr=files.split(".")[0]
			try:
				dateref=datetime.strptime(datestr,'%y-%m-%d,%H:%M')
				# here check how long time ago the picture was taken
				# if withindays==0 then is not applicable
				if withindays>0:
					todaydate=datetime.now()
					tdelta=timedelta(days=withindays)
					startdate=todaydate-tdelta
					print(" startdate " ,startdate)
					if dateref>=startdate:
						isok=True
				else:
					isok=True
			except:
				print("file name format not compatible with date")
				
			if isok:
				templist=[]
				templist.append("hydropicture/"+files)
				templist.append("Image taken on "+datestr)
				templist.append(dateref)
				templist.append("hydropicture/thumb/"+files)		
				filenamelist.append(templist)						
			
	return filenamelist # item1 (path+filename) item2 (name for title) item3 (datetime) item4 (thumbpath + filename)

def loglist(apprunningpath,logfolder,searchstring):
	templist=[]	
	folderpath=os.path.join(apprunningpath,logfolder)
	# control if the folder  exist otherwise exit
	if not os.path.exists(folderpath):
		print("log folder does not exist")
		return templist
	filenamelist=[]
	sortedlist=sorted(os.listdir(folderpath))
	sortedlist.reverse()
	for files in sortedlist:
		if (searchstring in files):
			templist.append(files)
	return templist 

def deleteallpictures(apprunningpath):
	#delete pictures
	folderpath=os.path.join(apprunningpath, "static")
	folderpath=os.path.join(folderpath, "hydropicture")	
	sortedlist=os.listdir(folderpath)
	i=0
	for files in sortedlist:
		if os.path.isfile(os.path.join(folderpath, files)):
			os.remove(os.path.join(folderpath, files))
			i=i+1
	#delete thumb 
	paththumb=os.path.join(folderpath,"thumb")
	sortedlist=os.listdir(paththumb)
	i=0
	for files in sortedlist:
		if os.path.isfile(os.path.join(paththumb, files)):
			os.remove(os.path.join(paththumb, files))
			i=i+1
	return i

def HWpresetlist(apprunningpath):
	folderpath=os.path.join(apprunningpath, "database")
	folderpath=os.path.join(folderpath, "default")
	folderpath=os.path.join(folderpath, "presetHWsetting")
	filenamelist=[]
	sortedlist=sorted(os.listdir(folderpath))
	sortedlist.reverse()
	for files in sortedlist:
		if files.startswith("defhwdata"):
			templist=[]
			templist.append("database/default/presetHWsetting/"+files)			
			templist.append(files)
			filenamelist.append(templist)
	return filenamelist # item1 (path) item2 (name)


def removephotodataperiod(removebeforedays, maxphototoremove=20):
	todaydate=datetime.now()
	num = removebeforedays
	tdelta=timedelta(days=num)
	enddate=todaydate-tdelta
	pastdays=364 # number of days between beforeremovedays and start to search
	num = pastdays
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta
	print(" startdate " ,startdate)
	print(" enddate ", enddate)
	
	photodata=photolist(get_path())
	i=0
	for photo in photodata:
		dateref=photo[2]
		if isinstance(dateref, datetime):
			print(dateref)
			if (dateref>=startdate)and(dateref<=enddate)and(i<maxphototoremove):
				try:
					filepath=os.path.join(get_path(), "static")
					filepath=os.path.join(filepath, photo[0])
					# remove photo
					filestoragemod.deletefile(filepath)
					print("removed Photo " , filepath)
					i=i+1
				except ValueError:
					print("Error in photo delete ")
		else:
			print("datetime format incorrect")
	thumbconsistency(get_path())
	
def videodevlist():
	return photomod.videodevlist()
	
def  thumbconsistency(apprunningpath):
	return photomod.thumbconsistency(apprunningpath)

def shotit(video,istest,resolution,positionvalue,vdirection):
	shottaken=False
    # send command to the actuator for test
	if istest:
		filepath=os.path.join(get_path(), "static")
		filepath=os.path.join(filepath, "cameratest")
		filedelete=os.path.join(filepath, "testimage.png")
		filestoragemod.deletefile(filedelete)		
		shottaken=photomod.saveshot(filepath,video,False,resolution,positionvalue,vdirection)       
	else:
		filepath=os.path.join(get_path(), "static")
		filepath=os.path.join(filepath, "hydropicture")
		shottaken=photomod.saveshot(filepath,video,True,resolution,positionvalue,vdirection)			
	if shottaken:
		ret_data = {"answer": "photo taken"}
	else:
		ret_data = {"answer": "Camera not detected"}	
	print("The photo ", ret_data)
	return shottaken , ret_data


			
def takephoto(Activateanyway=False):
	isok=False
	count=0
	print("take photo", " " , datetime.now())
	videolist=videodevlist()
	for video in videolist:
		isok=False
		if cameradbmod.isCameraActive(video)or(Activateanyway):
			videolist=[video]
			camdata=cameradbmod.getcameradata(videolist)# if not found return default parameters
			resolution=camdata[0]["resolution"] 
			position=camdata[0]["position"]
			servo=camdata[0]["servo"]
			vdirection=camdata[0]["vflip"]
			print("Camera: ", video , " Resolution ", resolution , " Position " , position , " Vertical direction " , vdirection) 
			logger.info("Camera: %s Resolution %s Position %s Vertical direction %s " , video , resolution , position , vdirection)
			positionlist=position.split(",")
			if (positionlist)and(servo!="none"):
				for positionvalue in positionlist:
					# move servo first
					servoangle(servo,positionvalue,2)
					isok , ret_data=shotit(video,False,resolution,positionvalue,vdirection)

			else:
				isok , ret_data=shotit(video,False,resolution,"0",vdirection)			

			logger.info(ret_data["answer"])
		else:
			logger.info("Camera: %s not activated " , video)
			
		if isok:
			count = count +1
	if count > 0:
		isok=True
	return isok	

		


def get_path():
    '''Get the path to this script no matter how it's run.'''
    #Determine if the application is a py/pyw or a frozen exe.
    if hasattr(sys, 'frozen'):
        # If run from exe
        dir_path = os.path.dirname(sys.executable)
    elif '__file__' in locals():
        # If run from py
        dir_path = os.path.dirname(__file__)
    else:
        # If run from command line
        dir_path = sys.path[0]
    return dir_path
	


def get_image_size(picturepath):
	filepath=os.path.join(get_path(), "static")
	fname=os.path.join(filepath, picturepath)
	'''Determine the image type of fhandle and return its size.
	from draco'''
	with open(fname, 'rb') as fhandle:
		head = fhandle.read(24)
		if len(head) != 24:
			return 0,0
		if imghdr.what(fname) == 'png':
			check = struct.unpack('>i', head[4:8])[0]
			if check != 0x0d0a1a0a:
				return 0,0
			width, height = struct.unpack('>ii', head[16:24])
		elif imghdr.what(fname) == 'gif':
			width, height = struct.unpack('<HH', head[6:10])
		elif imghdr.what(fname) == 'jpeg':
			try:
				fhandle.seek(0) # Read 0xff next
				size = 2
				ftype = 0
				while not 0xc0 <= ftype <= 0xcf:
					fhandle.seek(size, 1)
					byte = fhandle.read(1)
					while ord(byte) == 0xff:
						byte = fhandle.read(1)
					ftype = ord(byte)
					size = struct.unpack('>H', fhandle.read(2))[0] - 2
				# We are at a SOFn block
				fhandle.seek(1, 1)  # Skip `precision' byte.
				height, width = struct.unpack('>HH', fhandle.read(4))
			except Exception: #IGNORE:W0703
				return 0,0
		else:
			return 0,0
		return width, height
		
def additionalRowInit():
	#initialize IOdatarow	
	global IOdatarow	
	IOdatarow=InitRowHWsetting()
	return True
	
def InitRowHWsetting():
	fields=HWdataKEYWORDS
	tablehead=[]
	for key, value in fields.items():
		tablehead.append(key)
	datarow={}
	for th in tablehead:
		if len(fields[th])>1:
			datarow[th]=fields[th][0]
		else:
			datarow[th]=""
	return datarow
	

def addrow(dictrow, temp=True):
	dicttemp=copy.deepcopy(dictrow)
	global IOdata
	global IOdatatemp
	if temp:
		IOdatatemp.append(dicttemp)
		return True
	else:
		IOdata.append(dicttemp)
		filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
		return True
	
def deleterow(element, temp=True):
	global IOdata
	global IOdatatemp
	searchfield=HW_INFO_NAME
	searchvalue=element
	if temp:
		for line in IOdatatemp:
			if searchfield in line:
				if line[searchfield]==searchvalue:
					IOdatatemp.remove(line)
					return True
		return False
	else:	
		for line in IOdata:
			if searchfield in line:
				if line[searchfield]==searchvalue:
					IOdata.remove(line)
					filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
					return True
		return False



def blink(PINstr, wait, numtimes):
	HWcontrol.GPIO_setup(PINstr, "out")
	for i in range(0,numtimes):
		level=1
		HWcontrol.GPIO_output(PINstr, level)
		time.sleep(wait)
		level=0
		HWcontrol.GPIO_output(PINstr, level)	
		time.sleep(wait)
	




	
if __name__ == '__main__':
	# comment
	a=10
	
