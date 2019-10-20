# -*- coding: utf-8 -*-


#to kill python processes use  -- pkill python
import time
import datetime
import threading
from math import sqrt
#import sys,os
#import serial
import logging

logger = logging.getLogger("hydrosys4."+__name__)



global ISRPI

try:
	__import__("smbus")
except ImportError:
	ISRPI=False
else:
	import Adafruit_DHT #humidity temperature sensor
	import Adafruit_BMP.BMP085 as BMP085 #pressure sensor
	#from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor
	from stepperDOUBLEmod import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor
	import spidev
	import smbus
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM) 
	ISRPI=True


HWCONTROLLIST=["tempsensor","humidsensor","pressuresensor","analogdigital","lightsensor","pulse","pinstate","servo","stepper","stepperstatus","photo","mail+info+link","mail+info","returnzero","stoppulse","readinputpin"]
RPIMODBGPIOPINLIST=["2", "3", "4","5","6", "7", "8", "9", "10", "11", "12","13","14", "15", "16","17", "18", "19", "20","21","22", "23", "24", "25","26", "27"]
NALIST=["N/A"]
GPIOPLUSLIST=["I2C", "SPI"]
RPIMODBGPIOPINLISTNA=RPIMODBGPIOPINLIST+NALIST
RPIMODBGPIOPINLISTPLUS=RPIMODBGPIOPINLISTNA+GPIOPLUSLIST

ADCCHANNELLIST=["0","1","2","3","4","5","6","7", "N/A"] #MCP3008 chip has 8 input channels

# status variables
DHT22_data={}
DHT22_data["default"]={'temperature':None,'humidity':None,'lastupdate':datetime.datetime.utcnow() - datetime.timedelta(seconds=2)}

stepper_data={}
stepper_data["default"]={'busyflag':False}

GPIO_data={}
GPIO_data["default"]={"level":None, "state":None, "threadID":None}

PowerPIN_Status={}
PowerPIN_Status["default"]={"level":0, "state":"off", "pinstate":None}


#" GPIO_data is an array of dictionary, total 40 items in the array
#GPIO_data=[{"level":None, "state":None, "threadID":None} for k in range(40)]
#" PowerPIN_Status is an array of dictionary, total 40 items in the array, the array is used to avoid comflict between tasks using same PIN 
# each time the pin is activated the level is increased by 1 unit.
#PowerPIN_Status=[{"level":0, "state":"off", "pinstate":None} for k in range(40)]

MCP3008_busy_flag=False


def toint(thestring, outwhenfail):
	try:
		f=float(thestring)
		n=int(f)
		return n
	except:
		return outwhenfail

def read_status_data(data,element,variable):
	print data
	if element in data:
		print " element present"
		elementdata=data[element]
		if variable in elementdata:
			return elementdata[variable]
		else:
			# variable not in elementdata
			return ""
	else:
		print " element NOT present"
		# element not present in the data use the default
		data[element]=data["default"].copy()
		elementdata=data[element]
		print data
		if variable in elementdata:
			return elementdata[variable]
		else:
			# variable not in elementdata
			return ""

def read_status_dict(data,element):
	print data
	if element in data:
		print " element present"
		elementdata=data[element]
		return elementdata
	else:
		print " element NOT present"
		return {}

def write_status_data(data,element,variable,value):
	if element in data:
		data[element][variable]=value
	else:
		data[element]=data["default"].copy()
		data[element][variable]=value

