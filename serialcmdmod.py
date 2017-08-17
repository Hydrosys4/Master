# -*- coding: utf-8 -*-


#to kill python processes use  -- pkill python
import time
import datetime
import sys,os
import serial
import logging

# variable below is a flag to avoid send procedure to run concurrently
global sendcanstart
sendcanstart=True

# Time to wait after initializing serial, used in Board.__init__
BOARD_SETUP_WAIT_TIME = 5
BOARDS = {
    'arduino' : {
        'digital' : tuple(x for x in range(14)),
        'analog' : tuple(x for x in range(6)),
        'pwm' : (3, 5, 6, 9, 10, 11),
        'use_ports' : True,
        'disabled' : (0, 1) # Rx, Tx, Crystal
    }
}
    
class slavecontroller(object):

      
    def __init__(self, baudrate=57600, name=None):
		self.field_separator = ':' 
		self.command_separator = ';'
		self.baudrate=baudrate
		self.finishinit=False
		self.laststart= datetime.datetime.now()
		self.initserial()
		self.setup_layout()
		
		
    def initserial(self):
		self.finishinit=False
		maincou=0
		while (not self.finishinit)and(maincou<3):
			maincou=maincou+1
			locations=['/dev/ttyACM0','/dev/ttyACM1','/dev/ttyACM2','/dev/ttyACM3']    
			portconnect=False
			for device in locations:  
				try:  
					print "Trying...",device  
					self.sp = serial.Serial(device, 9600) #for some reason this make the port reset starting with different baud rate
					self.sp = serial.Serial(device, self.baudrate)
					portconnect=True
					break  
				except:  
					portconnect=False
					print "Failed to connect on",device 
			if not portconnect:
				print 'could not open port'
				break
			else:								
				print "RESET ARDUINO"
				self.sp.setDTR(False) # Drop DTR
				time.sleep(0.030)    # Read somewhere that 22ms is what the UI does.
				self.sp.setDTR(True)  # UP the DTR back
			
			# Iterate over the first messages to get arduino ready message ---------------------------------------------
			cou=0
			while (not self.bytes_available())and(cou<5):
				time.sleep(1) # delays for n seconds
				cou=cou+1
			print "received transmission" , self.bytes_available()
			rdata=[]
			while self.bytes_available():
				answer=self.iterate(rdata)
				print "Received data -",rdata
			
			
			recdata=["no"]
			ack=False
			cou=0
			while (not ack)and(cou<3):
				self.finishinit=True	
				ack=self.sendcommand("2","Arduino ready",recdata) #send command to ardunino and report answer in recdata
				self.finishinit=False
				cou=cou+1
				time.sleep(1) # delays for n seconds
			if (ack):
				self.finishinit=True
				print "initialization of serial port finished succesfully"
				print "start time " ,self.laststart
			else:
				if hasattr(self, 'sp'):
					self.sp.close()
				print "closed"

            

    def __del__(self):
        ''' 
        The connection with the a board can get messed up when a script is
        closed without calling board.exit() (which closes the serial
        connection). Therefore also do it here and hope it helps.
        '''
        self.exit()
        
    def pass_time(self, t):
        """ 
        Non-blocking time-out for ``t`` seconds.
        """
        cont = time.time() + t
        while time.time() < cont:
            time.sleep(0.01) # delays for n seconds
        

    def setup_layout(self):
        """
        Setup the Pin instances based on the given board-layout. Maybe it will
        be possible to do this automatically in the future, by polling the
        board for its type.
        """
        # Setup default handlers for standard incoming commands
        #self.add_cmd_handler(ANALOG_MESSAGE, self._handle_analog_message)
        #self.add_cmd_handler(DIGITAL_MESSAGE, self._handle_digital_message)
        #self.add_cmd_handler(REPORT_VERSION, self._handle_report_version)
        #self.add_cmd_handler(REPORT_FIRMWARE, self._handle_report_firmware)
    
    def add_cmd_handler(self, cmd, func):
        """ 
        Adds a command handler for a command.
        """
        len_args = len(inspect.getargspec(func)[0])
        def add_meta(f):
            def decorator(*args, **kwargs):
                f(*args, **kwargs)
            decorator.bytes_needed = len_args - 1 # exclude self
            decorator.__name__ = f.__name__
            return decorator
        func = add_meta(func)
        self._command_handlers[cmd] = func
     
    def bytes_available(self):
        return self.sp.inWaiting()

    def iterate(self, dataanswer): 
		# first value of the dataanswer list is always the cmd
		""" 
		Reads and handles data from the microcontroller over the serial port.
		This method should be called in a main loop, or in an
		:class:`Iterator` instance to keep this boards pin values up to date 
		"""
		received_data = ""
		while self.bytes_available(): #read byte per byte
			try:
				byte = self.sp.read()
			except IOError:
				print "something wrong with serial connection no data to read initiate restart"
				self.restartserial()
				return False

			if not byte:
				return False
			#print byte
			received_data=received_data+byte 
            

		#print "Received -",received_data
		if received_data.find(self.command_separator)>0:
			received_data=received_data.split(self.command_separator )[0]
			splitted_data=received_data.split(self.field_separator )
			cmdanswer=splitted_data[0]
			dataanswer.extend(splitted_data[:])
			#print "Received command - ", cmdanswer , " data -",dataanswer
			return True
		else:
			return False
		#-------------------------------------------------------------------------------
		"""
		handler = None       
		while received_data <> self.command_separator:
				received_data.append(self.sp.read())

		try:
		   handler = self._command_handlers[data]  #-----------------------------------------------------------------------
		except KeyError:
		   return

		# Handle the data
		try:
			handler(*received_data)
		except ValueError:
			pass
		"""

       
    def exit(self):
        """ Call this to exit cleanly. """
        if hasattr(self, 'sp'):
            self.sp.close()
            print "Serial connection closed"
        
    def restartserial(self):
        currenttime= datetime.datetime.now()		
        print "try to recover serial connection in ", (datetime.timedelta(minutes=1)-(currenttime-self.laststart))
        if (currenttime-self.laststart)> datetime.timedelta(minutes=1):
			self.exit()
			self.initserial()
			self.laststart=currenttime
			

		
        
    def sendcommand_task(self,cmd, message, recdata):
		global sendcanstart
		sendcanstart=False
		del recdata[:]
		for i in range(10):
			recdata.append("e")

		if not cmd:
			sendcanstart=True
			return False
			
		if not self.finishinit:
			print "Serial not initiated properly"
			self.restartserial()
			sendcanstart=True
			return False
			
		if not message:
			writestring=cmd + self.command_separator
		else:
			writestring=cmd + self.field_separator + message + self.command_separator
		try:
			self.sp.write(str(writestring))
		except IOError:
			print "something wrong with serial connection"
			self.restartserial()
			#SerialException: write failed: [Errno 5] Input/output error

		print "Sent -",writestring, "  -------------------->>>>> "
		# Iterate over the  messages to get arduino answer
		answer=False
		rcmd=""
		rdata=[]
		
		cou=0
		while ((not self.bytes_available()) and cou<50):
			self.pass_time(0.01)
			cou=cou+1	
		print "data received after seconds: ", cou*0.01

		self.pass_time(0.05) 

		cou=0
		while self.bytes_available() and (cou<500):
			answer=self.iterate(rdata)
			self.pass_time(0.01)

		self.pass_time(0.05) 
		#print "Received data -",rdata
		
		if not answer:
			sendcanstart=True
			return answer
			
		
		ack=False
		if (rdata[0]=="1"):
			if message:
				if (rdata[1]==message.split(self.field_separator)[0]):
					ack=True
					#print "acknowleded"
					
		#list([recdata.pop() for z in xrange(len(recdata))])
		#recdata.extend(rdata[1:])
		for i in range(10):
			if i+1 in range(len(rdata)):
				recdata[i]=rdata[1+i]
			else:
				recdata[i]=""
		
		
		print "received: cmd ",rdata[0], " Data: ",recdata , "  Answer integrity: ", (answer)and(ack) , " <<<< "
		sendcanstart=True
		return (answer)and(ack) # return true if there was no receiver problem and the answer is acknowledge




    def sendcommand(self,cmd, message, recdata):
		count=0
		while (not sendcanstart) and (count<50):
			time.sleep(0.1)
		if sendcanstart:
			self.sendcommand_task(cmd, message, recdata)
			return True
		else:
			print "time expired"
			return False	




    # Command handlers

    def _handle_report_version(self, major, minor):
        self.firmata_version = (major, minor)
        
    def _handle_report_firmware(self, *data):
        major = data[0]
        minor = data[1]
        self.firmware_version = (major, minor)
        self.firmware = two_byte_iter_to_str(data[2:])

