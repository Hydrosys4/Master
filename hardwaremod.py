# -*- coding: utf-8 -*-
"""
selected plan utility
"""
import shutil
import logging
import os
import os.path
import sys
import string
import random
from datetime import datetime,date,timedelta
import time
import filestoragemod
import plandbmod
import HWcontrol
import photomod
import cameradbmod
import struct
import imghdr


# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////


global DATABASEPATH
DATABASEPATH="database"
global HWDATAFILENAME
HWDATAFILENAME="hwdata.txt"
global DEFHWDATAFILENAME
DEFHWDATAFILENAME="default/defhwdata.txt"

logger = logging.getLogger("hydrosys4."+__name__)
print "logger name ", __name__

# ///////////////// -- Hawrware data structure Setting --  ///////////////////////////////
#important this data is used almost everywhere

HWdataRECORDKEY=[]
HWdataKEYWORDS={}

# HW_INFO group includes info for the UI and identification of the item
HW_INFO_IOTYPE="IOtype" # info group, needed, specify if input or output 
HW_INFO_NAME="name" # info group , mandatory, identifier of the item  (shown in the UI)
HW_INFO_MEASUREUNIT="unit"  # info group , mandatory, measurement unit of info parameter
HW_INFO_MEASURE="measure"  # info group , mandatory, measurement type of info parameter

# HW_CTRL group includes info hardware to speak with HWcontrol module
HW_CTRL_CMD="controllercmd" # HW control group , mandatory, command sent to the HWControl section to specify the function to select -> HW
HW_CTRL_PIN="pin" # HW control  group ,optional, specify the PIN board for the HWControl if needed -> gpiopin
HW_CTRL_ADCCH="ADCchannel" # HW control  group , optional, specify the arg1 board for the HWControl if needed -> "ADCchannel"
HW_CTRL_PWRPIN="powerpin"  # HW control  group , optional, specify PIN that is set ON before starting tasks relevant to ADC convert, Actuator pulse, then is set OFF when the task is finished -> "ADCpowerpin"
HW_CTRL_LOGIC="logic"  # HW control  group , optional, in case the relay works in negative logic
#"settingaction", # HW control  group , use the controllercmd instead -> to be removed
HW_CTRL_MAILADDR="mailaddress" # HW control  group , optional, specify this info for the HWControl if needed -> mailaddress
HW_CTRL_MAILTITLE="mailtitle" # HW control  group , optional, specify this info for the HWControl if needed (mail title) -> "mailtitle"

#servo
HW_CTRL_FREQ="frequency" # HW control  group , optional, working frequency of the servo
HW_CTRL_MIN="min"  # HW control  group , optional, minimum of the duty cycle
HW_CTRL_MAX="max"  # HW control  group , optional, maximum of the duty cycle


HW_FUNC_USEDFOR="usefor" # function group , optional, description of main usage of the item and the actions associated with the plan "selectedplanmod"
HW_FUNC_SCHEDTYPE="schedulingtype" # function group , optional, between "oneshot" and "periodic" 
HW_FUNC_TIME="time"  #function group , optional, description of time or interval to activate the item depending on the "schedulingtype" item, in case of interval information the minutes are used for the period, seconds are used for start offset

USAGELIST=["sensorquery", "watercontrol", "fertilizercontrol", "lightcontrol", "temperaturecontrol", "humiditycontrol", "photocontrol", "mailcontrol", "powercontrol", "N/A"]
MEASURELIST=["Temperature", "Humidity" , "Light" , "Pressure" , "Time", "Quantity", "Moisture","Percentage"]
MEASUREUNITLIST=["C", "%" , "Lum" , "hPa" , "Sec", "Pcs", "Volt"]


