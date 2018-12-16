# -*- coding: utf-8 -*-
Release="0.91"

#---------------------
from loggerconfig import LOG_SETTINGS
import logging, logging.config, logging.handlers
import basicSetting

DEBUGMODE=basicSetting.data["DEBUGMODE"]
PUBLICMODE=basicSetting.data["PUBLICMODE"]

if DEBUGMODE:
	# below line is required for the loggin of the apscheduler, this might not be needed in the puthon 3.x
	logging.basicConfig(level=logging.DEBUG,
						format='%(asctime)s %(levelname)s %(message)s',
						filename='logfiles/apscheduler_hydrosystem.log',
						filemode='w')


# dedicated logging for the standard operation

logging.config.dictConfig(LOG_SETTINGS)
logger = logging.getLogger('hydrosys4')
exc_logger = logging.getLogger('exception')



from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack, jsonify , Response

from datetime import datetime,date,timedelta
import systemtimeMod
import time	 
import os
import shutil
import sys
import string
import random
import json
import hardwaremod
import videomod
import sensordbmod
import actuatordbmod
import selectedplanmod
import wateringdbmod
import autowateringdbmod
import autowateringmod

import automationdbmod
import automationmod

import autofertilizerdbmod
import autofertilizermod
import fertilizerdbmod
import advancedmod
import networkmod
import networkdbmod
import emailmod
import emaildbmod
import logindbmod
import clockmod
import clockdbmod
import countryinfo
import cameradbmod
import sysconfigfilemod
import debuggingmod

# Raspberry Pi camera module (requires picamera package)
from camera_pi import Camera

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////
application = Flask(__name__)
application.config.from_object('flasksettings') #read the configuration variables from a separate module (.py) file, this file is mandatory for Flask operations
print "-----------------" , basicSetting.data["INTRO"], "--------------------"


MYPATH=""


# ///////////////// --- END GLOBAL VARIABLES ------



# ///////////////// -- MODULE INIZIALIZATION --- //////////////////////////////////////////


#-- start LOGGING utility--------////////////////////////////////////////////////////////////////////////////////////


#setup log file ---------------------------------------

print "starting new log session", datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
logger.info('Start logging -------------------------------------------- %s' , datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
logger.debug('This is a sample DEBUG message')
logger.info('This is a sample INFO message')
logger.warning('This is a sample WARNING message')
logger.error('This is a sample ERROR message')


# finish logging init

def runallconsistencycheck():
	wateringdbmod.consitencycheck()
	autowateringdbmod.consistencycheck()
	automationdbmod.consistencycheck()
	fertilizerdbmod.consitencycheck()
	autofertilizerdbmod.consistencycheck()
	sensordbmod.consistencycheck()
	actuatordbmod.consistencycheck()
	return True




# Setup mode of operation------------------------------
DEBUGMODE=True
PUBLICMODE=True
selectedplanmod.FASTSCHEDULER=False
	
# set minimum time in case the clock is gone, in future might be improved ------------------
#important for Arch linux OS

systemtimeMod.set_min_datetime()

#initiate the GPIO OUT pins
hardwaremod.initallGPIOoutput()

# GET path ---------------------------------------------
print "path ",hardwaremod.get_path()
MYPATH=hardwaremod.get_path()

# RUN ALL consistency chacks ------------------------
runallconsistencycheck()

#setup network connecton --------------------
try:
	print "start networking"
	networkmod.init_network()
except:
	print "No WiFi available"
	
#scheduler setup---------------------
selectedplanmod.start_scheduler()
# after internet connection because ofter the time is abruptly changed after connection
selectedplanmod.waitandsetmastercallback(networkmod.WAITTOCONNECT, 40)	# plus 40 seconds respect to internet connection
	
	
#prove varie qui ---------------------------------------------------
#selectedplanmod.startpump("1","10","25","10")
#selectedplanmod.setlight("","")
#periodicdatarequest(0)
#selectedplanmod.pulsenutrient("10","","","3")
#selectedplanmod.sendmail()
#ret_data=hardwaremod.takephoto()


# ///////////////// --- END init





	
@application.teardown_appcontext
def close_db_connection(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


@application.route('/')
def show_entries():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print "preparing home page"
	currentday=date.today()
			
	#Picture panel------------------------------------
	#folderpath=os.path.join(MYPATH, "static")
	#folderpath=os.path.join(folderpath, "hydropicture")
	#sortedlist=sorted(os.listdir(folderpath))
	#sortedlist.reverse()
	photolist=hardwaremod.photolist(MYPATH)
	photopanellist=[]	
	if photolist:
		referencestr=photolist[0][0].split(",")[0]
		for items in photolist:
			if referencestr in items[0]:
				photopanel={}
				photopanel["type"]="photo"	
				photopanel["active"]="yes"
				photopanel["title"]=""
				photopanel["subtitle"]=""
				photopanel["file"]=items[0]
				photopanel["thumb"]=items[3]	
				photopanel["link"]=url_for('imageshow')
				photopanel["linktitle"]="Go to Gallery"		
				#print photopanel
				photopanellist.append(photopanel)


	panelinfolist=[] # all the info relevant to a type of panel
	
	# temperature panels -------------------------------------------- (new version)
	MeasureType="Temperature"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist

	if namelist:
		paneldict={}	
		paneldict["icon"]="icons/temperature-transp.png"
		paneldict["color"]="green"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype="",  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=""
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:	
			sensordata=[]	
			sensordbmod.getsensordbdatadays(name,sensordata,1)
			#set date interval for average
			starttime= endtime - timedelta(days=1)
			evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
			paneldatarow={}		
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % evaluateddata["average"])
			paneldatarow["min"]=str('%.1f' % evaluateddata["min"])
			paneldatarow["max"]=str('%.1f' % evaluateddata["max"])
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata		
		panelinfolist.append(paneldict)



	# humidity panel --------------------------------------------
	MeasureType="Humidity"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	
	if namelist:
		paneldict={}	
		paneldict["icon"]="icons/humidity-transp.png"
		paneldict["color"]="primary"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype="",  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=""
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:	
			sensordata=[]
			sensordbmod.getsensordbdatadays(name,sensordata,1)
			#set date interval for average
			starttime= endtime - timedelta(days=1)
			evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
			paneldatarow={}		
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % evaluateddata["average"])
			paneldatarow["min"]=str('%.1f' % evaluateddata["min"])
			paneldatarow["max"]=str('%.1f' % evaluateddata["max"])
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata		
		panelinfolist.append(paneldict)
	
	

	# pressure panel --------------------------------------------
	MeasureType="Pressure"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	
	if namelist:
		paneldict={}	
		paneldict["icon"]="icons/pressure-transp.png"	
		paneldict["color"]="yellow"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype="",  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=""
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:		
			sensordata=[]
			sensordbmod.getsensordbdatadays(name,sensordata,1)
			#set date interval for average
			starttime= endtime - timedelta(days=1)
			evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
			paneldatarow={}		
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % evaluateddata["average"])
			paneldatarow["min"]=str('%.1f' % evaluateddata["min"])
			paneldatarow["max"]=str('%.1f' % evaluateddata["max"])
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata		
		panelinfolist.append(paneldict)
	
	
	

	# light panel --------------------------------------------
	MeasureType="Light"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	if namelist:
		paneldict={}	
		paneldict["icon"]="icons/light-transp.png"		
		paneldict["color"]="red"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype="",  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=""
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:		
			sensordata=[]
			sensordbmod.getsensordbdatadays(name,sensordata,1)
			#set date interval for average
			starttime= endtime - timedelta(days=1)
			evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
			paneldatarow={}		
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % evaluateddata["average"])
			paneldatarow["min"]=str('%.1f' % evaluateddata["min"])
			paneldatarow["max"]=str('%.1f' % evaluateddata["max"])
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata		
		panelinfolist.append(paneldict)	
	
	
	
	# Hygrometer panel --------------------------------------------
	MeasureType="Moisture"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist

	if namelist:
		paneldict={}	
		paneldict["icon"]="icons/moisture-transp.png"	
		paneldict["color"]="primary"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype="",  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]="booooo"
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:		
			sensordata=[]
			sensordbmod.getsensordbdatadays(name,sensordata,1)
			#set date interval for average
			starttime= endtime - timedelta(days=1)
			evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
			paneldatarow={}
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % evaluateddata["average"])
			paneldatarow["min"]=str('%.1f' % evaluateddata["min"])
			paneldatarow["max"]=str('%.1f' % evaluateddata["max"])
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata			
		panelinfolist.append(paneldict)	
	




	# watertap panel --------------------------------------------
	usedfor="watercontrol"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	
	if namelist:
		paneldict={}	
		paneldict["icon"]="icons/watertap-transp.png"		
		paneldict["color"]="primary"	
		paneldict["type"]="actuator"		
		paneldict["link"]=url_for('wateringplan' , selectedelement=namelist[0])
		paneldict["linktitle"]="Go to WateringPlan"
		paneldict["title"]="Water"
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:			
			sensordata=[]
			starttime= endtime - timedelta(days=1)
			data=[]
			actuatordbmod.getActuatordbdata(name,data)
			evaluateddata=sensordbmod.EvaluateDataPeriod(data,starttime,endtime)	#set date interval for average
			paneldatarow={}
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % (evaluateddata["sum"]/1000))
			paneldatarow["min"]=""
			paneldatarow["max"]=""
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
			paneldata.append(paneldatarow)	
		paneldict["data"]=paneldata			
		panelinfolist.append(paneldict)		


	# fertilizer panel --------------------------------------------
	usedfor="fertilizercontrol"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist

	if namelist:
		paneldict={}	
		paneldict["icon"]="icons/fertilizer-transp.png"		
		paneldict["color"]="green"	
		paneldict["type"]="actuator"		
		paneldict["link"]=url_for('fertilizerplan' , selectedelement=namelist[0])
		paneldict["linktitle"]="Go to FertilizerPlan"
		paneldict["title"]="Fertilizer"
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()		
		for name in namelist:		
			sensordata=[]
			starttime= endtime - timedelta(days=1)
			data=[]
			actuatordbmod.getActuatordbdata(name,data)
			evaluateddata=sensordbmod.EvaluateDataPeriod(data,starttime,endtime)	#set date interval for average
			paneldatarow={}
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % (evaluateddata["sum"]/1000))
			paneldatarow["min"]=""
			paneldatarow["max"]=""
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
			paneldata.append(paneldatarow)	
		paneldict["data"]=paneldata			
		panelinfolist.append(paneldict)	
	

	networklink=url_for('network')
	settinglink=url_for('show_Calibration')
	videolink=url_for('videostream')

	return render_template('homepage.html',panelinfolist=panelinfolist,photopanellist=photopanellist,currentday=currentday, networklink=networklink, settinglink=settinglink , videolink=videolink)


