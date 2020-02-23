#!/usr/bin/env python
from __future__ import print_function

import smbus, time, sys, argparse

class ChirpAV:
	def __init__(self, bus=1, address=0x20):
		self.bus_num = bus
		self.bus = smbus.SMBus(bus)
		self.address = address
		#self.reset()
		self.version()

	def reset(self):
		commandlist=[0x06]
		isok, data = self.get_data(commandlist, 0)
		if (isok) and (data==0):
			print("Reset procedure correctly activated")
			time.sleep(5)
		else:
			print("not able to start Reset")

	def version(self):
		commandlist=[0x07]
		isok, data = self.get_data(commandlist, 0)
		time.sleep(0.5)
		if isok:
		   print("version", hex(data))
		else:
		   print("not able to retrieve version data")
		return isok, data 

	def read(self,fallback): # fallback value is the value provided when not able to read corectly
		isok = False
		val = 0
		count=3
		while (count>0)and(isok==False):
			try:
				# sometime reading raises an IOError, i don't know why.
				val = self.bus.read_byte(self.address)
				isok = True
			except:
				print("Error Reading")
			count=count-1
			time.sleep(0.05)
		if isok:
			return val
		else:
			return fallback

	def write(self, reg):
		count = 3
		isok = False
		while (count>0)and(isok==False):
			try:
				# re-try in case writing raises an IOError.
				self.bus.write_byte(self.address, reg)
				isok = True
			except:
				print("Error Writing on I2C bus")
				count=count-1
				time.sleep(0.05)
		return isok


	def get_data(self, cmdlist, waittime=1):
		for data in cmdlist:
			self.write(data)
			time.sleep(0.05)
		time.sleep(waittime)
		# if the chrip has no data it sends 0xFF
		reg=cmdlist[0]
		t = self.read(0)
		count=20
		while (t != reg)and(count>0):
		  t = self.read(0)
		  print ("buffer read " , t)
		  count=count-1
		  time.sleep(0.05)
		  
		print ("count %d", count)
		  
		if t==reg:
		   b1 = self.read(0xFF)
		   time.sleep(0.05)
		   b2 = self.read(0xFF)		  
		   print ("B buffer read " , b1 , b2)
		 
		if (t==reg) and (b1 != 0xFF) and (b2 != 0xFF):
		   return True , (b1 << 8) + b2
		else:
		   return False, 0


	def read_capacity(self):
		commandlist=[0x03]
		return self.get_data(commandlist,1)

	def read_light(self):
		commandlist=[0x04]
		return self.get_data(commandlist,1.5)

	def read_address(self):
		commandlist=[0x02]
		isok , address = self.get_data(commandlist,0.5)
		if isok:
			return isok , hex(address)
		else:
			print("not able to read I2C address")
			return isok, 0

	def set_address(self, newaddress):
		commandlist=[0x01,newaddress]
		isok , address = self.get_data(commandlist,0)
		if isok:
			print("I2C Change address procedure initiated correctly, new address=",hex(address))	
			time.sleep(5)						
			return isok , hex(address)
		else:
			print("not able to read I2C address")
			return isok, 0


	def __repr__(self):
		return "<Chirp sensor on bus %d, addr 0x%02x>" % (self.bus_num, self.address)

if __name__ == "__main__":
	addr = 0x50
	bus = 0

	parser = argparse.ArgumentParser(description='Work with Chirp\'s')

	parser.add_argument('--set-address', type=str,
	  help='set the chirps i2c address to this address')

	parser.add_argument('address',
	  type=str,default="0x20",
	  help='the chirp\'s i2c address')

	parser.add_argument('bus',
	  type=int, default=1, nargs='?',
	  help='the i2c bus to look at')

	args = parser.parse_args()

	bus = args.bus
	addr = args.address
	try:
		if addr.startswith("0x"):
			addr = int(addr, 16)
		else:
			addr = int(addr)
	except ValueError:
		parser.error("can't parse %s as an i2c address" % (args.address))
		raise SystemExit

	chirp = ChirpAV(bus, addr)

	if args.set_address:
		sa = args.set_address
		try:
		  if sa.startswith("0x"):
			sa = int(sa, 16)
		  else:
			sa = int(sa)
		except ValueError:
		  parser.error("can't parse %s as an i2c address" % (args.set_address))
		  raise SystemExit

		print("Setting the chirp's i2c address to 0x%x" % (sa))
		chirp.set_address(sa)
		print("done")
		raise SystemExit

	#chirp.reset()
	
	#newaddress=0x30
	#chirp.set_address(newaddress)
	
	
	#chirp = ChirpAV(bus, newaddress)


	while True:
		#chirp.reset()
		print("cap", chirp.read_capacity())

		print("light", chirp.read_light())
		
		print("address", chirp.read_address())
		time.sleep(0.05)
		print()

