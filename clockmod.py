from __future__ import print_function
import logging
import sys
import time
import os
from datetime import datetime,date,timedelta
#!/usr/bin/env python
from socket import AF_INET, SOCK_DGRAM
import socket
import struct
import clockdbmod

logger = logging.getLogger("hydrosys4."+__name__)

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

DATEFORMAT="%d/%m/%Y %H:%M:%S"
timezone=clockdbmod.gettimezone()
os.environ['TZ'] = timezone
time.tzset()
print("timezone set to ->", timezone)
#logger.info('Timezone Set to  = %s', timezone) # if this is enabled,for some reason the whole logging become empty


# ///////////////// --- END GLOBAL VARIABLES AND INIT------

def timediffinsec(timestr1, timestr2):
	try:
		datetime1=datetime.strptime(timestr1, DATEFORMAT)
		datetime2=datetime.strptime(timestr2, DATEFORMAT)	
	except:
		print("Time in wrong format, not able to make diffsec ")
		return 0	
	delta=datetime2-datetime1
	timediff=abs(delta.total_seconds())
	return timediff


def readsystemdatetime():
	return datetime.now().strftime(DATEFORMAT)

def getNTPTime(host = "pool.ntp.org"):
	port = 123
	buf = 1024
	address = (host,port)
	msg = '\x1b' + 47 * '\0'

	# reference time (in seconds since 1900-01-01 00:00:00)
	TIME1970 = 2208988800 # 1970-01-01 00:00:00

	# connect to server
	try:	
		client = socket.socket( AF_INET, SOCK_DGRAM)
		client.settimeout(2)
		client.sendto(msg.encode(), address)
		msg, address = client.recvfrom( buf )
	except socket.timeout as e:
		print("server timeout")
		return ""		
	except socket.error as e:
		print("connection error")
		return ""		
	
	if msg:
		t = struct.unpack( "!12I", msg )[10]
		t -= TIME1970
		#strvalue=time.ctime(t).replace("  "," ")
		try: 
			datetimevalue=datetime.utcfromtimestamp(t)
		except:
			return ""			
		strvalueUTC=datetimevalue.strftime(DATEFORMAT)
		strvalue=convertUTCtoLOC(strvalueUTC)
		return strvalue
	else:
		print("No valid data in server answer ")			
		return ""				

def getHWclock():
	#need to check how to do it
	print("not done")

		
def setHWclock(datetime_format):
	
	datetimeUTC=convertLOCtoUTC(datetime_format)
	print("Set HWclock datetime UTC ->" ,datetimeUTC)
	
	datetimetype=datetime.strptime(datetimeUTC, DATEFORMAT)

	newformat="%d %b %Y %H:%M:%S"
	date_str="\"" + datetimetype.strftime(newformat) + "\""	
	print("Set HW clock ->" , date_str)
	
	try:
		os.system('hwclock --set --date %s --localtime' % date_str)
		#time.sleep(1)
		#newdatetime=getHWclockUTC()
		#delta=newdatetime-datetimetype
		#timediff=abs(delta.total_seconds())
		#print "time difference ", timediff , " System date " ,newdatetime , " Set Date" , datetimetype
		#if timediff<60:
		#	return "- Hardware Clock Set -"
		#else:
		#	return " - ERROR: not able to set Hardware Clock -"
		return " - HardwareClock Set - "
	except:
		print("Not able to set Hardware Clock ")
		#logger.error('Not able to set Hardware Clock')
		return "ERROR: not able to set Hardware Clock"	
		
		
		
def setsystemclock(datetime_format):

	datetimeUTC=convertLOCtoUTC(datetime_format)
	print("Set System date to datetime UTC ->" ,datetimeUTC)

	datetimetype=datetime.strptime(datetimeUTC, DATEFORMAT)
	print("Set system clock ->", datetimetype)
	newformat="%d %b %Y %H:%M:%S"
	date_str="\"" + datetimetype.strftime(newformat) + "\""
	
	print("Datetime value format for date setting ", date_str)


	try:
		os.system('date --set %s -u' % date_str)
		time.sleep(1)
		newdatetime=datetime.utcnow()
		delta=newdatetime-datetimetype
		timediff=abs(delta.total_seconds())
		print("time difference ", timediff , " System date " ,newdatetime , " Set Date" , datetimetype)
		if timediff<60:
			return "- System Clock Set -"
		else:
			return " - ERROR: not able to set system Clock -"

	except:
		print("Not able to set system Clock ")
		#logger.error('Not able to set Hardware Clock')
		return "- ERROR: not able to set system Clock -"	

	
def settimezone(timezone):
	os.environ['TZ'] = timezone
	time.tzset()
	return ""

	
def deltadatetimetoUTC():
	timeUTC=time.gmtime()
	timelocal=time.localtime()
	newformat="%d %b %Y %H:%M:%S"
	timestrUTC = time.strftime(newformat, timeUTC)
	timestrLOC = time.strftime(newformat, timelocal)	

	datetimeUTC=datetime.strptime(timestrUTC,newformat)
	datetimeLOC=datetime.strptime(timestrLOC,newformat)	
	delta = datetimeLOC-datetimeUTC
	return delta

def convertLOCtoUTC(dtime_str):
	dtime=datetime.strptime(dtime_str, DATEFORMAT)
	delta=deltadatetimetoUTC()
	UTCdtime=dtime-delta
	UTCdtime_str=UTCdtime.strftime(DATEFORMAT)
	return UTCdtime_str

def convertUTCtoLOC(dtime_str):
	dtime=datetime.strptime(dtime_str, DATEFORMAT)
	delta=deltadatetimetoUTC()
	LOCdtime=dtime+delta
	LOCdtime_str=LOCdtime.strftime(DATEFORMAT)
	return LOCdtime_str

def convertLOCtoUTC_datetime(dtime):
	delta=deltadatetimetoUTC()
	UTCdtime=dtime-delta
	return UTCdtime

def convertUTCtoLOC_datetime(dtime):
	delta=deltadatetimetoUTC()
	LOCdtime=dtime+delta
	return LOCdtime


	
if __name__ == '__main__':
	# comment
	a=10