HWdataKEYWORDS[HW_INFO_IOTYPE]=["input"  , "output" ]
HWdataKEYWORDS[HW_INFO_NAME]=[]
HWdataKEYWORDS[HW_INFO_MEASUREUNIT]=MEASUREUNITLIST
HWdataKEYWORDS[HW_INFO_MEASURE]=MEASURELIST
HWdataKEYWORDS[HW_CTRL_CMD]=HWcontrol.HWCONTROLLIST
HWdataKEYWORDS[HW_CTRL_PIN]=HWcontrol.RPIMODBGPIOPINLISTPLUS
HWdataKEYWORDS[HW_CTRL_ADCCH]=HWcontrol.ADCCHANNELLIST
HWdataKEYWORDS[HW_CTRL_PWRPIN]=HWcontrol.RPIMODBGPIOPINLIST
HWdataKEYWORDS[HW_CTRL_LOGIC]=["pos","neg"]
HWdataKEYWORDS[HW_CTRL_MAILADDR]=[]
HWdataKEYWORDS[HW_CTRL_MAILTITLE]=[]
HWdataKEYWORDS[HW_FUNC_USEDFOR]=USAGELIST #used for
HWdataKEYWORDS[HW_FUNC_SCHEDTYPE]=["oneshot", "periodic"] #scheduling type
HWdataKEYWORDS[HW_FUNC_TIME]=[] #time in format hh:mm:ss

HWdataKEYWORDS[HW_CTRL_FREQ]=[]
HWdataKEYWORDS[HW_CTRL_MIN]=[]
HWdataKEYWORDS[HW_CTRL_MAX]=[]


# ///////////////// -- Hawrware data structure Setting --  ///////////////////////////////

global IOdata
IOdata=[]
# read IOdata -----
if not filestoragemod.readfiledata(HWDATAFILENAME,IOdata): #read calibration file
	print "warning hwdata file not found -------------------------------------------------------"
	#read from default file
	filestoragemod.readfiledata(DEFHWDATAFILENAME,IOdata)
	print "writing default calibration data"
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
# end read IOdata -----



# ///////////////// --- END GLOBAL VARIABLES ------



#-- start filestorage utility--------////////////////////////////////////////////////////////////////////////////////////	

# filestoragemod.readfiledata(filename,filedata)
# filestoragemod.savefiledata(filename,filedata)
# filestoragemod.appendfiledata(filename,filedata)
# filestoragemod.savechange(filename,searchfield,searchvalue,fieldtochange,newvalue)
# filestoragemod.deletefile(filename)


def checkdata(dictdata): # check if basic info in the fields are corect
	# check free field first
	fieldname=HW_INFO_NAME
	fieldvalue=dictdata[HW_INFO_NAME]	
	if fieldvalue=="":
		message="Name is empty"
		return False, message
	else:
		#check same name already present in IOdata
		if searchmatch(fieldname,fieldvalue):
			message="Same name is already present"
			return False, message
					
	#dictdata[HW_CTRL_MAILADDR]=[]
	#dictdata[HW_CTRL_MAILTITLE]=[]		
	fieldname=HW_FUNC_TIME
	fieldvalue=dictdata[HW_FUNC_TIME]	
	if fieldvalue!="":
		#check format is correct
		if len(fieldvalue.split(":"))<3:
			message="Please enter correct time format hh:mm:ss"
			return False, message
	else:
		correlatedfield=HW_INFO_IOTYPE
		if dictdata[correlatedfield]=="input":
			message="Time cannot be empty for item belonging to input"
			return False, message	
	
	
	# check select field dependencies
	#dictdata[HW_INFO_IOTYPE]=["input"  , "output" ]
	#dictdata[HW_INFO_MEASUREUNIT]=MEASUREUNITLIST
	#dictdata[HW_INFO_MEASURE]=MEASURELIST
	#dictdata[HW_CTRL_CMD]=HWcontrol.HWCONTROLLIST
	
	correlatedfield=HW_CTRL_CMD
	if dictdata[HW_CTRL_CMD]=="pulse":
		fieldname=HW_CTRL_PIN
		fieldvalue=dictdata[HW_CTRL_PIN]	
		if searchmatch(fieldname,fieldvalue):
			message="Same PIN already used"
			return False, message
		
	#dictdata[HW_CTRL_ADCCH]=HWcontrol.ADCCHANNELLIST
	#dictdata[HW_CTRL_PWRPIN]=HWcontrol.RPIMODBGPIOPINLIST
	#dictdata[HW_CTRL_LOGIC]=["pos","neg"]
	#dictdata[HW_FUNC_USEDFOR]=USAGELIST #used for
	#dictdata[HW_FUNC_SCHEDTYPE]=["oneshot", "periodic"] #scheduling type
	return True, ""

def sendcommand(cmd,sendstring,recdata):
	return HWcontrol.sendcommand(cmd,sendstring,recdata)

	
