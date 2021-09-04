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
        HWCONTROLLIST=["readinput/HC12","pulse/HC12","stoppulse/HC12","pinstate/HC12"]
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
            
        elif cmd==HWCONTROLLIST[2]:	# stoppulse
            return HC12_stoppulse(cmd, message, recdata)			
        
        elif cmd==HWCONTROLLIST[3]:	# pinstate
            return HC12_pin_level(cmd, message, recdata)

    else:
        returnmsg(recdata,cmd,"Command not found",0)
        return False
    return False






def powerPIN_start(REGID,CMD,address,pulsesecond,ignorepowerpincount=False): # powerpin will work only with same address and same topic/"powerpin number"
    if REGID!="":
        PowerPINlevel=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"level")
        #start power pin
        if PowerPINlevel<1: 
            PowerPINlevel==0
        if not ignorepowerpincount:
            statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"level",PowerPINlevel+1)			
            
        
        # complication below is necessary.
        timeZero=int(time.time())+pulsesecond
        Lasttimezero=statusdataDBmod.read_status_data(PowerPIN_Status,REGID,"timeZero")
        if Lasttimezero:
            if timeZero>Lasttimezero:
                waittime=1 # seconds
                statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"timeZero",timeZero)
                HC12_output(CMD, address,1)
                time.sleep(waittime)				
        else:
            statusdataDBmod.write_status_data(PowerPIN_Status,REGID,"timeZero",timeZero)

        
        if PowerPINlevel==0:
            time.sleep(0.2)			
    return True	

        
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
    
    HC12_output(PIN_CMD["STOP"], address, 1)
    
    endwaittime=0
    powerPIN_stop(POWERPIN_CMD,endwaittime,address)

    #print "pulse ended", time.ctime() , " PIN=", PINstr , " Logic=", logic , " Level=", level
    return True


def create_pulse_CMD_list(PIN,POWERPIN,title,pulsesecond):
    # This function created the right format for the command to send to the HC12
    # The CMD dictionary will have one ID indicating the Title and PIN, and 2 commands: start, stop

    Durationperiod=pulsesecond
    
    PINnum=toint(PIN,0)
    PINstr=""
    if not PINnum==0:
        PINstr=PIN 	
    # MQTT publish commands	
    MQTT_CMD={"ID":title+PINstr}
    CMD={"topic":title+"/StartPulse/"+PINstr,"value":str(Durationperiod)}
    CMD_list=[]	
    CMD_list.append(CMD)
    MQTT_CMD["START"]=CMD_list	
    
    CMD={"topic":title+"/StopPulse/"+PINstr,"value":"0"}	
    CMD_list=[]
    CMD_list.append(CMD)		
    MQTT_CMD["STOP"]=CMD_list
    
    
    MQTT_CMD_PWR={"ID":"","START":"","STOP":""}
    POWERPINstr=""	
    POWERPINnum=toint(POWERPIN,0)
    if not POWERPINnum==0:  # commands are filled only if the PWRPIN is a number
        POWERPINstr=POWERPIN
        
        waittime=0.2
        
        # MQTT publish commands	PWR
        ID=title+POWERPINstr
        MQTT_CMD_PWR={"ID":ID}
        CMD={"topic":title+"/StartPulse/"+POWERPINstr,"value":str(Durationperiod+waittime*2)}
        CMD_list=[]	
        CMD_list.append(CMD)
        MQTT_CMD_PWR["START"]=CMD_list	
        
        CMD={"topic":title+"/StopPulse/"+POWERPINstr,"value":"0"}	
        CMD_list=[]
        CMD_list.append(CMD)		
        MQTT_CMD_PWR["STOP"]=CMD_list

    return MQTT_CMD, MQTT_CMD_PWR


def HC12_pulse(cmd, message, recdata):
    successflag=0
    msgarray=message.split(":")
    messagelen=len(msgarray)	
    PIN=msgarray[1]

    testpulsetime=msgarray[2] # in seconds
    pulsesecond=int(testpulsetime)

    if pulsesecond<10:
        msg="HC-12 cannot handle pulses with duration less than 10sec"
        successflag=0
        returnmsg(recdata,cmd,msg,successflag)        
        return True
    
    POWERPIN=""	
    if messagelen>4:	
        POWERPIN=msgarray[4]	

        
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
        

    MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,pulsesecond)

    # start pulse activation logic

    REGID=MQTT_CMD["ID"]  # this is made by the string "topic"+"PIN"
    ignorepowerpincount=False
    # in case another timer is active on this TOPIC ID it means that the PIN is activated 
    PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
    if not PINthreadID==None:
        
        # pin already active
        if activationmode=="NOADD": # no action needed
            successflag=1
            returnmsg(recdata,cmd,PIN,successflag) 
            return True		
        
        PINthreadID.cancel() # cancel thread 

        ignorepowerpincount=True # do not add levels to the powerpin
    
    

    powerPIN_start(MQTT_CMD_PWR["ID"],MQTT_CMD_PWR["START"],address,pulsesecond,ignorepowerpincount)

    level=1
    statusdataDBmod.write_status_data(GPIO_data,REGID,"level",level)
    logger.info("Set PIN=%s to State=%s", REGID, str(level))
    print (REGID + " *********************************************** " , level)
    
    isok , msg = HC12_output(MQTT_CMD["START"],address, 2)  # try two times
    
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
    
    MQTT_CMD, MQTT_CMD_PWR = create_pulse_CMD_list(PIN,POWERPIN,title,0)
    
    REGID=MQTT_CMD["ID"]	
    PINthreadID=statusdataDBmod.read_status_data(GPIO_data,REGID,"threadID")
    if not PINthreadID==None:
        #print "cancel the Thread of PIN=",PIN
        PINthreadID.cancel()
        
    endpulse(MQTT_CMD, MQTT_CMD_PWR,address)	#this also put powerpin off		
    returnmsg(recdata,cmd,PIN,1) 
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