@application.route('/network/', methods=['GET', 'POST'])
def network():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	wifilist=[]
	savedssid=[]	
	filenamelist="wifi networks"
	
	print "visualizzazione menu network:"


	iplocal=networkmod.get_local_ip()
	iplocalwifi=networkmod.IPADDRESS
	ipport=networkmod.PUBLICPORT
	connectedssidlist=networkmod.connectedssid()
	if len(connectedssidlist)>0:
		connectedssid=connectedssidlist[0]
	else:
		connectedssid=""
	
	
	localwifisystem=networkmod.localwifisystem
	print " localwifisystem = ", localwifisystem , " connectedssid ", connectedssid


	return render_template('network.html',filenamelist=filenamelist, connectedssid=connectedssid,localwifisystem=localwifisystem,  iplocal=iplocal, iplocalwifi=iplocalwifi , ipport=ipport)



@application.route('/wificonfig/', methods=['GET', 'POST'])
def wificonfig():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print "method " , request.method
	if request.method == 'GET':
		ssid = request.args.get('ssid')
		print " argument = ", ssid

	if request.method == 'POST':
		ssid = request.form['ssid']
		if request.form['buttonsub'] == "Save":
			password=request.form['password']
			networkmod.savewifi(ssid, password)
			networkmod.waitandconnect(7)
			print "Save"
			return redirect(url_for('show_entries'))
			
		elif request.form['buttonsub'] == "Forget":
			print "forget"		
			networkmod.waitandremovewifi(6,ssid)
			print "remove network ", ssid
			print "Try to connect AP"
			networkmod.waitandconnect_AP(7)
			return redirect(url_for('show_entries'))
			
		else:
			print "cancel"
			return redirect(url_for('network'))

	return render_template('wificonfig.html', ssid=ssid)


@application.route('/Imageshow/', methods=['GET', 'POST'])
def imageshow():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	monthdict= {1: "jan", 10: "oct", 11: "nov", 12: "dec", 2: "feb", 3: "mar", 4: "apr", 5: "may", 6: "jun", 7: "jul", 8: "aug", 9: "sep"}
	monthlist=[]
	for i in range(12):
		monthlist.append(monthdict[i+1])

	todaydate = date.today()
	currentmonth = todaydate.month
	monthtoshow=currentmonth
	
	if request.method == 'POST':
		actiontype=request.form['actionbtn']
		if actiontype=="DeleteAll":
			# delete all files in the folder
			deletedfilenumber=hardwaremod.deleteallpictures(MYPATH)
			print " picture files deleted " , deletedfilenumber
			logger.info(' all image files deleted ')
			
		else:
			monthtoshow=monthlist.index(actiontype)+1


	
	sortedlist=hardwaremod.photolist(MYPATH)
	
	filenamelist=[]
	wlist=[]
	hlist=[]
	titlelist=[]
	thumbfilenamelist=[]
	for files in sortedlist:
		filemonthnumber=files[2].month
		print filemonthnumber
		if filemonthnumber==monthtoshow :
			filenamelist.append(files[0])
			titlelist.append(files[1])
			(w,h)=hardwaremod.get_image_size(files[0])
			wlist.append(w)
			hlist.append(h)
			thumbfilenamelist.append(files[3])			
			
	print filenamelist
	selectedmothname=monthdict[monthtoshow]
	print selectedmothname
	return render_template('showimages.html',filenamelist=filenamelist,titlelist=titlelist,wlist=wlist,hlist=hlist,monthlist=monthlist,selectedmothname=selectedmothname, thumbfilenamelist=thumbfilenamelist)


	
@application.route('/echo/', methods=['GET'])
def echo():

	element=request.args['element']
	if element=="all":
		# take reading for all sensors
		ret_data = hardwaremod.readallsensors()	
	else:
		sensorvalue={}
		sensorvalue[element]=hardwaremod.getsensordata(element,3)
		ret_data=sensorvalue


	print ret_data
	return jsonify(ret_data)

@application.route('/echodatabase/', methods=['GET'])
def echodatabase():

	element=request.args['element']
	if element=="all":
		# take reading for all sensors
		ret_data = sensordbmod.readallsensorsdatabase()	
	else:
		ret_data={}


	print ret_data
	return jsonify(ret_data)

@application.route('/echowifi/', methods=['GET'])
def echowifi():
	ret_data={}
	element=request.args['element']
	if element=="all":
		# get wifi list
		wifilist=[]
		wifilist=networkmod.wifilist_ssid()
		connectedssidlist=networkmod.connectedssid()
		if len(connectedssidlist)>0:
			connectedssid=connectedssidlist[0]
		else:
			connectedssid=""
		
		savedssid=networkmod.savedwifilist_ssid()
		
		for ssid in wifilist:
			connected="0"
			if ssid==connectedssid:
				connected="1"
			idstatus="Unknown"
			if ssid in savedssid:
				idstatus="Saved"
				
			ret_data[ssid]=[idstatus , connected]
	
	print "Wifi Data " , ret_data
	return jsonify(ret_data)

	
