# -*- coding: utf-8 -*-
from __future__ import print_function
from builtins import str
from builtins import range

Release="3.46"

#---------------------
from loggerconfig import LOG_SETTINGS
import logging, logging.config, logging.handlers
import re
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

import requests

from datetime import datetime,date,timedelta
import systemtimeMod
import time
import os
import shutil
import sys
import string
import random
import json
import hashlib
import hardwaremod
import videomod
import sensordbmod
import actuatordbmod
import selectedplanmod
import wateringdbmod
from autowatering import autowateringdbmod
from autowatering import autowateringmod

import automationdbmod
import automationmod

import interruptdbmod
import interruptmod

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
import filemanagementmod
import weatherAPImod
import messageboxmod
import wateringplansensordbmod
import HASScompMatrix
from HC12mod import HC12radionet
from camera_pi import Camera   # Raspberry Pi camera module (requires picamera package)
import REGandDBmod

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////
application = Flask(__name__)
application.config.from_object('flasksettings') #read the configuration variables from a separate module (.py) file, this file is mandatory for Flask operations

print("-----------------" , basicSetting.data["INTRO"], "--------------------")


MYPATH=""


# ///////////////// --- END GLOBAL VARIABLES ------



# ///////////////// -- MODULE INIZIALIZATION --- //////////////////////////////////////////


#-- start LOGGING utility--------////////////////////////////////////////////////////////////////////////////////////


#setup log file ---------------------------------------

print("starting new log session", datetime.now().strftime("%Y-%m-%d %H:%M:%S")) 
logger.info('Start logging -------------------------------------------- %s Version Release: %s' , datetime.now().strftime("%Y-%m-%d %H:%M:%S"),Release)

# finish logging init

def runallconsistencycheck():
	wateringdbmod.consitencycheck()
	autowateringdbmod.consistencycheck()
	automationdbmod.consistencycheck()
	interruptdbmod.consistencycheck()
	fertilizerdbmod.consitencycheck()
	autofertilizerdbmod.consistencycheck()
	sensordbmod.consistencycheck()
	actuatordbmod.consistencycheck()
	wateringplansensordbmod.consistencycheck()
	hardwaremod.initMQTT()
	hardwaremod.initGPIOEXP()
	hardwaremod.initHC12()
	hardwaremod.UpdateCMDcontrol()
	HASScompMatrix.HASSIOintegr.remove_and_update_config()
	hardwaremod.thumbconsistency(hardwaremod.get_path())
	return True

def runallreadfile():
	hardwaremod.readfromfile()
	wateringdbmod.readfromfile()
	autowateringdbmod.readfromfile()
	automationdbmod.readfromfile()
	interruptdbmod.readfromfile()
	fertilizerdbmod.readfromfile()
	autofertilizerdbmod.readfromfile()
	advancedmod.readfromfile()
	return True

# Setup mode of operation------------------------------
selectedplanmod.FASTSCHEDULER=False

# set minimum time in case the clock is gone, in future might be improved ------------------
#important for Arch linux OS

systemtimeMod.set_min_datetime()

def initallGPIOpins():
	hardwaremod.initallGPIOpins()
	interruptmod.setinterruptevents()

#initiate the GPIO OUT pins
initallGPIOpins()

print("Finish interrupt initialization")

# GET path ---------------------------------------------
print("path ",hardwaremod.get_path())
MYPATH=hardwaremod.get_path()

# RUN ALL consistency checks ------------------------
runallconsistencycheck()
automationmod.cycleresetall()
autowateringmod.cycleresetall()

#scheduler start---------------------
selectedplanmod.start_scheduler()

#setup network connecton --------------------
isconnecting=False
networkmod.stopNTP()
networkmod.disableNTP()

if not networkmod.WIFIENDIS=="Disabled":
	networkmod.CheckandUnlockWlan()

	try:
		print("start networking")
		isconnecting=networkmod.init_network() # this includes also the clock check and scheduler setup
	except:
		print("No WiFi available")

#scheduler setup---------------------
if not isconnecting:
	logger.info('No connection condition available. Reset mastercallback')
	if not selectedplanmod.CheckNTPandAdjustClockandResetSched():
		selectedplanmod.waitandsetmastercallback(20,0)

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
	print("preparing home page")
	currentday=datetime.today().strftime('%d/%m/%Y')

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


	# input panels
	partialnamelistinput=[]  # used to put the remaining inputs in one unique panel at the end (other)

	panelinfolist=[] # all the info relevant to a type of panel

	# temperature panels -------------------------------------------- (new version)
	MeasureType="Temperature"
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	partialnamelistinput.extend(namelist)
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
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# humidity panel --------------------------------------------
	MeasureType="Humidity"
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	partialnamelistinput.extend(namelist)
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
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# pressure panel --------------------------------------------
	MeasureType="Pressure"
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	partialnamelistinput.extend(namelist)
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
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# light panel --------------------------------------------
	MeasureType="Light"
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	partialnamelistinput.extend(namelist)
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
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# Hygrometer panel --------------------------------------------
	MeasureType="Moisture"
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	partialnamelistinput.extend(namelist)
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
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# INPUTS OTHERS panel (all remaining inputs) --------------------------------------------
	iotype="input"
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,iotype,hardwaremod.HW_INFO_NAME)
	#remove the nemas already in partialnamelist
	for item in partialnamelistinput:
		if item in namelist:
			namelist.remove(item)
	#print "------------------------- namelist " , namelist

	if namelist:
		paneldict={}
		paneldict["icon"]="icons/cables-white-sm.png"
		paneldict["color"]="teal"
		paneldict["type"]="sensor"
		paneldict["link"]=url_for('show_sensordata' , elementtype="",  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]="Other Input"
		paneldict["subtitle"]="booooo"
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# available panel colors in CSS custom:
	#aqua: #00c0ef; blue: #0073b7; teal: #39CCCC; olive: #3D9970; lime: #01FF70; orange: #FF851B; purple: #605ca8; maroon: #D81B60; gray: #d2d6de;

	# OUTPUT panels below
	partialnamelist=[]
	# watertap panel --------------------------------------------
	usedfor="watercontrol"
	iotype="output"
	namelist=hardwaremod.searchdatalist2keys(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_IOTYPE,iotype,hardwaremod.HW_INFO_NAME)
	partialnamelist.extend(namelist)
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
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# fertilizer panel --------------------------------------------
	usedfor="fertilizercontrol"
	iotype="output"
	namelist=hardwaremod.searchdatalist2keys(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_IOTYPE,iotype,hardwaremod.HW_INFO_NAME)
	partialnamelist.extend(namelist)
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
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# Light actuator panel --------------------------------------------
	usedfor="lightcontrol"
	iotype="output"
	namelist=hardwaremod.searchdatalist2keys(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_IOTYPE,iotype,hardwaremod.HW_INFO_NAME)
	partialnamelist.extend(namelist)
	#print "------------------------- namelist " , namelist

	if namelist:
		paneldict={}
		paneldict["icon"]="icons/bulb1.png"
		paneldict["color"]="orange"
		paneldict["type"]="actuator"
		paneldict["link"]=url_for('show_Calibration')
		paneldict["linktitle"]="Go to Setting"
		paneldict["title"]="Light Control"
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# OTHERS panel (all outputs) --------------------------------------------
	iotype="output"
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,iotype,hardwaremod.HW_INFO_NAME)
	#remove the nemas already in partialnamelist
	for item in partialnamelist:
		if item in namelist:
			namelist.remove(item)
	#print "------------------------- namelist " , namelist

	if namelist:
		paneldict={}
		paneldict["icon"]="icons/tools3-sm.png"
		paneldict["color"]="olive"
		paneldict["type"]="actuator"
		paneldict["link"]=url_for('show_Calibration')
		paneldict["linktitle"]="Go to setting"
		paneldict["title"]="Other Outputs"
		paneldict["active"]="yes"
		paneldata=[]
		endtime=datetime.now()
		for name in namelist:
			paneldatarow={}
			paneldatarow["name"]=name
			paneldata.append(paneldatarow)
		paneldict["data"]=paneldata
		panelinfolist.append(paneldict)

	# available panel colors in CSS custom:
	#aqua: #00c0ef; blue: #0073b7; teal: #39CCCC; olive: #3D9970; lime: #01FF70; orange: #FF851B; purple: #605ca8; maroon: #D81B60; gray: #d2d6de;

	nameslist=[]
	for panelinfo in panelinfolist:
		if panelinfo["active"]=="yes":
			for paneldata in panelinfo["data"]:
				nameslist.append(paneldata["name"])

	#print nameslist

	# system tabs

	networklink=url_for('network')
	settinglink=url_for('show_Calibration')
	videolink=url_for('videostream')

	return render_template('homepage.html',nameslist=nameslist, panelinfolist=panelinfolist,photopanellist=photopanellist,currentday=currentday, networklink=networklink, settinglink=settinglink , videolink=videolink)


@application.route('/network/', methods=['GET', 'POST'])
def network():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	wifilist=[]
	savedssid=[]
	filenamelist="wifi networks"

	print("visualizzazione menu network:")

	iplocal=networkmod.get_local_ip()
	iplocallist=networkmod.get_local_ip_list()
	ipext=networkmod.get_external_ip()
	iplocalwifi=networkmod.IPADDRESS
	ipport=networkmod.PUBLICPORT
	hostname=networkmod.gethostname()
	connectedssidlist=networkmod.connectedssid()
	if len(connectedssidlist)>0:
		connectedssid=connectedssidlist[0]
	else:
		connectedssid=""

	localwifisystem=networkmod.localwifisystem
	#print " localwifisystem = ", localwifisystem , " connectedssid ", connectedssid
	message=networkmod.networkdbmod.getstoredmessage()

	return render_template('network.html',filenamelist=filenamelist, connectedssid=connectedssid,localwifisystem=localwifisystem, ipext=ipext, iplocallist=iplocallist , iplocal=iplocal, iplocalwifi=iplocalwifi , ipport=ipport , hostname=hostname, message=message)



@application.route('/wificonfig/', methods=['GET', 'POST'])
def wificonfig():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("method " , request.method)
	if request.method == 'GET':
		ssid = request.args.get('ssid')
		print(" argument = ", ssid)

	if request.method == 'POST':
		ssid = request.form['ssid']
		if request.form['buttonsub'] == "Save":
			password=request.form['password']
			#networkmod.savewifi(ssid, password)
			networkmod.waitandsavewifiandconnect(7,ssid,password)
			#redirect to login
			session.pop('logged_in', None)
			return redirect(url_for('login', message="Please wait until the WiFi disconnect and reconnect"))

		elif request.form['buttonsub'] == "Forget":
			print("forget")
			networkmod.waitandremovewifi(7,ssid)
			print("remove network ", ssid)
			print("Try to connect AP")
			networkmod.waitandconnect_AP(9)
			session.pop('logged_in', None)
			return redirect(url_for('login', message="Please wait until the WiFi disconnect and reconnect"))

		else:
			print("cancel")
			return redirect(url_for('network'))

	return render_template('wificonfig.html', ssid=ssid)

@application.route('/Imageshow/', methods=['GET', 'POST'])
def imageshow():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	monthdict= {1: "jan", 10: "oct", 11: "nov", 12: "dec", 2: "feb", 3: "mar", 4: "apr", 5: "may", 6: "jun", 7: "jul", 8: "aug", 9: "sep", 13: "all"}
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
			print(" picture files deleted " , deletedfilenumber)
			logger.info(' all image files deleted ')
			deletedfilenumber=hardwaremod.deleteallpictures(MYPATH)
		elif actiontype=="CreateImage":
			print("Create image manually")
			logger.info('Create image manually')
			hardwaremod.takephoto()
		elif actiontype=="all":
			monthtoshow="all"
		else:
			monthtoshow=monthlist.index(actiontype)+1

	sortedlist=hardwaremod.photolist(MYPATH)

	filenamelist=[]
	#wlist=[]
	#hlist=[]
	titlelist=[]
	thumbfilenamelist=[]
	for files in sortedlist:
		filemonthnumber=files[2].month
		#print filemonthnumber
		if filemonthnumber==monthtoshow or monthtoshow == "all":
			filenamelist.append(files[0])
			titlelist.append(files[1])
			#(w,h)=hardwaremod.get_image_size(files[0])
			#wlist.append(w)
			#hlist.append(h)
			thumbfilenamelist.append(files[3])

	if monthtoshow == "all":
		selectedmonthname = "all"
	else:
		selectedmonthname=monthdict[monthtoshow]

	return render_template('showimages.html',filenamelist=filenamelist, titlelist=titlelist, monthlist=monthlist, selectedmonthname=selectedmonthname, thumbfilenamelist=thumbfilenamelist)

@application.route('/echo/', methods=['GET'])
def echo():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login needed"}
		return jsonify(ret_data)
	element=request.args['element']
	if element=="all":
		# take reading for all sensors
		ret_data = hardwaremod.readallsensors()
	else:
		isok, reading , errmsg = hardwaremod.getsensordata(element,3)
		print("isok " ,isok, "reading " ,reading , "statusmsg ", errmsg)
		answer={}
		answer[element]={"isok":isok, "reading":reading , "statusmsg":errmsg}
		ret_data=answer


	#print ret_data
	return jsonify(ret_data)

@application.route('/echodatabase/', methods=['GET'])
def echodatabase():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login needed"}
		return jsonify(ret_data)
	element=request.args['element']
	if element=="all":
		# take reading for all sensors
		ret_data = sensordbmod.readallsensorsdatabase()
	else:
		ret_data={}


	#print ret_data
	return jsonify(ret_data)

