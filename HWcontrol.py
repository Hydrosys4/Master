# -*- coding: utf-8 -*-


#to kill python processes use  -- pkill python
from __future__ import print_function
from __future__ import division
from builtins import str
from builtins import hex
from builtins import range
from past.utils import old_div
import time
import datetime
import threading
from math import sqrt
#import sys,os
#import serial
#import os
import glob
import logging


logger = logging.getLogger("hydrosys4."+__name__)



global ISRPI

try:
	__import__("smbus")
except ImportError:
	ISRPI=False
else:
	import sys, os	
	basepath=os.getcwd()
	libpath="libraries/BMP/bmp180" # should be without the backslash at the beginning
	sys.path.append(os.path.join(basepath, libpath)) # this adds new import paths to add modules
	from grove_i2c_barometic_sensor_BMP180  import BMP085
	libpath="libraries/MotorHat" # should be without the backslash at the beginning
	sys.path.append(os.path.join(basepath, libpath)) # this adds new import paths to add modules	
	from stepperDOUBLEmod import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor	
	
	import Adafruit_DHT #humidity temperature sensor

	#from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor

	import spidev
	import smbus
	import Hygro24_I2C
	import hx711_AV
	import SlowWire
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM) 
	ISRPI=True


HWCONTROLLIST=["tempsensor","humidsensor","pressuresensor","analogdigital","lightsensor","pulse","pinstate","servo","stepper","stepperstatus","photo","mail+info+link","mail+info","returnzero","stoppulse","readinputpin","hbridge","hbridgestatus","DS18B20","Hygro24_I2C","HX711","SlowWire","InterrFreqCounter","WeatherAPI"]
RPIMODBGPIOPINLIST=["2", "3", "4","5","6", "7", "8", "9", "10", "11", "12","13","14", "15", "16","17", "18", "19", "20","21","22", "23", "24", "25","26", "27"]
NALIST=["N/A"]
GPIOPLUSLIST=["I2C", "SPI"]
RPIMODBGPIOPINLISTNA=NALIST+RPIMODBGPIOPINLIST
RPIMODBGPIOPINLISTPLUS=RPIMODBGPIOPINLISTNA+GPIOPLUSLIST

ADCCHANNELLIST=["N/A","0","1","2","3","4","5","6","7"] #MCP3008 chip has 8 input channels

# status variables
DHT22_data={}
DHT22_data["default"]={'temperature':None,'humidity':None,'lastupdate':datetime.datetime.utcnow() - datetime.timedelta(seconds=2)}

stepper_data={}
stepper_data["default"]={'busyflag':False}

hbridge_data={}
hbridge_data["default"]={'busyflag':False}

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
	#print data
	if element in data:
		#print " element present"
		elementdata=data[element]
		if variable in elementdata:
			return elementdata[variable]
		else:
			# variable not in elementdata
			return ""
	else:
		#print " element NOT present"
		# element not present in the data use the default
		data[element]=data["default"].copy()
		elementdata=data[element]
		#print data
		if variable in elementdata:
			return elementdata[variable]
		else:
			# variable not in elementdata
			return ""