def getsensordata(sensorname,attemptnumber): #needed
	# this procedure was initially uit to communicate using the serial interface with a module in charge of HW control (e.g. Arduino)
	# To lower the costs, I used the PI hardware itself but I still like the way to communicate with the HWcontrol module that is now a SW module not hardware
	cmd=searchdata(HW_INFO_NAME,sensorname,HW_CTRL_CMD)
	Thereading=""	
	if not cmd=="":
		pin=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_PIN))
		arg1=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_ADCCH))
		arg2=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_PWRPIN))
		sendstring=sensorname+":"+pin+":"+arg1+":"+arg2
		recdata=[]
		ack=False
		i=0
		while (not ack)and(i<attemptnumber):
			ack=HWcontrol.sendcommand(cmd,sendstring,recdata)
			i=i+1
		if ack:
			if recdata[0]==cmd: # this was used to check the response and command consistency when serial comm was used
				if recdata[2]>0:
					Thereading=recdata[1]
					print " Sensor " , sensorname  , "reading ",Thereading					
				else:
					print "Problem with sensor reading ", sensorname
			else:
				print "Problem with response consistency ", sensorname , " cmd " , cmd
		else:
			print "no answer from Hardware control module", sensorname					

	else:
		print "sensor name not found in list of sensors ", sensorname
	
	return Thereading

def makepulse(target,duration):
	#search the data in IOdata
	
	print "Check target is already ON ", target
	activated=getpinstate(target)
	if activated=="error":
		return "error"
	if activated=="on":
		return "Already ON"

	
	print "Fire Pulse - ", target
	
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	
	

	try:
		testpulsetime=str(int(duration))
	except ValueError:
		print " No valid data or zero for Doser ", target
		return "error"

	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	POWERPIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PWRPIN)
	if POWERPIN=="":
		POWERPIN="-1"
	
	if logic=="neg":
		sendstring="pulse:"+PIN+":"+testpulsetime+":0"+":"+POWERPIN
	elif logic=="pos":
		sendstring="pulse:"+PIN+":"+testpulsetime+":1"+":"+POWERPIN
	print "logic " , logic , " sendstring " , sendstring
	isok=False	
	if float(testpulsetime)>0:
		print "Sendstring  ", sendstring	
		isok=False
		i=0
		while (not(isok))and(i<2):
			i=i+1
			recdata=[]
			ack= HWcontrol.sendcommand("pulse",sendstring,recdata) #11 is the command to activate relay, 12 is the PIN to activate, 1000 is the ms the pulse is lasting
			print "returned data " , recdata
			if ack and recdata[1]!="e":
				print target, "correctly activated"
				isok=True
				return "Pulse Started"
			
	return "error"

def servoangle(target,percentage,delay): #percentage go from zeo to 100 and is the percentage between min and max duty cycle
	#search the data in IOdata
	
	
	print "Move Servo - ", target #normally is servo1
	
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	


	try:

		FREQ=searchdata(HW_INFO_NAME,target,HW_CTRL_FREQ)	
		MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
		MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	

		dutycycle= str(int(MIN)+(int(MAX)-int(MIN))*int(percentage)/float(100))

		if 0<=int(percentage)<=100:
			print "range OK"
		else:
			print " No valid data for Servo ", target
			return "error"

	except ValueError:
		print " No valid data for Servo", target
		return "error"


	sendstring="servo:"+PIN+":"+FREQ+":"+dutycycle+":"+str(delay)
	print " sendstring " , sendstring

	isok=False
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= HWcontrol.sendcommand("servo",sendstring,recdata) #11 is the command to activate relay, 12 is the PIN to activate, 1000 is the ms the pulse is lasting
		print "returned data " , recdata
		if ack and recdata[1]!="e":
			print target, "correctly activated"
			isok=True
			return "Servo angle set"
			
	return "error"

def getpinstate(target):
	#search the data in IOdata
	print "Check PIN state ", target
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)
	sendstring="status:"+PIN

	isok=False
	value=0
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= HWcontrol.sendcommand("readpin",sendstring,recdata) #11 is the command to activate relay, 12 is the PIN to activate, 1000 is the ms the pulse is lasting
		print "returned data " , recdata
		if ack and recdata[1]!="e":
			value=recdata[1]
			isok=True
		else:
			activated="error"
			
	if isok:
		logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
		if logic=="neg":
			if value=="0":
				activated="on"
			else:
				activated="off"
		elif logic=="pos":
			if value=="1":
				activated="on"
			else:
				activated="off"		

				
	return activated