@application.route('/echoMQTT/', methods=['GET'])
def echoMQTT():
	print(" ECHO MQTT ************************************")
	if not session.get('logged_in'):
		ret_data = {"answer":"Login needed"}
		return jsonify(ret_data)
	element=request.args['element']
	if element=="all":
		# take reading for all sensors
		# it is a dict with MQTT name as key and a dict of info as value
		ret_data = hardwaremod.getSTATfromall()
		print(" ECHO MQTT ************************************")
		print(ret_data)

	else:
		ret_data={}


	#print ret_data
	return jsonify(ret_data)

@application.route('/echohome/', methods=['GET'])
def echohome():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login needed"}
		return jsonify(ret_data)
	ret_data={}
	name=request.args['element']
	action=request.args['action']

	if action=="getdata":
		#actuatorlist=actuatordbmod.gettablelist()
		sensorlist=sensordbmod.gettablelist()

		# name is the input

		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		if name in sensorlist:
			sensordata=[]
			sensordbmod.getsensordbdatadaysV2(name,sensordata,starttime,endtime)
			isok, evaluateddata=sensordbmod.EvaluateDataPeriod(sensordata,starttime,endtime)
			paneldatarow={}
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % evaluateddata["average"])
			paneldatarow["min"]=str('%.1f' % evaluateddata["min"])
			paneldatarow["max"]=str('%.1f' % evaluateddata["max"])
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)
			paneldatarow["enabled"]="none"
		else:
			data=[]
			actuatordbmod.getactuatordbdatadaysV2(name,data,starttime,endtime)
			isok, evaluateddata=sensordbmod.EvaluateDataPeriod(data,starttime,endtime)	#set date interval for average
			paneldatarow={}
			paneldatarow["name"]=name
			paneldatarow["average"]=str('%.1f' % (evaluateddata["sum"]))
			paneldatarow["min"]=""
			paneldatarow["max"]=""
			paneldatarow["unit"]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT)
			cmdtype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_CTRL_CMD)
			if cmdtype.split("/")[0]=="pulse":
				paneldatarow["enabled"]=hardwaremod.ReadActuatorEnabled(name)
			else:
				paneldatarow["enabled"]="none"

		#set date interval for average

		ret_data=paneldatarow

		#print "Single item Data " , ret_data

	elif action=="enable":
		hardwaremod.WriteActuatorEnabled(name, "enable")
		paneldatarow={}
		paneldatarow["name"]=name
		paneldatarow["actiondone"]="enable"
		ret_data=paneldatarow

		#print "Single item Data " , ret_data

	elif action=="disable":
		hardwaremod.stoppulse(name) # stop before disable
		hardwaremod.WriteActuatorEnabled(name, "disable")
		paneldatarow={}
		paneldatarow["name"]=name
		paneldatarow["actiondone"]="disable"
		# stop pulse

		ret_data=paneldatarow

		#print "Single item Data " , ret_data

	return jsonify(ret_data)

@application.route('/echowifi/', methods=['GET'])
def echowifi():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login needed"}
		return jsonify(ret_data)
	ret_data={}
	element=request.args['element']
	if element=="all" and not networkmod.WIFIENDIS=="Disabled":
		# get wifi list
		wifilist=[]
		wifilist=networkmod.wifilist_ssid(2)
		connectedssidlist=networkmod.connectedssid()
		if len(connectedssidlist)>0:
			connectedssid=connectedssidlist[0]
		else:
			connectedssid=""

		savedssid=networkmod.savedwifilist_ssid()
		#print "Saved SSIDs ", savedssid

		for ssid in wifilist:
			connected="0"
			if ssid==connectedssid:
				connected="1"
			idstatus="Unknown"
			if ssid in savedssid:
				idstatus="Saved"

			ret_data[ssid]=[idstatus , connected]

	#print "Wifi Data " , ret_data
	return jsonify(ret_data)

@application.route('/doit/', methods=['GET'])
def doit():
	#if not session.get('logged_in'):
	#	ret_data = {"answer":"Login Needed"}
	#	return jsonify(ret_data)
	# send command to the actuator for test
	cmd=""
	sendstring=""
	recdata=[]
	ret_data={}
	argumentlist=request.args.getlist('name')
	name=argumentlist[0]
	namelist=name.split("/")
	if namelist:
		name=namelist[0]
	#print "value passed ", argumentlist
	#print "type " , name

	if name=="pulse":
		idx=1
		if idx < len(argumentlist):
			testpulsetime=argumentlist[idx]
		else:
			testpulsetime="20"
		element=request.args['element']

		print("starting pulse test " , testpulsetime)
		answer=selectedplanmod.activateandregister(element,testpulsetime)
		ret_data = {"answer": answer}

	elif name=="stoppulse":
		idx=1
		element=request.args['element']

		print("stop pulse  " , element)
		answer=selectedplanmod.activateandregister(element,"0")
		ret_data = {"answer": answer}

	elif name=="servo2":
		print("want to test servo")
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
		print("want to test stepper")
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
		print("want to set stepper position")
		idx=1
		if idx < len(argumentlist):
			newposition=argumentlist[idx]

		element=request.args['element']
		# set stepper position without moving it
		hardwaremod.setstepperposition(element, newposition)
		ret_data = {"answer": newposition}

	elif name=="hbridge":
		print("want to test hbridge")
		idx=1
		if idx < len(argumentlist):
			steps=argumentlist[idx]
		idx=2
		if idx < len(argumentlist):
			direction=argumentlist[idx]

		element=request.args['element']
		# move hbridge
		zerooffset=0
		position , isok=hardwaremod.GO_hbridge(element,steps,zerooffset,direction)
		if isok:
			REGandDBmod.register_output_value(element,position,saveonDB=False) # update the status register.
		ret_data = {"answer": position}

	elif name=="hbridgestop":
		print("want to stop hbridge")
		idx=1
		if idx < len(argumentlist):
			steps=argumentlist[idx]
		idx=2
		if idx < len(argumentlist):
			direction=argumentlist[idx]

		element=request.args['element']
		# stop hbridge
		position , isok=hardwaremod.gpio_stop_hbridge(element)
		if isok:
			REGandDBmod.register_output_value(element,position,saveonDB=False) # update the status register.
		ret_data = {"answer": position}

	elif name=="sethbridge":
		print("want to set hbridge position")
		idx=1
		if idx < len(argumentlist):
			newposition=argumentlist[idx]

		element=request.args['element']
		# set hbridge position without moving it
		hardwaremod.sethbridgeposition(element, newposition)
		ret_data = {"answer": newposition}

	elif name=="photo":
		print("Capture photo")

		idx=1
		if idx < len(argumentlist):
			video=argumentlist[idx]

		logger.info('Capture photo on %s', video)
		resolution=request.args.getlist('resolution')[0]
		position=request.args.getlist('position')[0]
		servo=request.args.getlist('servo')[0]
		vdirection=request.args.getlist('vflip')[0]
		positionlist=position.split(",")
		position=""

		if positionlist[0] != "":
			# move servo
			position=positionlist[0]
			logger.info('Move servo to position %s', position)
			hardwaremod.servoangle(servo,position,1)

		# take picture
		isok, ret_data=hardwaremod.shotit(video,True,resolution,position,vdirection)

	elif name=="mail":
		mailaname=request.args['element']
		mailaddress=request.args['address']
		mailtitle=request.args['title']
		cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,mailaname,hardwaremod.HW_CTRL_CMD)
		print("want to test mail, address=" , mailaddress , " Title=" , mailtitle)
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
			print("datetime Local ->" ,datetime)
			logger.info('Clock has been manually changed')
			answer1=clockmod.setsystemclock(datetime)
			answer2=clockmod.setHWclock(datetime)
			answer=answer1 + answer2
			selectedplanmod.resetmastercallback()

		ret_data = {"answer":answer, "value":datetime}

	elif name=="HC12":
		element=request.args['element']
		value=request.args['value']
		if element=="version":
			HC12radionet.medium.enableATpin()
			isOk, versionByteArray = HC12radionet.medium.sendReceiveATcmds(value)
			HC12radionet.medium.disableATpin()
			answer="Something went wrong"
			try:
				version=versionByteArray.decode('ascii','ignore')
			except:
				version="not able to read the version"
			if isOk:
				answer="ready"
			else:
				version="Problem reading version"
			version = version

		ret_data = {"answer":answer, "value":version}

	elif name=="HASSIO":
		element=request.args['element']
		value=request.args['value']
		msg=""
		answer=""
		topic_list=[]
		if element=="sendupdateconfig":
			msg, isok = HASScompMatrix.HASSIOintegr.configure_device(True)
			answer="OK"

		if element=="removeconfig":
			msg, isok =HASScompMatrix.HASSIOintegr.remove_configuration(True)
			answer="OK"

		if element=="query_topics":
			print (" query topic")
			msg="topics"
			topic_list=HASScompMatrix.HASSIOintegr.topic_list(value)
			answer="OK"

		ret_data = {"answer":answer, "value": msg , "topics":topic_list}

	elif name=="APItesting":
		answer="nothing to declare"
		testtype=request.args['element']
		if testtype=="createURL":
			#print " creating URL"
			URLlist=weatherAPImod.CreateQueryUrlall()
			#print " The URL" , URLlist
			answer='\n'.join(URLlist)

		elif testtype=="parse":
			print(" creating URL")
			isok , result=weatherAPImod.CalculateRainMultiplier()
			print(" result" , result)
			answer = str(result)


		ret_data = {"answer": answer}

	elif name=="timezone":
		element=request.args['element']
		timezone=request.args['timezone']
		if element=="settimezone":
			print("Set timezone ->" ,timezone)
			logger.info('Time Zone has been manually changed')
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
	print("Saving .." , name)
	if name=="mail":
		mailaname=request.args['element']
		mailaddress=request.args['address']
		mailtitle=request.args['title']
		mailtime=request.args['time']
		mailurl=request.args['url']
		#print "save mail, name " ,mailaname , " address=" , mailaddress , " Title=" , mailtitle , " Time=", mailtime , "CustomURL=" , mailurl
		hardwaremod.changesavecalibartion(mailaname,hardwaremod.HW_CTRL_ADDR,mailaddress)
		hardwaremod.changesavecalibartion(mailaname,hardwaremod.HW_CTRL_TITLE,mailtitle)
		hardwaremod.changesavecalibartion(mailaname,hardwaremod.HW_FUNC_TIME,mailtime)
		oldurl=networkdbmod.getCUSTOMURL()
		if not oldurl==mailurl:
			networkdbmod.changesavesetting("customURL",mailurl)
			# Change hostapd file first row with HERE
			data=[]
			networkdbmod.readdata(data)
			sysconfigfilemod.hostapdsavechangerow_spec(data)

	elif name=="setsensor":
		print("want to save sensor calibration")
		element=request.args['element']

		paramnamelist=request.args.getlist('paramname')
		paramvaluelist=request.args.getlist('paramvalue')
		#print element
		#print paramnamelist
		#print paramvaluelist
		i=0
		for paramname in paramnamelist:
			hardwaremod.changesavecalibartion(element,paramname,paramvaluelist[i])
			i=i+1

	elif name=="photo":
		# save photo time
		phototime=""
		phototime=request.args['time']

		print("save photo setting, time=" , phototime)
		hwname=hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_INFO_NAME)
		hardwaremod.changesavecalibartion(hwname,hardwaremod.HW_FUNC_TIME,phototime)
		#hardwaremod.changesavecalibartion(hwname,hardwaremod.HW_CTRL_LOGIC,vdirection)

		camname=request.args['element']
		resolution=request.args['resolution']
		position=request.args['position']
		servo=request.args['servo']
		active=request.args['active']
		vflip=request.args['vflip']

		#print "save camera name " ,camname , " resolution=" , resolution , " position=" , position , " servo=" , servo ," time=", phototime ," Active=", active, " vflip ", vflip
		cameradbmod.changecreatesetting("camera",camname,"resolution",resolution)
		cameradbmod.changecreatesetting("camera",camname,"position",position)
		cameradbmod.changecreatesetting("camera",camname,"servo",servo)
		cameradbmod.changecreatesetting("camera",camname,"time",phototime)
		cameradbmod.changecreatesetting("camera",camname,"active",active)
		cameradbmod.changecreatesetting("camera",camname,"vflip",vflip)
		cameradbmod.savesetting()

	elif name=="light1":
		lighttime=""
		lighttime=request.args['time']
		print("save light setting, time=" , lighttime)
		hardwaremod.changesavecalibartion(name,hardwaremod.HW_FUNC_TIME,lighttime)

	ret_data = {"answer": "saved"}
	print("The actuator ", ret_data)
	return jsonify(ret_data)


