"""
This file holds the SlowWire communication protocol class
"""
#!/usr/bin/env python
from __future__ import print_function
from __future__ import division

from builtins import hex
from builtins import range
from builtins import object
from past.utils import old_div
import time  # this is in python 2.7 which does not have the routine "time.perf_counter" in python 2.7 need a way to operate
import sys
import logging

logger = logging.getLogger("hydrosys4."+__name__)

try:
    # Python >= 3.3
    from time import perf_counter
    default_timer = time.perf_counter
    
except ImportError:
	# Python < 3.3
	if sys.platform == "win32":
		# On Windows, the best timer is time.clock()
		default_timer = time.clock
	else:
		# On most other platforms the best timer is time.time()
		default_timer = time.time

import RPi.GPIO as GPIO


class SlowWire(object):
	"""
	HX711 represents chip for reading load cells.
	"""

	def __init__(self,dout_pin):  # accept integer
		self._dout_pin = dout_pin
		self._t_init_low=0.020  # s
		self._t_wait_sensor=2  # s
		GPIO.setup(self._dout_pin,  GPIO.OUT)  # set pin to out, and to level high
		GPIO.output(self._dout_pin, 1)
		self.MAXCOUNT=1000
		self.MAXSAMPLING=10000




	def read_bytes(self):  # return a tuple with boolean for OK and array of bytes (isOK, List)
	
		MAXCOUNT=self.MAXCOUNT
		MAXSAMPLING=self.MAXSAMPLING


		#Set pin to output.
		GPIO.setup(self._dout_pin,  GPIO.OUT)
		GPIO.output(self._dout_pin, 1)
		time.sleep(0.001)
		# Set pin low for t_init_low milliseconds. This will tell the sensor to start measuring and get beck the data
		GPIO.output(self._dout_pin, 0)
		time.sleep(self._t_init_low)
		GPIO.output(self._dout_pin, 1)
		time.sleep(0.001)				
		#Set pin to imput, ready to receive data. Configuration pull-up
		GPIO.setup(self._dout_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		cyclewait=0.001
		numcycles=int(old_div(self._t_wait_sensor,cyclewait))
		print ("numero di cicli --------------------------->", numcycles)

		# Wait for sensor to pull pin low.
		count = 0
		while (GPIO.input(self._dout_pin))and(numcycles>count):
			count=count+1
			time.sleep(cyclewait)

		print ("Conta --------------------------->", count)
		if (count >= numcycles):
			# Timeout waiting for response.
			print ("error reading the SlowWire sensor: Wait too long for sensor answer")
			logger.error("error reading the SlowWire sensor: Wait too long for sensor answer")
			return False,0
			
		# Record pulse widths for the self.PULSES bits expected from the sensor
		LowpulseCounts=[]
		HighpulseCounts=[]
		n=MAXSAMPLING
		exitcondition=False
		while (n>0)and(not exitcondition):
		#for i in range(0,self.PULSES*2,2): # i starts from zero and increase by +2
			# Count how long pin is low and store in pulseCounts[i]
			thispulsecount=0
			while (not GPIO.input(self._dout_pin))and(not exitcondition):
				thispulsecount=thispulsecount+1
				time.sleep(0.0001)
				if (thispulsecount >= MAXCOUNT):
					# Timeout waiting for pulse lenght.
					exitcondition=True
			if (not exitcondition)and(thispulsecount):
				LowpulseCounts.append(thispulsecount)

			# Count how long pin is high and store in pulseCounts[i+1]
			thispulsecount=0
			while GPIO.input(self._dout_pin)and(not exitcondition):
				thispulsecount=thispulsecount+1
				time.sleep(0.0001)
				if (thispulsecount >= MAXCOUNT):
					# Timeout waiting for pulse lenght.
					exitcondition=True
			if (not exitcondition)and(thispulsecount):
				HighpulseCounts.append(thispulsecount)		

		print ("High pulse count ------------------------------------>", HighpulseCounts)
		#check data consistency:
		if len(HighpulseCounts)>7:
			print ("lenghts High=%d Low=%d ", len(HighpulseCounts),len(LowpulseCounts))
			if not ((len(HighpulseCounts)+1)==len(LowpulseCounts)):
				#data mismatch
				print ("error reading the SlowWire sensor: Data mismatch ")
				logger.error("error reading the SlowWire sensor: Data mismatch ")
				return False,0			
		else:
			print ("error reading the SlowWire sensor: Insufficient data")
			logger.error("error reading the SlowWire sensor: Insufficient data")
			return False,0					
			
				
		# Compute the average low pulse width in terms of number of samples
		# Ignore the first readings because it is not relevant.
		threshold = 0
		for i in range(1,len(LowpulseCounts)): # i starts from 2 and increase by +2
			threshold = threshold + LowpulseCounts[i]

		threshold /= len(LowpulseCounts)-1
		threshold /=2
		print("Slow Wire Threshold: -------------------------------------------- ", threshold)
		#Interpret each high pulse as a 0 or 1 by comparing it to the average size of the low pulses.

		data=[]
		databyte=0
		# skip the first 1 pulse
		for i in range(1,len(HighpulseCounts)):
			databyte = (databyte >> 1)
			if (HighpulseCounts[i] <= threshold):
				# One bit for long pulse.
				databyte |= 0x80
			# Else zero bit for short pulse.
			if (i%8==0): # got one byte
				data.append(databyte)
				databyte=0
  

		print("Slow Wire Data: -------------------------------------------- ", data)
		for item in data:
			print("The hexadecimal data" , hex(item)) 



		# Verify checksum of received data.
		if len(data)>=2:
			if self.checkCRC(data):
				print ("CRC OK --------------------")
				data.pop()  # remove last byte from list as this is the CRC
				return True, data
			else:
				print ("error reading the SlowWire sensor: Data Checksum error")
				logger.error("error reading the SlowWire sensor: Data Checksum error")
				return False,0
		else:
			print ("error reading the SlowWire sensor: Not enough bites of data")
			logger.error("error reading the SlowWire sensor: Not enough bites of data")
			
		return False,0
		
		
		
	def TwoBytesOneInt(self, byteslist):  # return array of int grouping two bytes togeter
		# return it to integer
		intlist=[]
		for i in range(0,len(byteslist)-1,2):
			result = (byteslist[i+1] << 8) + byteslist[i]
			intlist.append(result)
		# debugging
		print("Int Data: -------------------------------------------- ", intlist)
		return intlist


	def read_uint(self):
		uintlist=[]
		isOK, byteslist = self.read_bytes()
		if isOK:
			uintlist = self.TwoBytesOneInt(byteslist)
			if uintlist:
				return True, uintlist
		return False, 0
				
	def AddToCRC(self, b, crc):
		generator=0x1D
		crc ^= b
		for i in range(8):
			if ((crc & 0x80) != 0):
				crc = (crc << 1) ^ generator
			else:
				crc <<= 1
			crc= crc & 0xFF
		return crc
		
	def checkCRC(self, byteslist):	# input is a list of bytes, the last byte should be the CRC code sent by the transmitter
		check = 0x00
		for i in byteslist:
			check = self.AddToCRC(i, check)
		if (check==0):
			return True
		return False
			


if __name__ == '__main__':
	
	"""
	This is an usage example, connected to GPIO PIN 17 (BCM)
	"""
	PINDATA=18
	GPIO.setmode(GPIO.BCM)
	Sensor_bus = SlowWire(dout_pin=PINDATA)
	
	#print "Starting sample reading"
	ReadingAttempt=3
	isok=False
	while (ReadingAttempt>0)and(not isok):

		isok,datalist = Sensor_bus.read_uint()
		if isok:
			data=datalist[0]		
			print ("*************** SlowWire data: *********************** ",data)
		else:
			print ("error")
		ReadingAttempt=ReadingAttempt-1
