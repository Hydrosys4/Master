# -*- coding: utf-8 -*-
"""
Flaskr
~~~~~~

A microblog example application written as Flask tutorial with
Flask and sqlite3.

:copyright: (c) 2010 by Armin Ronacher.
:license: BSD, see LICENSE for more details.
"""
from loggerconfig import LOG_SETTINGS
import logging, logging.config, logging.handlers
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
import plandbmod
import sensordbmod
import actuatordbmod
import selectedplanmod
import wateringdbmod
import fertilizerdbmod
import advancedmod
import networkmod
import emailmod
import emaildbmod
import logindbmod
import clockmod
import clockdbmod
import countryinfo
import cameradbmod

# Raspberry Pi camera module (requires picamera package)
from camera_pi import Camera

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////
application = Flask(__name__)
application.config.from_object('flasksettings') #read the configuration variables from a separate module (.py) file
global SELTABLENAME
SELTABLENAME=""
global DEBUGMODE
DEBUGMODE=False
global PUBLICMODE
PUBLICMODE=True
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
global MYPATH
print "path ",hardwaremod.get_path()
MYPATH=hardwaremod.get_path()

wateringdbmod.consitencycheck()
fertilizerdbmod.consitencycheck()
#scheduler setup---------------------
selectedplanmod.start()
selectedplanmod.setmastercallback()

#setup network connecton --------------------
try:
	print "start networking"
	networkmod.init_network()