@application.route('/doit/', methods=['GET'])
def doit():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login Needed"}
		return jsonify(ret_data)
    # send command to the actuator for test
	cmd=""
	sendstring=""
	recdata=[]
	ret_data={}
	argumentlist=request.args.getlist('name')
	name=argumentlist[0]
	print "value passed ", argumentlist
	print "type " , name 
	
		
	if name=="pulse":
		idx=1
		if idx < len(argumentlist):
			testpulsetime=argumentlist[idx]
		else:
			testpulsetime="20"
		element=request.args['element']		

		print "starting pulse test " , testpulsetime
		answer=selectedplanmod.activateandregister(element,testpulsetime)
		ret_data = {"answer": answer}


	elif name=="servo2":
		print "want to test servo"
		idx=1
		if idx < len(argumentlist):
			steps=int(argumentlist[idx])
		idx=2
		if idx < len(argumentlist):
			direction=argumentlist[idx]
		
		element=request.args['element']	
		position=int(hardwaremod.getservopercentage(element))
		
		if direction=="FORWARD":
			position=position+steps
		elif direction=="BACKWARD":
			position=position-steps

		# move servo
		delay=0.5
		position , isok=hardwaremod.servoangle(element,position,delay)		
		ret_data = {"answer": position}			
	
		



	elif name=="stepper":
		print "want to test stepper"
		idx=1
		if idx < len(argumentlist):
			steps=argumentlist[idx]
		idx=2
		if idx < len(argumentlist):
			direction=argumentlist[idx]
		
		element=request.args['element']	
		# move stepper
		position , isok=hardwaremod.GO_stepper(element,steps,direction)
		ret_data = {"answer": position}


	elif name=="setstepper":
		print "want to set stepper position"
		idx=1
		if idx < len(argumentlist):
			newposition=argumentlist[idx]
		
		element=request.args['element']	
		# set stepper position without moving it
		hardwaremod.setstepperposition(element, newposition)
		ret_data = {"answer": newposition}




	elif name=="photo":
		print "want to test photo"
		idx=1
		if idx < len(argumentlist):
			video=argumentlist[idx]
		resolution=request.args.getlist('resolution')[0]
		position=request.args.getlist('position')[0]
		servo=request.args.getlist('servo')[0]
		vdirection=request.args.getlist('vdirection')[0]
		print "resolution ", resolution , " position ", position
		positionlist=position.split(",")
		position=""
		if positionlist:
			print "only use the first position for testing " , positionlist[0]
			# move servo
			position=positionlist[0]
			hardwaremod.servoangle(servo,position,1)			
		# take picture
		#vdirection=hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_CTRL_LOGIC)
		ret_data=hardwaremod.shotit(video,True,resolution,position,vdirection)
		
	elif name=="mail":
		mailaname=request.args['element']
		mailaddress=request.args['address']
		mailtitle=request.args['title']
		cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,mailaname,hardwaremod.HW_CTRL_CMD)
		print "want to test mail, address=" , mailaddress , " Title=" , mailtitle
		issent=emailmod.send_email_main(mailaddress,mailtitle,cmd,"report","Periodic system report generated automatically")
		if issent:
			ret_data = {"answer": "Mail sent"}
		else:	
			ret_data = {"answer": "Error mail not sent"}
			
			
	elif name=="clock":
		element=request.args['element']
		datetime=request.args['datetime']
		if element=="system":
			datetime=clockmod.readsystemdatetime()
			answer="ready"
		elif element=="network":
			datetime=clockmod.getNTPTime()
			if datetime=="":
				answer="Error not able to get the Network time using NTP protocol"
			else:
				answer="ready"
		elif element=="setHWClock":
			print "datetime Local ->" ,datetime
			answer=clockmod.setsystemclock(datetime)
			answer=clockmod.setHWclock(datetime)

		ret_data = {"answer":answer, "value":datetime}

	elif name=="timezone":
		element=request.args['element']
		timezone=request.args['timezone']
		if element=="settimezone":
			print "Set timezone ->" ,timezone
			answer=clockmod.settimezone(timezone)
			clockdbmod.changesavesetting("timezone",timezone)
			# reset scheduling 
			selectedplanmod.resetmastercallback()
		ret_data = {"answer":"Saved"}

	return jsonify(ret_data)

@application.route('/saveit/', methods=['GET'])
def saveit():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login needed"}
		return jsonify(ret_data)
    # send command to the actuator for test
	cmd=""
	sendstring=""
	recdata=[]
	ret_data={}
	name=request.args['name']
	print "Saving .." , name
	if name=="mail":
		mailaname=request.args['element']
		mailaddress=request.args['address']
		mailtitle=request.args['title']
		mailtime=request.args['time']
		print "save mail, name " ,mailaname , " address=" , mailaddress , " Title=" , mailtitle , " Time=", mailtime
		hardwaremod.changesavecalibartion(mailaname,hardwaremod.HW_CTRL_MAILADDR,mailaddress)
		hardwaremod.changesavecalibartion(mailaname,hardwaremod.HW_CTRL_MAILTITLE,mailtitle)
		hardwaremod.changesavecalibartion(mailaname,hardwaremod.HW_FUNC_TIME,mailtime)
		
	elif name=="photo":
		
		# save photo time
		phototime=""
		phototime=request.args['time']
		vdirection=request.args['vdirection']
		print "save photo setting, time=" , phototime , " Vertical direction " , vdirection
		hwname=hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_INFO_NAME)
		hardwaremod.changesavecalibartion(hwname,hardwaremod.HW_FUNC_TIME,phototime)
		hardwaremod.changesavecalibartion(hwname,hardwaremod.HW_CTRL_LOGIC,vdirection)
				
		camname=request.args['element']
		resolution=request.args['resolution']
		position=request.args['position']
		servo=request.args['servo']
		print "save camera name " ,camname , " resolution=" , resolution , " position=" , position , " servo=" , servo ," time=", phototime
		cameradbmod.changecreatesetting("camera",camname,"resolution",resolution)
		cameradbmod.changecreatesetting("camera",camname,"position",position)
		cameradbmod.changecreatesetting("camera",camname,"servo",servo)
		cameradbmod.changecreatesetting("camera",camname,"time",phototime)
		cameradbmod.savesetting()
		
		
	elif name=="light1":
		lighttime=""
		lighttime=request.args['time']
		print "save light setting, time=" , lighttime
		hardwaremod.changesavecalibartion(name,hardwaremod.HW_FUNC_TIME,lighttime)


	ret_data = {"answer": "saved"}
	print "The actuator ", ret_data
	return jsonify(ret_data)




	
@application.route('/downloadit/', methods=['GET'])
def downloadit():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login Needed"}
		return jsonify(ret_data)
    # check the download destination folder exist otherwise create it
	folderpath=os.path.join(MYPATH, "static")
	folderpath=os.path.join(folderpath, "download")
	if not os.path.exists(folderpath):
		os.makedirs(folderpath)
    
	recdata=[]
	ret_data={}
	
	name=request.args['name']
	if name=="downloadlog":
		dstfilename="log"+datetime.now().strftime("%Y-%m-%d-time:%H:%M")+".log"
		filename=LOG_SETTINGS['handlers']['access_file_handler']['filename']
		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		dst=os.path.join(folderpath, dstfilename+".txt")
		print "prepare file for download, address=" , filename, "destination " , dst
		try:
			shutil.copyfile(filename, dst)
			answer="ready"
		except:
			answer="problem copying file"
		dstfilenamelist=[]
		dstfilenamelist.append("download/"+dstfilename+".txt")	
		
	elif name=="downloadprevlog":
		filenamestring=LOG_SETTINGS['handlers']['access_file_handler']['filename']		
		logfolder=filenamestring.split('/')[0]
		filename=filenamestring.split('/')[1]
		sortedlist=hardwaremod.loglist(MYPATH,logfolder,filename)

		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		
		answer="files not available"
		dstfilenamelist=[]
		for dstfilename in sortedlist:
			dst=os.path.join(folderpath, dstfilename+".txt")
			source=os.path.join(logfolder, dstfilename)
			print "prepare file for download, address=" , source, "destination " , dst
			try:
				shutil.copyfile(source, dst)
				answer="ready"
			except:
				answer="problem copying file"
			dstfilenamelist.append("download/"+dstfilename+".txt")

	elif name=="downloadlogSCHED":
		dstfilename="Sched_log"+datetime.now().strftime("%Y-%m-%d-time:%H:%M")+".log"
		filename="logfiles/apscheduler_hydrosystem.log"
		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		dst=os.path.join(folderpath, dstfilename+".txt")
		print "prepare file for download, address=" , filename, "destination " , dst
		try:
			shutil.copyfile(filename, dst)
			answer="ready"
		except:
			answer="problem copying file"
		dstfilenamelist=[]
		dstfilenamelist.append("download/"+dstfilename+".txt")	


	elif name=="downloadHW":
		dstfilename=hardwaremod.HWDATAFILENAME
		filename=os.path.join(hardwaremod.DATABASEPATH, hardwaremod.HWDATAFILENAME)
		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		dst=os.path.join(folderpath,  hardwaremod.HWDATAFILENAME)
		print "prepare file for download, address=" , filename, "destination " , dst
		try:
			shutil.copyfile(filename, dst)
			answer="ready"
		except:
			answer="problem copying file"
		dstfilenamelist=[]
		dstfilenamelist.append("download/"+dstfilename)	

	elif name=="downloadsyslog":
		dstfilename="syslog"+datetime.now().strftime("%Y-%m-%d-time:%H:%M")+".txt"
		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		dst=os.path.join(folderpath, dstfilename)
		print "prepare file for download, destination " , dst
		# create the file using the tail command
		isok=debuggingmod.createfiletailsyslog(dst)
		if not isok:
			answer="problem cretating file"
		else:
			answer="ready"
		dstfilenamelist=[]
		dstfilenamelist.append("download/"+dstfilename)	

	ret_data = {"answer": answer, "filename": dstfilenamelist}
	print "The actuator ", ret_data
	return jsonify(ret_data)
	
