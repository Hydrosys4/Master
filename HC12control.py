# -*- coding: utf-8 -*-

import time
from datetime import datetime,date,timedelta
import threading
import logging
import statusdataDBmod
import json
import HC12mod

logger = logging.getLogger("hydrosys4."+__name__)

ISRPI=False
HWCONTROLLIST=[]
pinlist=["14","15","4"]
# IMPORTANT *****************************************************************************
# the following pins should not be set as output otherwise they lose the Serial configuration
# PIN=14 TX PIN=15 RX



def initHC12():
    HC12mod.initHC12()
    global ISRPI
    global HWCONTROLLIST
    ISRPI=HC12mod.HC12radionet.mediumconnected
    if ISRPI:
        HWCONTROLLIST=["readinput/HC12","pulse/HC12","stoppulse/HC12","pinstate/HC12", "switchoff/HC12" , "switchon/HC12" ]
    else:
        HWCONTROLLIST=[]


# status variables
GPIO_data={}
GPIO_data["default"]={"level":0, "state":None, "threadID":None}

PowerPIN_Status={}
PowerPIN_Status["default"]={"level":0, "state":"off", "pinstate":None, "timeZero":0}




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

    print(" WELLCOME TO THE HC12 CONTROL ")
    print("MESSAGE " + message)
    
    if cmd in HWCONTROLLIST:
        

        if cmd==HWCONTROLLIST[0]:	# readinput
            return HC12_readinput(cmd, message, recdata)
            
        if cmd==HWCONTROLLIST[1]:	# pulse
            return HC12_pulse(cmd, message, recdata)
            
        if cmd==HWCONTROLLIST[2]:	# stoppulse
            return HC12_stoppulse(cmd, message, recdata)			
        
        if cmd==HWCONTROLLIST[3]:	# pinstate
            return HC12_pin_level(cmd, message, recdata)

        if cmd==HWCONTROLLIST[4]:	# pinstate
            return HC12_switchoff(cmd, message, recdata)

        if cmd==HWCONTROLLIST[5]:	# pinstate
            return HC12_switchon(cmd, message, recdata)

    else:
        returnmsg(recdata,cmd,"Command not found",0)
        return False
    return False






def powerPIN_status(REGID,pulsesecond,pwr_level_increase=1): # powerpin will work only with same address and same topic/"powerpin number"
    power_pulse_needed=False
    pulsesecond=toint(pulsesecond,0)

    if REGID!="":
        PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"level")
        #start power pin
        if PowerPINlevel<1: 
            PowerPINlevel==0
        statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"level",PowerPINlevel+pwr_level_increase)			
            
        
        # complication below is necessary. to increase the duration incase there are other pin active with longer durations
        timeZero=int(time.time())+pulsesecond
        Lasttimezero=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"timeZero")
        if not Lasttimezero:
            Lasttimezero=0

        if timeZero>Lasttimezero:
            waittime=1 # seconds
            statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"timeZero",timeZero)
            power_pulse_needed=True
            time.sleep(waittime)				
		
    return power_pulse_needed	

        
def powerPIN_stop(CMD_PWR,waittime,address):
    REGID=CMD_PWR["ID"]
    if REGID!="":
        PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"level")
        statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"level",PowerPINlevel-1)

        #stop power pin	if level less or equal to zero
        if (PowerPINlevel-1)<=0:

            time.sleep(waittime)
            
            HC12_output(CMD_PWR["STOP"], address,3)


    return True	



def HC12_output(CMD_LIST,address, retry): 

    for CMD in CMD_LIST: # in case of HC-12 list is made always by one command, otherwise we have timing problems
        topic=CMD["topic"]
        value=CMD["value"]
        print("HC12-CMD string: " + "   " + topic + "   "  + value)
        # topic is the concatemation of 3 strings: title+/<action>/+PIN
        # where <action> can be /StartPulse/ or /StopPulse/
        # value is the duration in seconds
        # Key is the title which is the same as the chiperkey 
        isok, msg = HC12mod.HC12radionet.sendCommand(topic, value, retry)
        #clientobj.publish(topic=topic, payload=str(payload), qos=2)
        time.sleep(0.1)
    
    return isok, msg


def endpulse(PIN_CMD,POWERPIN_CMD,address):
    REGID=PIN_CMD["ID"]
    statusdataDBmod.write_status_data(GPIO_data,REGID,"threadID",None)
    
    isok, msg = HC12_output(PIN_CMD["STOP"], address, 1)
    
    endwaittime=0
    powerPIN_stop(POWERPIN_CMD,endwaittime,address)

    #print "pulse ended", time.ctime() , " PIN=", PINstr , " Logic=", logic , " Level=", level
    return isok, msg 


