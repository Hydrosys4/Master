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
	import spidev
	import smbus
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM) 
	ISRPI=True


HWCONTROLLIST=["tempsensor","humidsensor","pressuresensor","analogdigital","lightsensor","pulse","readpin","servo","photo","mail+info+link","mail+info"]
RPIMODBGPIOPINLISTPLUS=["I2C", "SPI", "2", "3", "4","5","6", "7", "8", "9", "10", "11", "12","13","14", "15", "16","17", "18", "19", "20","21","22", "23", "24", "25","26", "27", "N/A"]
RPIMODBGPIOPINLIST=["2", "3", "4","5","6", "7", "8", "9", "10", "11", "12","13","14", "15", "16","17", "18", "19", "20","21","22", "23", "24", "25","26", "27","N/A"]
ADCCHANNELLIST=["0","1","2","3","4","5","6","7", "N/A"] #MCP3008 chip has 8 input channels

DHT22_data={'Temperature':None,'Humidity':None,'lastupdate':None}
DHT22_data['lastupdate']=datetime.datetime.now() - datetime.timedelta(seconds=2)
Servo_data={'duty':"3"}

#" GPIO_data is an array of dictionary, total 40 items in the array
GPIO_data=[{"level":None, "state":None} for k in range(40)]
#" PowerPIN_Status is an array of dictionary, total 40 items in the array, the array is used to avoid comflict between tasks using same PIN 
# each time the pin is activated the level is increased by 1 unit.
PowerPIN_Status=[{"level":0, "state":"off", "pinstate":None} for k in range(40)]

MCP3008_busy_flag=False

def execute_task(cmd, message, recdata):
	global DHT22_data
	global Servo_data
	
	
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

	elif cmd==HWCONTROLLIST[7]:	
		return gpio_set_servo(cmd, message, recdata, Servo_data)

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
		
	else:
		print "no fake command available" , cmd
		recdata.append(cmd)
		recdata.append("e")
		recdata.append(0)
		return False;
	return True



def get_DHT22_temperature_fake(cmd, message, recdata, DHT22_data):
	deltat=datetime.datetime.now()-DHT22_data['lastupdate']
	if deltat.total_seconds()>2:
		
		DHT22_data['Humidity']="10.10"
		DHT22_data['Temperature']="20.10"
		DHT22_data['lastupdate']=datetime.datetime.now()

	recdata.append(cmd)
	recdata.append(DHT22_data['Temperature'])
	recdata.append(1)
	return DHT22_data['lastupdate']
	
	

def get_DHT22_temperature(cmd, message, recdata, DHT22_data):
	
	successflag=0
	msgarray=message.split(":")
	pin=int(msgarray[1])

	deltat=datetime.datetime.now()-DHT22_data['lastupdate']
	if deltat.total_seconds()>2:
		
		humidity=None
		temperature=None
		
		try:
			sensor = Adafruit_DHT.DHT22
			humidity, temperature = Adafruit_DHT.read(sensor, pin)
		except:
			print "error reading the DHT sensor (Humidity,Temperature)"
			logger.error("error reading the DHT sensor (Humidity,Temperature)")
			logger.exception("message")


		if (humidity is not None) and (temperature is not None):
			print 'Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity)
			DHT22_data['Humidity']=('{:3.2f}'.format(humidity / 1.))
			DHT22_data['Temperature']=('{:3.2f}'.format(temperature / 1.))
			DHT22_data['lastupdate']=datetime.datetime.now()
			successflag=1
		else:
			print 'Failed to get DHT22 reading'

	else:
		successflag=1 # use the data in memory, reading less than 2 sec ago
		
	recdata.append(cmd)
	recdata.append(DHT22_data['Temperature'])
	recdata.append(successflag)	
	return DHT22_data['lastupdate']
	

def get_DHT22_humidity(cmd, message, recdata, DHT22_data):
	successflag=0
	msgarray=message.split(":")
	pin=int(msgarray[1])
	deltat=datetime.datetime.now()-DHT22_data['lastupdate']
	if deltat.total_seconds()>2:
		
		humidity=None
		temperature=None
		try:
			sensor = Adafruit_DHT.DHT22
			humidity, temperature = Adafruit_DHT.read(sensor, pin)
		except:
			print "error reading the DHT sensor (Humidity,Temperature)"
			logger.exception("message")

		if (humidity is not None) and (temperature is not None):
			print 'Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity)
			DHT22_data['Humidity']=('{:3.2f}'.format(humidity / 1.))
			DHT22_data['Temperature']=('{:3.2f}'.format(temperature / 1.))
			DHT22_data['lastupdate']=datetime.datetime.now()
			successflag=1
		else:
			print 'Failed to get DHT22 reading'
	else:
		successflag=1 # use the data in memory, reading less than 2 sec ago
		
	recdata.append(cmd)
	recdata.append(DHT22_data['Humidity'])
	recdata.append(successflag)	
	return DHT22_data['lastupdate']


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
	
	POWERPIN=-1	
	if messagelen>3:	
		POWERPIN=int(msgarray[3])
	
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
		logger.info("Wait Time exceeded, not able to read ADCdata Channel: %d", channel)
		return False

	MCP3008_busy_flag=True		

	
	powerPIN_start(POWERPIN,"pos",0.05)

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
		for x in range(0, 39):
			
			# read data from selected channel
			adc = spi.xfer2([1,(8+channel)<<4,0])
			data = ((adc[1]&3) << 8) + adc[2]
			
			dataarray.append(data)
			inde=inde+1
			datatext=datatext+str(data)+","			
			print "MCP3008 chennel ", channel, " data:",data
						
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

	final_list = [x for x in lst if ((x > mean - sd) and (x < mean + sd))]
	num_items_final = len(final_list)
	normmean=sum(final_list) / float(num_items_final)
	
	print "discarded ", num_items-num_items_final , " mean difefrence ", normmean-mean

	return normmean, mean