@application.route('/testit/', methods=['GET'])
def testit():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login Needed"}
		return jsonify(ret_data)
   # this is used for debugging purposes, activate the functiontest from web button
	recdata=[]
	ret_data={}
	
	name=request.args['name']
	if name=="testing":
		answer="done"
		print "testing"
		answer=functiontest()

	ret_data = {"answer": answer}
	print "The actuator ", ret_data
	return jsonify(ret_data)
	
	
		
@application.route('/ShowRealTimeData/', methods=['GET', 'POST'])
def show_realtimedata():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	
	sensorlist=sensordbmod.gettablelist()	
	selectedsensor=sensorlist[0]
	
	if request.method == 'POST':
		selectedsensor=request.form['postsensor']

	unitdict={}
	for item in sensorlist:
		unitdict[item]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,item,hardwaremod.HW_INFO_MEASUREUNIT)
	print "unitdict "  , unitdict
	return render_template('ShowRealTimeSensor.html', sensorlist=sensorlist, unitdict=unitdict, selectedsensor=selectedsensor)
	
@application.route('/systemmailsetting/', methods=['GET', 'POST'])
def systemmailsetting():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	error = None
	
	if request.method == 'POST':
		print " here we are"
		reqtype = request.form['button']
		if reqtype=="save":
			print "saving email credentials"
			address=request.form['address']
			password=request.form['password']
			isok1=emaildbmod.changesavesetting('address',address)
			isok2=emaildbmod.changesavesetting('password',password)
			if isok1 and isok2:
				flash('Email credentials Saved')   
				return redirect(url_for('show_Calibration'))
		elif reqtype=="cancel":
			return redirect(url_for('show_Calibration'))
	
	password=emaildbmod.getpassword()
	address=emaildbmod.getaddress()
	return render_template('systemmailsetting.html', address=address, password=password)	
	
@application.route('/networksetting/', methods=['GET', 'POST'])
def networksetting():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	error = None
	
	Fake_password="AP-password"
	
	if request.method == 'POST':
		print " here we are at network setting"
		reqtype = request.form['button']
		if reqtype=="save":
			print "saving network advanced setting"
			gotADDRESS=request.form['IPADDRESS']
			AP_SSID=request.form['AP_SSID']
			AP_PASSWORD=request.form['AP_PASSWORD']
			AP_TIME=request.form['AP_TIME']
			
			
			
			# Check
			isok1 , IPADDRESS = networkmod.IPv4fromString(gotADDRESS)
			isok2=False
			isok3=False
			if len(AP_PASSWORD)>7:
				isok2=True
			if len(AP_SSID)>3:
				isok3=True
			
			
			
			
			
			if isok1 and isok2 and isok3:
				
				# previous paramenters
				IPADDRESSold=networkmod.IPADDRESS
				AP_SSIDold=networkmod.localwifisystem	
				AP_TIMEold=str(networkmod.WAITTOCONNECT)
							
				
				print "save in network file in database"
				networkdbmod.changesavesetting('LocalIPaddress',IPADDRESS)
				networkdbmod.changesavesetting('LocalAPSSID',AP_SSID)
				networkdbmod.changesavesetting('APtime',AP_TIME)				

				
				# save and change values in the HOSTAPD config file
				sysconfigfilemod.hostapdsavechangerow("ssid",AP_SSID)
				if AP_PASSWORD!=Fake_password:
					# change password in the HOSTAPD config file
					sysconfigfilemod.hostapdsavechangerow("wpa_passphrase",AP_PASSWORD)
					print "password changed"
				else:
					AP_PASSWORD=""
					
				if IPADDRESSold!=IPADDRESS:
					# save changes in DHCPCD confign file
					sysconfigfilemod.modifydhcpcdconfigfile(IPADDRESSold, IPADDRESS)
		
					# save changes in DNSMASQ confign file				
					sysconfigfilemod.modifydnsmasqconfigfile(IPADDRESSold, IPADDRESS)			
				
				# proceed with changes
				networkmod.applyparameterschange(AP_SSID, AP_PASSWORD, IPADDRESS)
				networkmod.WAITTOCONNECT=AP_TIME
				
				# Change hostapd file first row with HERE
				data=[]
				networkdbmod.readdata(data)
				sysconfigfilemod.hostapdsavechangerow_spec(data)				

				flash('Network setting Saved')   
				return redirect(url_for('network'))
			else:
				if not isok1:
					flash('please input valid IP address','danger') 				
				if not isok2:
					flash('please input password longer than 7 characters','danger') 
				if not isok3:
					flash('please input SSID longer than 3 characters','danger') 
		elif reqtype=="cancel":
			return redirect(url_for('network'))
	


	iplocal=networkmod.get_local_ip()
	IPADDRESS=networkmod.IPADDRESS
	PORT=networkmod.PUBLICPORT
	AP_SSID=networkmod.localwifisystem	
	AP_TIME=str(networkmod.WAITTOCONNECT)	
	connectedssidlist=networkmod.connectedssid()
	if len(connectedssidlist)>0:
		connectedssid=connectedssidlist[0]
	else:
		connectedssid=""	
	AP_PASSWORD=Fake_password



	return render_template('networksetting.html', IPADDRESS=IPADDRESS, AP_SSID=AP_SSID, AP_PASSWORD=AP_PASSWORD, AP_TIME=AP_TIME)	
	


@application.route('/About/', methods=['GET', 'POST'])
def show_about():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	return render_template('About.html',Release=Release)
	
	
@application.route('/ShowCalibration/', methods=['GET', 'POST'])
def show_Calibration():  #on the contrary of the name, this show the setting menu
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print "visualizzazione menu Setting:"
	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="delete":
			#remove the calibration file and read the default
			print "restore hardware default file"
			#hardwaremod.restoredefault()
			wateringdbmod.restoredefault()
			fertilizerdbmod.restoredefault()
			advancedmod.restoredefault()
			emaildbmod.restoredefault()
			networkmod.restoredefault()
			logindbmod.restoredefault()
			cameradbmod.restoredefault()
			# try to align the config to new setting (this is not tested properly, better reboot in this case)
			wateringdbmod.consitencycheck()
			fertilizerdbmod.consitencycheck()
			#scheduler setup---------------------
			selectedplanmod.resetmastercallback()
			#initiate the GPIO OUT pins
			hardwaremod.initallGPIOoutput()	
		
		if requesttype=="editnames":
			return hardwaresettingeditfield()	

	actuatorlist=[]
	actuatorlist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"pulse",hardwaremod.HW_INFO_NAME)
	

	print " actuator list " , actuatorlist
	lightsetting=[]
	lightsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,"light1",hardwaremod.HW_FUNC_TIME))
	photosetting=[]
	photosetting.append(hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_FUNC_TIME))
	photosetting.append(hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_CTRL_LOGIC))
		
	mailelements=emaildbmod.getelementlist()
	mailsettinglist=[]
	for element in mailelements:
		mailsetting=[]
		mailsetting.append(element)
		mailsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_FUNC_TIME))
		mailsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_CTRL_MAILADDR))
		mailsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_CTRL_MAILTITLE))
		mailsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_CTRL_CMD))
		mailsettinglist.append(mailsetting)
		
	# stepper	
	stepperlist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"stepper",hardwaremod.HW_INFO_NAME)
	stepperstatuslist=[]
	for stepper in stepperlist:
		stepperstatuslist.append(hardwaremod.getstepperposition(stepper))	
	# servo
	servolist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"servo",hardwaremod.HW_INFO_NAME)
	servostatuslist=[]
	for servo in servolist:	
		servostatuslist.append(hardwaremod.getservopercentage(servo))	
	servolist.insert(0, "none")
	servostatuslist.insert(0, "None")	
	videolist=hardwaremod.videodevlist()
	camerasettinglist=cameradbmod.getcameradata(videolist)
	print camerasettinglist
	
	
	sensorlist = []
	sensorlist=sensordbmod.gettablelist()
	
	#read the sensors data
	#print "read sensor data " 
	unitdict={}
	for item in sensorlist:
		unitdict[item]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,item,hardwaremod.HW_INFO_MEASUREUNIT)
	print "unitdict "  , unitdict
	
	initdatetime=clockmod.readsystemdatetime()
	
	#timezone
	countries=countryinfo.countries
	timezone=clockdbmod.gettimezone()
	print "Current timezone ->", timezone
	
	
	return render_template('ShowCalibration.html',servolist=servolist,servostatuslist=servostatuslist,stepperlist=stepperlist,stepperstatuslist=stepperstatuslist,videolist=videolist,actuatorlist=actuatorlist, sensorlist=sensorlist,lightsetting=lightsetting,photosetting=photosetting, camerasettinglist=camerasettinglist ,mailsettinglist=mailsettinglist, unitdict=unitdict, initdatetime=initdatetime, countries=countries, timezone=timezone)

	
	