@application.route('/getunseencount/', methods=['GET'])
def getunseencount():
	unseencount = messageboxmod.GetUnseenCount()
	ret_data = {"unseencount": unseencount}
	return jsonify(unseencount)

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
	answer="None"

	name=request.args['name']
	if name=="downloadlog":
		dstfilename="log"+datetime.now().strftime("%Y-%m-%d-time:%H:%M")+".log"
		filename=LOG_SETTINGS['handlers']['access_file_handler']['filename']
		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		dst=os.path.join(folderpath, dstfilename+".txt")
		print("prepare file for download, address=" , filename, "destination " , dst)
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
			print("prepare file for download, address=" , source, "destination " , dst)
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
		print("prepare file for download, address=" , filename, "destination " , dst)
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
		print("prepare file for download, address=" , filename, "destination " , dst)
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
		print("prepare file for download, destination " , dst)
		# create the file using the tail command
		isok=debuggingmod.createfiletailsyslog(dst)
		if not isok:
			answer="problem creating file"
		else:
			answer="ready"
		dstfilenamelist=[]
		dstfilenamelist.append("download/"+dstfilename)

	elif name=="configzip":
		dstfilename=filemanagementmod.configfilezip()
		if dstfilename=="":
			answer="problem creating file"
		else:
			answer="ready"

		dstfilenamelist=[]
		dstfilenamelist.append(dstfilename)

	elif name=="weatherAPIdata": # configuration of the weatherAPI page
		dstfilename=weatherAPImod.weatherAPIdbmod.DATAFILENAME
		filename=os.path.join(hardwaremod.DATABASEPATH, dstfilename)
		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		dst=os.path.join(folderpath,  dstfilename)
		print("prepare file for download, address=" , filename, "destination " , dst)
		try:
			shutil.copyfile(filename, dst)
			answer="ready"
		except:
			answer="problem copying file"
		dstfilenamelist=[]
		dstfilenamelist.append("download/"+dstfilename)

	if not dstfilenamelist:
		dstfilenamelist = None

	ret_data = {"answer": answer, "filename": dstfilenamelist}
	print("The actuator ", ret_data)
	return jsonify(ret_data)

@application.route('/testit/', methods=['GET'])
def testit():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login Needed"}
		return jsonify(ret_data)

	recdata=[]
	ret_data={}
	answer="None"

	name=request.args['name']
	if name=="testing":
		answer="done"
		print("testing")
		answer=Generictesting()

	name=request.args['name']
	if name=="testing1":
		answer="done"
		print("testing1")
		answer=Autotesting1()

	name=request.args['name']
	if name=="testing2":
		answer="done"
		print("testing2")
		answer=Autotesting2()

	name=request.args['name']
	if name=="testing3":
		answer="done"
		print("testing2")
		answer=Autotesting3()

	ret_data = {"answer": answer}
	print("The actuator ", ret_data)
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
	#print "unitdict "  , unitdict
	return render_template('ShowRealTimeSensor.html', sensorlist=sensorlist, unitdict=unitdict, selectedsensor=selectedsensor)

@application.route('/systemmailsetting/', methods=['GET', 'POST'])
def systemmailsetting():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	error = None

	if request.method == 'POST':
		#print " here we are"
		reqtype = request.form['button']
		if reqtype=="save":
			print("saving email credentials")
			address=request.form['address']
			password=request.form['password']
			server=request.form['server']
			port=request.form['port']			
			isok1=emaildbmod.changesavesetting('address',address)
			isok2=emaildbmod.changesavesetting('password',password)
			isok3=emaildbmod.changesavesetting('server',server)
			isok4=emaildbmod.changesavesetting('port',port)		
			if isok1 and isok2 and isok3 and isok4:
				flash('Email credentials Saved')
				return redirect(url_for('show_Calibration'))
		elif reqtype=="cancel":
			return redirect(url_for('show_Calibration'))

	password=emaildbmod.getpassword()
	address=emaildbmod.getaddress()
	server=emaildbmod.getserver()
	port=emaildbmod.getport()

	return render_template('systemmailsetting.html', address=address, password=password, server=server, port=port)

@application.route('/HC12setting/', methods=['GET', 'POST'])
def HC12setting():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	formDataClass=HC12radionet.dataManagement
	jsonschema, itemslist =formDataClass.readJsonFormFilePlusValues()
	ATinfolist=HC12radionet.medium.ATcmdInfoList()

	if request.method == 'POST':
		print(" HC12 setting POST")
		datadict={}
		for item in itemslist:
			itemdata = request.form.get(item)
			#print(itemdata , ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
			if itemdata:
				datadict[item]=itemdata

		# save hte new setting
		if datadict:
			isok = HC12radionet.saveDataFileAndApply(datadict)
			jsonschema["value"]=datadict
			if isok:
				flash('Setting has been applied')
			else:
				flash('problem with Setting','danger')
		# Apply the new setting to the devide


	return render_template('HC12setting.html', jsonschema=jsonschema, ATinfolist=ATinfolist)

@application.route('/HASSIOsetting/', methods=['GET', 'POST'])
def HASSIOsetting():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	formDataClass=HASScompMatrix.HASSIOintegr.dataManagement
	jsonschema, itemslist =formDataClass.readJsonFormFilePlusValues()
	itemlist=HASScompMatrix.HASSIOintegr.get_item_list()

	if request.method == 'POST':
		print(" HASSIO setting POST")
		datadict={}
		for item in itemslist:
			itemdata = request.form.get(item)
			#print(itemdata , ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
			if itemdata:
				datadict[item]=itemdata

		# save hte new setting
		if datadict:

			isok = HASScompMatrix.HASSIOintegr.saveDataFileAndApply(datadict)
			jsonschema["value"]=datadict

			if isok:

				if HASScompMatrix.HASSIOintegr.check_loop_and_connect():
					HASScompMatrix.HASSIOintegr.remove_and_update_config() # if the discovery setting is Yes
					flash('Setting has been saved')
				else:
					flash('Error, not able establish connection with the MQTT broker','danger')
			else:
				flash('Error, not able to save setting','danger')

		# Apply the new setting to the devide

	return render_template('HASSIOsetting.html', jsonschema=jsonschema, itemlist=itemlist)

@application.route('/dontclick/', methods=['GET', 'POST'])
def dontclick():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	print(" Why did you click it !")
	if request.method == 'POST':

		itemdata = request.form.get("buttonsub")
		print("value from button ", itemdata)
		if itemdata=="reset":
			os.system("reboot")
		if itemdata=="shutdown":
			os.system("halt")
		if itemdata=="cancel":
			return redirect(url_for('hardwaresetting'))

	return render_template('dontclick.html')

@application.route('/networksetting/', methods=['GET', 'POST'])
def networksetting():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	error = None

	Fake_password="AP-password"

	if request.method == 'POST':
		print(" here we are at network setting")
		reqtype = request.form['button']
		if reqtype=="save":
			print("saving network advanced setting")
			gotADDRESS=request.form['IPADDRESS']
			AP_SSID=request.form['AP_SSID']
			AP_PASSWORD=request.form['AP_PASSWORD']
			AP_TIME=request.form['AP_TIME']
			WIFIENDIS=request.form['WIFIENDIS']
			HOSTNAME=request.form['HOSTNAME']
			forceStaticIP=request.form['forceStaticIP']

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
				HOSTNAMEold=networkmod.gethostname()
				WIFIENDISold=networkmod.WIFIENDIS

				print("save in network file in database")
				networkdbmod.changesavesetting('LocalIPaddress',IPADDRESS)
				networkdbmod.changesavesetting('LocalAPSSID',AP_SSID)
				networkdbmod.changesavesetting('APtime',AP_TIME)
				networkdbmod.changesavesetting('WIFIENDIS',WIFIENDIS)
				networkdbmod.changesavesetting('forceStaticIP',forceStaticIP)
				networkmod.FORCESTATICIP=forceStaticIP

				# save and change values in the HOSTAPD config file
				sysconfigfilemod.hostapdsavechangerow("ssid",AP_SSID)
				if AP_PASSWORD!=Fake_password:
					# change password in the HOSTAPD config file
					sysconfigfilemod.hostapdsavechangerow("wpa_passphrase",AP_PASSWORD)
					print("password changed")
				else:
					AP_PASSWORD=""

				if IPADDRESSold!=IPADDRESS:
					# save changes in DHCPCD confign file
					sysconfigfilemod.modifydhcpcdconfigfile(IPADDRESSold, IPADDRESS)

					# save changes in DNSMASQ confign file
					sysconfigfilemod.modifydnsmasqconfigfile(IPADDRESSold, IPADDRESS)

				if HOSTNAME!=HOSTNAMEold:
					networkmod.setnewhostname(HOSTNAME)

				# proceed with changes
				networkmod.applyparameterschange(AP_SSID, AP_PASSWORD, IPADDRESS)
				networkmod.WAITTOCONNECT=AP_TIME
				networkmod.WIFIENDIS=WIFIENDIS

				# Change hostapd file first row with HERE
				data=[]
				networkdbmod.readdata(data)
				sysconfigfilemod.hostapdsavechangerow_spec(data)

				if WIFIENDISold!=WIFIENDIS:
					if WIFIENDIS=="Disabled":
						networkmod.Disable_WiFi()
					else:
						networkmod.connect_network()

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

	HOSTNAME=networkmod.gethostname()
	iplocal=networkmod.get_local_ip()
	IPADDRESS=networkmod.IPADDRESS
	PORT=networkmod.PUBLICPORT
	AP_SSID=networkmod.localwifisystem
	AP_TIME=str(networkmod.WAITTOCONNECT)
	WIFIENDIS=networkmod.WIFIENDIS
	forceStaticIP=networkmod.FORCESTATICIP
	connectedssidlist=networkmod.connectedssid()
	if len(connectedssidlist)>0:
		connectedssid=connectedssidlist[0]
	else:
		connectedssid=""
	AP_PASSWORD=Fake_password

	return render_template('networksetting.html', IPADDRESS=IPADDRESS, AP_SSID=AP_SSID, AP_PASSWORD=AP_PASSWORD, AP_TIME=AP_TIME , HOSTNAME=HOSTNAME, WIFIENDIS=WIFIENDIS, forceStaticIP=forceStaticIP)	

@application.route('/About/', methods=['GET', 'POST'])
def show_about():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	return render_template('About.html',Release=Release)

@application.route('/ShowCalibration/', methods=['GET', 'POST'])
def show_Calibration():  #on the contrary of the name, this show the setting menu
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu Setting:")
	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="delete":
			#remove the calibration file and read the default
			print("restore hardware default file")
			#hardwaremod.restoredefault()
			wateringdbmod.restoredefault()
			fertilizerdbmod.restoredefault()
			advancedmod.restoredefault()
			emaildbmod.restoredefault()
			networkmod.restoredefault()
			logindbmod.restoredefault()
			cameradbmod.restoredefault()
			interruptdbmod.restoredefault()
			# try to align the config to new setting (this is not tested properly, better reboot in this case)
			wateringdbmod.consitencycheck()
			fertilizerdbmod.consitencycheck()
			#scheduler setup---------------------
			selectedplanmod.resetmastercallback()
			#initiate the GPIO OUT pins
			initallGPIOpins()

		if requesttype=="editnames":
			return hardwaresettingeditfield()

		if requesttype=="uploadfile":
			print("upload")

			if 'file' not in request.files:
				flash('No file')
			else:
				f = request.files['file']
				if f.filename == '':
					flash('No file selected')
				else:
					if ".zip" in f.filename:
						print( " ZIP filename ", f.filename)
						# control if the folder exist otherwise create it
						uploadfolder=application.config['UPLOAD_FOLDER']
						fullfolderpath=os.path.join(MYPATH, uploadfolder)
						if not os.path.exists(fullfolderpath):
							os.makedirs(fullfolderpath)
							print(" folder has been created")

						f.save(os.path.join(uploadfolder, f.filename))
						filemanagementmod.restoreconfigfilefromzip(fullfolderpath,f.filename)
						print("Align the data to the new files config")
						# align the files and memory
						runallreadfile()
						# align the data
						runallconsistencycheck()
						# scheduler setup---------------------
						selectedplanmod.resetmastercallback()
						# initiate the GPIO OUT pins
						initallGPIOpins()

					else:
						flash('Allowed file types is .zip ')

	actuatorlist=[]
	actuatorlist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"pulse*",hardwaremod.HW_INFO_NAME)

	#print " actuator list " , actuatorlist

	photosetting=[]
	photosetting.append(hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_FUNC_TIME))
	photosetting.append(hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_CTRL_LOGIC))

	mailelements=emaildbmod.getelementlist()
	mailsettinglist=[]
	for element in mailelements:
		mailsetting=[]
		mailsetting.append(element)
		mailsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_FUNC_TIME))
		mailsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_CTRL_ADDR))
		mailsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_CTRL_TITLE))
		mailsetting.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,element,hardwaremod.HW_CTRL_CMD))
		# mail URL to be founf in network data
		mailsetting.append(networkdbmod.getCUSTOMURL())
		mailsettinglist.append(mailsetting)

	# stepper
	stepperlist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"stepper",hardwaremod.HW_INFO_NAME)
	stepperstatuslist=[]
	for stepper in stepperlist:
		stepperstatuslist.append(hardwaremod.getstepperposition(stepper))
	# hbridge
	hbridgelist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"hbridge*",hardwaremod.HW_INFO_NAME)
	hbridgestatuslist=[]
	for hbridge in hbridgelist:
		hbridgestatuslist.append(hardwaremod.gethbridgeposition(hbridge))

	# servo
	servolist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"servo",hardwaremod.HW_INFO_NAME)
	servostatuslist=[]
	for servo in servolist:
		servostatuslist.append(hardwaremod.getservopercentage(servo))

	#servolist.insert(0, "none")
	#servostatuslist.insert(0, "None")
	videolist=hardwaremod.videodevlist()
	camerasettinglist=cameradbmod.getcameradata(videolist)
	#print camerasettinglist

	sensorlist = []
	sensorlist=sensordbmod.gettablelist()

	#read the sensors data
	#print "read sensor data "
	unitdict={}
	for item in sensorlist:
		unitdict[item]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,item,hardwaremod.HW_INFO_MEASUREUNIT)
	#print "unitdict "  , unitdict

	initdatetime=clockmod.readsystemdatetime()

	#timezone
	countries=countryinfo.countries
	timezone=clockdbmod.gettimezone()
	print("Current timezone ->", timezone)

	MQTTclientexist=False
	if len(hardwaremod.MQTTcontrol.CLIENTSLIST):
		MQTTclientexist=True

	HC12ok=HC12radionet.mediumconnected

	return render_template('ShowCalibration.html',servolist=servolist,servostatuslist=servostatuslist,stepperlist=stepperlist,stepperstatuslist=stepperstatuslist,hbridgelist=hbridgelist,hbridgestatuslist=hbridgestatuslist,videolist=videolist,actuatorlist=actuatorlist, sensorlist=sensorlist,photosetting=photosetting, camerasettinglist=camerasettinglist ,mailsettinglist=mailsettinglist, unitdict=unitdict, initdatetime=initdatetime, countries=countries, timezone=timezone, MQTTclientexist=MQTTclientexist, HC12ok=HC12ok)