except:
	print "No WiFi available"
	
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
		referencestr=photolist[0][0].split("@")[0]
		for items in photolist:
			if items[0].split("@")[0]==referencestr:
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

	panelinfolist=[]
	
	# temperature panels -------------------------------------------- (new version)
	MeasureType="Temperature"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/temperature-transp.png"
		paneldict["color"]="green"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=name
		paneldict["active"]="yes"
		sensordata=[]
		sensordbmod.getsensordbdatadays(name,sensordata,1)
		#set date interval for average
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
		paneldict["average"]=str('%.1f' % evaluateddata["average"])
		paneldict["min"]=str('%.1f' % evaluateddata["min"])
		paneldict["max"]=str('%.1f' % evaluateddata["max"])
		paneldict["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
		panelinfolist.append(paneldict)



	# humidity panel --------------------------------------------
	MeasureType="Humidity"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/humidity-transp.png"
		paneldict["color"]="primary"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=name
		paneldict["active"]="yes"
		sensordata=[]
		sensordbmod.getsensordbdatadays(name,sensordata,1)
		#set date interval for average
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
		paneldict["average"]=str('%.1f' % evaluateddata["average"])
		paneldict["min"]=str('%.1f' % evaluateddata["min"])
		paneldict["max"]=str('%.1f' % evaluateddata["max"])
		paneldict["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
		panelinfolist.append(paneldict)
	
	

	# pressure panel --------------------------------------------
	MeasureType="Pressure"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/pressure-transp.png"	
		paneldict["color"]="yellow"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=name
		paneldict["active"]="yes"
		sensordata=[]
		sensordbmod.getsensordbdatadays(name,sensordata,1)
		#set date interval for average
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
		paneldict["average"]=str('%.1f' % evaluateddata["average"])
		paneldict["min"]=str('%.1f' % evaluateddata["min"])
		paneldict["max"]=str('%.1f' % evaluateddata["max"])
		paneldict["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
		panelinfolist.append(paneldict)
	
	
	

	# light panel --------------------------------------------
	MeasureType="Light"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/light-transp.png"		
		paneldict["color"]="red"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=name
		paneldict["active"]="yes"
		sensordata=[]
		sensordbmod.getsensordbdatadays(name,sensordata,1)
		#set date interval for average
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
		paneldict["average"]=str('%.1f' % evaluateddata["average"])
		paneldict["min"]=str('%.1f' % evaluateddata["min"])
		paneldict["max"]=str('%.1f' % evaluateddata["max"])
		paneldict["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
		panelinfolist.append(paneldict)	
	
	
	
	# Hygrometer panel --------------------------------------------
	MeasureType="Moisture"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/moisture-transp.png"	
		paneldict["color"]="primary"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
		paneldict["subtitle"]=name
		paneldict["active"]="yes"
		sensordata=[]
		sensordbmod.getsensordbdatadays(name,sensordata,1)
		#set date interval for average
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
		paneldict["average"]=str('%.1f' % evaluateddata["average"])
		paneldict["min"]=str('%.1f' % evaluateddata["min"])
		paneldict["max"]=str('%.1f' % evaluateddata["max"])
		paneldict["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
		panelinfolist.append(paneldict)	
	


	# watertap panel --------------------------------------------
	usedfor="watercontrol"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/watertap-transp.png"		
		paneldict["color"]="primary"	
		paneldict["type"]="actuator"		
		paneldict["link"]=url_for('wateringplan' , selectedelement=name)
		paneldict["linktitle"]="Go to WateringPlan"
		paneldict["title"]=name
		paneldict["active"]="yes"
		sensordata=[]
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		data=[]
		actuatordbmod.getActuatordbdata(name,data)
		evaluateddata=sensordbmod.EvaluateDataPeriod(data,starttime,endtime)	#set date interval for average
		paneldict["average"]=str('%.1f' % (evaluateddata["sum"]/1000))
		paneldict["min"]=""
		paneldict["max"]=""
		paneldict["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
		panelinfolist.append(paneldict)	
	


	# fertilizer panel --------------------------------------------
	usedfor="fertilizercontrol"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_NAME)
	#print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/fertilizer-transp.png"		
		paneldict["color"]="green"	
		paneldict["type"]="actuator"		
		paneldict["link"]=url_for('fertilizerplan' , selectedelement=name)
		paneldict["linktitle"]="Go to FertilizerPlan"
		paneldict["title"]=name
		paneldict["active"]="yes"
		sensordata=[]
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		data=[]
		actuatordbmod.getActuatordbdata(name,data)
		evaluateddata=sensordbmod.EvaluateDataPeriod(data,starttime,endtime)	#set date interval for average
		paneldict["average"]=str('%.1f' % (evaluateddata["sum"]/1000))
		paneldict["min"]=""
		paneldict["max"]=""
		paneldict["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)		
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


	wifilistencr=["s","a","d"]
	wifilist=networkmod.wifilist_ssid()
	iplocal=networkmod.get_local_ip()
	iplocalwifi=networkmod.IPADDRESS
	ipport=networkmod.PUBLICPORT
	connectedssidlist=networkmod.connectedssid()
	if len(connectedssidlist)>0:
		connectedssid=connectedssidlist[0]
	else:
		connectedssid=""
	
	savedssid=networkmod.savedwifilist_ssid()
	
	savedwifilist=[]
	for ssid in wifilist:
		if ssid in savedssid:
			savedwifilist.append("Saved")
		else:
			savedwifilist.append("Unknown")
		
		
	
	localwifisystem=networkmod.localwifisystem


	return render_template('network.html',filenamelist=filenamelist, connectedssid=connectedssid,localwifisystem=localwifisystem, wifilist=wifilist, wifilistencr=wifilistencr,savedwifilist=savedwifilist, iplocal=iplocal, iplocalwifi=iplocalwifi , ipport=ipport)



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
			networkmod.removewifi(ssid)
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
    # read from serial the values for arduino

	teperatura=string.join(random.choice(string.digits) for x in range(2)).replace(" ", "")
	light=string.join(random.choice(string.digits) for x in range(2)).replace(" ", "")
		
	#ret_data = {"tempsensor1": "1", "humidsensor1": "20"}
	
	ret_data = hardwaremod.readallsensors()

	print ret_data
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
		#answer=hardwaremod.makepulse(element,testpulsetime)
		answer=selectedplanmod.pulsenutrient(element,testpulsetime)
		ret_data = {"answer": answer}

	elif name=="servo":
		print "want to test servo"
		idx=1
		if idx < len(argumentlist):
			position=argumentlist[idx]
		servo=request.args.getlist('servo')[0]		
		print "Servo ", servo , " position ", position
		# move servo
		delay=0.1
		hardwaremod.servoangle(servo,position,delay)
		ret_data = {"answer": position}


	elif name=="photo":
		print "want to test photo"
		idx=1
		if idx < len(argumentlist):
			video=argumentlist[idx]
		resolution=request.args.getlist('resolution')[0]
		position=request.args.getlist('position')[0]
		servo=request.args.getlist('servo')[0]
		print "resolution ", resolution , " position ", position
		positionlist=position.split(",")
		print "oly use the first position for testing " , positionlist[0]
		# move servo
		hardwaremod.servoangle(servo,positionlist[0],1)
		# take picture
		ret_data=hardwaremod.shotit(video,True,resolution,positionlist[0])
		
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
	print "Saving .."
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
		print "save photo setting, time=" , phototime
		hardwaremod.changesavecalibartion(name,hardwaremod.HW_FUNC_TIME,phototime)
		
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
    # send command to the actuator for test
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
	unitdict={}
	for item in sensorlist:
		unitdict[item]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,item,hardwaremod.HW_INFO_MEASUREUNIT)
	print "unitdict "  , unitdict
	return render_template('ShowRealTimeSensor.html', sensorlist=sensorlist, unitdict=unitdict)
	
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
	

@application.route('/About/', methods=['GET', 'POST'])
def show_about():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	return render_template('About.html')
	
	
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
			selectedplanmod.setmastercallback()
			#initiate the GPIO OUT pins
			hardwaremod.initallGPIOoutput()		

	actuatorlist=[]
	actuatorlist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"pulse",hardwaremod.HW_INFO_NAME)
	print " actuator list " , actuatorlist
	lightsetting=[]
	lightsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,"light1",hardwaremod.HW_FUNC_TIME))
	photosetting=[]
	photosetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,"photo",hardwaremod.HW_FUNC_TIME))
	
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
	
	servolist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"servo",hardwaremod.HW_INFO_NAME)
	servolist.insert(0, "none")
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
	
	
	return render_template('ShowCalibration.html',servolist=servolist , videolist=videolist,actuatorlist=actuatorlist, sensorlist=sensorlist,lightsetting=lightsetting,photosetting=photosetting, camerasettinglist=camerasettinglist ,mailsettinglist=mailsettinglist, unitdict=unitdict, initdatetime=initdatetime, countries=countries, timezone=timezone)

	
	
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


	return render_template('showsensordata.html',actiontype=actiontype,periodtype=periodtype,periodlist=periodlist,usedsensorlist=usedsensorlist,sensordata=json.dumps(sensordata),usedactuatorlist=usedactuatorlist,actuatordata=json.dumps(actuatordata))


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
			selectedplanmod.startnewselectionplan()
			
		if actiontype == "advconfig":	
			print "open advanced setting"
			return redirect('/Advanced/')
			
		
	return render_template("wateringplan.html", title=title,paramlist=paramlist,elementlist=elementlist,schemaementlist=schemaementlist,table=table,table1=table1,table2=table2,selectedelement=selectedelement)