@application.route('/setstepper/', methods=['GET', 'POST'])
def setstepper():  # set the stepper zero point
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print "visualizzazione menu set stepper:"
	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="cancel":
			return redirect(url_for('show_Calibration'))	

	# stepper	
	stepperlist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"stepper",hardwaremod.HW_INFO_NAME)
	stepperstatuslist=[]
	for stepper in stepperlist:
		stepperstatuslist.append(hardwaremod.getstepperposition(stepper))	

	return render_template('setstepper.html',stepperlist=stepperlist,stepperstatuslist=stepperstatuslist)

		
	
@application.route('/Sensordata/', methods=['GET', 'POST'])
def show_sensordata():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	#----------------
	periodlist=["Day","Week","Month","Year"]
	perioddaysdict={"Day":1,"Week":7,"Month":31,"Year":365}	

	periodtype=periodlist[0]
	actiontype="show"
	
	if request.method == 'POST':
		periodtype=request.form['period']	
		actiontype=request.form['actionbtn']
	elif request.method == 'GET':
		periodtype = request.args.get('period')	
		actiontype = request.args.get('actionbtn')	
		if periodtype==None:
			actiontype="show"
			periodtype=periodlist[0]

	sensordata=[]
	if actiontype=="delete":
		print "delete all records"
		sensordbmod.deleteallrow()
		actuatordbmod.deleteallrow()
		actiontype="show"
		periodtype=periodlist[0]
		usedsensorlist=[]
		usedactuatorlist=[]
		sensordata=[]
		actuatordata=[]
		
	else:
	#if actiontype=="sensor":
		sensorlist=sensordbmod.gettablelist()
		startdate=datetime.now()
		#sensordbmod.getSensorDataPeriod(sensortype,sensordata,startdate,perioddaysdict[periodtype])
		sensordata, usedsensorlist, mintime, maxtime = sensordbmod.getAllSensorsDataPeriodv2(startdate,perioddaysdict[periodtype])		

	#if actiontype=="actuator":
		actuatorlist=actuatordbmod.gettablelist()
		startdate=datetime.now()
		#actuatordbmod.getActuatorDataPeriod(sensortype,sensordata,startdate,perioddaysdict[periodtype])
		actuatordata,usedactuatorlist=actuatordbmod.getAllActuatorDataPeriodv2(startdate,perioddaysdict[periodtype])


		#Usedfor="Moisturecontrol"	
		#hygrosensorlist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,Usedfor,hardwaremod.HW_INFO_NAME)
		hygroactuatornumlist=[]
		hygrosensornumlist=[]
		actuatorlisth= autowateringdbmod.getelementlist()
		for inde in range(len(usedactuatorlist)):
			element=usedactuatorlist[inde]
			if element in actuatorlisth:
				linkedsensor=autowateringdbmod.gethygrosensorfromactuator(element)
				if linkedsensor in usedsensorlist: # if the actuator has an associated sensor hygro
					hygroactuatornumlist.append(inde)
					hygrosensornumlist.append(usedsensorlist.index(linkedsensor))
				
		print "hygrosensornumlist " , hygrosensornumlist
		print "hygroactuatornumlist " , hygroactuatornumlist
	return render_template('showsensordata.html',actiontype=actiontype,periodtype=periodtype,periodlist=periodlist,usedsensorlist=usedsensorlist,sensordata=json.dumps(sensordata),usedactuatorlist=usedactuatorlist,actuatordata=json.dumps(actuatordata), hygrosensornumlist=hygrosensornumlist, hygroactuatornumlist=hygroactuatornumlist)


@application.route('/wateringplan/' , methods=['GET', 'POST'])
def wateringplan():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	title = "Watering Schedule"
	elementlist= wateringdbmod.getelementlist()	
	paramlist= wateringdbmod.getparamlist()
	table=wateringdbmod.gettable(1) # watering time multiplieer
	table1=wateringdbmod.gettable(0) # watering schema
	table2=wateringdbmod.gettable(2) # watering time delay
	
	#advparamlist= advancedmod.getparamlist()
	schemaementlist= advancedmod.getelementlist()

	
	print "table  --------------------------------------------------- > ",  table
	print "table1  --------------------------------------------------- > ",  table1
	print "table2  --------------------------------------------------- > ",  table2
		
	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		if elementlist:
			selectedelement=elementlist[0]	
	
	print " watering plan - selectedelement ", selectedelement
	
	if request.method == 'POST':	
		actiontype=request.form['actionbtn']
		print actiontype
		
		if actiontype == "save":
			element=request.form['element']
			print "save il water form...:" , element
			selectedelement=element	
			
			
			#add proper formatting
			dicttemp={}
			dicttemp["element"]=element
			for j in range(len(paramlist)):
				thelist=[]
				selectedschema=request.form[element+ "_" + str(j) + "_0"]
				schemaindex=schemaementlist.index(selectedschema)+1			
				thelist.append(schemaindex)
				thelist.append(request.form[element+ "_" + str(j)])
				thelist.append(request.form[element+ "_" + str(j) + "_1"]) #name of the time delay input filed
				param=paramlist[j]
				dicttemp[param]=thelist	
				
			wateringdbmod.replacerow(element,dicttemp)		
			flash('Table as been saved')
			table=wateringdbmod.gettable(1) # watering time multiplieer
			table1=wateringdbmod.gettable(0) # watering schema
			table2=wateringdbmod.gettable(2) # watering schema
			#print "after",table
			selectedplanmod.resetmastercallback()
			
		if actiontype == "advconfig":	
			print "open advanced setting"
			return redirect('/Advanced/')
			
		
	return render_template("wateringplan.html", title=title,paramlist=paramlist,elementlist=elementlist,schemaementlist=schemaementlist,table=table,table1=table1,table2=table2,selectedelement=selectedelement)