def execute_task(cmd, message, recdata):
	global DHT22_data
	global Servo_data
	global stepper_data
	
	
	if cmd==HWCONTROLLIST[0]:
		return get_DHT22_temperature(cmd, message, recdata , DHT22_data)
		
	elif cmd==HWCONTROLLIST[1]:
		return get_DHT22_humidity(cmd, message, recdata , DHT22_data)

	elif cmd==HWCONTROLLIST[2]:
		return get_BMP180_pressure(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[3]:
		retok=get_MCP3008_channel(cmd, message, recdata)
		return retok

	elif cmd==HWCONTROLLIST[4]:	
		return get_BH1750_light(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[5]:	# pulse
		return gpio_pulse(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[6]:	
		return gpio_pin_level(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[7]:	# servo
		return gpio_set_servo(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[8]: #stepper	
		return gpio_set_stepper(cmd, message, recdata, stepper_data)

	elif cmd==HWCONTROLLIST[9]: #stepper status	
		return get_stepper_status(cmd, message, recdata, stepper_data)

	elif cmd==HWCONTROLLIST[13]: #return zero	
		print "returnzero"
		returndata="0"
		recdata.append(cmd)
		recdata.append(returndata)
		recdata.append(1) # confirm data for acknowledge
		return True

	elif cmd==HWCONTROLLIST[14]:	# stoppulse
		return gpio_stoppulse(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[15]:	# readinputpin
		return read_input_pin(cmd, message, recdata)


	else:
		print "Command not found"
		recdata.append(cmd)
		recdata.append("e")
		recdata.append(0)
		return False;
	return False;


def execute_task_fake(cmd, message, recdata):
	
	if cmd==HWCONTROLLIST[0]:
		get_DHT22_temperature_fake(cmd, message, recdata, DHT22_data)
		return True;
	
	elif cmd==HWCONTROLLIST[5]:	
		gpio_pulse(cmd, message, recdata)
		return True;

	elif cmd==HWCONTROLLIST[6]:	
		gpio_pin_level(cmd, message, recdata)
		return True;

	elif cmd==HWCONTROLLIST[14]:	
		gpio_stoppulse(cmd, message, recdata)
		return True;
		
	else:
		print "no fake command available" , cmd
		recdata.append(cmd)
		recdata.append("e")
		recdata.append(0)
		return False;
		
	return True



def get_DHT22_temperature_fake(cmd, message, recdata, DHT22_data):

	recdata.append(cmd)
	recdata.append("10.10")
	recdata.append(1)
	return True
	

def get_DHT22_reading(cmd, message, recdata, DHT22_data):	
	
	successflag=0
	msgarray=message.split(":")
	pin=int(msgarray[1])
	element=msgarray[1]
	TemperatureUnit="C"
	if len(msgarray)>4:
		TemperatureUnit=msgarray[4]
		
	lastupdate=read_status_data(DHT22_data,element,'lastupdate')	
	deltat=datetime.datetime.utcnow()-lastupdate
	
	if deltat.total_seconds()<0:
		logger.warning("last reading DHT sensor was in the past? maybe due to time change, go to reset lastupdate time")
		lastupdate=datetime.datetime.utcnow() - datetime.timedelta(seconds=3)
		DHT22_data[element]['lastupdate']=lastupdate	
		deltat=datetime.datetime.utcnow()-lastupdate

	if deltat.total_seconds()>3:
		
		humidity=None
		temperature=None
		
		readingattempt=3
		inde=0
		while (inde<readingattempt) and (successflag==0):
			inde=inde+1
			try:
				sensor = Adafruit_DHT.DHT22
				humidity, temperature = Adafruit_DHT.read(sensor, pin)
				if (TemperatureUnit=="F") and (temperature is not None):
					temperature=temperature*1.8+32

			except:
				print "error reading the DHT sensor (Humidity,Temperature)"
				logger.error("error reading the DHT sensor (Humidity,Temperature)")
				
			# if reading OK, update status variable
			if (humidity is not None) and (temperature is not None):
				# further checks
				if (humidity>=0)and(humidity<=100)and(temperature>-20)and(temperature<200):
					print 'Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity)
					DHT22_data[element]['humidity']=('{:3.2f}'.format(humidity / 1.))
					DHT22_data[element]['temperature']=('{:3.2f}'.format(temperature / 1.))
					DHT22_data[element]['lastupdate']=datetime.datetime.utcnow()
					successflag=1
				else:
					print 'Failed to get DHT22 reading'	
					logger.error("Failed to get DHT22 reading, values in wrong range")					
			else:
				print 'Failed to get DHT22 reading'	
				logger.error("Failed to get DHT22 reading")
			time.sleep(1)
		
		# data in status variable will not be used in case of failure reading, only in case of reading request less than 10sec
	else:
		# use the data in memory, reading less than 10 sec ago
		temperature=read_status_data(DHT22_data,element,'temperature')
		humidity=read_status_data(DHT22_data,element,'humidity')
		if (humidity is not None) and (temperature is not None):		
			successflag=1
	
	return successflag, element

		
def get_DHT22_temperature(cmd, message, recdata, DHT22_data):

	successflag , element=get_DHT22_reading(cmd, message, recdata, DHT22_data)
	recdata.append(cmd)
	recdata.append(DHT22_data[element]['temperature'])
	recdata.append(successflag)	
	return DHT22_data[element]['lastupdate']
	

def get_DHT22_humidity(cmd, message, recdata, DHT22_data):

	successflag , element=get_DHT22_reading(cmd, message, recdata, DHT22_data)		
	recdata.append(cmd)
	recdata.append(DHT22_data[element]['humidity'])
	recdata.append(successflag)	
	return DHT22_data[element]['lastupdate']


def get_BMP180_pressure(cmd, message, recdata):
	successflag=0
	Pressure=0
	try:
		sensor = BMP085.BMP085(3) # 3 = High resolution mode
		Pressure = '{0:0.2f}'.format(sensor.read_pressure()/float(100))
		successflag=1
	except:
		print " I2C bus reading error, BMP180 , pressure sensor "
	#pressure is in hecto Pascal
	recdata.append(cmd)
	recdata.append(Pressure)
	recdata.append(successflag)	
	return True
	
	
def get_BH1750_light(cmd, message, recdata):
	successflag=0
	
	DEVICE     = 0x23 # Default device I2C address
	POWER_DOWN = 0x00 # No active state
	POWER_ON   = 0x01 # Power on
	RESET      = 0x07 # Reset data register value
	# Start measurement at 4lx resolution. Time typically 16ms.
	CONTINUOUS_LOW_RES_MODE = 0x13
	# Start measurement at 1lx resolution. Time typically 120ms
	CONTINUOUS_HIGH_RES_MODE_1 = 0x10
	# Start measurement at 0.5lx resolution. Time typically 120ms
	CONTINUOUS_HIGH_RES_MODE_2 = 0x11
	# Start measurement at 1lx resolution. Time typically 120ms
	# Device is automatically set to Power Down after measurement.
	ONE_TIME_HIGH_RES_MODE_1 = 0x20
	# Start measurement at 0.5lx resolution. Time typically 120ms
	# Device is automatically set to Power Down after measurement.
	ONE_TIME_HIGH_RES_MODE_2 = 0x21
	# Start measurement at 1lx resolution. Time typically 120ms
	# Device is automatically set to Power Down after measurement.
	ONE_TIME_LOW_RES_MODE = 0x23

	bus = smbus.SMBus(1)  # Rev 2 Pi uses 1
	light=0
	try:
		data = bus.read_i2c_block_data(DEVICE,ONE_TIME_HIGH_RES_MODE_1)
		light = '{0:0.2f}'.format(((data[1] + (256 * data[0])) / 1.2))
		successflag=1  
	except:
		print " I2C bus reading error, BH1750 , light sensor "
	
	recdata.append(cmd)
	recdata.append(light)
	recdata.append(successflag)	
	return True
	
	
def get_MCP3008_channel(cmd, message, recdata):
	
	successflag=0
	volts=0
	
	
	msgarray=message.split(":")
	
	messagelen=len(msgarray)
	
	#PIN=msgarray[1]

	SUBPIN=int(msgarray[2])
	channel=SUBPIN	
	
	POWERPIN=""
	if messagelen>3:	
		POWERPIN=msgarray[3]
	
	logic="pos"
	if messagelen>5:
		logic=msgarray[5]
	
	
	
	global MCP3008_busy_flag
	waitstep=0.1
	waittime=0
	maxwait=2.5
	while (MCP3008_busy_flag==True)and(waittime<maxwait):
		time.sleep(waitstep)
		waittime=waittime+waitstep
	
	print "MCP3008 wait time -----> ", waittime
		
	if (waittime>=maxwait):
		#something wrog, wait too long, avoid initiate further processing
		print "MCP3008 wait time EXCEEDED "
		logger.warning("Wait Time exceeded, not able to read ADCdata Channel: %d", channel)
		return False

	MCP3008_busy_flag=True		

	
	powerPIN_start(POWERPIN,logic,0.2)

	refvoltage=5.0
	
	try:
		# Open SPI bus

		spi_speed = 1000000 # 1 MHz
		spi = spidev.SpiDev()
		spi.open(0,0)
		spi.max_speed_hz=spi_speed

		# Function to read SPI data from MCP3008 chip
		# Channel must be an integer 0-7
		datatext=""	
		inde =0
		dataarray=[]
		
		print "Starting sample reading"
		
		samplesnumber=39
		for x in range(0, samplesnumber): #number of samples
			
			# read data from selected channel
			adc = spi.xfer2([1,(8+channel)<<4,0])
			data = ((adc[1]&3) << 8) + adc[2]
			
			dataarray.append(data)
			inde=inde+1
			datatext=datatext+str(data)+","			
			print "MCP3008 channel ", channel, " data:",data
						
		logger.info("ADCdata Channel: %d", channel)
		logger.info("ADCdata Sampling: %s", datatext)
		dataaverage, mean = normalize_average(dataarray)
		
		# Function to convert data to voltage level,
		# rounded to specified number of decimal places.
		voltsraw = (mean * refvoltage) / float(1023)
		voltsnorm = (dataaverage * refvoltage) / float(1023)
		volts = round(voltsnorm,2)	
	
		print "MCP3008 chennel ", channel, " Average (volts): ",voltsraw , " Average Norm (v): ", voltsnorm
		
		spi.close()
		successflag=1
	except:
		print " I2C bus reading error, MCP3008 , AnalogDigitalConverter  "
	
	recdata.append(cmd)
	recdata.append(volts)
	recdata.append(successflag)


	powerPIN_stop(POWERPIN,0)
	
	time.sleep(1.3) # wait after the power pin has been set to LOW
	
	MCP3008_busy_flag=False

	return True	


def normalize_average(lst):
	"""Calculates the standard deviation for a list of numbers."""
	num_items = len(lst)
	mean = sum(lst) / float(num_items)
	differences = [x - mean for x in lst]
	sq_differences = [d ** 2 for d in differences]
	ssd = sum(sq_differences)
	variance = ssd / float(num_items)
	sd = sqrt(variance)
	 
	# use functions to adjust data, keep only the data inside the standard deviation

	final_list = [x for x in lst if ((x >= mean - sd) and (x <= mean + sd))]
	num_items_final = len(final_list)
	normmean=sum(final_list) / float(num_items_final)
	
	print "discarded ", num_items-num_items_final , " mean difefrence ", normmean-mean

	return normmean, mean



def powerPIN_start(POWERPIN,logic,waittime):
	if POWERPIN!="":
		PowerPINlevel=read_status_data(PowerPIN_Status,POWERPIN,"level")
		write_status_data(PowerPIN_Status,POWERPIN,"level",PowerPINlevel+1)
		#PowerPIN_Status[POWERPIN]["level"]+=1
		#start power pin
		PowerPINstate=read_status_data(PowerPIN_Status,POWERPIN,"state")
		if PowerPINstate=="off":
			GPIO_setup(POWERPIN, "out")
			if logic=="pos": 
				GPIO_output(POWERPIN, 1)
				write_status_data(PowerPIN_Status,POWERPIN,"pinstate","1")
				#PowerPIN_Status[POWERPIN]["pinstate"]="1"
			else:
				GPIO_output(POWERPIN, 0)
				write_status_data(PowerPIN_Status,POWERPIN,"pinstate","0")
				#PowerPIN_Status[POWERPIN]["pinstate"]="0"
				
			write_status_data(PowerPIN_Status,POWERPIN,"state","on")	
			#PowerPIN_Status[POWERPIN]["state"]="on"
			print "PowerPin activated ", POWERPIN
			time.sleep(waittime)
	return True	

		
def powerPIN_stop(POWERPIN,waittime):
	if POWERPIN!="":
		#set powerpin to zero again in case this is the last thread
		PowerPINlevel=read_status_data(PowerPIN_Status,POWERPIN,"level")
		write_status_data(PowerPIN_Status,POWERPIN,"level",PowerPINlevel-1)
		#PowerPIN_Status[POWERPIN]["level"]-=1		
		#stop power pin	
		if (PowerPINlevel-1)<=0:
			PowerPINstate=read_status_data(PowerPIN_Status,POWERPIN,"state")
			if PowerPINstate=="on":
				time.sleep(waittime)
				PowerPINpinstate=read_status_data(PowerPIN_Status,POWERPIN,"pinstate")
				if PowerPINpinstate=="1": 
					GPIO_output(POWERPIN, 0)
					write_status_data(PowerPIN_Status,POWERPIN,"pinstate","0")
					#PowerPIN_Status[POWERPIN]["pinstate"]="0"
				elif PowerPINpinstate=="0":
					GPIO_output(POWERPIN, 1)
					write_status_data(PowerPIN_Status,POWERPIN,"pinstate","1")
					#PowerPIN_Status[POWERPIN]["pinstate"]="1"
				write_status_data(PowerPIN_Status,POWERPIN,"state","off")
				#PowerPIN_Status[POWERPIN]["state"]="off"

	return True	


def CheckRealHWpin(PIN=""):
	if ISRPI:
		if PIN in RPIMODBGPIOPINLIST:
			try:
				PINint=int(PIN)
				return True, PINint
				print "Real * PIN *"
			except:
				return False, 0	
	return False, 0		


def GPIO_output(PINstr, level):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		GPIO.output(PIN, level)
	#GPIO_data[PIN]["level"]=level
	write_status_data(GPIO_data,PINstr,"level",level)
	return True
		



def GPIO_setup(PINstr, state, pull_up_down=""):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		if state=="out":
			GPIO.setup(PIN,  GPIO.OUT)
		else:
			if pull_up_down=="pull_down":
				GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
			elif pull_up_down=="pull_up":
				GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
			else:
				GPIO.setup(PIN,  GPIO.IN)
	
	#GPIO_data[PIN]["state"]=state
	write_status_data(GPIO_data,PINstr,"state",state)
	return True



def GPIO_add_event_detect(PINstr, evenslopetype, eventcallback):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		print "add event ", PIN
		GPIO.add_event_detect(PIN, GPIO.BOTH, callback=eventcallback, bouncetime=200)


def GPIO_remove_event_detect(PINstr):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		GPIO.remove_event_detect(PIN)




def endpulse(PINstr,logic,POWERPIN):
	#GPIO_data[PIN]["threadID"]=None
	write_status_data(GPIO_data,PINstr,"threadID",None)
	if logic=="pos":
		level=0
	else:
		level=1
		
	GPIO_output(PINstr, level)
	
	powerPIN_stop(POWERPIN,0)

	print "pulse ended", time.ctime() , " PIN=", PINstr , " Logic=", logic , " Level=", level
	return True


def gpio_pulse(cmd, message, recdata):
	successflag=0
	msgarray=message.split(":")
	messagelen=len(msgarray)	
	PIN=msgarray[1]

	testpulsetime=msgarray[2]
	pulsesecond=int(testpulsetime)
	if messagelen>3:
		if msgarray[3]=="0":
			logic="neg"
		elif msgarray[3]=="1":
			logic="pos"	
	
	POWERPIN=""	
	if messagelen>4:	
		POWERPIN=msgarray[4]	

	

	# in case another timer is active on this PIN, cancel it 
	PINthreadID=read_status_data(GPIO_data,PIN,"threadID")
	if not PINthreadID==None:
		print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
	
	else:
		powerPIN_start(POWERPIN,logic,0.2) # it is assumed that the logic (pos,neg) of the powerpin is the same of the pin to pulse, in the future it might be useful to specify the powerpin logic separately
		GPIO_setup(PIN, "out")
		if logic=="pos":
			level=1
		else:
			level=0
		GPIO_output(PIN, level)

	NewPINthreadID=threading.Timer(pulsesecond, endpulse, [PIN , logic , POWERPIN])
	NewPINthreadID.start()
	write_status_data(GPIO_data,PIN,"threadID",NewPINthreadID)

	print "pulse started", time.ctime() , " PIN=", PIN , " Logic=", logic 
	successflag=1
	recdata.append(cmd)
	recdata.append(PIN)
	recdata.append(successflag)
	return True	

def gpio_stoppulse(cmd, message, recdata):
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN=msgarray[1]
	
	if messagelen>3:
		if msgarray[3]=="0":
			logic="neg"
		elif msgarray[3]=="1":
			logic="pos"	
	
	POWERPIN=""
	if messagelen>4:	
		POWERPIN=msgarray[4]	
	
	PINthreadID=read_status_data(GPIO_data,PIN,"threadID")
	if not PINthreadID==None:
		print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
		
	endpulse(PIN,logic,POWERPIN)	#this also put powerpin off		
	recdata.append(cmd)
	recdata.append(PIN)
	return True	


def gpio_pin_level(cmd, message, recdata):
	msgarray=message.split(":")
	PIN=msgarray[1]
	recdata.append(msgarray[0])
	PINlevel=read_status_data(GPIO_data,PIN,"level")
	if PINlevel is not None:
		recdata.append(str(PINlevel))
		return True
	else:
		recdata.append("e")
		return False	

def read_input_pin(cmd, message, recdata):
	successflag=1
	msgarray=message.split(":")
	print " read pin input ", message
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



def gpio_set_servo(cmd, message, recdata):
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN=int(msgarray[1])
	frequency=int(msgarray[2])
	duty=float(msgarray[3])
	delay=float(msgarray[4])
	previousduty=float(msgarray[5])
	stepnumber=int(msgarray[6])
	
	step=(duty-previousduty)/stepnumber
	
	
	GPIO_setup(str(PIN), "out")
	pwm = GPIO.PWM(PIN, frequency) # set the frequency
	pwm.start(previousduty)
	for inde in range(stepnumber):
		currentduty=previousduty+(inde+1)*step
		pwm.ChangeDutyCycle(currentduty)
		time.sleep(0.02)		
	time.sleep(0.2+delay)	
	pwm.stop()
	time.sleep(0.1)		
	print "servo set to frequency", frequency , " PIN=", PIN , " Duty cycle=", duty 
	recdata.append(cmd)
	recdata.append(PIN)
	return True	
	

	
def gpio_set_stepper(cmd, message, recdata , stepper_data):
			
	msgarray=message.split(":")
	messagelen=len(msgarray)
	Interface=msgarray[1]
	Interface_Number=int(Interface) # this is the interface on same I2C board
	direction=msgarray[2]
	speed=int(msgarray[3])
	steps=int(msgarray[4])

	# following instructions have been removed as in case there is cuncurrency, then better not to wait, automation will eventually repeat the command
	#waitstep=0.1
	#waittime=0
	#maxwait=2.5
	#while (read_status_data(stepper_data,Interface,"busyflag")==True)and(waittime<maxwait):
	#	time.sleep(waitstep)
	#	waittime=waittime+waitstep
		
		
	if read_status_data(stepper_data,Interface,"busyflag"):
		# check how long the busyflag has been True
		lasttime=read_status_data(stepper_data,Interface,"busyflagtime")	
		deltat=datetime.datetime.utcnow()-lasttime
		if deltat.total_seconds()>600: # 600 seconds = 10 minutes
			# someting wrong, try to reset the stepper controller
			logger.warning("Stepper busy status Time exceeded, reset stepper controller: %s  ************", Interface)
			write_status_data(stepper_data,Interface,"busyflag",False)
			#reset
			mh = Adafruit_MotorHAT()
			mh.reset()
		else:
			print "Stepper busy "
			logger.warning("Stepper Busy, not proceeding with stepper: %s", Interface)
			return False
	
	write_status_data(stepper_data,Interface,"busyflag",True)
	write_status_data(stepper_data,Interface,"busyflagtime",datetime.datetime.utcnow())

	# stepper is no busy, proceed

	try:
		# create a default object, no changes to I2C address or frequency
		mh = Adafruit_MotorHAT()
		
		# set motor parameters
		myStepper = mh.getStepper(200, Interface_Number)  # 200 steps/rev, motor port #1 or #2
		myStepper.setSpeed(speed)             # 30 RPM

		print "Double coil steps"
		if direction=="FORWARD":
			myStepper.step(steps, Adafruit_MotorHAT.FORWARD,  Adafruit_MotorHAT.DOUBLE)
		elif direction=="BACKWARD":
			myStepper.step(steps, Adafruit_MotorHAT.BACKWARD, Adafruit_MotorHAT.DOUBLE)	
		
		# turn off motors
		mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
		mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
		mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
		mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)	
		
		del mh	
		write_status_data(stepper_data,Interface,"busyflag",False)

	except:
		print "problem I2C stepper controller"
		logger.error("problem I2C stepper controller")
		write_status_data(stepper_data,Interface,"busyflag",False)
		return False

		
	print "stepper: Interface", Interface_Number , " direction=", direction , " speed=", speed , " steps=", steps 
	recdata.append(cmd)
	recdata.append(Interface_Number)
	
	return True	


def get_stepper_status(cmd, message, recdata , stepper_data):
	print "get stepper status"
	msgarray=message.split(":")
	messagelen=len(msgarray)
	Interface=msgarray[1]
	returndata=read_status_dict(stepper_data,Interface)
	recdata.append(cmd)
	recdata.append(returndata)
	return True


def sendcommand(cmd, message, recdata):
	# as future upgrade this function might be run asincronously using "import threading"

	if ISRPI:
		ack=execute_task(cmd, message, recdata)
	else:
		ack=execute_task_fake(cmd, message, recdata)
	return ack
	






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
		print DHT22_data['lastupdate']