def create_pulse_CMD_list(PIN,POWERPIN,title,pulsevalue):
    # This function created the right format for the command to send to the HC12
    # The CMD dictionary will have one ID indicating the Title and PIN, and 2 commands: start, stop

    PINstr=PIN+"+"

    # HC-12  commands	
    # "SP" : start pulse, followed by pin and duration in integer. To start pulses on multiple pins within the same command,
    # "ON" : switch ON , followed by pin 
    # "OFF" : switch OFF , follower by PIN
    # it is possbile to concat the PIN and Duration values using "+"  PIN = PIN1+PIN2: .... and the duration = duration1+duration2:...
    # after last PIN or Duration the "+" symbolo should be added, even for single use 
    # example string "topic:Relay1/SP/5+" or "topic:Relay1/SP/5+6+7+"

    MQTT_CMD_PWR={"ID":"","START":"","STOP":""}


    pulsesecond=pulsevalue+"+"
    pwrpulse=pulsesecond

    if pulsevalue in ["ON", "OFF"]:
        pwrpulse="0+"
        pulsesecond="0+"

    # check if power pin is valid
    PINpowstr=POWERPIN
    if not POWERPIN=="":
        PINpowstr=POWERPIN+"+"
        ID=title+POWERPIN
        MQTT_CMD_PWR["ID"]=ID
    else:
        pwrpulse=""



    MQTT_CMD={"ID":title+PINstr}
    CMD={"topic":title+"/SP/"+PINstr,"value":pulsesecond}
    CMD_list=[]	
    CMD_list.append(CMD)
    MQTT_CMD["START"]=CMD_list	

    CMD={"topic":title+"/ON/"+PINstr,"value":"0+"}	
    CMD_list=[]
    CMD_list.append(CMD)		
    MQTT_CMD["ON"]=CMD_list

    CMD={"topic":title+"/OFF/"+PINstr,"value":"0+"}	
    CMD_list=[]
    CMD_list.append(CMD)		
    MQTT_CMD["STOP"]=CMD_list

    CMD={"topic":title+"/SP/"+PINstr+PINpowstr,"value":pulsesecond+pwrpulse}
    CMD_list=[]
    CMD_list.append(CMD)		
    MQTT_CMD_PWR["START"]=CMD_list

    CMD={"topic":title+"/OFF/"+PINpowstr,"value":"0+"}	
    CMD_list=[]
    CMD_list.append(CMD)		
    MQTT_CMD_PWR["STOP"]=CMD_list


    return MQTT_CMD , MQTT_CMD_PWR


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


def HC12_pulse(cmd, message, recdata):
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

    if (pulsesecond<10)and(not pulsetime_str=="ON"):
        msg="HC-12 cannot handle pulses with duration less than 10sec"
        successflag=0
        returnmsg(recdata,cmd,msg,successflag)        
        return True
    
    POWERPIN=""	
    if messagelen>4:	
        POWERPIN=msgarray[4]
        if not toint(POWERPIN,0):
            POWERPIN=""	

        
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
        msg = "No topic specified, please insert it in the Title field"
        successflag=0
        returnmsg(recdata,cmd,msg,successflag) 
        return True
        

    MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,pulsetime_str) # in this case MQTT_CMD_PWR[Start] includes both pwr and normal pin

    REGID=MQTT_CMD["ID"]  # this is made by the string "topic"+"PIN"
    pwr_level_increase=1 # determine how many levels to add to the power pin (power pin level are used to OFF the power when level is Zero or below)
    # in case another timer is active on this TOPIC ID it means that the PIN is activated 
    PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
    if not PINthreadID==None:
        # pin already active
        if activationmode=="NOADD": # no action needed
            successflag=1
            returnmsg(recdata,cmd,PIN,successflag) 
            return True		
        PINthreadID.cancel() # cancel thread 
        pwr_level_increase=pwr_level_increase-1 # do not add levels to the powerpin, pin is already active and is already counted
    
    level=1
    statusdataDBmod.write_status_data(GPIO_data,REGID,"level",level)
    logger.info("Set PIN=%s to State=%s", REGID, str(level))
    print (REGID + " *********************************************** " , level)
    
    if pulsetime_str=="ON":
        pwr_level_increase=pwr_level_increase-1 # do not add levels to the powerpin


    need_power_pulse=powerPIN_status(MQTT_CMD_PWR["ID"],pulsesecond,pwr_level_increase)
    print("need_power_pulse " , need_power_pulse)
    if (not pulsetime_str=="ON")and(need_power_pulse): # exclude powerpin functiopn in case of ON
        isok , msg = HC12_output(MQTT_CMD_PWR["START"],address, 2)  # try two times # starts both the PIN and Powerpin
    else:
        if pulsetime_str=="ON":
            isok , msg = HC12_output(MQTT_CMD["ON"],address, 2)  # try two times # starts the PIN 
        else:
            isok , msg = HC12_output(MQTT_CMD["START"],address, 2)  # try two times # starts the PIN 
        
    if not pulsetime_str=="ON": # exclude powerpin functiopn in case of ON
        NewPINthreadID=threading.Timer(pulsesecond, endpulse, [MQTT_CMD, MQTT_CMD_PWR, address])
        NewPINthreadID.start()
        statusdataDBmod.write_status_data(GPIO_data,REGID,"threadID",NewPINthreadID)

    if isok:
        successflag=1
        returnmsg(recdata,cmd,PIN,successflag) 
    else:
        successflag=0
        returnmsg(recdata,cmd,msg,successflag) 

    return True	