@application.route('/autowatering/' , methods=['GET', 'POST'])
def autowatering():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	title = "Auto Watering Setting"
	elementlist= autowateringdbmod.getelementlist()		
	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		selectedelement=elementlist[0]	
	

	sensorlist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,"Moisture",hardwaremod.HW_INFO_NAME)	
	#sensorlist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,"Moisturecontrol",hardwaremod.HW_INFO_NAME)
	print "sensorlist ",sensorlist
	
	modelist=["None", "Full Auto" , "Emergency Activation" , "Alert Only"]
	formlist=["workmode", "sensor" , "threshold", "wtstepsec", "maxstepnumber", "pausebetweenwtstepsmin", "allowedperiod" , "maxdaysbetweencycles", "sensorminacceptedvalue", "mailalerttype"  ]
	alertlist=["infoandwarning", "warningonly"]


	
	if request.method == 'POST':	
		actiontype=request.form['actionbtn']
		print actiontype
		
		if actiontype == "save":
			element=request.form['element']
			print "save il water form...:" , element
			selectedelement=element	
			
			
			#add proper formatting
			dicttemp={}
			dicttemp["element"]=element		
			dicttemp["workmode"]=request.form[element+'_1']
			dicttemp["sensor"]=request.form[element+'_2']
			dicttemp["threshold"]=[request.form[element+'_3'],request.form[element+'_4']]
			dicttemp["wtstepsec"]=request.form[element+'_5']
			dicttemp["maxstepnumber"]=request.form[element+'_6']
			dicttemp["pausebetweenwtstepsmin"]=request.form[element+'_7']
			dicttemp["allowedperiod"]=[request.form[element+'_8'],request.form[element+'_9']]
			dicttemp["maxdaysbetweencycles"]=request.form[element+'_10']
			dicttemp["sensorminacceptedvalue"]=request.form[element+'_11']
			dicttemp["mailalerttype"]=request.form[element+'_12']

			print "dicttemp ----->",dicttemp 
			autowateringdbmod.replacerow(element,dicttemp)		
			flash('Table as been saved')

			#selectedplanmod.resetmastercallback()
			
			
		if actiontype == "reset":
			element=request.form['element']
			print "Reset the Cycle:" , element
			selectedelement=element	
			autowateringmod.cyclereset(element)
			
			

			
			
			
	watersettinglist=[]
	for element in elementlist:
		watersetting=[]
		watersetting.append(element)
		for item in formlist:
			watersetting.append(autowateringdbmod.searchdata("element",element,item))

		watersettinglist.append(watersetting)
	
	
	cyclestatuslist=[]
	for element in elementlist:
		if not (element in autowateringmod.AUTO_data):
			autowateringmod.cyclereset(element)
		cyclestatus=[]		
		cyclestatus.append(autowateringmod.AUTO_data[element]["cyclestartdate"].strftime("%Y-%m-%d %H:%M:%S"))
		cyclestatus.append(autowateringmod.AUTO_data[element]["cyclestatus"])
		cyclestatus.append(autowateringmod.AUTO_data[element]["watercounter"])
		cyclestatus.append(autowateringmod.AUTO_data[element]["alertcounter"])		
		#{"cyclestartdate":datetime.utcnow(),"lastwateringtime":datetime.utcnow(),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}
		cyclestatuslist.append(cyclestatus)


		
	return render_template("autowatering.html", title=title,selectedelement=selectedelement,modelist=modelist,sensorlist=sensorlist,watersettinglist=watersettinglist, cyclestatuslist=cyclestatuslist)




@application.route('/automation/' , methods=['GET', 'POST'])
def automation():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	title = "Auto Watering Setting"
	elementlist= automationdbmod.getelementlist()		
	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		selectedelement=elementlist[0]	
	

	sensorlist=automationdbmod.sensorlist()	
	#sensorlist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,"Moisturecontrol",hardwaremod.HW_INFO_NAME)
	print "sensorlist ",sensorlist
	
	modelist=["None", "Full Auto" , "Emergency Activation" , "Alert Only"]
	formlist=["workmode", "sensor" , "sensor_threshold", "actuator_threshold", "stepnumber", "pausebetweenwtstepsmin", "averagesample", "allowedperiod" , "mailalerttype"  ]
	alertlist=["infoandwarning", "warningonly"]


	
	if request.method == 'POST':	
		actiontype=request.form['actionbtn']
		print actiontype
		
		if actiontype == "save":
			element=request.form['element']
			print "save il form...:" , element
			selectedelement=element	
			
			
			#add proper formatting
			dicttemp={}
			dicttemp["element"]=element		
			dicttemp["workmode"]=request.form[element+'_1']
			dicttemp["sensor"]=request.form[element+'_2']
			dicttemp["sensor_threshold"]=[request.form[element+'_3_1'],request.form[element+'_3_2']]
			dicttemp["actuator_threshold"]=[request.form[element+'_4_1'],request.form[element+'_4_2']]
			dicttemp["stepnumber"]=request.form[element+'_5']
			dicttemp["pausebetweenwtstepsmin"]=request.form[element+'_6']
			dicttemp["averagesample"]=request.form[element+'_7']			
			dicttemp["allowedperiod"]=[request.form[element+'_8_1'],request.form[element+'_8_2']]
			dicttemp["mailalerttype"]=request.form[element+'_9']

			print "dicttemp ----->",dicttemp 
			automationdbmod.replacerow(element,dicttemp)		
			flash('Table as been saved')

			#selectedplanmod.resetmastercallback()
			
			
		if actiontype == "reset":
			element=request.form['element']
			print "Reset the Cycle:" , element
			selectedelement=element	
			automationmod.cyclereset(element)
			
			

			
			
			
	watersettinglist=[]
	for element in elementlist:
		watersetting=[]
		watersetting.append(element)
		for item in formlist:
			watersetting.append(automationdbmod.searchdata("element",element,item))

		watersettinglist.append(watersetting)
	
	
	cyclestatuslist=[]
	for element in elementlist:
		if not (element in automationmod.AUTO_data):
			automationmod.cyclereset(element)
		cyclestatus=[]		
		cyclestatus.append(automationmod.AUTO_data[element]["lastactiontime"].strftime("%Y-%m-%d %H:%M:%S"))
		cyclestatus.append(automationmod.AUTO_data[element]["status"])
		cyclestatus.append(automationmod.AUTO_data[element]["actionvalue"])
		cyclestatus.append(automationmod.AUTO_data[element]["alertcounter"])		
		#{"cyclestartdate":datetime.utcnow(),"lastwateringtime":datetime.utcnow(),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}
		cyclestatuslist.append(cyclestatus)


		
	return render_template("automation.html", title=title,selectedelement=selectedelement,modelist=modelist,sensorlist=sensorlist,watersettinglist=watersettinglist, cyclestatuslist=cyclestatuslist)








@application.route('/fertilizerplan/' , methods=['GET', 'POST'])
def fertilizerplan():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	title = "Fertilizer Schedule"
	elementlist=fertilizerdbmod.getelementlist()	
	paramlist= fertilizerdbmod.getparamlist()
	argumentnumber=2
	table=fertilizerdbmod.gettable(1)	
	table1=fertilizerdbmod.gettable(0)
	
	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		if elementlist:
			selectedelement=elementlist[0]	
	
	# Autofertilizer Function START
	
	#sensorlist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,"Moisture",hardwaremod.HW_INFO_NAME)	
	linkemelementlist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,"watercontrol",hardwaremod.HW_INFO_NAME)
	print "linkemelementlist ",linkemelementlist
	
	modelist=["SceduledTime","BeforeWatering"]
	formlist=["workmode","waterZone","minactivationsec","time"]
	#alertlist=["infoandwarning", "warningonly"]


	

	# Autofertilizer function END
	
	if request.method == 'POST':	
		actiontype=request.form['actionbtn']
		print actiontype
		
		if actiontype == "save":
			element=request.form['element']
			print "save il fertilizer form...:" , element
			selectedelement=element
			#add proper formatting
			dicttemp={}
			dicttemp["element"]=element
			for j in range(len(paramlist)):
				thelist=[]
				thelist.append(request.form[element+ "_" + str(j) + "_0"])
				thelist.append(request.form[element+ "_" + str(j)])
				param=paramlist[j]
				dicttemp[param]=thelist				
				
			fertilizerdbmod.replacerow(element,dicttemp)		
			table=fertilizerdbmod.gettable(1)	
			table1=fertilizerdbmod.gettable(0)
			#print "after",table
			selectedplanmod.resetmastercallback()
			
			
			#add proper formatting for the Autofertilizer
			dicttemp={}
			dicttemp["element"]=element		
			dicttemp["workmode"]=request.form[element+'_param1']
			dicttemp["waterZone"]=request.form[element+'_param2']
			dicttemp["minactivationsec"]=request.form[element+'_param3']
			dicttemp["time"]=request.form[element+'_param4']

			print "dicttemp ----->",dicttemp 
			autofertilizerdbmod.replacerow(element,dicttemp) #modify autofertilizer row
			flash('Table as been saved')

		if actiontype == "advconfig":	
			print "open advanced setting"
			return redirect('/Advanced/')
			
	
			
	fertilizersettinglist=[]
	for element in elementlist:
		fertilizersetting=[]
		fertilizersetting.append(element)
		for item in formlist:
			fertilizersetting.append(autofertilizerdbmod.searchdata("element",element,item))

		fertilizersettinglist.append(fertilizersetting)
	
	return render_template("fertilizerplan.html", title=title,paramlist=paramlist,elementlist=elementlist,table=table,table1=table1, selectedelement=selectedelement, formlist=formlist , fertilizersettinglist=fertilizersettinglist , linkemelementlist=linkemelementlist, modelist=modelist)