@application.route('/setinputcalibration/', methods=['GET', 'POST'])
def setinputcalibration():  # set the hbridge zero point
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu sensor calibration:")
	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="cancel":
			return redirect(url_for('show_Calibration'))

	# Sensors data
	sensorparameters=[
		hardwaremod.HW_CTRL_MIN,
		hardwaremod.HW_CTRL_MAX,
		hardwaremod.HW_CTRL_SUBTRACT,		
		hardwaremod.HW_CTRL_SCALE,
		hardwaremod.HW_CTRL_DIVIDE,		
		hardwaremod.HW_CTRL_OFFSET,
		hardwaremod.HW_CTRL_DIR,
	]
	
	sensorlist = []
	sensorlist=sensordbmod.gettablelist()
	sensorstatuslist=[]
	for sensorname in sensorlist:
		tempdict={}
		for item in sensorparameters:
			tempdict[item]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,sensorname,item)
		sensorstatuslist.append(tempdict)

	selectvalues=hardwaremod.HWdataKEYWORDS[hardwaremod.HW_CTRL_DIR]

	return render_template('setinputcalibration.html',sensorlist=sensorlist,sensorstatuslist=sensorstatuslist, sensorparameters=sensorparameters, selectvalues=selectvalues)

@application.route('/showdeviceaddresseslist/', methods=['GET', 'POST'])
def showdeviceaddresseslist():  # set the hbridge zero point
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu :")
	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="cancel":
			return redirect(url_for('show_Calibration'))

	deviceaddresseslist=hardwaremod.get_device_list_address_property()

	return render_template('showdeviceaddresseslist.html',deviceaddresseslist=deviceaddresseslist)

@application.route('/showmqttdevicelist/', methods=['GET', 'POST'])
def showmqttdevicelist():  # set the hbridge zero point
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("showmqttdevicelist menu :")
	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="cancel":
			return redirect(url_for('show_Calibration'))

	hardwaremod.SendSTATcmdtoall()
	MQTTclientdict=hardwaremod.MQTTcontrol.CLIENTSLIST
	MQTTclientlist=[]
	for clientname in MQTTclientdict:
		clientinfo=MQTTclientdict[clientname]
		infodict={}
		infodict["subtopic"]=clientinfo["subtopic"]
		infodict["subtopicstat5"]=clientinfo["subtopicstat5"]
		infodict["name"]=clientname
		MQTTclientlist.append(infodict)

	return render_template('showmqttdevicelist.html',MQTTclientlist=MQTTclientlist)

@application.route('/setstepper/', methods=['GET', 'POST'])
def setstepper():  # set the stepper zero point
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu set stepper:")
	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="cancel":
			return redirect(url_for('show_Calibration'))

	# stepper
	stepperlist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"stepper",hardwaremod.HW_INFO_NAME)
	stepperstatuslist=[]
	for stepper in stepperlist:
		tempdict={}
		tempdict["position"]=hardwaremod.getstepperposition(stepper)
		tempdict["busy"]=hardwaremod.get_stepper_busystatus(stepper)
		stepperstatuslist.append(tempdict)

	return render_template('setstepper.html',stepperlist=stepperlist,stepperstatuslist=stepperstatuslist)

@application.route('/sethbridge/', methods=['GET', 'POST'])
def sethbridge():  # set the hbridge zero point
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu set hbridge:")
	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="cancel":
			return redirect(url_for('show_Calibration'))

	# hbridge
	hbridgelist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"hbridge*",hardwaremod.HW_INFO_NAME)
	hbridgestatuslist=[]
	for hbridge in hbridgelist:
		tempdict={}
		tempdict["position"]=hardwaremod.gethbridgeposition(hbridge)
		tempdict["busy"]="" #hardwaremod.get_hbridge_busystatus(hbridge)
		hbridgestatuslist.append(tempdict)

	return render_template('sethbridge.html',hbridgelist=hbridgelist,hbridgestatuslist=hbridgestatuslist)

@application.route('/DATAsetup/', methods=['GET', 'POST'])
def DATAsetup():  # set the items to ble visualized by default in the graphs
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	print (" we are here to show data")

	sensorlist=sensordbmod.gettablelist()
	actuatorlist=actuatordbmod.gettablelist()
	itemslist = sensorlist + actuatorlist

	if request.method == 'POST':
		requesttype=request.form['buttonsub']
		if requesttype=="cancel":
			return redirect(url_for('show_sensordata'))
		if requesttype=="save":
			for item in itemslist:
				#print "selsettingactive_" + item
				isactive=request.form["selsettingactive_" + item]
				#save isactive
				hardwaremod.WriteVisibleStatus(item,isactive)

			return redirect(url_for('show_sensordata'))

	finalitemlist=[]
	for item in itemslist:
		dicttemp={}
		dicttemp["name"]=item
		dicttemp["active"]=hardwaremod.ReadVisibleStatus(item)
		finalitemlist.append(dicttemp)

	print(finalitemlist)

	return render_template('DATAsetup.html', finalitemlist=finalitemlist)

@application.route('/Sensordata/', methods=['GET', 'POST'])
def show_sensordata():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	#----------------
	DATEFORMAT="%d/%m/%Y"
	periodlist=["Day","Week","Month","Year","Custom"]
	perioddaysdict={"Day":1,"Week":7,"Month":31,"Year":365}

	periodtype=periodlist[0]
	actiontype="show"

	if request.method == 'POST':
		periodtype=request.form['period']
		actiontype=request.form['actionbtn']
		startdatestr = request.form['startdate']
		enddatestr = request.form['enddate']

	elif request.method == 'GET':
		periodtype = request.args.get('period')
		actiontype = request.args.get('actionbtn')
		startdatestr = request.args.get('startdate')
		enddatestr = request.args.get('enddate')
		if periodtype==None:
			actiontype="show"
			periodtype=periodlist[0]

	usedsensorlist=[]
	usedactuatorlist=[]

	hygroactuatornumlist=[]
	hygrosensornumlist=[]
	hygrosensornumlistwithout=[]
	actuatornumlistwithout=[]
	hygrosensornumlistwithoutactive=[]

	chartjssensordata = []
	chartjsactuatordata = []

	if actiontype=="delete":
		print("delete all records")
		sensordbmod.deleteallrow()
		actuatordbmod.deleteallrow()
		actiontype="show"
		periodtype=periodlist[0]
		daysinthepast=perioddaysdict[periodtype]
		enddate=datetime.now()
		startdate = enddate - timedelta(days=daysinthepast)
	else:
		if periodtype!="Custom":
			daysinthepast=perioddaysdict[periodtype]
			enddate=datetime.now()
			startdate = enddate - timedelta(days=daysinthepast)
			startdatestr = str(startdate)
			enddatestr = str(enddate)
		else:
			startdate=datetime.strptime(startdatestr, DATEFORMAT)
			enddate=datetime.strptime(enddatestr, DATEFORMAT)
			# check days in the future
			daysinthefuture=(datetime.now()-enddate).days
			if daysinthefuture<0:
				enddate=datetime.now()
			# check enddate is after the startdate
			daysinthepast=(enddate-startdate).days
			if daysinthepast<0:
				daysinthepast=1
				startdate = enddate - timedelta(days=daysinthepast)

			daysinthepast=daysinthepast+1
			enddate = enddate.replace(hour=23, minute=59)

		logger.info("Start collect data...")

		sensordatafull, usedsensorlistfull = sensordbmod.getAllSensorsDataPeriodv2(enddate, daysinthepast)
		actuatordatafull,usedactuatorlistfull = actuatordbmod.getAllActuatorDataPeriodv2(enddate, daysinthepast)

		logger.info("Data collected for %d sensors and %d actuators",
			len(usedsensorlistfull),
			len(usedactuatorlistfull)
		)

		# Modify usedsensorlist and usedactuatorlist and remove the item that should be not visible
		usedsensorlist=[]
		for inde in range(len(usedsensorlistfull)):
			item=usedsensorlistfull[inde]
			visible = hardwaremod.ReadVisibleStatus(item)
			print ("item ", item , " visible ", visible)
			if visible == "True":
				usedsensorlist.append(item)

				data = []
				i = 0
				lastvalue = -10001
				for sd in sensordatafull[inde]:
					if sd[1] != lastvalue or len(data) <= 1: # only add data if lastvalue hast changed (improve js performance)
						timestamp = datetime.strptime(sd[0], '%Y-%m-%d %H:%M:%S').timestamp() * 1000
						data.append({'x':timestamp, 'y':sd[1]})
						lastvalue = sd[1]
						i += 1

				data.sort(key=lambda k: k['x'])
				chartjssensordata.append({'label':item, 'data':data})

		logger.info("sensor data converted (%d)", i)

		print("SENSOR LIST USED ", usedsensorlist )

		usedactuatorlist=[]
		for inde in range(len(usedactuatorlistfull)):
			item=usedactuatorlistfull[inde]
			visible = hardwaremod.ReadVisibleStatus(item)
			print ("item ", item , " visible ", visible)
			if visible == "True":
				usedactuatorlist.append(item)

				data = []
				i= 0
				for sd in actuatordatafull[inde]:
					timestamp = datetime.strptime(sd[0], '%Y-%m-%d %H:%M:%S').timestamp() * 1000
					data.append({'x':timestamp, 'y':sd[1]})
					i += 1

				data.sort(key=lambda k: k['x'])
				chartjsactuatordata.append({'label':item, 'data':data})

		logger.info("actuator data converted (%d)", i)

		actuatorlist=actuatordbmod.gettablelist()
		# associate same number to coupled actuators and sensors
		actuatorlisth= autowateringdbmod.getelementlist()
		for inde in range(len(usedactuatorlist)):
			element=usedactuatorlist[inde]
			if element in actuatorlisth:
				linkedsensor=autowateringdbmod.gethygrosensorfromactuator(element)
				if linkedsensor in usedsensorlist: # if the actuator has an associated sensor hygro
					hygroactuatornumlist.append(inde) # create list with index number of the actuator
					hygrosensornumlist.append(usedsensorlist.index(linkedsensor)) # create list with index of the matching sensros

		# select hygrometers in usedsensorlist with associated actuator where the actuator is not in the usedactuatorlist
		# this sensor would be solid line but not associated because the actuator is not used then not in the graph
		for inde in range(len(usedsensorlist)):
			element=usedsensorlist[inde]
			if not inde in hygrosensornumlist:
				#print "sensor element=", element
				if autowateringdbmod.checkactivehygrosensor(element): # sensor is active even if the associated actuator is not present
					#print "sensor element active=", element
					hygrosensornumlistwithoutactive.append(inde) # create list with index number of the actuator

		# select hygrometers without associated actuator,
		sensorlist=autowateringdbmod.getsensorlist()
		for hygro in sensorlist:
			if hygro in usedsensorlist:
				if not usedsensorlist.index(hygro) in hygrosensornumlist:
					if not usedsensorlist.index(hygro) in hygrosensornumlistwithoutactive:
						hygrosensornumlistwithout.append(usedsensorlist.index(hygro))

		# select watercontrol actuator without associated hygrometer
		#Usedfor="Moisturecontrol"
		#hygrosensorlist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,Usedfor,hardwaremod.HW_INFO_NAME)

		# actuatorlisth is provided by autowatering
		for actuator in actuatorlisth:
			if actuator in usedactuatorlist:
				if not usedactuatorlist.index(actuator) in hygroactuatornumlist:
					actuatornumlistwithout.append(usedactuatorlist.index(actuator))

		logger.info("showsensordata finished")

		#print "Sensors"
		#print "hygrosensornumlist " , hygrosensornumlist
		#print "hygrosensornumlistwithoutactive " , hygrosensornumlistwithoutactive
		#print "hygrosensornumlistwithout " , hygrosensornumlistwithout

		#print "actuators"
		#print "hygroactuatornumlist " , hygroactuatornumlist
		#print "actuatornumlistwithout " , actuatornumlistwithout

	startdatestr=startdate.strftime(DATEFORMAT)
	enddatestr=enddate.strftime(DATEFORMAT)

	#print "date periods " , startdatestr , " " , enddatestr , " days ", daysinthepast

	return render_template(
		'showsensordata.html',
		actiontype=actiontype,
		periodtype=periodtype,
		periodlist=periodlist,
		startdatestr=startdatestr,
		enddatestr=enddatestr,
		usedsensorlist=usedsensorlist,
		usedactuatorlist=usedactuatorlist,
		hygrosensornumlist=hygrosensornumlist,
		hygroactuatornumlist=hygroactuatornumlist,
		hygrosensornumlistwithout=hygrosensornumlistwithout,
		actuatornumlistwithout=actuatornumlistwithout,
		hygrosensornumlistwithoutactive=hygrosensornumlistwithoutactive,
		chartjssensordata=chartjssensordata,
		chartjsactuatordata=chartjsactuatordata
	)


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

	#print "table  --------------------------------------------------- > ",  table
	#print "table1  --------------------------------------------------- > ",  table1
	#print "table2  --------------------------------------------------- > ",  table2

	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		if elementlist:
			selectedelement=elementlist[0]

	print(" watering plan - selectedelement ", selectedelement)

	if request.method == 'POST':
		actiontype=request.form['actionbtn']
		print(actiontype)

		if actiontype == "save":
			element=request.form['element']
			print("save il water form...:" , element)
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
			flash('Table has been saved')
			table=wateringdbmod.gettable(1) # watering time multiplieer
			table1=wateringdbmod.gettable(0) # watering schema
			table2=wateringdbmod.gettable(2) # watering schema
			#print "after",table
			selectedplanmod.resetmastercallback()

		if actiontype == "advconfig":
			print("open advanced setting")
			return redirect('/Advanced/')

		if actiontype == "changename":
			print("change schema name")
			return hardwaresettingeditfieldschemaname()

		if actiontype == "sensorselect":
			print("select sensor for wateringplan")
			return wateringplansensorselect()

	return render_template(
		"wateringplan.html",
		title=title,
		paramlist=paramlist,
		elementlist=elementlist,
		schemaementlist=schemaementlist,
		table=table,
		table1=table1,
		table2=table2,
		selectedelement=selectedelement
	)