def HC12_stoppulse(cmd, message, recdata):   # when ON send MQTT message with the duration in seconds of the activation, and when OFF send zero.
    print(" Don't stop me now ")
    
    msgarray=message.split(":")
    messagelen=len(msgarray)
    PIN=msgarray[1]
    
    logic="pos"
    if messagelen>3:
        logic=msgarray[3]
    
    POWERPIN=""
    if messagelen>4:	
        POWERPIN=msgarray[4]
        
    
    address=""	# this is the MQTT client ID
    if messagelen>7:	
        address=msgarray[7]

    
    title=""
    if messagelen>8:	
        title=msgarray[8]	
    
    if title=="":
        msg="No topic specified"
        successflag=0
        returnmsg(recdata,cmd,msg,successflag) 
        return True
    
    MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,"")
    
    REGID=MQTT_CMD["ID"]	
    PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
    if not PINthreadID==None:
        #print "cancel the Thread of PIN=",PIN
        PINthreadID.cancel()
        
    endpulse(MQTT_CMD, MQTT_CMD_PWR,address)	#this also put powerpin off		
    returnmsg(recdata,cmd,PIN,1) 
    return True	



def HC12_switchon(cmd, message, recdata):
    successflag=0
    msgarray=message.split(":")
    messagelen=len(msgarray)	
    PIN=msgarray[1]

    onoffcmd=msgarray[2]
    
    POWERPIN=""	
    if messagelen>4:	
        POWERPIN=msgarray[4]
        if not toint(POWERPIN,0):
            POWERPIN=""	

        
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
        msg = "No topic specified, please insert it in the Title field"
        successflag=0
        returnmsg(recdata,cmd,msg,successflag) 
        return True
        

    MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,onoffcmd) # in this case MQTT_CMD_PWR[Start] includes both pwr and normal pin

    REGID=MQTT_CMD["ID"]  # this is made by the string "topic"+"PIN"
 
    # in case another timer is active on this TOPIC ID it means that the PIN is activated 
    PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
    if not PINthreadID==None:
        # pin already active
        if activationmode=="NOADD": # no action needed
            successflag=1
            returnmsg(recdata,cmd,PIN,successflag) 
            return True		
        PINthreadID.cancel() # cancel thread 
  
    level=1
    statusdataDBmod.write_status_data(GPIO_data,REGID,"level",level)
    logger.info("Set PIN=%s to State=%s", REGID, str(level))
    print (REGID + " *********************************************** " , level)


    isok , msg = HC12_output(MQTT_CMD["ON"],address, 2)  # try two times # starts the PIN 
      
    if isok:
        successflag=1
        returnmsg(recdata,cmd,PIN,successflag) 

    else:
        successflag=0
        returnmsg(recdata,cmd,msg,successflag) 
  
    return True	