def getsensornamebymeasure(measure):
	# MEASURELIST is the list with valid values for the "measure" parameter
	sensorlist=searchdatalist(HW_INFO_MEASURE,measure,HW_INFO_NAME)
	return sensorlist

			
def readallsensors():
	# read from serial the values for arduino
	sensorlist=searchdatalist(HW_INFO_IOTYPE,"input",HW_INFO_NAME)
	sensorvalues={}
	for sensorname in sensorlist:
		sensorvalues[sensorname]=getsensordata(sensorname,3)
	return sensorvalues



			
def checkallsensors():
	# check if the sensor respond properly according to sensor list in HWdata file
	print " check sensor list "
	sensorlist=searchdatalist(HW_INFO_IOTYPE,"input",HW_INFO_NAME)
	sensorvalues={}
	for sensorname in sensorlist:
		sensorvalues[sensorname]=getsensordata(sensorname,3)
	return sensorvalues



		
def initallGPIOoutput():
	for ln in IOdata:
		iotype=ln[HW_INFO_IOTYPE]
		if (iotype=="output") :
			if (ln[HW_CTRL_CMD]=="pulse"):
				HWcontrol.GPIO_setup(int(ln[HW_CTRL_PIN]), "out")
				if ln[HW_CTRL_LOGIC]=="pos":
					HWcontrol.GPIO_output(int(ln[HW_CTRL_PIN]), 0)
				else:
					HWcontrol.GPIO_output(int(ln[HW_CTRL_PIN]), 1)
					
			if (HW_CTRL_PWRPIN in ln):
				try: 
					HWcontrol.GPIO_setup(int(ln[HW_CTRL_PWRPIN]), "out")
					HWcontrol.GPIO_output(int(ln[HW_CTRL_PWRPIN]), 0)
				except ValueError:
					print "powerpin not se because is not a number"
	#print HWcontrol.GPIO_data
	return True



	
def restoredefault():
	filestoragemod.deletefile(HWDATAFILENAME)
	filestoragemod.readfiledata(DEFHWDATAFILENAME,IOdata)
	savecalibartion()
	
def savecalibartion():
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)

def changesavecalibartion(IOname,IOparameter,IOvalue):  #needed
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	for line in IOdata:
		if line[HW_INFO_NAME]==IOname:
			line[IOparameter]=IOvalue
			savecalibartion()
			return True
	return False

def searchdata(recordkey,recordvalue,keytosearch):
	for ln in IOdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					return ln[keytosearch]	
	return ""

def searchmatch(recordkey,recordvalue):
	for ln in IOdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				return True	
	return False


def gettimedata(name):
	# return list with three integer values: hour , minute, second
	timestr=searchdata(HW_INFO_NAME,name,HW_FUNC_TIME)
	return separatetimestringint(timestr)


def separatetimestringint(timestr):
	outlist=[]
	timelist=timestr.split(":")
	for i in range(3):
		if i<len(timelist):
			if timelist[i]!="":
				outlist.append(toint(timelist[i],1))
			else:
				outlist.append(0)	
		else:
			outlist.append(0)		
	return outlist
		
def tonumber(thestring, outwhenfail):
	try:
		n=float(thestring)
		return n
	except:
		return outwhenfail

def toint(thestring, outwhenfail):
	try:
		f=float(thestring)
		n=int(f)
		return n
	except:
		return outwhenfail


def searchdatalist(recordkey,recordvalue,keytosearch):
	datalist=[]
	for ln in IOdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					datalist.append(str(ln[keytosearch]))	
	return datalist

def getfieldvaluelist(fielditem,valuelist):
	del valuelist[:]
	for line in IOdata:
		valuelist.append(line[fielditem])

def getfieldinstringvalue(fielditem,stringtofind,valuelist):
	del valuelist[:]
	for line in IOdata:
		name=line[fielditem]
		if name.find(stringtofind)>-1:
			valuelist.append(name)