def powerPIN_start(POWERPIN,logic,waittime):

	if POWERPIN>0:
		PowerPIN_Status[POWERPIN]["level"]+=1
		#start power pin
		if PowerPIN_Status[POWERPIN]["state"]=="off":
			GPIO_setup(POWERPIN, "out")
			if logic=="pos": 
				GPIO_output(POWERPIN, 1)
				PowerPIN_Status[POWERPIN]["pinstate"]="1"
			else:
				GPIO_output(POWERPIN, 0)
				PowerPIN_Status[POWERPIN]["pinstate"]="0"
				
			PowerPIN_Status[POWERPIN]["state"]="on"
			time.sleep(waittime)
	return True	

		
def powerPIN_stop(POWERPIN,waittime):
	
	if POWERPIN>0:
		#set powerpin to zero again in case this is the last thread
		PowerPIN_Status[POWERPIN]["level"]-=1		
		#stop power pin
		if PowerPIN_Status[POWERPIN]["level"]<=0:
			if PowerPIN_Status[POWERPIN]["state"]=="on":
				time.sleep(waittime)
				if PowerPIN_Status[POWERPIN]["pinstate"]=="1": 
					GPIO_output(POWERPIN, 0)
					PowerPIN_Status[POWERPIN]["pinstate"]="0"
				elif PowerPIN_Status[POWERPIN]["pinstate"]=="0":
					GPIO_output(POWERPIN, 1)
					PowerPIN_Status[POWERPIN]["pinstate"]="1"
				PowerPIN_Status[POWERPIN]["state"]="off"

	return True	


def GPIO_output(PIN, level):
	if ISRPI:
		GPIO.output(PIN, level)
	GPIO_data[PIN]["level"]=level
	return True

def GPIO_setup(PIN, state):
	if ISRPI:
		if state=="out":
			GPIO.setup(PIN,  GPIO.OUT)
		else:
			GPIO.setup(PIN,  GPIO.IN)
	GPIO_data[PIN]["state"]=state
	return True

def endpulse(PIN,logic,POWERPIN):

	if logic=="pos":
		level=0
	else:
		level=1
	GPIO_output(PIN, level)
	
	powerPIN_stop(POWERPIN,0)	
	print "pulse ended", time.ctime() , " PIN=", PIN , " Logic=", logic , " Level=", level
	return True


def gpio_pulse(cmd, message, recdata):
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN=int(msgarray[1])
	testpulsetime=msgarray[2]
	pulsesecond=int(testpulsetime)/1000
	
	if messagelen>3:
		if msgarray[3]=="0":
			logic="neg"
		elif msgarray[3]=="1":
			logic="pos"	
	
	POWERPIN=-1	
	if messagelen>4:	
		POWERPIN=int(msgarray[4])
	
	powerPIN_start(POWERPIN,logic,0.2) # it is assumed that the logic (pos,neg) of the powerpin is the same of the pin to pulse, in the future it might be useful to specify the powerpin logic separately
	
		
	GPIO_setup(PIN, "out")
	if logic=="pos":
		level=1
	else:
		level=0
	GPIO_output(PIN, level)
		
	t = threading.Timer(pulsesecond, endpulse, [PIN , logic , POWERPIN]).start()
	print "pulse started", time.ctime() , " PIN=", PIN , " Logic=", logic , " Level=", level
	recdata.append(cmd)
	recdata.append(PIN)
	return True	

def gpio_pin_level(cmd, message, recdata):
	msgarray=message.split(":")
	PIN=int(msgarray[1])
	recdata.append(msgarray[0])
	if GPIO_data[PIN]["level"] is not None:
		recdata.append(str(GPIO_data[PIN]["level"]))
		return True
	else:
		recdata.append("e")
		return False	



def gpio_set_servo(cmd, message, recdata, Servo_data):
	msgarray=message.split(":")
	messagelen=len(msgarray)
	PIN=int(msgarray[1])
	frequency=int(msgarray[2])
	duty=float(msgarray[3])
	delay=float(msgarray[4])
	
	GPIO_setup(PIN, "out")
	pwm = GPIO.PWM(PIN, frequency) # set the frequency
	pwm.start(duty)
	time.sleep(0.2+delay)
	#pwm.ChangeDutyCycle(duty)
	pwm.stop()

	Servo_data['duty']=msgarray[3]
		
	print "servo set to frequency", frequency , " PIN=", PIN , " Duty cycle=", duty 
	recdata.append(cmd)
	recdata.append(PIN)
	return True	

def get_servo_duty():
	return Servo_data['duty']


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