def HC12_switchoff(cmd, message, recdata):  
    print(" Switch OFF ")
    
    msgarray=message.split(":")
    messagelen=len(msgarray)
    PIN=msgarray[1]
    
    logic="pos"
    if messagelen>3:
        logic=msgarray[3]
    
    POWERPIN=""
    if messagelen>4:	
        POWERPIN=msgarray[4]
        
    
    address=""	# this is the MQTT client ID
    if messagelen>7:	
        address=msgarray[7]

    
    title=""
    if messagelen>8:	
        title=msgarray[8]	
    
    if title=="":
        msg="No topic specified"
        successflag=0
        returnmsg(recdata,cmd,msg,successflag) 
        return True
    
    MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,"")
    
    REGID=MQTT_CMD["ID"]	
    PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
    if not PINthreadID==None:
        #print "cancel the Thread of PIN=",PIN
        PINthreadID.cancel()
        
    isok, msg = endpulse(MQTT_CMD, MQTT_CMD_PWR,address)	#this also put powerpin off		
    if isok:
        returnmsg(recdata,cmd,PIN,1) 
    else:
        returnmsg(recdata,cmd,msg,0) 
    return True	


def HC12_pin_level(cmd, message, recdata):
    msgarray=message.split(":")
    PIN=msgarray[1]
    PINlevel=statusdataDBmod.read_status_data(GPIO_data,PIN,"level")
    if PINlevel is not None:
        returnmsg(recdata,cmd,str(PINlevel),1) 
        return True
    else:
        msg="Not found"
        returnmsg(recdata,cmd,msg,0) 
        return True	


def HC12_readinput(cmd, message, recdata):
    
    print("HC12 inputs ..............................")
    
    # This provides the latest reading of the device, the reading is passive, it means that the system is not sendig command to get the reading , 
    # it just record the latest value send by the sensor
    


    msgarray=message.split(":")

    PIN_str=""
    if len(msgarray)>1:
        PIN_str=msgarray[1]	


    measureUnit=""
    if len(msgarray)>4:
        measureUnit=msgarray[4]

    SensorAddress=""
    if len(msgarray)>6:
        SensorAddress=msgarray[6]	

    PIN2_str=""
    if len(msgarray)>7:
        PIN2_str=msgarray[7]	

    Topic=""
    if len(msgarray)>8:
        Topic=msgarray[8]

    Timeperiodstr=""
    if len(msgarray)>9:
        Timeperiodstr=msgarray[9]
    Timeperiodsec=tonumber(Timeperiodstr,0) # zero is a special case , never expire

    print(" Timeperiodsec  " , msgarray[9], "   "  , Timeperiodsec)

    PIN=toint(PIN_str,-1)
    PIN2=toint(PIN2_str,-1)



    if (Topic==""):
        msg = "Error, HC12 reading no topic defined" + Topic
        returnmsg(recdata,cmd,msg,0) 
        return True
    
    # Get the last value pubished for this topic. 
    reading=0

    datadict=HC12mod.GetEntityLastData(Topic)
    if datadict:
        result=datadict.get("value")
        timestamp=datadict.get("timestamp")
        isok=True
    else:
        msg= "Error, HC12 reading no Reading for the topic" + Topic
        returnmsg(recdata,cmd,msg,0) 
        return True
    
    deltaseconds=(datetime.utcnow()-timestamp).total_seconds()
    
    print(" deltaseconds  " , deltaseconds)
    
    if deltaseconds<0:
        # reading happenend in the future .... somethign wrong, issue error
        msg="Error, reading in the future "
        returnmsg(recdata,cmd,msg,0) 
        return True		
    

    # extract value 
    print ("HC12 sensor ", isok, "  " , result)	
    
    
    if Timeperiodsec>0:
        if ((deltaseconds+1)>Timeperiodsec):
            # value not valid because too old, replace with empty string
            result=""	

    
    if isok:
        if result=="":
            msg = "Error, no updates from the sensor since " + str(deltaseconds) + " (sec)"
            returnmsg(recdata,cmd,msg,0) 
            return True

        else:
            reading=result
            successflag=1	
            logger.info("HC12 input reading: %s", reading)
            print("HC12 input reading ", reading)
            returnmsg(recdata,cmd,reading,successflag)             
            statusmsg="HC12 last update " + '{:.1f}'.format(deltaseconds) + " seconds "
            recdata.append(statusmsg)
            return True
        

    msg="Error, HC12 reading"
    returnmsg(recdata,cmd,msg,0) 
        
    return True


def sendcommand(cmd, message, recdata):
    # as future upgrade this function might be run asincronously using "import threading"

    if ISRPI:
        ack=execute_task(cmd, message, recdata)
    else:
        print(" Client to support HC12 not installed")
    return ack


if __name__ == '__main__':
    
    """
    to be acknowledge a message should include the command and a message to identyfy it "identifier" (example "temp"), 
    if arduino answer including the same identifier then the message is acknowledged (return true) command is "1"
    the data answer "recdata" is a vector. the [0] field is the identifier, from [1] start the received data
    """