def photolist(apprunningpath):

	folderpath=os.path.join(apprunningpath, "static")
	folderpath=os.path.join(folderpath, "hydropicture")
	# control if the folder hydropicture exist otherwise create it
	if not os.path.exists(folderpath):
		os.makedirs(folderpath)
		print "Hydropicture folder has been created"
	
	filenamelist=[]
	sortedlist=sorted([f for f in os.listdir(folderpath) if os.path.isfile(os.path.join(folderpath, f))])
	sortedlist.reverse()
	for files in sortedlist:
		if (files.endswith(".jpg") or files.endswith(".png")):
			templist=[]
			templist.append("hydropicture/"+files)
			if "@" in files:
				templist.append("Image taken on "+files.split("@")[0])
				datestr=files.split("@")[0]
			else:
				templist.append("Image taken on "+files.split(".")[0])
				datestr=files.split(".")[0]
			try:
				dateref=datetime.strptime(datestr,'%y-%m-%d,%H:%M')
				templist.append(dateref)
			except:
				print "file name format not compatible with date"
				templist.append("")
			templist.append("hydropicture/thumb/"+files)
			filenamelist.append(templist)			
	return filenamelist # item1 (path+filename) item2 (name for title) item3 (datetime) item4 (thumbpath + filename)

def loglist(apprunningpath,logfolder,searchstring):
	templist=[]	
	folderpath=os.path.join(apprunningpath,logfolder)
	# control if the folder  exist otherwise exit
	if not os.path.exists(folderpath):
		print "log folder does not exist"
		return templist
	filenamelist=[]
	sortedlist=sorted(os.listdir(folderpath))
	sortedlist.reverse()
	for files in sortedlist:
		if (searchstring in files):
			templist.append(files)
	return templist 

def deleteallpictures(apprunningpath):
	#delete pictures
	folderpath=os.path.join(apprunningpath, "static")
	folderpath=os.path.join(folderpath, "hydropicture")	
	sortedlist=os.listdir(folderpath)
	i=0
	for files in sortedlist:
		if os.path.isfile(os.path.join(folderpath, files)):
			os.remove(os.path.join(folderpath, files))
			i=i+1
	#delete thumb 
	paththumb=os.path.join(folderpath,"thumb")
	sortedlist=os.listdir(paththumb)
	i=0
	for files in sortedlist:
		if os.path.isfile(os.path.join(paththumb, files)):
			os.remove(os.path.join(paththumb, files))
			i=i+1
	return i

def HWpresetlist(apprunningpath):
	folderpath=os.path.join(apprunningpath, "database")
	folderpath=os.path.join(folderpath, "default")
	folderpath=os.path.join(folderpath, "presetHWsetting")
	filenamelist=[]
	sortedlist=sorted(os.listdir(folderpath))
	sortedlist.reverse()
	for files in sortedlist:
		if files.startswith("defhwdata"):
			templist=[]
			templist.append("database/default/presetHWsetting/"+files)			
			templist.append(files)
			filenamelist.append(templist)
	return filenamelist # item1 (path) item2 (name)


def removephotodataperiod(removebeforedays):

	todaydate=datetime.now()
	num = removebeforedays
	tdelta=timedelta(days=num)
	enddate=todaydate-tdelta
	pastdays=364
	num = pastdays
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta
	print " stratdate " ,startdate
	print " enddate ", enddate
	
	photodata=photolist(get_path())

	for photo in photodata:
		dateref=photo[2]
		print dateref
		if (dateref>=startdate)and(dateref<=enddate):
			try:
				filepath=os.path.join(get_path(), "static")
				filepath=os.path.join(filepath, photo[0])
				# remove photo
				filestoragemod.deletefile(filepath)
				print "removed Photo " , filepath
			except ValueError:
				print "Error in photo delete "
	thumbconsistency(get_path())

			
	
def shotit(video,istest,resolution,positionvalue):
    # send command to the actuator for test
	if istest:
		filepath=os.path.join(get_path(), "static")
		filepath=os.path.join(filepath, "cameratest")
		filedelete=os.path.join(filepath, "testimage.png")
		filestoragemod.deletefile(filedelete)		
		shottaken=photomod.saveshot(filepath,video,False,resolution,positionvalue)       
	else:
		filepath=os.path.join(get_path(), "static")
		filepath=os.path.join(filepath, "hydropicture")
		shottaken=photomod.saveshot(filepath,video,True,resolution,positionvalue)			
	if shottaken:
		ret_data = {"answer": "photo taken"}
	else:
		ret_data = {"answer": "Camera not detected"}	
	print "The photo ", ret_data
	return ret_data
	
