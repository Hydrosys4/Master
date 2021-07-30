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

def initHC12():
    HC12mod.initHC12()
    global ISRPI
    global HWCONTROLLIST
    ISRPI=HC12mod.HC12radionet.mediumconnected
    if ISRPI:
        HWCONTROLLIST=["readinput/HC12"]
    else:
        HWCONTROLLIST=[]





# IMPORTANT *****************************************************************************
# the following pins should not be set as output otherwise they lose the Serial configuration
# PIN=14 TX PIN=15 RX


# status variables

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


def execute_task(cmd, message, recdata):

    print(" WELLCOME TO THE HC12 CONTROL ")
    print("MESSAGE " + message)
    
    if cmd in HWCONTROLLIST:
        

        if cmd==HWCONTROLLIST[0]:	# readinput
            return readinput_HC12(cmd, message, recdata)
            

    else:
        print("Command not found")
        recdata.append(cmd)
        recdata.append("e")
        recdata.append(0)
        return False;
    return False;





def readinput_HC12(cmd, message, recdata):
    
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
        print("Error, HC12 reading no topic defined", Topic)
        # address not correct
        logger.error("HC12 reading no topic defined %s", Topic)
        recdata.append(cmd)
        recdata.append("Topic not configured ")
        recdata.append(0)
        return True
    
    # Get the last value pubished for this topic. 
    reading=0

    datadict=HC12mod.GetEntityLastData(Topic)
    if datadict:
        result=datadict.get("value")
        timestamp=datadict.get("timestamp")
        isok=True
    else:
        print("Error, HC12 reading no Reading for the topic ", Topic)
        # address not correct
        logger.error("HC12 reading no Reading for the topic %s", Topic)
        recdata.append(cmd)
        recdata.append("Error, HC12 no Reading for the topic " + Topic)
        recdata.append(0)
        return True
    
    deltaseconds=(datetime.utcnow()-timestamp).total_seconds()
    
    print(" deltaseconds  " , deltaseconds)
    
    if deltaseconds<0:
        # reading happenend in the future .... somethign wrong, issue error
        print("Error, reading in the future ")
        # address not correct
        logger.error("reading in the future")
        recdata.append(cmd)
        recdata.append("Error, reading in the future ...")
        recdata.append(0)
        return True		
    

    # extract value 
    print ("HC12 sensor ", isok, "  " , result)	
    
    
    if Timeperiodsec>0:
        if ((deltaseconds+1)>Timeperiodsec):
            # value not valid because too old, replace with empty string
            result=""	

    
    if isok:
        if result=="":
            print("Error, no updates from the sensor since ", str(deltaseconds) , " (sec)")
            # address not correct
            logger.error(" no updates from the sensor %s (sec)", str(deltaseconds))
            recdata.append(cmd)
            recdata.append("Error, no updates from the sensor")
            recdata.append(0)
            return True

        else:
            reading=result
            successflag=1	
            logger.info("HC12 input reading: %s", reading)
            print("HC12 input reading ", reading)
            recdata.append(cmd)
            recdata.append(reading)
            recdata.append(successflag)
            statusmsg="HC12 last update " + '{:.1f}'.format(deltaseconds) + " seconds "
            recdata.append(statusmsg)
            return True
        

    print("Error, HC12 reading")
    logger.error("HC12 reading")
    recdata.append(cmd)
    recdata.append("Generic Error, MQTT reading")
    recdata.append(0)
        
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