def read_status_dict(data,element):
	#print data
	if element in data:
		#print " element present"
		elementdata=data[element]
		return elementdata
	else:
		#print " element NOT present"
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
	global hbridge_data
	
	print(" RASPBERRY HARDWARE CONTROL ")
	
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

	elif cmd==HWCONTROLLIST[6]:	# pinstate
		return gpio_pin_level(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[7]:	# servo
		return gpio_set_servo(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[8]: #stepper	
		return gpio_set_stepper(cmd, message, recdata, stepper_data)

	elif cmd==HWCONTROLLIST[9]: #stepper status	
		return get_stepper_status(cmd, message, recdata, stepper_data)

	elif cmd==HWCONTROLLIST[13]: #return zero	
		#print "returnzero"
		returndata="0"
		recdata.append(cmd)
		recdata.append(returndata)
		recdata.append(1) # confirm data for acknowledge
		return True

	elif cmd==HWCONTROLLIST[14]:	# stoppulse
		return gpio_stoppulse(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[15]:	# readinputpin
		return read_input_pin(cmd, message, recdata)
		
	elif cmd==HWCONTROLLIST[16]: #hbridge	
		return gpio_set_hbridge(cmd, message, recdata, hbridge_data)	

	elif cmd==HWCONTROLLIST[17]: #hbridge status	
		return get_hbridge_status(cmd, message, recdata, hbridge_data)

	elif cmd==HWCONTROLLIST[18]: #DS18B20 temperature sensor	
		return get_DS18B20_temperature(cmd, message, recdata)
		
	elif cmd==HWCONTROLLIST[19]: #Hygro24_I2C temperature sensor		
		return get_Hygro24_capacity(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[20]: #HX711 cell loads amplifier, for weight sensor		
		return get_HX711_voltage(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[21]: #SlowWire , Digital Hygrometer	
		return get_SlowWire_reading(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[22]: # Interrupt frequency counter
		return get_InterruptFrequency_reading(cmd, message, recdata)

	elif cmd==HWCONTROLLIST[23]: # weather API counter
		return get_WeatherAPI_reading(cmd, message, recdata)

	else:
		print("Command not found")
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
		print("no fake command available" , cmd)
		recdata.append(cmd)
		recdata.append("e")
		recdata.append(0)
		return False;
		
	return True


def get_1wire_devices_list():
	device_folder_list=[]
	outlist=[]
	base_dir = '/sys/bus/w1/devices/'
	lbs=len(base_dir)
	device_folder_list = glob.glob(base_dir+"*")
	for item in device_folder_list:
		strout=item[lbs:]
		if strout[0].isdigit():
			outlist.append(strout)
	return outlist

def get_I2C_devices_list():
	device_list=[]
	bus_number = 1  # 1 indicates /dev/i2c-1
	bus = smbus.SMBus(bus_number)
	for device in range(3, 128):
		try:
			bus.write_byte(device, 0)
			device_list.append("{0}".format(hex(device)))
		except:
			#print "device I2C not found"
			a=1
			
	bus.close()
	bus = None
	return device_list


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
				print("error reading the DHT sensor (Humidity,Temperature)")
				logger.error("error reading the DHT sensor (Humidity,Temperature)")
				
			# if reading OK, update status variable
			if (humidity is not None) and (temperature is not None):
				# further checks
				if (humidity>=0)and(humidity<=100)and(temperature>-20)and(temperature<200):
					print('Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity))
					DHT22_data[element]['humidity']=('{:3.2f}'.format(old_div(humidity, 1.)))
					DHT22_data[element]['temperature']=('{:3.2f}'.format(old_div(temperature, 1.)))
					DHT22_data[element]['lastupdate']=datetime.datetime.utcnow()
					successflag=1
				else:
					print('Failed to get DHT22 reading')	
					logger.error("Failed to get DHT22 reading, values in wrong range")					
			else:
				print('Failed to get DHT22 reading')	
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

	# Initialise the BMP085 and use STANDARD mode (default value)
	# bmp = BMP085(0x77, debug=True)
	# bmp = BMP085(0x77, 1)

	# To specify a different operating mode, uncomment one of the following:
	# bmp = BMP085(0x77, 0)  # ULTRALOWPOWER Mode
	# bmp = BMP085(0x77, 1)  # STANDARD Mode
	# bmp = BMP085(0x77, 2)  # HIRES Mode
	bmp = BMP085(0x77, 3)  # ULTRAHIRES Mode

	#temp = bmp.readTemperature()

	try:
		isok, Pressure = bmp.readPressure()
		if isok:
			Pressure = '{0:0.2f}'.format(Pressure/100) # the reading is in Hpa
			successflag=1
	except:
		#print " I2C bus reading error, BMP180 , pressure sensor "
		logger.error(" I2C bus reading error, BMP180 , pressure sensor ")
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
		light = '{0:0.2f}'.format((old_div((data[1] + (256 * data[0])), 1.2)))
		successflag=1  
	except:
		#print " I2C bus reading error, BH1750 , light sensor "
		logger.error(" I2C bus reading error, BH1750 , light sensor ")
	
	recdata.append(cmd)
	recdata.append(light)
	recdata.append(successflag)	
	return True
	
	
	
def get_DS18B20_temperature(cmd, message, recdata):
	successflag=0
	
	# this sensors uses the one wire protocol. Multiple sensors can be connected to the same wire and they can be distinguished using an Address which is the mane of the file
	# in this algorithm, the message should include the address, if the address field is empty then it gets the first reading available.


	msgarray=message.split(":")

	TemperatureUnit="C"
	if len(msgarray)>4:
		TemperatureUnit=msgarray[4]

	SensorAddress=""
	if len(msgarray)>6:
		SensorAddress=msgarray[6]	
	
	temperature=0

	# These tow lines mount the device:
	#os.system('modprobe w1-gpio')
	#os.system('modprobe w1-therm')
	 
	base_dir = '/sys/bus/w1/devices/'
	# Get all the filenames begin with 28 in the path base_dir.
	device_folder_list = glob.glob(base_dir + '28*')
	
	SensorAddress=SensorAddress.strip()
	isOK=False
	if device_folder_list:
		device_folder=device_folder_list[0]	
		if SensorAddress!="":
			for item in device_folder_list:
				if SensorAddress in item:
					device_folder=item
					isOK=True
					break
		else:	
			isOK=True
					
	if not isOK:
		# address of the termometer not found
		logger.error("DS18B20 address not found: %s", SensorAddress)
		recdata.append(cmd)
		recdata.append("DS18B20 address not found")
		recdata.append(0)	
		return True
	
	
	device_file = device_folder + '/w1_slave'

	#below commands reads the DS18B20 rom, which effectively is the address
	#name_file=device_folder+'/name'
	#f = open(name_file,'r')
	#RomReading=f.readline()
 
	f = open(device_file, 'r')
	lines = f.readlines()
	f.close()		

	if len(lines)>1:
		if ("YES" in lines[0].upper()):
			#first row found and OK
			# Find the index of 't=' in a string.
			equals_pos = lines[1].find('t=')
			if equals_pos != -1:
				# Read the temperature .
				temp_string = lines[1][equals_pos+2:] # takes the right part of the string
				
				try:
					temperature = old_div(float(temp_string), 1000.0)
					if (TemperatureUnit=="F") and (temperature is not None):
						temperature=temperature*1.8+32
					temperature=('{:3.2f}'.format(old_div(temperature, 1.)))
					successflag=1

				except:
					#print "error reading the DS18B20"
					logger.error("error reading the DS18B20")
	
	recdata.append(cmd)
	recdata.append(temperature)
	recdata.append(successflag)	
	return True
	
	
def get_HX711_voltage(cmd, message, recdata):
	
	#print "starting HX711 reading ****"
	
	successflag=0
	
	# this sensors uses the I2C protocol. Multiple sensors can be connected and can be distinguished using an Address 
	# in this algorithm, the message should include the address, if the address field is empty then it gets the default address 0x20.


	msgarray=message.split(":")

	PINDATA_str=""
	if len(msgarray)>1:
		PINDATA_str=msgarray[1]	


	measureUnit=""
	if len(msgarray)>4:
		measureUnit=msgarray[4]

	SensorAddress="0x20"
	if len(msgarray)>6:
		SensorAddress=msgarray[6]	

	PINCLK_str=""
	if len(msgarray)>7:
		PINCLK_str=msgarray[7]	


	PINDATA=toint(PINDATA_str,-1)
	PINCLK=toint(PINCLK_str,-1)



	if (PINDATA<0)or(PINCLK<0):
		print("HX711 PIN not valid", SensorAddress)
		# address not correct
		logger.error("HX711 PIN not valid: Pindata = %s  Pinclk= %s", PINDATA_str,PINCLK_str)
		recdata.append(cmd)
		recdata.append("HX711 PIN not valid")
		recdata.append(0)
		return True
	
	reading=0
	bus = 1
	HX711_hardware = hx711_AV.HX711(dout_pin=PINDATA, pd_sck_pin=PINCLK)
	
	# start reading multimple sample and making some filtering and average

	datatext=""	
	inde =0
	dataarray=[]
	
	#print "Starting sample reading"
	
	samplesnumber=25
	for x in range(0, samplesnumber): #number of samples
		
		# read data 

		isok,data = HX711_hardware.read()
		if isok:
			dataarray.append(data)
			inde=inde+1
			datatext=datatext+str(data)+","			
			#print "HX711 data:",data
					
	if inde==0:
		logger.error("HX711 reading error")
		recdata.append(cmd)
		recdata.append("HX711 reading error")
		recdata.append(0)
		return True	
			
	successflag=1	
	logger.info("HX711 Channel: %s", HX711_hardware.get_current_channel())
	logger.info("HX711 Channel: %d", HX711_hardware.get_current_gain_A())
	averagefiltered, average = normalize_average(dataarray)
	

	print("HX711 data Average: ",average , " Average filtered: ", averagefiltered)	


	reading=averagefiltered

	print("reading ", reading)

	recdata.append(cmd)
	recdata.append(reading)
	recdata.append(successflag)	
	return True
	
def get_SlowWire_reading(cmd, message, recdata):
	
	#print "starting SlowWire reading ****"
	
	successflag=0
	
	# this sensors uses the SlowWire protocol which is similar to one wire but with relaxed times and single Sensor per wire. 
	# The relaxed timing allow longer cable distances, for application like hygrometers which do not require speed.


	msgarray=message.split(":")

	PINDATA_str=""
	if len(msgarray)>1:
		PINDATA_str=msgarray[1]	


	measureUnit=""
	if len(msgarray)>4:
		measureUnit=msgarray[4]


	PINDATA=toint(PINDATA_str,-1)



	if (PINDATA<0):
		print("SlowWire PIN not valid")
		# address not correct
		logger.error("SlowWire PIN not valid: Pindata = %s ", PINDATA_str)
		recdata.append(cmd)
		recdata.append("SlowWire PIN not valid")
		recdata.append(0)
		return True
	
	reading=0

	Sensor_bus = SlowWire.SlowWire(dout_pin=PINDATA)
	
	# start reading multimple sample and making some filtering and average

	
	#print "Starting sample reading"
	ReadingAttempt=3
	inde=0
	while (ReadingAttempt>0)and(inde==0):
		datatext=""	
		inde=0
		dataarray=[]	
		samplesnumber=1
		for x in range(0, samplesnumber): #number of samples
			
			# read data 

			isok,datalist = Sensor_bus.read_uint()
			if isok:
				data=datalist[0]
				dataarray.append(data)
				inde=inde+1
				datatext=datatext+str(data)+","			
				#print "SlowWire data:",data
		ReadingAttempt=ReadingAttempt-1
						
						
	if inde==0:
		logger.error("SlowWire reading error")
		recdata.append(cmd)
		recdata.append("SlowWire reading error")
		recdata.append(0)
		return True	
			
	successflag=1	
	averagefiltered, average = normalize_average(dataarray)
	

	print("SlowWire data Average: ",average , " Average filtered: ", averagefiltered)	


	reading=averagefiltered

	print("reading ", reading)

	recdata.append(cmd)
	recdata.append(reading)
	recdata.append(successflag)	
	return True
	
	
def get_Hygro24_capacity(cmd, message, recdata):
	
	#print "starting Hygro24_I2C reading ****"
	
	successflag=0
	
	# this sensors uses the I2C protocol. Multiple sensors can be connected and can be distinguished using an Address 
	# in this algorithm, the message should include the address, if the address field is empty then it gets the default address 0x20.


	msgarray=message.split(":")

	measureUnit=""
	if len(msgarray)>4:
		measureUnit=msgarray[4]

	SensorAddress="0x20"
	if len(msgarray)>6:
		SensorAddress=msgarray[6]	
	
	if SensorAddress=="":
		SensorAddress="0x20" # try with default address

	try:
		if SensorAddress.startswith("0x"):
			SensorAddressInt = int(SensorAddress, 16)
		else:
			SensorAddressInt = int(SensorAddress)
	except:
		print("can't parse %s as an i2c address", SensorAddress)
		# address not correct
		logger.error("Hygro24_I2C address incorrect: %s", SensorAddress)
		recdata.append(cmd)
		recdata.append("Hygro24_I2C address incorrect")
		recdata.append(0)
		return True
	
	reading=0
	bus = 1
	chirp = Hygro24_I2C.ChirpAV(bus, SensorAddressInt)

	isOK , reading=chirp.read_capacity()
	# need to add control in case there is an error in reading
	print("reading ", reading)

	if isOK:
		successflag=1
	else:
		logger.error("Hygro24_I2C reading error")
		recdata.append(cmd)
		recdata.append("Hygro24_I2C reading error")
		recdata.append(0)
		return True
	
	
	recdata.append(cmd)
	recdata.append(reading)
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
	
	#print "MCP3008 wait time -----> ", waittime
		
	if (waittime>=maxwait):
		#something wrog, wait too long, avoid initiate further processing
		print("MCP3008 wait time EXCEEDED ")
		logger.warning("Wait Time exceeded, not able to read ADCdata Channel: %d", channel)
		return False

	MCP3008_busy_flag=True		

	
	powerPIN_start(POWERPIN,logic,2)

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
		
		#print "Starting sample reading"
		
		samplesnumber=39
		for x in range(0, samplesnumber): #number of samples
			
			# read data from selected channel
			adc = spi.xfer2([1,(8+channel)<<4,0])
			data = ((adc[1]&3) << 8) + adc[2]
			
			dataarray.append(data)
			inde=inde+1
			datatext=datatext+str(data)+","			
			#print "MCP3008 channel ", channel, " data:",data
						
		logger.info("ADCdata Channel: %d", channel)
		logger.info("ADCdata Sampling: %s", datatext)
		dataaverage, mean = normalize_average(dataarray)
		
		# Function to convert data to voltage level,
		# rounded to specified number of decimal places.
		voltsraw = old_div((mean * refvoltage), float(1023))
		voltsnorm = old_div((dataaverage * refvoltage), float(1023))
		volts = round(voltsnorm,2)	
	
		#print "MCP3008 chennel ", channel, " Average (volts): ",voltsraw , " Average Norm (v): ", voltsnorm
		
		spi.close()
		successflag=1
	except:
		print(" DPI bus reading error, MCP3008 , AnalogDigitalConverter  ")
		logger.error(" DPI bus reading error, MCP3008 , AnalogDigitalConverter  ")
	
	recdata.append(cmd)
	recdata.append(volts)
	recdata.append(successflag)


	powerPIN_stop(POWERPIN,0)
	
	time.sleep(0.2) # wait after the power pin has been set to LOW
	
	MCP3008_busy_flag=False

	return True	


def normalize_average(lst):
	"""Calculates the standard deviation for a list of numbers."""
	num_items = len(lst)
	if num_items>0:
		mean = old_div(sum(lst), float(num_items))
		differences = [x - mean for x in lst]
		sq_differences = [d ** 2 for d in differences]
		ssd = sum(sq_differences)
		variance = old_div(ssd, float(num_items))
		sd = sqrt(variance)
		 
		# use functions to adjust data, keep only the data inside the standard deviation

		final_list = [x for x in lst if ((x >= mean - sd) and (x <= mean + sd))]
		num_items_final = len(final_list)
		normmean=old_div(sum(final_list), float(num_items_final))
		
		#print "discarded ", num_items-num_items_final , " mean difefrence ", normmean-mean

		return normmean, mean
	
	else:
		return 0, 0



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
			#print "PowerPin activated ", POWERPIN
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
				#print "Real * PIN *"
			except:
				return False, 0	
	return False, 0		


def GPIO_output(PINstr, level):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		GPIO.output(PIN, level)
	#GPIO_data[PIN]["level"]=level
	write_status_data(GPIO_data,PINstr,"level",level)
	logger.info("Set PIN=%s to State=%s", PINstr, str(level))
	#print PINstr , " ***********************************************" , level
	return True
		
def GPIO_output_nostatus(PINstr, level):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		GPIO.output(PIN, level)
	logger.info("NO Record, Set PIN=%s to State=%s", PINstr, str(level))
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



def GPIO_add_event_detect(PINstr, evenslopetype, eventcallback, bouncetimeINT=200 ):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		#print "add event ", PIN
		# bouncetime in ms to avoid signal instability (default 200)
		GPIO.add_event_detect(PIN, GPIO.BOTH, callback=eventcallback, bouncetime=bouncetimeINT)


def GPIO_remove_event_detect(PINstr):
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	if isRealPIN:
		GPIO.remove_event_detect(PIN)




def endpulse(PINstr,logic,POWERPIN,MIN=0,MAX=0):
	#GPIO_data[PIN]["threadID"]=None
	write_status_data(GPIO_data,PINstr,"threadID",None)
	if logic=="pos":
		level=0
	else:
		level=1
	
	if MIN and MAX:
		# dual pulse option
		# stop the pulse after MAX seconds
		levelinvert=1-level		
		GPIO_output_nostatus(PINstr, levelinvert)
		NorecordthreadID=threading.Timer(MAX, GPIO_output, [PINstr , level]) 
		NorecordthreadID.start()
	else:
		# normal pulse stop
		GPIO_output(PINstr, level)
	
	powerPIN_stop(POWERPIN,0)

	#print "pulse ended", time.ctime() , " PIN=", PINstr , " Logic=", logic , " Level=", level
	return True


def gpio_pulse(cmd, message, recdata):
	successflag=0
	msgarray=message.split(":")
	messagelen=len(msgarray)	
	PIN=msgarray[1]

	testpulsetime=msgarray[2]
	pulsesecond=int(testpulsetime)
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

	activationmode=""
	if messagelen>7:	
		activationmode=msgarray[7]

	if isPinActive(PIN,logic):
		if activationmode=="NOADD": # no action needed
			print("No Action, pulse activated when PIN already active and activationmode is NOADD")
			logger.warning("No Action, pulse activated when PIN already active and activationmode is NOADD")
			successflag=1
			recdata.append(cmd)
			recdata.append(PIN)
			recdata.append(successflag)
			return True



	# in case another timer is active on this PIN, cancel it 
	PINthreadID=read_status_data(GPIO_data,PIN,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
	
	else:
		powerPIN_start(POWERPIN,logic,0.2) # it is assumed that the logic (pos,neg) of the powerpin is the same of the pin to pulse, in the future it might be useful to specify the powerpin logic separately
		GPIO_setup(PIN, "out")
		if logic=="pos":
			level=1
		else:
			level=0
		GPIO_output(PIN, level)
		if MIN and MAX:
			# dual pulse  mode
			#print "dual pulse Mode"
			# stop the pulse after MIN seconds
			levelinvert=1-level
			NorecordthreadID=threading.Timer(MIN, GPIO_output_nostatus, [PIN , levelinvert])
			NorecordthreadID.start()

	NewPINthreadID=threading.Timer(pulsesecond, endpulse, [PIN , logic , POWERPIN , MIN , MAX])
	NewPINthreadID.start()
	write_status_data(GPIO_data,PIN,"threadID",NewPINthreadID)

	#print "pulse started", time.ctime() , " PIN=", PIN , " Logic=", logic 
	successflag=1
	recdata.append(cmd)
	recdata.append(PIN)
	recdata.append(successflag)
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
		
	MIN=0	
	if messagelen>5:	
		MIN=int(msgarray[5])	
		
	MAX=0	
	if messagelen>6:	
		MAX=int(msgarray[6])	
	
	
	if not isPinActive(PIN,logic):
		print("No Action, Already OFF")
		logger.warning("No Action, Already OFF")
		successflag=1
		recdata.append(cmd)
		recdata.append(PIN)
		recdata.append(successflag)
		return True	
	
	
	PINthreadID=read_status_data(GPIO_data,PIN,"threadID")
	if not PINthreadID==None:
		#print "cancel the Thread of PIN=",PIN
		PINthreadID.cancel()
		
	endpulse(PIN,logic,POWERPIN,MIN,MAX)	#this also put powerpin off		
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

def get_InterruptFrequency_reading(cmd, message, recdata):
	import interruptmod
	successflag=1
	msgarray=message.split(":")
	#print " read pin input ", message
	PINstr=msgarray[1]
	isRealPIN,PIN=CheckRealHWpin(PINstr)
	recdata.append(cmd)		
	if isRealPIN:
		# here the reading
		reading=interruptmod.ReadInterruptFrequency(PIN)
		recdata.append(reading)
		recdata.append(successflag)	
	else:
		successflag=0
		recdata.append("e")
		recdata.append(successflag)	
	return True
	
def get_WeatherAPI_reading(cmd, message, recdata):
	import weatherAPImod
	successflag=1
	recdata.append(cmd)		

	# here the reading
	isok, reading=weatherAPImod.CalculateRainMultiplier()
	if isok:
		recdata.append(reading)
		recdata.append(successflag)	
	else:
		successflag=0
		recdata.append("e")
		recdata.append(successflag)	
	return True
	


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



def gpio_set_servo(cmd, message, recdata):
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN=int(msgarray[1])
	frequency=int(msgarray[2])
	duty=float(msgarray[3])
	delay=float(msgarray[4])
	previousduty=float(msgarray[5])
	stepnumber=int(msgarray[6])
	
	step=old_div((duty-previousduty),stepnumber)
	
	
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
	#print "servo set to frequency", frequency , " PIN=", PIN , " Duty cycle=", duty 
	recdata.append(cmd)
	recdata.append(PIN)
	return True	
	
def isPinActive(PIN, logic):
	PINlevel=read_status_data(GPIO_data,PIN,"level")
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

	
def gpio_set_hbridge(cmd, message, recdata , hbridge_data ):
			
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

# START stepper section

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
			print("Stepper busy ")
			logger.warning("Stepper Busy, not proceeding with stepper: %s", Interface)
			return False
	
	write_status_data(stepper_data,Interface,"busyflag",True)
	write_status_data(stepper_data,Interface,"busyflagtime",datetime.datetime.utcnow())

	# stepper is no busy, proceed

#	try:
	# create a default object, no changes to I2C address or frequency
	mh = Adafruit_MotorHAT()
	
	# set motor parameters
	myStepper = mh.getStepper(200, Interface_Number)  # 200 steps/rev, motor port #1 or #2
	myStepper.setSpeed(speed)             # 30 RPM

	#print "Double coil steps"
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
	try:
		write_status_data(stepper_data,Interface,"busyflag",False)

	except:
		print("problem I2C stepper controller")
		logger.error("problem I2C stepper controller")
		write_status_data(stepper_data,Interface,"busyflag",False)
		return False

		
	#print "stepper: Interface", Interface_Number , " direction=", direction , " speed=", speed , " steps=", steps 
	recdata.append(cmd)
	recdata.append(Interface_Number)
	
	return True	


def get_stepper_status(cmd, message, recdata , stepper_data):
	#print "get stepper status"
	msgarray=message.split(":")
	messagelen=len(msgarray)
	Interface=msgarray[1]
	returndata=read_status_dict(stepper_data,Interface)
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
		print(" NO Raspberry detected ")
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
		print(DHT22_data['lastupdate'])