@application.route('/fertilizerplan/' , methods=['GET', 'POST'])
def fertilizerplan():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	title = "Fertilizer Schedule"
	elementlist= fertilizerdbmod.getelementlist()	
	paramlist= fertilizerdbmod.getparamlist()
	argumentnumber=2
	table=fertilizerdbmod.gettable(1)	
	table1=fertilizerdbmod.gettable(0)
	
	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		selectedelement=elementlist[0]	
	
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
			flash('Table as been saved')
			table=fertilizerdbmod.gettable(1)	
			table1=fertilizerdbmod.gettable(0)
			#print "after",table
			selectedplanmod.startnewselectionplan()
			
		if actiontype == "advconfig":	
			print "open advanced setting"
			return redirect('/Advanced/')
			
		
	return render_template("fertilizerplan.html", title=title,paramlist=paramlist,elementlist=elementlist,table=table,table1=table1, selectedelement=selectedelement)



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
				flash('You were logged in')   
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
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@application.route('/HardwareSetting/', methods=['GET', 'POST'])
def hardwaresetting():  #on the contrary of the name, this show the setting menu
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print "visualizzazione menu hardwareSetting:"
	
	fields=hardwaremod.HWdataKEYWORDS
	hwdata=hardwaremod.IOdata

	tablehead=[]
	for key, value in fields.iteritems():
		tablehead.append(key)
	#print "tablehead ", tablehead
	
	HWfilelist=hardwaremod.HWpresetlist(MYPATH) #list of fiels (path , Name)
	#print "HW file list ---> ", HWfilelist
	
	if request.method == 'POST':
		requestinfo=request.form['buttonsub']
		requesttype=requestinfo.split("_")[0]
		print "requesttype "  , requestinfo , " " , requesttype
		if requesttype=="delete":
			name=requestinfo.split("_")[1]
			#remove the calibration file and read the default
			print " Delete ", name
			if hardwaremod.deleterow(name):
				flash('Record has been deleted')


		if requesttype=="save":
			print "Save row"
			dictrow={}
			for record in tablehead:
				dictrow[record]=request.form[record]
			print dictrow
			
			isok, message = hardwaremod.checkdata(dictrow)
			if isok:
				hardwaremod.addrow(dictrow)		
				flash('Table has been saved')
				# apply changes to the system (this is not best way, should be system reset indeed
				wateringdbmod.consitencycheck()
				fertilizerdbmod.consitencycheck()
				hardwaremod.initallGPIOoutput()	
				
			else:
				print "problem ", message
				flash(message, 'danger')				
				
				
		if requesttype=="applyHWpreset":
			print "Apply HW setting"
			selectedfilename=request.form['HWfilelist']
			for items in HWfilelist:
				if items[1]==selectedfilename:
					selectedpath=items[0]

			
			# copy file to the default HWdata
			filename=os.path.join(MYPATH, selectedpath)
			folderpath=os.path.join(MYPATH, hardwaremod.DATABASEPATH)
			dstdef=os.path.join(folderpath, hardwaremod.DEFHWDATAFILENAME)
			print "Source selected path ", filename , " Destination ", dstdef

			isdone=False
			try:
				shutil.copyfile(filename, dstdef) #this is the default HW file
				answer="ready"
				isdone=True
			except:
				answer="problem copying file"
				
				
			# apply changes to the system
			if isdone:
				hardwaremod.restoredefault() # copy default to normal file and reload HWdata
				wateringdbmod.consitencycheck()
				fertilizerdbmod.consitencycheck()
				sensordbmod.consistencycheck()
				actuatordbmod.consistencycheck()
				#scheduler setup---------------------
				selectedplanmod.setmastercallback()
				#initiate the GPIO OUT pins
				hardwaremod.initallGPIOoutput()			
			
				


	return render_template('hardwaresetting.html',fields=fields, hwdata=hwdata, tablehead=tablehead , HWfilelist=HWfilelist)



def currentpath(filename):
	return os.path.join(MYPATH, filename)


def functiontest():
	print " testing "
	mailname="mail1"
	#emailmod.sendallmail("alert","System detected IP address change, below the updated links")
	hardwaremod.takephoto()
	#selectedplanmod.heartbeat()


	return True


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
	initposition=50
	return render_template('videostream.html',initposition=initposition, itemlist=itemlist, ipaddress=ipaddress, videolist=videolist, servolist=servolist)


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