"""
// ------------------ S E R I A L  M O N I T O R -----------------------------
// 
// Try typing these command messages in the serial monitor!
// 
// 4, Temp reqding
// 5; PH reqding
// 5,PH
// 5,PH
// 2;
// 6;
// 
// 

// 
"""


if __name__ == '__main__':
	
	"""
	to be acknowledge a message should include the command and a message to identyfy it "identifier" (example "temp"), 
	if arduino answer including the same identifier then the message is acknowledged (return true) command is "1"
	the data answer "recdata" is a vector. the [0] field is the identifier, from [1] start the received data
	"""
	
	board1 = slavecontroller()
	recdata=[]
	ack=False
	ack=board1.sendcommand("4","temp",recdata)

	board1.pass_time(1)
	#ack=board1.sendcommand("11","pulse:12:2000",recdata)
	#print  ack, "  ", recdata;
	ack=board1.sendcommand("5","PH",recdata)
	
	print "verify wrong propocol:"
	ack=board1.sendcommand("6","",recdata)


	ack=board1.sendcommand("4","Temp",recdata)


	board1.pass_time(1)
		
	for x in range(10):
		ack = board1.sendcommand("7","ECenable:10000",recdata) #enable for 10 sec
		ack=board1.sendcommand("4","temp",recdata)
		#board1.pass_time(0.1)
	


