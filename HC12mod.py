#!/usr/bin/env python3
 
import serial
import time
import RPi.GPIO as GPIO
import logging
from datetime import datetime,date,timedelta
import threading
import jsonFormUtils

logger = logging.getLogger("hydrosys4."+__name__)
 



class _SerialConnection:

    listenflag=True
    serialconn=None
    

    def __init__(self, port="/dev/serial0",timeout=1):
        self.lastSerRestart=datetime.utcnow() #- timedelta(days=2)
        self.createSerial()
        self.port=port
        self.timeout=timeout # timeout is in seconds
        self.serialok=False
        self.listenPauseFlag=False

    def createSerial(self):
        if not _SerialConnection.serialconn:
            try:
                _SerialConnection.serialconn=serial.Serial() # serial instance but not open the port.
            except Exception as e:
                print (e)
                logger.warning("Not able to connect to the Serial interface, try to enable it using raspi-config")
                print("Not able to connect to the Serial interface, try to enable it using raspi-config")

                    
    def closeSerialConn(self):
        if _SerialConnection.serialconn.is_open:
            # disable the thread using the serial
            _SerialConnection.listenflag=False
            time.sleep(0.4)
            _SerialConnection.listenflag=True            
            # close the Serial connection
            _SerialConnection.serialconn.close()
            print (" Close Serial ")
            time.sleep(0.1)


    def setserial(self,baudrate):
        if _SerialConnection.serialconn:
            self.baudrate=baudrate
            _SerialConnection.serialconn.baudrate=self.baudrate
            _SerialConnection.serialconn.port=self.port
            _SerialConnection.serialconn.timeout=self.timeout
            self.serialok=False
            try:
                self.closeSerialConn()
                _SerialConnection.serialconn.open()
                time.sleep(0.1)
                self.serialok=_SerialConnection.serialconn.is_open
            except Exception as e:
                print (e)
                
            if not self.serialok:
                logger.warning("Not able to set Serial interface, try to enable it using raspi-config")
                print("Not able to set the Serial interface, try to enable it using raspi-config")
            else:
                print("Serial OPEN and set to baudrate ", _SerialConnection.serialconn.baudrate, " provided " , baudrate)
                



    def listenSerial(self):
        if not _SerialConnection.serialconn:
            return
        print("Listening Serial Port")
        _SerialConnection.serialconn.flushInput()
        while _SerialConnection.listenflag:
            isok , received_data = self.readSerialBuffer()
            if isok and received_data:
                #print (received_data)
                self.received_data=received_data
            time.sleep(0.2)
    
    def listenasinch(self,callback=None):
        if not _SerialConnection.serialconn:
            return
        _SerialConnection.listenflag=False
        time.sleep(0.4)
        _SerialConnection.listenflag=True
        ListenthreadID=threading.Timer(1, self.listen, [callback])
        ListenthreadID.start()

    def listen(self,callback=None): # enable the callback function when data is received
        if not _SerialConnection.serialconn:
            return
        print("Listening Serial Port, Enabling callback")
        _SerialConnection.serialconn.flushInput()
        while _SerialConnection.listenflag:
            if not self.listenPauseFlag:
                isok , received_data = self.readSerialBuffer()
                if isok and received_data:
                    if callback: 
                        print(" PAUSE? -------------------------___>", self.listenPauseFlag)
                        callback(received_data)
            time.sleep(0.2)


    def restart(self):
        if not _SerialConnection.serialconn:
            return
        now=datetime.utcnow()
        deltatime=now-self.lastSerRestart
        if deltatime.total_seconds()> 86400: #one day
            logger.warning("Try to Restart Serial Connection %s", self.lastSerRestart.strftime("%Y-%m-%d %H:%M:%S"))
            print("Try to Restart Serial: last restart attempt: ", self.lastSerRestart.strftime("%Y-%m-%d %H:%M:%S"))
            self.lastSerRestart=now
            self.closeSerialConn()
            _SerialConnection.serialconn.open()
            time.sleep(1)

    def waitfordata(self,count):
        if not _SerialConnection.serialconn:
            return 
        # wait for data
        while (not _SerialConnection.serialconn.inWaiting())and(count>0):
            time.sleep(0.1)
            count=count-1

    def readSerialBuffer(self):
        if not _SerialConnection.serialconn:
            return 
        ser=_SerialConnection.serialconn
        received_data=bytearray()  # strig of bytes
        try:        
            count=20
            while (ser.inWaiting()>0)and(count>0):
                size = ser.inWaiting()
                try:
                    received_data.extend(ser.read(size))
                    #print (received_data , "---------------------------- COUNT-> ", count)
                    #print ("*******************+++ data in the buffer", received_data)
                except Exception as ex:
                    print(ex)
                    print("problem receiving from serial")
                time.sleep(0.1)  
                count=count-1
        except IOError:
            self.restart()
            return False, received_data
        return True, received_data

    def sendString(self,stringdata):
        if not _SerialConnection.serialconn:
            return 
        _SerialConnection.serialconn.write(bytes((stringdata), 'utf-8'))

    def sendBytes(self,bytesdata):
        if not _SerialConnection.serialconn:
            print("Serial Not Connected ")
            return 
        _SerialConnection.serialconn.write(bytesdata)