@application.route('/Advanced/', methods=['GET', 'POST'])
def advanced():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	title = "Advanced Watering Schedule"
	paramlist= advancedmod.getparamlist()
	elementlist= advancedmod.getelementlist()
	table=advancedmod.gettable()
	tablehead=advancedmod.gettableheaders()

	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		selectedelement=elementlist[0]
	#print  "table  " ,table

    
	if request.method == 'POST':	
		actiontype=request.form['actionbtn']
		print actiontype
		
		if actiontype == "save":


			element=request.form['element']
			print "save advanced form...:" , element
			selectedelement=element	


			table=advancedmod.gettable()
			#print "before",table

			paramlist= advancedmod.getparamlist()
			elementlist= advancedmod.getelementlist()
			tablehead=advancedmod.gettableheaders()
			

			#add proper formatting
			dicttemp={}
			dicttemp["name"]=element
			# table includes all the elements: Element, Parameters, rows, columns
			# element is fixed and not relevent for save procedure
			a=-1
			for param in table[elementlist.index(element)]:
				a=a+1
				b=-1
				listrowtemp=[]
				for rowp in param:
					b=b+1
					c=-1
					listcoltemp=[]
					for colp in rowp:
						c=c+1
						#print "cursore" , element+paramlist[a]+ "_" + str(b) + str(c)
						strtemp = request.form[element+paramlist[a]+ "_" + str(b) + str(c)]
						listcoltemp.append(strtemp)
					listrowtemp.append(listcoltemp)
						
				dicttemp[paramlist[a]]= listrowtemp
				
			#print "dicttemp ", dicttemp 
			advancedmod.replacerow(element,dicttemp)

			print "Table saved"
			flash('Table as been saved')
			
			table=advancedmod.gettable()
			#print "after",table
			title = "Advanced Setting"


		if actiontype == "setdefault":	
			advancedmod.restoredefault()
			print "default restored"
			flash('Default values have been set')
    
    
    
    
	return render_template("advanced.html", title=title,paramlist=paramlist,elementlist=elementlist,table=table,tablehead=tablehead,selectedelement=selectedelement)


	
@application.route('/login', methods=['GET', 'POST'])
def login():

	error = None
	change=False
	username=logindbmod.getusername().lower() #always transform to lowercase
	password=logindbmod.getpassword()
	
	if request.method == 'POST':
		print " LOGIN " , username
		reqtype = request.form['button']
		if reqtype=="login":
			usernameform=request.form['username'].lower()
			passwordform=request.form['password']
			if (usernameform != username) or (passwordform != password):
				error = 'Invalid Credentials'
			else:
				session['logged_in'] = True
				#flash('You were logged in')   
				return redirect(url_for('show_entries'))

		elif reqtype=="change":
			print "Display change password interface"
			change=True
						
		elif reqtype=="save":
			print "saving new login password"
			usernameform=request.form['username'].lower()
			passwordform=request.form['password']
			newpassword=request.form['newpassword']
			if (usernameform != username) or (passwordform != password):
				error = 'Invalid Credentials'
				change=True
			else:
				isok1=logindbmod.changesavesetting('password',newpassword)
				if isok1:
					flash('New Password Saved')   
					return redirect(url_for('show_entries'))
				
		elif reqtype=="cancel":
			return redirect(url_for('show_entries'))

	return render_template('login.html', error=error, change=change)	




@application.route('/logout')
def logout():
    session.pop('logged_in', None)
    #flash('You were logged out')
    return redirect(url_for('show_entries'))


@application.route('/HardwareSetting/', methods=['GET', 'POST'])
def hardwaresetting():  #on the contrary of the name, this show the setting menu
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print "visualizzazione menu hardwareSetting:"
	
	fields=hardwaremod.HWdataKEYWORDS
	hwdata=hardwaremod.IOdata
	debugmode=DEBUGMODE

	tablehead=[]
	for key, value in fields.iteritems():
		tablehead.append(key)
	#print "tablehead ", tablehead
	
	HWfilelist=hardwaremod.HWpresetlist(MYPATH) #list of fiels (path , Name)
	presetfilenamelist=[]
	presetfilenamelist.append("-No Selection-")
	for item in HWfilelist:
		presetfilenamelist.append(item[1])		
	#print "HW file list ---> ", HWfilelist
	
	if request.method == 'POST':
		requestinfo=request.form['buttonsub']
		requesttype=requestinfo.split("_")[0]
		print "requesttype "  , requestinfo , " " , requesttype
		
				
				
		if requesttype=="applyHWpreset":
			print "Apply HW setting"
			selectedpath=""
			selectedfilename=request.form['HWfilelist']
			for items in HWfilelist:
				if items[1]==selectedfilename:
					selectedpath=items[0]

			isdone=False
			if selectedpath!="":
			
				# copy file to the default HWdata
				filename=os.path.join(MYPATH, selectedpath)
				folderpath=os.path.join(MYPATH, hardwaremod.DATABASEPATH)
				dstdef=os.path.join(folderpath, hardwaremod.DEFHWDATAFILENAME)
				print "Source selected path ", filename , " Destination ", dstdef


				try:
					shutil.copyfile(filename, dstdef) #this is the default HW file
					answer="ready"
					isdone=True
				except:

					answer="problem copying file"
			else:
				print "No file was selected"				
				answer="No file selected"
				
				
			# apply changes to the system
			if isdone:
				hardwaremod.restoredefault() # copy default to normal file and reload HWdata
				runallconsistencycheck()
				#scheduler setup---------------------
				selectedplanmod.resetmastercallback()
				#initiate the GPIO OUT pins
				hardwaremod.initallGPIOoutput()			

		if requesttype=="edit":
			return hardwaresettingedit()


	return render_template('hardwaresetting.html',fields=fields, hwdata=json.dumps(hwdata), tablehead=tablehead , presetfilenamelist=presetfilenamelist, debugmode=debugmode)



@application.route('/HardwareSettingedit/', methods=['GET', 'POST'])
def hardwaresettingedit():  #on the contrary of the name, this show the setting menu
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print "visualizzazione menu hardwareSettingedit:"

	
	fields=hardwaremod.HWdataKEYWORDS


	tablehead=[]
	for key, value in fields.iteritems():
		tablehead.append(key)
	#print "tablehead ", tablehead

	if request.method == 'POST':
		requestinfo=request.form['buttonsub']
		requesttype=requestinfo.split("_")[0]
		print "requesttype POST "  , requestinfo , " " , requesttype

		if requestinfo=="edit":
			#request coming from previous page, need init table from zero
			print "the teporary Tables have been reset"
			#initialize IOdatarow
			hardwaremod.additionalRowInit()

			# Alignt the hardwaremod IOdatatemp to IOdata
			hardwaremod.IOdatatempalign()

				
		if requesttype=="confirm":
			print "Confirm table"
			# Copy the hardwaremod IOdatatemp to IOdata and save it
			hardwaremod.IOdatafromtemp()	
				
			# apply changes to the system
			runallconsistencycheck()
			#scheduler setup---------------------
			selectedplanmod.resetmastercallback()
			#initiate the GPIO OUT pins
			hardwaremod.initallGPIOoutput()	
			return redirect(url_for('hardwaresetting'))

		if requesttype=="reload":	
			hardwaremod.IOdatatempalign()

		if requesttype=="cancel":
			return redirect(url_for('hardwaresetting'))
						
		if requesttype=="delete":
			name=requestinfo.split("_")[1]
			#remove the row in IOdatatemp
			print " Delete ", name
			if hardwaremod.deleterow(name):
				flash('Row has been correctly deleted')
				print " deleted"
			else:
				flash('Errors to delelte the row','danger')
			
				
		if requesttype=="addrow":
			dictrow=hardwaremod.IOdatarow
			isok, message = hardwaremod.checkdata("",dictrow)
			if isok:
				hardwaremod.addrow(dictrow)
				flash('Row has been correctly Added')
				ret_data = {"answer":"Added"}
			else:
				print "problem ", message
				flash(message,'danger')
				ret_data = {"answer":"Error"}