@application.route('/autowatering/' , methods=['GET', 'POST'])
def autowatering():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	title = "Auto Watering Setting"
	elementlist= autowateringdbmod.getelementlist()
	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		selectedelement=elementlist[0]

	#sensorlist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,"Moisture",hardwaremod.HW_INFO_NAME)

	sensorlist= autowateringdbmod.getsensorlist()
	#print "sensorlist ",sensorlist

	modelist=["None", "Full Auto" , "under MIN over MAX"]
	formlist=["workmode", "sensor" , "threshold", "wtstepsec", "maxstepnumber", "pausebetweenwtstepsmin", "allowedperiod" , "maxdaysbetweencycles", "sensorminacceptedvalue", "mailalerttype","samplesminutes" ]
	alertlist=["infoandwarning", "warningonly","none"]

	if request.method == 'POST':
		actiontype=request.form['actionbtn']
		print(actiontype)

		if actiontype == "save":
			element=request.form['element']
			print("save il water form...:" , element)
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
			dicttemp["samplesminutes"]=request.form[element+'_13']

			#print "dicttemp ----->",dicttemp
			autowateringdbmod.replacerow(element,dicttemp)
			flash('Table has been saved')
			autowateringmod.configupdate(element)

			print("Reset the Cycle:" , element)
			autowateringmod.cyclereset(element)
			#selectedplanmod.resetmastercallback()

		if actiontype == "reset":
			element=request.form['element']
			print("Reset the Cycle:" , element)
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
		cyclestatus=[]
		LOCtime=clockmod.convertUTCtoLOC_datetime(autowateringmod.getstatus(element,"cyclestartdate"))
		cyclestatus.append(LOCtime.strftime("%Y-%m-%d %H:%M:%S"))
		LOCtime=clockmod.convertUTCtoLOC_datetime(autowateringmod.getstatus(element, "lastwateringtime"))
		cyclestatus.append(LOCtime.strftime("%Y-%m-%d %H:%M:%S"))
		cyclestatus.append(autowateringmod.getstatus(element,"cyclestatus"))
		cyclestatus.append(autowateringmod.getstatus(element,"watercounter"))
		cyclestatus.append(autowateringmod.getstatus(element,"alertcounter"))
		#{"cyclestartdate":datetime.utcnow(),"lastwateringtime":datetime.utcnow(),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}
		cyclestatuslist.append(cyclestatus)

	return render_template(
		"autowatering.html",
		title=title,
		selectedelement=selectedelement,
		modelist=modelist,
		sensorlist=sensorlist,
		watersettinglist=watersettinglist,
		cyclestatuslist=cyclestatuslist,
		alertlist=alertlist
	)

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
	#print "sensorlist ",sensorlist
	timetriggerlist=automationdbmod.sensorlisttriggertime()

	modelist=["None", "Full Auto" , "Emergency Activation" , "Alert Only"]
	formlist=["workmode", "sensor" , "sensor_threshold", "actuator_threshold", "stepnumber", "pausebetweenwtstepsmin", "averagesample", "allowedperiod" , "mailalerttype" ,"mathoperation", "activationdelay" ]
	alertlist=["infoandwarning", "warningonly","none"]
	operationlist=["average", "min" , "max" ]

	if request.method == 'POST':
		actiontype=request.form['actionbtn']
		print(actiontype)

		if actiontype == "save":
			element=request.form['element']
			print("save il form...:" , element)
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
			dicttemp["mathoperation"]=request.form[element+'_10']
			dicttemp["activationdelay"]=request.form[element+'_11']

			#print "dicttemp ----->",dicttemp
			automationdbmod.replacerow(element,dicttemp)
			flash('Table has been saved')

			print("Reset the Cycle:" , element)
			automationmod.cyclereset(element)
			#selectedplanmod.resetmastercallback()

		if actiontype == "reset":
			element=request.form['element']
			print("Reset the Cycle:" , element)
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
		LOCtime=clockmod.convertUTCtoLOC_datetime(automationmod.AUTO_data[element]["lastactiontime"])
		cyclestatus.append(LOCtime.strftime("%Y-%m-%d %H:%M:%S"))
		cyclestatus.append(automationmod.AUTO_data[element]["status"])
		cyclestatus.append(automationmod.AUTO_data[element]["actionvalue"])
		cyclestatus.append(automationmod.AUTO_data[element]["alertcounter"])
		#{"cyclestartdate":datetime.utcnow(),"lastwateringtime":datetime.utcnow(),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}
		cyclestatuslist.append(cyclestatus)

	return render_template(
		"automation.html",
		title=title,
		selectedelement=selectedelement,
		modelist=modelist,
		sensorlist=sensorlist,
		watersettinglist=watersettinglist,
		cyclestatuslist=cyclestatuslist,
		operationlist=operationlist,
		alertlist=alertlist,
		timetriggerlist=timetriggerlist
	)

@application.route('/interrupt/' , methods=['GET', 'POST'])
def interrupt():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	title = "Auto Watering Setting"
	elementlist= interruptdbmod.getelementlist()
	selectedelement = request.args.get('selectedelement')
	if selectedelement==None:
		selectedelement=elementlist[0]

	sensorlist=interruptdbmod.sensorlist()
	#print "sensorlist ",sensorlist
	timetriggerlist=interruptdbmod.sensorlisttriggertime()

	modelist=["None","Pre-emptive Blocking","Counter Only" ]
	triggermode=["Counter","Frequency"]
	sensormodelist=["First Edge" , "First Edge + Level", "Second Edge" , "Second Edge + Level (inv)", "both Edges"]
	followupactionlist=["None", "Extend blocking state" , "Remove blocking state" , "Follow-up action" , "Remove and Follow-up" , "Extend and Follow-up"]
	formlist=["workmode", "sensor" , "sensor_mode", "actuator_output", "preemptive_period", "actionmode_afterfirst", "folloup_output", "allowedperiod" , "mailalerttype" , "interrupt_triggernumber" , "interrupt_validinterval", "trigger_mode"]
	alertlist=["infoandwarning", "warningonly","none"]

	if request.method == 'POST':
		actiontype=request.form['actionbtn']
		print(actiontype)

		if actiontype == "save":
			element=request.form['element']
			print("save il form...:" , element)
			selectedelement=element

			#add proper formatting
			dicttemp={}
			dicttemp["element"]=element
			dicttemp[formlist[0]]=request.form[element+'_1']
			dicttemp[formlist[1]]=request.form[element+'_2']
			dicttemp[formlist[2]]=request.form[element+'_3']
			dicttemp[formlist[3]]=request.form[element+'_4']
			dicttemp[formlist[4]]=request.form[element+'_5']
			dicttemp[formlist[5]]=request.form[element+'_6']
			dicttemp[formlist[6]]=request.form[element+'_7']
			dicttemp[formlist[7]]=[request.form[element+'_8_1'],request.form[element+'_8_2']]
			dicttemp[formlist[8]]=request.form[element+'_9']
			dicttemp[formlist[9]]=request.form[element+'_10']
			dicttemp[formlist[10]]=request.form[element+'_11']
			dicttemp[formlist[11]]=request.form[element+'_12']

			interruptdbmod.replacerow(element,dicttemp)
			flash('Table has been saved')

			interruptmod.cyclereset(element)

		if actiontype == "reset":
			element=request.form['element']
			print("Reset the Cycle:" , element)
			selectedelement=element
			interruptmod.cyclereset(element)

	watersettinglist=[]
	for element in elementlist:
		watersetting=[]
		watersetting.append(element)
		for item in formlist:
			watersetting.append(interruptdbmod.searchdata("element",element,item))

		watersettinglist.append(watersetting)

	cyclestatuslist=[]
	for element in elementlist:
		if not (element in interruptmod.AUTO_data):
			interruptmod.cyclereset(element)
		cyclestatus=[]
		try: # in case the object is not datetime
			cyclestatus.append(interruptmod.readstatus(element,"lastactiontime").strftime("%Y-%m-%d %H:%M:%S"))
		except:
			cyclestatus.append("")
		cyclestatus.append(interruptmod.readstatus(element,"status"))
		cyclestatus.append(interruptmod.readstatus(element,"actionvalue"))
		cyclestatus.append(interruptmod.readstatus(element,"alertcounter"))
		#{"cyclestartdate":datetime.utcnow(),"lastwateringtime":datetime.utcnow(),"cyclestatus":"done", "checkcounter":0, "alertcounter":0, "watercounter":0}
		cyclestatuslist.append(cyclestatus)

	print("ready to go to html")

	return render_template(
		"interrupt.html",
		title=title,
		selectedelement=selectedelement,
		modelist=modelist,
		sensormodelist=sensormodelist,
		followupactionlist=followupactionlist,
		sensorlist=sensorlist,
		watersettinglist=watersettinglist,
		cyclestatuslist=cyclestatuslist,
		alertlist=alertlist,
		timetriggerlist=timetriggerlist,
		triggermode=triggermode
	)

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

	#sensorlist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,"Moisture",hardwaremod.HW_INFO_NAME)	
	linkemelementlist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,"watercontrol",hardwaremod.HW_INFO_NAME)
	#print "linkemelementlist ",linkemelementlist

	modelist=["None","ScheduledTime","BeforeWatering"]
	formlist=["workmode","waterZone","minactivationsec","time"]
	#alertlist=["infoandwarning", "warningonly"]

	if request.method == 'POST':
		actiontype=request.form['actionbtn']
		print(actiontype)

		if actiontype == "save":
			element=request.form['element']
			print("save il fertilizer form...:" , element)
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

			#print "dicttemp ----->",dicttemp
			autofertilizerdbmod.replacerow(element,dicttemp) #modify autofertilizer row
			flash('Table has been saved')

		if actiontype == "advconfig":
			print("open advanced setting")
			return redirect('/Advanced/')

	fertilizersettinglist=[]
	for element in elementlist:
		fertilizersetting=[]
		fertilizersetting.append(element)
		for item in formlist:
			fertilizersetting.append(autofertilizerdbmod.searchdata("element",element,item))

		fertilizersettinglist.append(fertilizersetting)

	return render_template(
		"fertilizerplan.html",
		title=title,
		paramlist=paramlist,
		elementlist=elementlist,
		table=table,
		table1=table1,
		selectedelement=selectedelement,
		formlist=formlist,
		fertilizersettinglist=fertilizersettinglist,
		linkemelementlist=linkemelementlist,
		modelist=modelist
	)

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
		print(actiontype)

		if actiontype == "save":


			elementnum=request.form['element'] # this returns the Actuator in row_i number
			element=elementlist[int(elementnum)]
			print("save advanced form...:" , element)

			table=advancedmod.gettable()
			#print "before",table

			paramlist= advancedmod.getparamlist()
			elementlist= advancedmod.getelementlist()
			tablehead=advancedmod.gettableheaders()

			selectedelement=element

			#add proper formatting
			dicttemp={}
			dicttemp["name"]=element
			# table includes all the elements: Element, Parameters, rows, columns
			# element is fixed and not relevent to save procedure
			a=-1
			for param in table[int(elementnum)]:
				a=a+1
				b=-1
				listrowtemp=[]
				for rowp in param:
					b=b+1
					c=-1
					listcoltemp=[]
					for colp in rowp:
						c=c+1
						#print ("cursore" , str(element)+paramlist[a]+ "_" + str(b) + str(c))
						strtemp = request.form[str(elementnum)+paramlist[a]+ "_" + str(b) + str(c)]
						listcoltemp.append(strtemp)
					listrowtemp.append(listcoltemp)

				dicttemp[paramlist[a]]= listrowtemp
				dicttemp["cycleOption"] =request.form[str(elementnum)+"cycleOption"]
				dicttemp["dayCycle"]=request.form[str(elementnum)+"dayCycle"]
				dicttemp["startDate"]=datetime.now().strftime("%d/%m/%Y")

			#print( "dicttemp ", dicttemp )
			advancedmod.replacerow(element,dicttemp)
			# reset the scheduler
			print("Table saved")
			selectedplanmod.resetmastercallback()
			print("Schedule has been updated")
			flash('Schedule has been updated')

			table=advancedmod.gettable()
			#print "after",table
			title = "Advanced Setting"

		if actiontype == "setdefault":
			advancedmod.restoredefault()
			print("default restored")
			flash('Default values have been set')

		if actiontype == "goback":
			print("open watering plan setting")
			return redirect('/wateringplan/')

	cycleOptionList = ["Weekly Setting","Daily Setting"]
	dayCycleList = ["1","2","3","4","5","6","7","8","9","10"]

	selCycleOption=advancedmod.getSelCycleOpt(default=cycleOptionList[0])
	selDayCycle=advancedmod.getSelDayCycle(default=dayCycleList[0])

	print("********* ----" , selCycleOption)
	print(selDayCycle)

	return render_template(
		"advanced.html",
		title=title,
		cycleOptionList=cycleOptionList,
		dayCycleList=dayCycleList,
		selCycleOption=selCycleOption,
		selDayCycle=selDayCycle,
		paramlist=paramlist,
		elementlist=elementlist,
		table=table,
		tablehead=tablehead,
		selectedelement=selectedelement
	)