class HC12:

    def __init__(self, datadict={}):

        
        self.getATcommandlistFromFormData(datadict)
        # define the Set PIN
        self.SetPIN=4
        # start serial connection    
        self.ser=_SerialConnection() # create instance of serial class
        # Medium check 
        self.mediumOK=False
        self.mediumOK=self.VerifySerialATwithPIN() # this also eneble serial connection at the right baud rate.
        if self.mediumOK:
            print("HC-12 active check: OK")
            logger.info("HC-12 active check: OK")
            isok = self.setATcommands()

            if isok:
                print("AT Commands settong: OK")
                logger.info("AT Commands settong: OK")
            else:
                print("AT Commands settong: Problems detected")
                logger.warning("AT Commands setting: Problems detected")
        else:
            print("HC-12 not detected")
            logger.warning("HC-12 not detected")


    def ATcmdInfoList(self):
        ATcmdlist=["AT+RB", "AT+RC", "AT+RF" , "AT+RP", "AT+V"]
        return ATcmdlist

    def getATcommandlistFromFormData(self,datadict):
        self.ATcommandslist=[]
        # channel
        keyword="Channel"
        ATstr=datadict.get(keyword)
        if ATstr:
            while len(ATstr)<3:
                ATstr="0"+ATstr
            ATcmd="AT+C"+ATstr
            self.ATcommandslist.append(ATcmd)
        
        # Power
        keyword="Power"
        ATstr=datadict.get(keyword)
        if ATstr:
            ATcmd="AT+P"+ATstr
            self.ATcommandslist.append(ATcmd)

        # Power
        keyword="Tmode"
        ATstr=datadict.get(keyword)
        if ATstr:
            ATcmd="AT+"+ATstr
            self.ATcommandslist.append(ATcmd)

        # Sleep/disable
        keyword="Activate"
        ATstr=datadict.get(keyword)
        if ATstr=="Disabled":
            ATcmd="AT+SLEEP"
            self.ATcommandslist.append(ATcmd)

        #print(self.ATcommandslist , "*********************************************************")


    def setAT(self, datadict):
        self.getATcommandlistFromFormData(datadict)
        return self.setATcommands()


    def VerifySerialAT(self):
        isok=False
        #send first AT command just to check the HC-12 is answering
        print("Check if AT commands are working")
        cmd="AT\n"
        outok , received_data = self.sendReceiveATcmds(cmd)
        if outok:
            if b"ok" in received_data or b"OK" in received_data:
                isok=True
                print ("Check AT Successfull")
            else:
                #self.disableATpin() 
                #self.enableATpin()
                time.sleep(0.5)
        return isok

    def enableATpin(self):
        print (" Enable AT pin")
        # the HC-12 set pin should be put to LOW to enable AT commands
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.SetPIN, GPIO.OUT)        
        GPIO.output(self.SetPIN, GPIO.LOW) # set HC12 to AT mode
        self.ser.listenPauseFlag=True
        print(" Set Serial Listening PAUSE flag to TRUE")
        time.sleep(1)

    def disableATpin(self):
        print (" Disable AT pin")
        GPIO.output(self.SetPIN, GPIO.HIGH) # set HC12 to normal mode
        self.ser.listenPauseFlag=False 
        # pause the receiver based
        print(" Set Serial Listening PAUSE flag to FALSE")
        time.sleep(0.5)


    def VerifySerialATwithPIN(self):
        # list the requireb baudrate
        baudRateList=[1200,9600]
        # pause the receiver based
        self.enableATpin() 
        isok=False
        for baudrate in baudRateList:
           
            self.ser.setserial(baudrate=baudrate)

            if self.ser.serialok:
                inde=2
                isok=False
                while (inde>0)and(not isok):
                    isok=self.VerifySerialAT()            
                    inde=inde-1
                if isok:
                    break
            else:
                break

        self.disableATpin()


        
        return isok
 
    def sendReceiveATcmds(self,cmd):
        isok=False
        # empty the serial buffer

        self.ser.readSerialBuffer() 
        time.sleep(0.1)
        print("send AT command = ", cmd)
        self.ser.sendString(cmd)
        time.sleep(0.1)
        j=0
        received_data=b""   
        while (j<2):
            # wait for data
            self.ser.waitfordata(14)
            outok, received_data = self.ser.readSerialBuffer()   
            if outok:
                if received_data:
                    print("Received = " , received_data)
                    isok=True
                    break
                else:
                    # try to send again the comamand
                    print("re-send AT command = ", cmd)
                    self.ser.sendString(cmd)
            print(j, "inside loop Command =",cmd)
            j=j+1
        return isok , received_data

    def setATcommands(self):

        self.enableATpin()

        print ("AT commands list ",self.ATcommandslist)

        ATok=True  # if one of the AT command is not successful it return false
        if self.mediumOK:
            print ("Medium OK")
            # Execute the AT commmands, they will be made effective after the AT PIN is set batck
            for cmd in self.ATcommandslist:
                isok , received_data = self.sendReceiveATcmds(cmd)
                time.sleep(0.4)                
                if not isok:
                    print("Warning , No response for AT command = ", cmd)
                    ATok=False

             # set the UART baud rate to 1200 in teh HC12 side

            cmd="AT+B1200"
            isok , received_data = self.sendReceiveATcmds(cmd)
            time.sleep(0.4)
            if not isok:
                print("Warning , No response for AT command = ", cmd)
                ATok=False
            if self.ser.baudrate!= 1200:                
                # set the Baud rate to 1200 in raspberry side
                self.ser.setserial(1200)
                if not self.ser.serialok:
                    logger.error("Not able to reconnect to the serial interface")
                    return False
                time.sleep(0.4)
        else:
            ATok=False
                                   

        self.disableATpin()
        #restart the receiver
 
        return ATok