def videodevlist():
	return photomod.videodevlist()
	
def  thumbconsistency(apprunningpath):
	return photomod.thumbconsistency(apprunningpath)
			
			
def takephoto():
	print "take photo", " " , datetime.now()
	videolist=videodevlist()
	for video in videolist:
		resolution=cameradbmod.searchdata("camname",video,"resolution") # if not found return ""
		position=cameradbmod.searchdata("camname",video,"position")
		servo=cameradbmod.searchdata("camname",video,"servo")
		print "Camera: ", video , " Resolution ", resolution , " Position " , position
		positionlist=position.split(",")
		if (positionlist)and(servo!="none"):
			for positionvalue in positionlist:
			# move servo
				servoangle(servo,positionvalue,2)
				ret_data={}
				ret_data=shotit(video,False,resolution,positionvalue)
		else:
			ret_data={}
			ret_data=shotit(video,False,resolution,"0")			
		logger.info(ret_data["answer"])

def resetandbackuplog_bak():
	#setup log file ---------------------------------------
	mainpath=get_path()
	filename=LOGFILENAME
	try:
		#os.rename(os.path.join(mainpath,filename), os.path.join(mainpath,filename+".txt"))
		shutil.copyfile(os.path.join(mainpath,filename), os.path.join(mainpath,filename+".txt"))

	except:
		print "No log file"

	logger.FileHandler(filename=os.path.join(mainpath,filename), mode='w')	
	#logger.basicConfig(filename=os.path.join(mainpath,filename),level=logger.INFO)
	#logger.basicConfig(format='%(asctime)s %(message)s')
	#logger.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
	
	# set up logging to file - see previous section for more details
	logger.basicConfig(level=logging.INFO,
						format='%(asctime)-2s %(levelname)-8s %(message)s',
						datefmt='%H:%M:%S',
						filename=os.path.join(mainpath,filename))


def get_path():
    '''Get the path to this script no matter how it's run.'''
    #Determine if the application is a py/pyw or a frozen exe.
    if hasattr(sys, 'frozen'):
        # If run from exe
        dir_path = os.path.dirname(sys.executable)
    elif '__file__' in locals():
        # If run from py
        dir_path = os.path.dirname(__file__)
    else:
        # If run from command line
        dir_path = sys.path[0]
    return dir_path
	


def get_image_size(picturepath):
	filepath=os.path.join(get_path(), "static")
	fname=os.path.join(filepath, picturepath)
	'''Determine the image type of fhandle and return its size.
	from draco'''
	with open(fname, 'rb') as fhandle:
		head = fhandle.read(24)
		if len(head) != 24:
			return
		if imghdr.what(fname) == 'png':
			check = struct.unpack('>i', head[4:8])[0]
			if check != 0x0d0a1a0a:
				return
			width, height = struct.unpack('>ii', head[16:24])
		elif imghdr.what(fname) == 'gif':
			width, height = struct.unpack('<HH', head[6:10])
		elif imghdr.what(fname) == 'jpeg':
			try:
				fhandle.seek(0) # Read 0xff next
				size = 2
				ftype = 0
				while not 0xc0 <= ftype <= 0xcf:
					fhandle.seek(size, 1)
					byte = fhandle.read(1)
					while ord(byte) == 0xff:
						byte = fhandle.read(1)
					ftype = ord(byte)
					size = struct.unpack('>H', fhandle.read(2))[0] - 2
				# We are at a SOFn block
				fhandle.seek(1, 1)  # Skip `precision' byte.
				height, width = struct.unpack('>HH', fhandle.read(4))
			except Exception: #IGNORE:W0703
				return
		else:
			return
		return width, height

def addrow(dicttemp):
	IOdata.append(dicttemp)
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
	return True
	
def deleterow(element):
	searchfield=HW_INFO_NAME
	searchvalue=element
	for line in IOdata:
		if searchfield in line:
			if line[searchfield]==searchvalue:
				IOdata.remove(line)
				filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
				return True
	return False


	
if __name__ == '__main__':
	# comment
	a=10
	