@application.route('/login', methods=['GET', 'POST'])
def login():
	message=""
	error = None
	change=False
	username=logindbmod.getusername().lower() #always transform to lowercase
	password=logindbmod.getpassword()

	# check if password needs to be secured (hashed)
	if len(password) != 64:
		logindbmod.restoredefault()
		password=logindbmod.getpassword()
		message = "Insecure password, reset to 'default'!"
		change = True

	elif request.method == 'POST':
		print(" LOGIN " , username)
		reqtype = request.form['button']
		if reqtype == "login":
			usernameform = request.form['username'].lower()
			passwordform = request.form['password']

			# hash the pw and compare
			m = hashlib.sha256()
			m.update(passwordform.encode("UTF-8"))
			hashedpw = m.hexdigest()

			if (usernameform != username) or (hashedpw != password):
				error = 'Invalid Credentials'
				logger.warning("Invalid Credentials for %s", username)
			else:
				session['logged_in'] = True
				#flash('You were logged in')
				return redirect(url_for('show_entries'))

		elif reqtype == "change":
			print("Display change password interface")
			change = True

		elif reqtype == "save":
			print("saving new login password")
			usernameform = request.form['username'].lower()
			passwordform = request.form['password']
			newpassword = request.form['newpassword']

			# hash the old pw entered
			m = hashlib.sha256()
			m.update(passwordform.encode("UTF-8"))
			password_hashed=m.hexdigest()

			if (usernameform != username) or (password_hashed != password):
				error = 'Invalid Credentials'
				change = True
			else:
				# hash the new pw
				m = hashlib.sha256()
				m.update(newpassword.encode("UTF-8"))
				newpassword_hashed=m.hexdigest()

				isok1 = logindbmod.changesavesetting('password',newpassword_hashed)
				if isok1:
					session['logged_in'] = True
					flash('New Password Saved')
					return redirect(url_for('show_entries'))

		elif reqtype=="cancel":
			return redirect(url_for('show_entries'))

	elif request.method == 'GET':
		message = request.args.get('message')
		#print "we are in GETTTTTTTTTTTT  " , message

	return render_template('login.html', error=error, change=change, message=message )

@application.route('/logout')
def logout():
	session.pop('logged_in', None)
	#flash('You were logged out')
	return redirect(url_for('show_entries'))


@application.route('/HardwareSetting/', methods=['GET', 'POST'])
def hardwaresetting():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu hardwareSetting:")

	fields=hardwaremod.HWdataKEYWORDS
	hwdata=hardwaremod.IOdata
	debugmode=DEBUGMODE

	tablehead=[]
	for key, value in fields.items():
		tablehead.append(key)
	#print "tablehead ", tablehead

	HWfilelist=hardwaremod.HWpresetlist(MYPATH) #list of fiels (path , Name)
	presetfilenamelist=[]
	listitem={}
	listitem["title"]="-No Selection-"
	listitem["filename"]="-No Selection-"
	presetfilenamelist.append(listitem)
	for item in HWfilelist:
		itemstr=item[1]
		listitem={}
		listitem["title"]=itemstr[10:len(itemstr)-4]
		listitem["filename"]=itemstr
		presetfilenamelist.append(listitem)
	#print "HW file list ---> ", presetfilenamelist

	if request.method == 'POST':
		requestinfo=request.form['buttonsub']
		requesttype=requestinfo.split("_")[0]
		print("requesttype "  , requestinfo , " " , requesttype)

		if requesttype=="applyHWpreset":
			print("Apply HW setting")
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
				#print "Source selected path ", filename , " Destination ", dstdef


				try:
					shutil.copyfile(filename, dstdef) #this is the default HW file
					answer="ready"
					isdone=True
				except:

					answer="problem copying file"
			else:
				print("No file was selected")
				answer="No file selected"

			# apply changes to the system
			if isdone:
				hardwaremod.restoredefault() # copy default to normal file and reload HWdata
				runallconsistencycheck()
				#scheduler setup---------------------
				selectedplanmod.resetmastercallback()
				#initiate the GPIO OUT pins
				initallGPIOpins()
				flash('New Hardware configuration has been Applied ')

		if requesttype=="edit":
			return hardwaresettingedit()

		if requesttype=="refresh":
			runallconsistencycheck()
			initallGPIOpins()
			flash('Hardware configuration has been Reset ')

	return render_template(
		'hardwaresetting.html',
		fields=fields,
		hwdata=json.dumps(hwdata),
		tablehead=tablehead,
		presetfilenamelist=presetfilenamelist,
		debugmode=debugmode
	)

@application.route('/HardwareSettingedit/', methods=['GET', 'POST'])
def hardwaresettingedit():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu hardwareSettingedit:")

	fields=hardwaremod.HWdataKEYWORDS

	tablehead=[]
	for key, value in fields.items():
		tablehead.append(key)
	#print "tablehead ", tablehead

	if request.method == 'POST':
		requestinfo=request.form['buttonsub']
		requesttype=requestinfo.split("_")[0]
		print("requesttype POST "  , requestinfo , " " , requesttype)

		if requestinfo=="edit":
			#request coming from previous page, need init table from zero
			print("the temporary Tables have been reset")
			#initialize IOdatarow
			hardwaremod.additionalRowInit()

			# Alignt the hardwaremod IOdatatemp to IOdata
			hardwaremod.IOdatatempalign()

		if requesttype=="confirm":
			print("Confirm table")
			# Copy the hardwaremod IOdatatemp to IOdata and save it
			hardwaremod.IOdatafromtemp()

			# apply changes to the system
			runallconsistencycheck()
			#scheduler setup---------------------
			selectedplanmod.resetmastercallback()
			#initiate the GPIO OUT pins
			initallGPIOpins()
			flash('New Hardware configuration has been Applied ')
			return redirect(url_for('hardwaresetting'))

		if requesttype=="reload":
			hardwaremod.IOdatatempalign()

		if requesttype=="cancel":
			return redirect(url_for('hardwaresetting'))

		if requesttype=="delete":
			strposition=len(requesttype)
			name=requestinfo[strposition+1:]
			#remove the row in IOdatatemp
			print(" Delete ", name)
			if hardwaremod.deleterow(name):
				flash('Row has been correctly deleted')
				print(" deleted")
			else:
				flash('Errors to delete the row','danger')

		if requesttype=="addrow":
			dictrow=hardwaremod.IOdatarow
			isok, message = hardwaremod.checkdata("",dictrow)
			if isok:
				hardwaremod.addrow(dictrow)
				flash('Row has been correctly Added')
				ret_data = {"answer":"Added"}
				hardwaremod.IOdatarow[hardwaremod.HW_INFO_NAME]=""
			else:
				print("problem ", message)
				flash(message,'danger')
				ret_data = {"answer":"Error"}

#	return render_template('hardwaresettingedit.html',fields=fields, hwdata=json.dumps(hwdata), tablehead=tablehead , HWfilelist=HWfilelist)

	hwdata=hardwaremod.IOdatatemp
	additionalrow=hardwaremod.IOdatarow

	return render_template('hardwaresettingedit.html',fields=fields, hwdata=hwdata, tablehead=tablehead , additionalrow=additionalrow)

@application.route('/hardwaresettingeditfield/', methods=['GET', 'POST'])
def hardwaresettingeditfield():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu hardwareSettingedit:")

	fields=hardwaremod.HWdataKEYWORDS

	tablehead=[]
	#for key, value in fields.iteritems():
	#	tablehead.append(key)
	#print "tablehead ", tablehead
	tablehead=[hardwaremod.HW_INFO_NAME]

	if request.method == 'POST':
		requestinfo=request.form['buttonsub']
		requesttype=requestinfo.split("_")[0]
		print("hardwaresettingeditfield requesttype POST "  , requestinfo , " " , requesttype)

		#if requestinfo=="editnames":
			#request coming from previous page, need init table from zero
			#print "the teporary Tables have been reset"
			# Alignt the hardwaremod IOdatatemp to IOdata
			#hardwaremod.IOdatatempalign()

		if requesttype=="confirm":
			print("Confirm table")
			# get the diferences in name field
			newnames=[]
			hardwaremod.getfieldvaluelisttemp("name",newnames)
			oldnames=[]
			hardwaremod.getfieldvaluelist("name",oldnames)

			# Copy the hardwaremod IOdatatemp to IOdata and save it
			hardwaremod.IOdatafromtemp()

			# apply changes to the system
			# basically instead of the consistencycheck procedure it should be simply the rename procedure -- Done

			autowateringdbmod.replacewordandsave(oldnames,newnames)
			wateringdbmod.replacewordandsave(oldnames,newnames)
			autofertilizerdbmod.replacewordandsave(oldnames,newnames)
			fertilizerdbmod.replacewordandsave(oldnames,newnames)
			automationdbmod.replacewordandsave(oldnames,newnames)
			interruptdbmod.replacewordandsave(oldnames,newnames)
			sensordbmod.consistencycheck()
			actuatordbmod.consistencycheck()
			#scheduler setup---------------------
			selectedplanmod.resetmastercallback()
			#initiate the GPIO OUT pins
			initallGPIOpins()
			return redirect(url_for('show_Calibration'))
		else:
			# Alignt the hardwaremod IOdatatemp to IOdata
			hardwaremod.IOdatatempalign()

		if requesttype=="reload":
			hardwaremod.IOdatatempalign()

		if requesttype=="cancel":
			return redirect(url_for('show_Calibration'))

	hwdata=hardwaremod.IOdatatemp

	returnfunction="hardwaresettingeditfield"

	ajaxurl="HWsettingEditAjax"

	return render_template(
		'hardwaresettingeditfield.html',
		returnfunction=returnfunction,
		ajaxurl=ajaxurl,
		fields=fields,
		hwdata=hwdata,
		tablehead=tablehead
	)

@application.route('/hardwaresettingeditfieldschemaname/', methods=['GET', 'POST'])
def hardwaresettingeditfieldschemaname():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu hardwareSettingeditschemaname:")

	fields={'name':[]}

	tablehead=['name']

	if request.method == 'POST':
		print("daje")

		buttonsub = request.form.get('buttonsub', None)
		requestinfo=""
		requesttype=""

		if buttonsub:
			requestinfo=request.form['buttonsub']
			requesttype=requestinfo.split("_")[0]

			print("hardwaresettingeditfieldschemaname requesttype POST "  , requestinfo , " " , requesttype)

			if requesttype=="confirm":
				print("Confirm table")
				print(advancedmod.tempelementdict)

				advancedmod.replaceschemanameandsave(advancedmod.tempelementdict)

				return redirect(url_for('wateringplan'))

			#if requesttype=="reload":
			#	hardwaremod.IOdatatempalign()

			if requesttype=="cancel":
				return redirect(url_for('wateringplan'))

		else:
			print("Not a real POST")

	hwdata=[]

	advancedmod.tempelementdict={}
	elementlist= advancedmod.getelementlist()
	for item in elementlist:
		hwdata.append({'name':item})
		advancedmod.tempelementdict[item]=item

	returnfunction="hardwaresettingeditfieldschemaname"

	ajaxurl="SchemaNameEditAjax"

	return render_template(
		'hardwaresettingeditfield.html',
		returnfunction=returnfunction,
		ajaxurl=ajaxurl,
		fields=fields,
		hwdata=hwdata,
		tablehead=tablehead
	)

@application.route('/HWsettingEditAjax/', methods=['GET','POST'])
def HWsettingEditAjax():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login Needed"}
		return jsonify(ret_data)

	recdata=[]
	ret_data={}
	if request.method == 'POST':
		print("we are in the HWsettingEdit")
		pk = request.form['pk']
		value = request.form['value']
		name = request.form['name']
		#print "request type : " , pk , "  " , value , "  " , name

		IOname=pk
		if IOname=="addrow":
			dictrow=hardwaremod.deepcopydict(hardwaremod.IOdatarow)
		else:
			dictrow=hardwaremod.searchrowtempbyname(IOname)
		dictrow[name]=value
		fieldtocheck=name

		#print "Dictrow: " ,dictrow
		#print "IOdatatemp: " , hardwaremod.IOdatatemp
		isok, message = hardwaremod.checkdata(fieldtocheck,dictrow)

	notok=False
	if isok:
		print("data is OK")

		#modify the IOdatatemp matrix
		if IOname=="addrow":
			hardwaremod.IOdatarow[name]=value
		else:
			isfound=hardwaremod.changeIOdatatemp(IOname,name,value)

		ret_data = {"answer": message}
		return jsonify(ret_data)
	else:
		print("data NOK ", message)
		ret_data = message
		return ret_data,400