class dataBufferCl:

    def __init__(self):
        # datadict is a dictionary of dictionaries with nameID as index
        # stored values are the last value received, no history
        self.datadict={}

    def addLastData(self,protocoldatadict):
        subdatadict={}
        subdatadict["timestamp"]= datetime.utcnow()
        subdatadict["millisindex"]= protocoldatadict.get("millisindex")
        subdatadict["value"]= protocoldatadict.get("value")
        self.datadict[protocoldatadict.get("name")]=subdatadict
        #print(self.datadict)

    def GetEntityData(self, nameID):
        return self.datadict.get(nameID)

class NetworkProtocol:
    # this class defined a simple protocol which given media will provide:
    #  1) Encription
    #  2) ACK/NACK
    #  3) N transmittes to 1 receiver configuration (same media channel)
    #  4) Haloa style collision handling for multiple recived signals (most of this implementation is on the transmitter side
    #  5) data buffer with the latest messages divided per Entity

    def __init__(self, dataBuffer, dataManagement):
        self.dataManagement=dataManagement
        self.datadict=dataManagement.readDataFile()
        self.dataBuffer=dataBuffer 
        self.key=self.datadict.get("ChiperKey")  
        self.mediumconnected=False
        self.ackDict={}
        self.sendCommandBusy=False


    def initRadio(self):
        # start HC12 setting         
        self.medium = HC12(self.datadict)
        self.mediumconnected=self.medium.mediumOK
        # start reading the serial
        if self.mediumconnected:
            # the medium seems ok
            self.setmeduimcomm()


    def saveDataFileAndApply(self,datadict):
        if datadict:
            self.datadict=datadict
            self.dataManagement.saveDataFile(datadict)
            self.key=self.datadict.get("ChiperKey")
            if self.mediumconnected:
                return self.medium.setAT(self.datadict)
        return False       

    def gotdata(self,received_data=""):
        print("hey I got data ", received_data)
        # decript data
        databytes=self.dechiper(received_data, self.key)
        datastring=""
        try:
            datastring=databytes.decode('UTF-8')
        except:
            print("Not able to decode the bytes in UTF-8")
            logger.warning("Not able to decode the bytes in UTF-8")
        #print("Decipher ", datastring)
        # when using the lowbitrate long distance mode, only 60 bytes at once can be transmitted. for this reason, Json is not used due to too much overhead
        datadict=self.extracNameandValue(datastring)
        #print (datadict)
        
        if datadict:
            # received message can be a Sensor reading, or an ack sent in response to a command
            # if this is an ack, then the "value" of the datadict should be "OK"
            if datadict.get("value","")=="OK":
                # this is an ack
                # save the ACK in ack list
                # datadict={"name":datalist[0],"millisindex":datalist[1],"value":datalist[2]}
                uniString=datadict.get("name","")+datadict.get("millisindex","")
                self.ackDict[uniString]="OK"

            else:
                # this is a message and requires an ACK

                # confirm the message has been correctly received
                # send back message with confirmation
                self.sendAck(self.medium.ser,datadict)
                self.dataBuffer.addLastData(datadict)


    def setmeduimcomm(self):
        self.medium.ser.listenasinch(self.gotdata)

    def dechiper(self, data, key):
        # returns plain text by repeatedly xoring it with key
        if key:
            pt = data
            keybyte= bytes(key, 'utf-8')
            len_key = len(key)
            encoded = []
            
            for i in range(0, len(pt)):
                encoded.append(pt[i] ^ keybyte[i % len_key])
            return bytes(encoded)
        return data


    def extracNameandValue(self, datastr):
        # the formant {nameID:data:millisindex:} is used.

        datadict={}
        if datastr=="":
            return datadict

        print ("received string after ciphering ", datastr)
        # search the {} and remove them
        init = datastr.find("{")
        end = datastr.find("}")
        if (init>=0) and (end>=0):
            datastr=datastr[init+1:end]
        else:
            print("data string not valid not found begin and end")
            return datadict
        datalist=[]
        datalist=datastr.split(":")
        if len(datalist)>2:
            datadict={"name":datalist[0],"millisindex":datalist[1],"value":datalist[2]}
        else:
            print("data string not valid")
        return datadict

    def sendAck(self, ser, datadict):
        # the {nameID:data:millisindex:} is used.
        datastr=bytes("{"+datadict.get("name")+":"+datadict.get("millisindex")+":OK:}", 'utf-8')
        # chiper
        print("Send ACK " , datastr)
        dataByteschip=self.dechiper(datastr, self.key)
        ser.sendBytes(dataByteschip)
        return datadict

    def createMillisTimestamps(self,strlenght):
        millis= round(time.time() * 1000)
        millisstr=str(millis)
        start=0
        if len(millisstr)>strlenght:
            start=len(millisstr)-strlenght
        return millisstr[start:]




    def sendCommand(self, topic, value , retry):
        # this function sends a command to be transmitted over the HC-12 and waits the ack
        # if ACK correct then return True otherwise False
        waitinde=60
        while (self.sendCommandBusy) and (waitinde>0): # avoid sending other command if the previous is not finished
            time.sleep(0.1)
            waitinde=waitinde-1
        if self.sendCommandBusy:
            return False, "HC-12 busy"

        self.sendCommandBusy=True

        returnvals = False , "HC-12 not detected"
        # check if the medium is connected
        if self.mediumconnected:


            # millisindex is a value to univoquely identify the sent message, and is the number of milliseconds
            millisindex=self.createMillisTimestamps(6)
            # prepare the string
            datastr=bytes("{"+topic+":"+millisindex+":"+value+":}", 'utf-8')
            print("Send HC-12 command " , datastr)
            dataByteschip=self.dechiper(datastr, self.key) # in this case it chipers

            # manage the retry 
            inde=0
            while (not returnvals[0]) and (inde<retry):
                print("Transmiting retry " , inde)               
                inde=inde+1
                # transmit the string

                self.medium.ser.sendBytes(dataByteschip)

                print("Waiting ACK ")
                # now wait for possible ACK from the remote device

                uniString=topic+millisindex

                waitinde=90
                while (not self.ackDict.get(uniString,"")=="OK")and(waitinde>0):
                    time.sleep(0.1)
                    waitinde=waitinde-1
                    print("Waiting ACK " , waitinde)
                
                if self.ackDict.get(uniString,"")=="OK":
                    returnvals = True, "ACK OK"
                else:
                    returnvals = False, "No ACK received"

        self.sendCommandBusy=False
        print(" Message delivered to HC12 -------> ", returnvals)
        return returnvals



    def waitForAck(self, uniString):
        waitinde=90
        while (not self.ackDict.get(uniString,"")=="OK")and(waitinde>0):
            time.sleep(0.1)
            waitinde=waitinde-1
            print("Waiting ACK " , waitinde)
        
        if self.ackDict.get(uniString,"")=="OK":
            returnvals = True, "ACK OK"
            self.ackDict.pop(uniString, None)
        else:
            returnvals = False, "No ACK received"