#	return render_template('hardwaresettingedit.html',fields=fields, hwdata=json.dumps(hwdata), tablehead=tablehead , HWfilelist=HWfilelist)

	hwdata=hardwaremod.IOdatatemp
	additionalrow=hardwaremod.IOdatarow

	return render_template('hardwaresettingedit.html',fields=fields, hwdata=hwdata, tablehead=tablehead , additionalrow=additionalrow)

@application.route('/hardwaresettingeditfield/', methods=['GET', 'POST'])
def hardwaresettingeditfield():  #on the contrary of the name, this show the setting menu
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print "visualizzazione menu hardwareSettingedit:"

	
	fields=hardwaremod.HWdataKEYWORDS


	tablehead=[]
	#for key, value in fields.iteritems():
	#	tablehead.append(key)
	#print "tablehead ", tablehead
	tablehead=[hardwaremod.HW_INFO_NAME]


	if request.method == 'POST':
		requestinfo=request.form['buttonsub']
		requesttype=requestinfo.split("_")[0]
		print "requesttype POST "  , requestinfo , " " , requesttype

		if requestinfo=="edit":
			#request coming from previous page, need init table from zero
			print "the teporary Tables have been reset"

			# Alignt the hardwaremod IOdatatemp to IOdata
			hardwaremod.IOdatatempalign()

				
		if requesttype=="confirm":
			print "Confirm table"
			# get the diferences in name field
			newnames=[]
			hardwaremod.getfieldvaluelisttemp("name",newnames)
			oldnames=[]
			hardwaremod.getfieldvaluelist("name",oldnames)
			print newnames
			print oldnames
			
			# Copy the hardwaremod IOdatatemp to IOdata and save it
			hardwaremod.IOdatafromtemp()	
				
			# apply changes to the system
			# basically instead of the consistencycheck procedure it should be simply the rename procedure -- Done

			autowateringdbmod.replacewordandsave(oldnames,newnames)
			wateringdbmod.replacewordandsave(oldnames,newnames)
			autofertilizerdbmod.replacewordandsave(oldnames,newnames)
			fertilizerdbmod.replacewordandsave(oldnames,newnames)
			automationdbmod.replacewordandsave(oldnames,newnames)			
			sensordbmod.consistencycheck()
			actuatordbmod.consistencycheck()
			#scheduler setup---------------------
			selectedplanmod.resetmastercallback()
			#initiate the GPIO OUT pins
			hardwaremod.initallGPIOoutput()	
			return redirect(url_for('show_Calibration'))

		if requesttype=="reload":	
			hardwaremod.IOdatatempalign()

		if requesttype=="cancel":
			return redirect(url_for('show_Calibration'))


#	return render_template('hardwaresettingedit.html',fields=fields, hwdata=json.dumps(hwdata), tablehead=tablehead , HWfilelist=HWfilelist)

	hwdata=hardwaremod.IOdatatemp

	return render_template('hardwaresettingeditfield.html',fields=fields, hwdata=hwdata, tablehead=tablehead )




@application.route('/HWsettingEditAjax/', methods=['GET','POST'])
def HWsettingEditAjax():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login Needed"}
		return jsonify(ret_data)

	
    
	recdata=[]
	ret_data={}
	if request.method == 'POST':
		print "we are in the HWsettingEdit"
		pk = request.form['pk']
		value = request.form['value']
		name = request.form['name']
		print "request type : " , pk , "  " , value , "  " , name		
		
		IOname=pk
		if IOname=="addrow":
			dictrow=hardwaremod.IOdatarow	
		else:		
			dictrow=hardwaremod.searchrowtempbyname(IOname)
		dictrow[name]=value		
		fieldtocheck=name
		
		#print "Dictrow: " ,dictrow
		#print "IOdatatemp: " , hardwaremod.IOdatatemp
		isok, message = hardwaremod.checkdata(fieldtocheck,dictrow)
					
				

	notok=False
	if isok:
		print "data is OK"
		#modify the IOdatatemp matrix
		if IOname=="addrow":
			hardwaremod.IOdatarow[name]=value
			#print "row: " , hardwaremod.IOdatarow
		else:
			isfound=hardwaremod.changeIOdatatemp(IOname,name,value) 
		
		#print "item found " , isfound
		#print "IOdatatemp: " , hardwaremod.IOdatatemp

		
		ret_data = {"answer": message}
		return jsonify(ret_data)
	else:
		print "data NOK ", message
		ret_data = message
		return ret_data,400




def currentpath(filename):
	return os.path.join(MYPATH, filename)


def functiontest():
	print " testing "
	#mailname="mail1"
	testo=[" riga 1 ", "riga 2 " , " Riga fine"]
	emailmod.sendallmail("alert","prova mail", testo)
	#autofertilizermod.AUTO_data["doser1"]["tobeactivated"]=True
	#autofertilizermod.AUTO_data["doser1"]["duration"]=5000
	#autowateringmod.activatewater("water2", 50000)
	
	#startdate=datetime.strptime('Sep 7 2018  5:00AM', '%b %d %Y %I:%M%p')
	#enddate=datetime.strptime('Sep 7 2018  8:00AM', '%b %d %Y %I:%M%p')
	#slopeOK=autowateringmod.checkinclination("hygroBalcFront",startdate,enddate)
	#print "got array " , slopeOK
	
	#selectedplanmod.heartbeat()
	sensorname="hygroBalcFrontR"
	selectedplanmod.periodicdatarequest(sensorname)
	
	#selectedplanmod.removeallscheduledjobs()
	#hardwaremod.takephoto()

	message = "OK"

	return message

# video part ---------------------------------- hello -------------------------------
import videocontrolmod

@application.route('/videostream/')
def videostream():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	itemlist=['video0','b']
	"""Video streaming home page."""
	ipaddress=networkmod.get_local_ip()
	videolist=hardwaremod.videodevlist()
	servolist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"servo",hardwaremod.HW_INFO_NAME)
	initposition=hardwaremod.getservopercentage(servolist[0])
	vdirection=hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_CTRL_LOGIC)
	if vdirection=="neg":
		rotdeg="180"
	else:
		rotdeg="0"
	return render_template('videostream.html',initposition=initposition, itemlist=itemlist, ipaddress=ipaddress, videolist=videolist, servolist=servolist, rotdeg=rotdeg)


@application.route('/videocontrol/', methods=['GET'])
def videocontrol():
	if not session.get('logged_in'):
		ret_data = {"answer":"login"}
		videocontrolmod.stop_stream()
		return jsonify(ret_data)
    # this is used for debugging purposes, activate the functiontest from web button
	ret_data={}
	cmd=""
	sendstring=""
	argumentlist=request.args.getlist('name')
	name=argumentlist[0]

	if name=="testing":
		print "testing video stop"
		answer="done"		
		answer=videocontrolmod.stream_video()
		
	if name=="start":
		idx=1
		data=""
		print "argument list ", argumentlist
		while idx < len(argumentlist):
			data=data+"x"+argumentlist[idx]
			idx=idx+1
		data=data[1:]
		print data
		element=request.args['element']	
		print "element " , element
		print "starting Stream " , data
		vdirection=hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_CTRL_LOGIC)
		answer=videocontrolmod.stream_video(element,data) + "-" + element
		time.sleep(2)
		

	if name=="close":
		print "Closing mjpg-streamer server"
		videocontrolmod.stop_stream()
		answer="closed"

	if name=="stop":
		print "Stop mjpg-streamer server"
		videocontrolmod.stop_stream()
		answer="stopped"


	ret_data = {"answer": answer}
	print "response data ", ret_data
	return jsonify(ret_data)
	

#if __name__ == '__main__':  
#    application.run(host='0.0.0.0', debug=True, threaded=True)


# END ---------------------------------video part ---------------------------






	
if __name__ == '__main__':
	

	# start web server--------------- -------------------------
	print "start web server"	
	global PUBLICPORT
	if PUBLICMODE:
		application.run(debug=DEBUGMODE,use_reloader=False,host= '0.0.0.0',port=networkmod.LOCALPORT)
		#application.run(host='0.0.0.0', debug=True, port=12345, use_reloader=True)
	else:
		application.run(debug=DEBUGMODE,use_reloader=False,port=80)	

	print "close"
	selectedplanmod.stop()