@application.route('/SchemaNameEditAjax/', methods=['GET','POST'])
def SchemaNameEditAjax():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login Needed"}
		return jsonify(ret_data)

	isok=True
	message="ok"

	recdata=[]
	ret_data={}
	if request.method == 'POST':
		print("we are in the SchemaNameEdit")
		pk = request.form['pk']
		value = request.form['value']
		name = request.form['name']
		#print "request type : " , pk , "  " , value , "  " , name

		print(pk)
		previousname=pk
		print(value)
		newname=value
		print(name)

		# check if the new name is already present
		if newname in advancedmod.tempelementdict:
			message="name already present"
			print(message)
			isok=False
		if newname in advancedmod.tempelementdict.values():
			message="name already present"
			print(message)
			isok=False

		if newname=="":
			message="name cannot be empty"
			print(message)
			isok=False

	if isok:
		advancedmod.tempelementdict[previousname]=newname
		print(advancedmod.tempelementdict)
		ret_data = {"answer": message}
		return jsonify(ret_data)
	else:
		print("data NOK ", message)
		ret_data = message
		return ret_data,400

@application.route('/wateringplansensorselect/', methods=['GET', 'POST'])
def wateringplansensorselect():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu wateringplansensorselect:")
	#wateringplansensordbmod

	sensorlist=wateringplansensordbmod.sensorlist()
	selsensorlist, selsensorlist2=wateringplansensordbmod.getactivesensor()
	selduration=wateringplansensordbmod.getselduration()
	selcondition=wateringplansensordbmod.getselcondition()

	if request.method == 'POST':
		buttonsub = request.form.get('buttonsub', None)
		requestinfo=""
		requesttype=""

		if buttonsub:
			requestinfo=request.form['buttonsub']
			requesttype=requestinfo.split("_")[0]
			#print "requesttype "  , requestinfo , " " , requesttype

			if requesttype=="save":
				print("save")

				# time interval
				selduration=request.form['durationmin']
				print(selduration)
				wateringplansensordbmod.saveselduration(selduration)
				# logic condition
				selcondition=request.form['condition']
				print(selcondition)
				wateringplansensordbmod.saveselcondition(selcondition)

				selsensorlist=[]
				sensorlist=wateringplansensordbmod.sensorlist() #provides the list of value of the checked items

				selsensorlist = request.form.getlist('list1')
				print(selsensorlist)
				selsensorlist2 = request.form.getlist('list2')
				print(selsensorlist2)

				wateringplansensordbmod.saveselsensors(selsensorlist,selsensorlist2)

				wateringplansensordbmod.savesetting()
				return redirect(url_for('wateringplan'))

			if requesttype=="cancel":
				return redirect(url_for('wateringplan'))

	print ("selsensorlist ", selsensorlist)

	selsensorlistGUI=[]
	for item in sensorlist:
		dicttemp={}
		dicttemp["name"]=item
		if item in selsensorlist:
			dicttemp["active"]="True"
		else:
			dicttemp["active"]="False"
		if item in selsensorlist2:
			dicttemp["active2"]="True"
		else:
			dicttemp["active2"]="False"
		selsensorlistGUI.append(dicttemp)

	durationlist=["60","120","360","720","1440"]
	conditionlist=["AND","OR"]

	return render_template(
		'waterinplansensorselect.html',
		selcondition=selcondition,
		conditionlist=conditionlist,
		selduration=selduration,
		durationlist=durationlist,
		selsensorlistGUI=selsensorlistGUI
	)

@application.route('/weatherAPI/', methods=['GET', 'POST'])
def weatherAPI():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)
	print("visualizzazione menu weatherAPI:")

	APIfilelist=weatherAPImod.APIpresetlist() #list of fiels (path , Name)
	presetfilenamelist=[]
	listitem={}
	listitem["title"]="-No Selection-"
	listitem["filename"]="-No Selection-"
	presetfilenamelist.append(listitem)
	for item in APIfilelist:
		itemstr=item[1]
		listitem={}
		listitem["title"]=itemstr
		listitem["filename"]=itemstr
		presetfilenamelist.append(listitem)

	#print "HW file list ---> ", presetfilenamelist

	GUIitems=weatherAPImod.GetVisibleParam()
	for i in range(len(GUIitems)):
		GUIitems[i]["nameID"]=GUIitems[i]["name"]+"_"+str(i)

	#print " GUIitems ******************************** ", GUIitems

	wateringtems= wateringdbmod.getelementlist()
	activewateringlist=weatherAPImod.getactivewatering()
	wateringtemsGUI=[]
	for item in wateringtems:
		dicttemp={}
		dicttemp["name"]=item
		if item in activewateringlist:
			dicttemp["active"]="True"
		else:
			dicttemp["active"]="False"
		wateringtemsGUI.append(dicttemp)

	#print " wateringtemsGUI ******************************+++++ ", wateringtemsGUI

	if request.method == 'POST':
		requestinfo=request.form['buttonsub']
		requesttype=requestinfo.split("_")[0]
		#print "requesttype "  , requestinfo , " " , requesttype

		if requesttype=="applypreset":
			#print "Apply API setting"
			selectedpath=""
			selectedfilename=request.form['APIfilelist']
			for items in APIfilelist:
				if items[1]==selectedfilename:
					selectedpath=items[0]

			isdone=False
			isdone=weatherAPImod.CopytoDatabase(selectedpath)

			# apply changes to the system
			if isdone:
				GUIitems=weatherAPImod.GetVisibleParam()
				for i in range(len(GUIitems)):
					GUIitems[i]["nameID"]=GUIitems[i]["name"]+"_"+str(i)

				#print " GUIitems ******************************** ", GUIitems

				wateringtems= wateringdbmod.getelementlist()
				activewateringlist=weatherAPImod.getactivewatering()
				wateringtemsGUI=[]
				for item in wateringtems:
					dicttemp={}
					dicttemp["name"]=item
					if item in activewateringlist:
						dicttemp["active"]="True"
					else:
						dicttemp["active"]="False"
					wateringtemsGUI.append(dicttemp)

				flash('New API configuration has been Applied ')
			else:
				flash('Problem reading the configuration ','danger')

		if requesttype=="save":
			print("save")
			#print "GUIitems --------------------------->",GUIitems
			for formdata in GUIitems:
				if formdata["GUItype"]=="input":
					#print " reuest from web " , formdata["nameID"]
					formdata["value"]=request.form[formdata["nameID"]]

			#print " ................... FINISH GETTING DATA .............................::::"
			weatherAPImod.SetVisibleParam(GUIitems)
			wateringtemsactivelist=[]
			wateringtems= wateringdbmod.getelementlist()
			for item in wateringtems:
				#print "selsettingactive_" + item
				isactive=request.form["selsettingactive_" + item]
				#print isactive
				if isactive=="True":
					wateringtemsactivelist.append(item)
			weatherAPImod.SetWateractuators(wateringtemsactivelist)

			weatherAPImod.SaveSetting()

			activewateringlist=weatherAPImod.getactivewatering()
			wateringtemsGUI=[]
			for item in wateringtems:
				dicttemp={}
				dicttemp["name"]=item
				if item in activewateringlist:
					dicttemp["active"]="True"
				else:
					dicttemp["active"]="False"
				wateringtemsGUI.append(dicttemp)

		if requesttype=="TestQuery":
			weatherAPImod.QueryParse(GUIitems)

		if requesttype=="apply":
			# create counter
			newHWsettingRow=hardwaremod.InitRowHWsetting()
			weatherAPImod.ProvideHWsettingFields(newHWsettingRow)  # change relevant fields in dataromw

			#print "Row data" , newHWsettingRow
			# Copy the hardwaremod IOdatatemp to IOdata and save it

			hardwaremod.AddUpdateRowByName(newHWsettingRow)

			# apply changes to the system
			runallconsistencycheck()
			#scheduler setup---------------------
			selectedplanmod.resetmastercallback()
			#initiate the GPIO OUT pins
			#initallGPIOpins()
			flash('New Hardware configuration has been Applied ')

			# activate multiplier for the watering

		if requesttype=="uploadfile":
			print("import configuration file")

			if 'file' not in request.files:
				flash('No file','danger')
			else:
				f = request.files['file']
				if f.filename == '':
					flash('No file selected','danger')
				else:
					if ".txt" in f.filename:
						# control if the folder exist otherwise create it
						uploadfolder=application.config['UPLOAD_FOLDER'] # load the folder from config file, this is a fix folder, the file will be then moved
						fullfolderpath=os.path.join(MYPATH, uploadfolder)
						if not os.path.exists(fullfolderpath):
							os.makedirs(fullfolderpath)
							print(" folder has been created")

						f = request.files['file']
						#f.save(f.filename)
						selectedpath=os.path.join(uploadfolder, f.filename)
						f.save(selectedpath)
						# copy file to database folder
						isdone=False
						isdone=weatherAPImod.CopytoDatabase(selectedpath)

						print("Align the data to the new files config")

						# apply changes to the system
						if isdone:
							GUIitems=weatherAPImod.GetVisibleParam()
							for i in range(len(GUIitems)):
								GUIitems[i]["nameID"]=GUIitems[i]["name"]+"_"+str(i)

							#print " GUIitems ******************************** ", GUIitems

							wateringtems= wateringdbmod.getelementlist()
							activewateringlist=weatherAPImod.getactivewatering()
							wateringtemsGUI=[]
							for item in wateringtems:
								dicttemp={}
								dicttemp["name"]=item
								if item in activewateringlist:
									dicttemp["active"]="True"
								else:
									dicttemp["active"]="False"
								wateringtemsGUI.append(dicttemp)

							flash('New API configuration has been Applied ')
						else:
							flash('Problem reading the configuration ','danger')
					else:
						flash('Allowed file types is .txt ','danger')

	return render_template('weatherAPI.html', presetfilenamelist=presetfilenamelist,GUIitems=GUIitems, wateringtemsGUI=wateringtemsGUI)

@application.route('/notification/' , methods=['GET','POST'])
def messagebox():
	if request.method == 'POST':
		actiontype=request.form['actionbtn']
		print(actiontype)
		if actiontype == "DeleteAllMessages":
			messageboxmod.DeleteAllMessages()
		else:
			messageboxmod.DeleteMessage(int(actiontype))


	posts=messageboxmod.GetMessages()
	print(posts)

	# remember last seen
	messageboxmod.SaveLastSeen()

	return render_template('messagebox.html', posts=posts)

def currentpath(filename):
	return os.path.join(MYPATH, filename)

# interesting code to use flask as proxy to view the page contents. It works only for view
@application.route('/embedpage/', defaults={'path': ''})
@application.route('/embedpage/<path:path>')
def embedpage(path):
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	SITE_NAME="http://192.168.1.179/"
	r = requests.get(f'{SITE_NAME}{path}')
	return r.content



def Generictesting():
	print("Generic testing routine")
	Errorcounter=0
	errorstring=""
	#hardwaremod.initMQTT()
	#emailmod.sendallmail("alert", "sono un messaggio di prova")

	ThesholdOFFON="55"
	ThesholdONOFF="85"

	HASScompMatrix.HASSIOintegr.check_loop_and_connect()
	print(" testing the HASSIO hartbeat ò@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")

	if Errorcounter > 0:
		returnstr="Errors: " + errorstring
	else:
		returnstr="No errors"

	return returnstr

def Autotesting1():
	print("Auto testing Automation HAT")
	print("Ensure that the right HWsetting is loaded")

	#ActuatorList=["Relay1_2","Relay1_3","Relay1_4","Relay1_5","Relay1_6","Relay1_7","Relay1_8","Relay2_1","Relay2_2","Relay2_3","Relay2_4","Relay2_5","Relay2_6","Relay2_7","Relay2_8"]
	recordkey=hardwaremod.HW_INFO_IOTYPE
	recordvalue="output"
	recordkey1=hardwaremod.HW_CTRL_CMD
	recordvalue1="pulse"
	keytosearch="name"
	ActuatorList=hardwaremod.searchdatalist2keys(recordkey,recordvalue,recordkey1,recordvalue1,keytosearch)

	for target in ActuatorList:
		hardwaremod.makepulse(target,"10",True, 0)
		print(" Actuator ", target)
		time.sleep(0.16)

	GPIOpinlist=["21","25","7","24"]

	for gpio in GPIOpinlist:
		# Set the pin as output at level 1
		hardwaremod.setPinOutput(gpio,1)

	Sensorlist=[
		{"name":"pressuresensor1","min":800, "max":1200},
		#{"name":"tempsensor1", "min":10, "max":40},
		{"name":"Analog0","min":2.4, "max":2.6},
		{"name":"Analog1","min":2.4, "max":2.6},
		{"name":"Analog2","min":2.4, "max":2.6},
		{"name":"Analog3","min":2.4, "max":2.6},
		{"name":"Analog4","min":2.4, "max":2.6},
		{"name":"Analog5_15v","min":4.1, "max":5.9},
		{"name":"Analog6","min":2.4, "max":2.6},
		{"name":"Analog7","min":2.4, "max":2.6}
	]
	Errorcounter=0
	for sensor in Sensorlist:
		sensorname=sensor["name"]
		rangemin=sensor["min"]
		rangemax=sensor["max"]
		isok, readingstr, errmsg = hardwaremod.getsensordata(sensorname,1)
		try:
			reading=float(readingstr)
			print(" sensorname " , sensorname , " data " , reading)

			if (reading>rangemin)and(reading<rangemax):
				print(" sensorname " , sensorname , " data in RANGE !!!!!!!!!!!! ")
			else:
				Errorcounter=Errorcounter+1
				errorstring=" sensorname " + sensorname + " data out of range :( "
				print(errorstring)
				break
		except:
			Errorcounter=Errorcounter+1
			errorstring=" sensorname " + sensorname + " Not able to read the sensor :(  "
			print(errorstring)
			break
		time.sleep(1)

	if Errorcounter > 0:
		returnstr="Errors: " + errorstring
	else:
		returnstr="Well DONE ! :)"

	return returnstr