if __name__ != '__main__':

    # single instantiation


    _dataBufferCl=dataBufferCl()
    _FormAndSettingManagement=jsonFormUtils.utils('HC12form')

    def GetEntityLastData(name):
        return _dataBufferCl.GetEntityData(name)


    HC12radionet=NetworkProtocol(_dataBufferCl,_FormAndSettingManagement)

    def initHC12():
        global HC12radionet
        logger.info("Starting HC-12")
        print("Starting HC-12")
        HC12radionet.initRadio()
	
if __name__ == '__main__':
    

    HC12inst=HC12()
    time.sleep(3)

    SetPIN=4
    print ("pause standard reading AT started, Set PIN Low (AT enabled) ---------------------------------------------------" )       
    # the HC-12 set pin should be put to LOW to enable AT commands
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SetPIN, GPIO.OUT, initial=GPIO.LOW) # set pin 7 (GPIO4) to OUTPUT (SET pin of HC12)
    GPIO.output(SetPIN, GPIO.LOW) # set HC12 to AT mode

    time.sleep(1)
    HC12inst.sendReceiveATcmds("AT+DEFAULT") 
      
    time.sleep(0.3)
    HC12inst.sendReceiveATcmds("AT+RB")                                

    time.sleep(0.3)
    HC12inst.sendReceiveATcmds("AT+V")

    time.sleep(0.3)
    HC12inst.sendReceiveATcmds("AT+RB")   

    GPIO.output(SetPIN, GPIO.HIGH) # set HC12 to normal mode
    time.sleep(0.5)
    #restart the receiver 
    print ("remove pause, Set PIN High (AT disabled)  ---------------------------------------------------" )  



    """
    AT+Cxxx: Change wireless communication channel, selectable from 001 to 127 (for wireless channels exceeding 100, the communication distance cannot be guaranteed). The default value for the wireless channel is 001, with a working frequency of 433.4MHz. The channel stepping is 400KHz, and the working frequency of channel 

    AT+FUx:  Change the serial port transparent transmission mode of the module. Four modes are available, namely FU1, FU2, FU3, and FU4. Only when the serial port speed, channel, and transparent transmission mode of two modules is set to be the same,can normal wireless communications occur. For more details, please see the abovesection “Wireless Serial Port Transparent Transmission”.
    FU4 mode is useful for maximum range, up to 1.8km. Only a single baud rate of 1200bps is supported, with the in the air baud rate reduced to 500bps for improved communication distance. This mode can only be used for small amounts ofdata (each packet should be 60 bytes or less), and the time interval between sending packets must not be too short (preferably no less than 2 seconds) in order to prevent loss of data.

    AT+Px:   Set the transmitting power of the module, with x selectable from 1 to 8, default 8.
    
    """ 