def Autotesting1_v10():
	print("Auto testing Automation HAT")
	print("Ensure that the right HWsetting is loaded")

	#ActuatorList=["Relay1_2","Relay1_3","Relay1_4","Relay1_5","Relay1_6","Relay1_7","Relay1_8","Relay2_1","Relay2_2","Relay2_3","Relay2_4","Relay2_5","Relay2_6","Relay2_7","Relay2_8"]
	recordkey=hardwaremod.HW_INFO_IOTYPE
	recordvalue="output"
	recordkey1=hardwaremod.HW_CTRL_CMD
	recordvalue1="pulse"
	keytosearch="name"
	ActuatorList=hardwaremod.searchdatalist2keys(recordkey,recordvalue,recordkey1,recordvalue1,keytosearch)

	for target in ActuatorList:
		hardwaremod.makepulse(target,"10",True, 0)
		print(" Actuator ", target)

	Sensorlist=[
		{"name":"pressuresensor1","min":800, "max":1200},
		{"name":"tempsensor1", "min":10, "max":40},
		{"name":"Analog0","min":2.4, "max":2.6},
		{"name":"Analog1","min":2.4, "max":2.6},
		{"name":"Analog2","min":2.4, "max":2.6},
		{"name":"Analog3","min":2.4, "max":2.6},
		{"name":"Analog4","min":2.4, "max":2.6},
		{"name":"Analog5_15v","min":4.5, "max":5.5}
	]
	Errorcounter=0
	for sensor in Sensorlist:
		sensorname=sensor["name"]
		rangemin=sensor["min"]
		rangemax=sensor["max"]
		isok, readingstr, errmsg = hardwaremod.getsensordata(sensorname,1)
		try:
			reading=float(readingstr)
			print(" sensorname " , sensorname , " data " , reading)

			if (reading>rangemin)and(reading<rangemax):
				print(" sensorname " , sensorname , " data in RANGE !!!!!!!!!!!! ")
			else:
				Errorcounter=Errorcounter+1
				errorstring=" sensorname " + sensorname + " data out of range :( "
				print(errorstring)
				break
		except:
			Errorcounter=Errorcounter+1
			errorstring=" sensorname " + sensorname + " Not able to read the sensor :(  "
			print(errorstring)
			break
		time.sleep(1)

	if Errorcounter > 0:
		returnstr="Errors: " + errorstring
	else:
		returnstr="Well DONE ! :)"

	return returnstr

def Autotesting2():
	print("Auto testing Irrigation HAT")
	print("Ensure that the right HWsetting is loaded")

	#ActuatorList=["Relay1_2","Relay1_3","Relay1_4","Relay1_5","Relay1_6","Relay1_7","Relay1_8","Relay2_1","Relay2_2","Relay2_3","Relay2_4","Relay2_5","Relay2_6","Relay2_7","Relay2_8"]
	recordkey=hardwaremod.HW_INFO_IOTYPE
	recordvalue="output"
	recordkey1=hardwaremod.HW_CTRL_CMD
	recordvalue1="pulse"
	keytosearch="name"
	ActuatorList=hardwaremod.searchdatalist2keys(recordkey,recordvalue,recordkey1,recordvalue1,keytosearch)

	# test pulse actuators
	for target in ActuatorList:
		hardwaremod.makepulse(target,"10",True, 0)
		print(" Actuator ", target)

	# test PINS of irrigation hat
	PINlist=["7","8"]
	for PIN in PINlist:
		hardwaremod.GPIO_setup(PIN, "out" , "pull_down")
		recdata=[]
		priority=0
		sendstring="pulse:"+PIN+":"+"2"+":"+"neg"+":"+"0"
		ack=hardwaremod.sendcommand("pulse",sendstring,recdata,target,priority)
		time.sleep(1)

	Sensorlist=[
		{"name":"humidsensor1","min":0, "max":100},
		{"name":"tempsensor1", "min":10, "max":40},
		{"name":"lightsensor1","min":10, "max":5000}
	]
	Errorcounter=0
	for sensor in Sensorlist:
		sensorname=sensor["name"]
		rangemin=sensor["min"]
		rangemax=sensor["max"]
		isok, readingstr, errmsg = hardwaremod.getsensordata(sensorname,1)
		try:
			reading=float(readingstr)
			print(" sensorname " , sensorname , " data " , reading)

			if (reading>rangemin)and(reading<rangemax):
				print(" sensorname " , sensorname , " data in RANGE !!!!!!!!!!!! ")
			else:
				Errorcounter=Errorcounter+1
				errorstring=" sensorname " + sensorname + " data out of range :( "
				print(errorstring)
				break
		except:
			Errorcounter=Errorcounter+1
			errorstring=" sensorname " + sensorname + " Not able to read the sensor :(  "
			print(errorstring)
			break
		time.sleep(1)

	if Errorcounter > 0:
		returnstr = "Errors: " + errorstring
	else:
		returnstr="Well DONE ! :)"

	return returnstr

def Autotesting3():
	print("Auto testing Super HAT")
	print("Ensure that the right HWsetting is loaded")

	#ActuatorList=["Relay1_2","Relay1_3","Relay1_4","Relay1_5","Relay1_6","Relay1_7","Relay1_8","Relay2_1","Relay2_2","Relay2_3","Relay2_4","Relay2_5","Relay2_6","Relay2_7","Relay2_8"]
	recordkey=hardwaremod.HW_INFO_IOTYPE
	recordvalue="output"
	recordkey1=hardwaremod.HW_CTRL_CMD
	recordvalue1="pulse/I2CGPIOEXP"
	keytosearch="name"
	ActuatorList=hardwaremod.searchdatalist2keys(recordkey,recordvalue,recordkey1,recordvalue1,keytosearch)
	print(" Testing Pulse output ********** ")

	for target in ActuatorList:
		hardwaremod.makepulse(target,"10",True, 0)
		time.sleep(0.01)
		print(" Actuator ", target)

	GPIOpinlist=["21","16","5","24","25","26","13","7","27","15","20","6","22","18","4","19","12","23","17","14"]

	for gpio in GPIOpinlist:
		# Set the pin as output at level 1
		hardwaremod.setPinOutput(gpio,1)

	Sensorlist=[
		{"name":"Analog1","min":2.4, "max":2.6},
		{"name":"Analog2","min":2.4, "max":2.6},
		{"name":"Analog3","min":2.4, "max":2.6},
		{"name":"Analog4","min":2.4, "max":2.6},
		{"name":"Analog5","min":2.4, "max":2.6},
		{"name":"Analog6","min":2.4, "max":2.6},
		{"name":"Analog7","min":2.4, "max":2.6},
		{"name":"Analog8_15v","min":4.5, "max":5.5}
	]
	Errorcounter=0
	for sensor in Sensorlist:
		sensorname=sensor["name"]
		rangemin=sensor["min"]
		rangemax=sensor["max"]
		isok, readingstr, errmsg = hardwaremod.getsensordata(sensorname,1)
		try:
			reading=float(readingstr)
			print(" sensorname " , sensorname , " data " , reading)
			logger.info('Testing SuperHat: Sensor= %s , Reading %s', sensorname, readingstr)

			if (reading>rangemin)and(reading<rangemax):
				print(" sensorname " , sensorname , " data in RANGE !!!!!!!!!!!! ")
			else:
				Errorcounter=Errorcounter+1
				errorstring=" sensorname " + sensorname + " data out of range :( "
				print(errorstring)
				break
		except:
			Errorcounter=Errorcounter+1
			errorstring=" sensorname " + sensorname + " Not able to read the sensor :(  "
			print(errorstring)
			break
		time.sleep(1)

	if Errorcounter > 0:
		returnstr="Errors: " + errorstring
	else:
		returnstr="Well DONE ! :)"

	return returnstr

def functiontest():
	print(" testing ")

	selectedplanmod.periodicdatarequest("Temp_DS18B20")

	#selectedplanmod.heartbeat()
	#mailname="mail1"
	#testo=[" riga 1 ", "riga 2 " , " Riga fine"]
	#emailmod.sendallmail("alert","prova mail", testo)

	#hardwaremod.GO_hbridge_position("Hbridge2",0)

	#filemanagementmod.configfilezip()

	#import statusdataDBmod
	#statusdataDBmod.write_status_data(autofertilizermod.AUTO_data,"doser1","tobeactivated",True)
	#statusdataDBmod.write_status_data(autofertilizermod.AUTO_data,"doser1","duration",5)
	#autowateringmod.activatewater("water1", 50)

	#target="doser1"
	#activationseconds="10"
	#selectedplanmod.pulsenutrient(target,activationseconds)

	#startdate=datetime.strptime('Sep 7 2018  5:00AM', '%b %d %Y %I:%M%p')
	#enddate=datetime.strptime('Sep 7 2018  8:00AM', '%b %d %Y %I:%M%p')
	#slopeOK=autowateringmod.checkinclination("hygroBalcFront",startdate,enddate)
	#print "got array " , slopeOK

	#selectedplanmod.mastercallback(True)
	#target="water1"
	#selectedplanmod.startpump(target,"30","10","5")

	#selectedplanmod.removeallscheduledjobs()
	#isok=hardwaremod.takephoto(True)
	#hostname=networkmod.gethostname()

	#refsensor="TimeTrigger"
	#element="water2"
	#automationmod.automationexecute(refsensor,element)
	#automationmod.activateactuator("mail1", 5)

	#isok, quantity = automationmod.sensorreading("pressuresensor1",5,"average")
	#print "isok " , isok , " quantity " , quantity
	#message = quantity

	return ""

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
	if servolist:
		initposition=hardwaremod.getservopercentage(servolist[0])
	else:
		initposition=""
	vdirection=hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_CTRL_LOGIC)
	if vdirection=="neg":
		rotdeg="180"
	else:
		rotdeg="0"

	return render_template(
		'videostream.html',
		initposition=initposition,
		itemlist=itemlist,
		ipaddress=ipaddress,
		videolist=videolist,
		servolist=servolist,
		rotdeg=rotdeg
	)


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
	if len(argumentlist) > 0:
		name=argumentlist[0]
	else:
		return jsonify(ret_data)

	if name=="testing":
		print("testing video stop")
		answer="done"
		answer=videocontrolmod.stream_video()

	if name=="start":
		idx=1
		data=""
		#print "argument list ", argumentlist
		while idx < len(argumentlist):
			data=data+"x"+argumentlist[idx]
			idx=idx+1
		data=data[1:]
		#print data
		element=request.args['element']
		#print "element " , element
		#print "starting Stream " , data
		vdirection=hardwaremod.searchdata(hardwaremod.HW_FUNC_USEDFOR,"photocontrol",hardwaremod.HW_CTRL_LOGIC)
		answer=videocontrolmod.stream_video(element,data) + "-" + element
		time.sleep(0.1)

	if name=="close":
		print("Closing mjpg-streamer server")
		videocontrolmod.stop_stream("non blocking")
		answer="closed"

	if name=="stop":
		print("Stop mjpg-streamer server")
		videocontrolmod.stop_stream()
		answer="stopped"


	ret_data = {"answer": answer}
	print("response data ", ret_data)
	return jsonify(ret_data)

# END ---------------------------------video part ---------------------------

@application.route('/logstream/')
def logstream():
	if not session.get('logged_in'):
		ret_data = {"answer":"Login Needed"}
		return jsonify(ret_data)

	lastreqtime = 0
	data = request.args['lasttime']
	if data and data != "0":
		try:
			# convert servertime to unixtime
			data = datetime.strptime(data,"%d/%m/%Y %H:%M:%S").timestamp()
			lastreqtime = int(float(data))
		except Exception as e:
			logger.error("Exception occured in logstream: ", e)

	def generate(lastlogtime):
		folderpath=os.path.join(MYPATH, "logfiles")
		logpath=folderpath+"/actuator.log"
		timeformat = "%Y-%m-%d %H:%M:%S"

		if not os.path.isfile(logpath):
			return False

		for line in list(open(logpath, "r+")):
			logtime = re.search(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
			if logtime:
				# convert logtime found to unixtime
				logtime = datetime.strptime(str(logtime.group()), timeformat).timestamp()
				if int(logtime) > lastlogtime:
					yield line

	return application.response_class(generate(lastreqtime), mimetype='text/plain')

@application.route('/showlogs/')
def showlogs():
	if not session.get('logged_in'):
		return render_template('login.html',error=None, change=False)

	# check the logs destination folder exist otherwise create it
	folderpath=os.path.join(MYPATH, "static")
	folderpath=os.path.join(folderpath, "logs")
	if not os.path.exists(folderpath):
		os.makedirs(folderpath)

	return render_template('showlogs.html')


if __name__ == '__main__':
	# start web server--------------- -------------------------
	print("start web server")
	global PUBLICPORT
	if PUBLICMODE:
		application.run(debug=DEBUGMODE,use_reloader=False,host= '0.0.0.0',port=networkmod.LOCALPORT)
	else:
		application.run(debug=DEBUGMODE,use_reloader=False,port=80)

	print("close")
