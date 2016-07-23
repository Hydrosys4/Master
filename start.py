# -*- coding: utf-8 -*-
"""
Flaskr
~~~~~~

A microblog example application written as Flask tutorial with
Flask and sqlite3.

:copyright: (c) 2010 by Armin Ronacher.
:license: BSD, see LICENSE for more details.
"""
import logging
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

# Raspberry Pi camera module (requires picamera package)
from camera_pi import Camera

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////
app = Flask(__name__)
app.config.from_object('flasksettings') #read the configuration variables from a separate module (.py) file
global SELTABLENAME
SELTABLENAME=""
global DEBUGMODE
DEBUGMODE=True
global PUBLICMODE
PUBLICMODE=True
MYPATH=""


# ///////////////// --- END GLOBAL VARIABLES ------


# ///////////////// -- MODULE INIZIALIZATION --- //////////////////////////////////////////

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





	
@app.teardown_appcontext
def close_db_connection(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


@app.route('/')
def show_entries():
	print "preparing home page"
	currentday=date.today()
			
	#Picture panel------------------------------------
	folderpath=os.path.join(MYPATH, "static")
	folderpath=os.path.join(folderpath, "hydropicture")
	sortedlist=sorted(os.listdir(folderpath))
	sortedlist.reverse()
	photopanellist=[]	
	if sortedlist:
		picturefile="hydropicture/"+sortedlist[0]	
		referencestr=sortedlist[0].split("@")[0]
		for filelist in sortedlist:
			if filelist.split("@")[0]==referencestr:
				picturefile="hydropicture/"+filelist
				photopanel={}
				photopanel["type"]="photo"	
				photopanel["active"]="yes"
				photopanel["title"]=""
				photopanel["file"]=picturefile	
				photopanel["link"]=url_for('imageshow')
				photopanel["linktitle"]="Go to Gallery"		
				print photopanel
				photopanellist.append(photopanel)

	panelinfolist=[]
	
	# temperature panels -------------------------------------------- (new version)
	MeasureType="Temperature"	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_MEASURE,MeasureType,hardwaremod.HW_INFO_NAME)
	print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/temperature-transp.png"
		paneldict["color"]="green"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
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
	print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/humidity-transp.png"
		paneldict["color"]="primary"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
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
	print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/pressure-transp.png"	
		paneldict["color"]="yellow"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
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
	print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/light-transp.png"		
		paneldict["color"]="red"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
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
	print "------------------------- namelist " , namelist
	for name in namelist:	
		paneldict={}	
		paneldict["icon"]="icons/moisture-transp.png"	
		paneldict["color"]="primary"	
		paneldict["type"]="sensor"		
		paneldict["link"]=url_for('show_sensordata' , elementtype=name,  period="Day", actionbtn="sensor")
		paneldict["linktitle"]="Go to Sensordata"
		paneldict["title"]=MeasureType
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
	print "------------------------- namelist " , namelist
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
	print "------------------------- namelist " , namelist
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

	return render_template('homepage.html',panelinfolist=panelinfolist,photopanellist=photopanellist,currentday=currentday, networklink=networklink, settinglink=settinglink)


@app.route('/network/', methods=['GET', 'POST'])
def network():
	wifilist=[]
	savedssid=[]	
	filenamelist="wifi networks"
	
	print "visualizzazione menu network:"


	wifilistencr=["s","a","d"]
	wifilist=networkmod.wifilist_ssid()
	iplocal=networkmod.get_local_ip()
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


	return render_template('network.html',filenamelist=filenamelist, connectedssid=connectedssid,localwifisystem=localwifisystem, wifilist=wifilist, wifilistencr=wifilistencr,savedwifilist=savedwifilist, iplocal=iplocal, ipport=ipport)



@app.route('/wificonfig/', methods=['GET', 'POST'])
def wificonfig():
	print "method " , request.method
	if request.method == 'GET':
		ssid = request.args.get('ssid')
		print " argument = ", ssid

	if request.method == 'POST':
		ssid = request.form['ssid']
		if request.form['buttonsub'] == "Save":
			password=request.form['password']
			networkmod.savewifi(ssid, password)
			networkmod.waitandconnect(5)
			print "Save"
		elif request.form['buttonsub'] == "Forget":
			print "forget"		
			networkmod.removewifi(ssid)
			print "remove network ", ssid
			print "Try to connect AP"
			networkmod.connect_AP()

		else:
			print "cancel"
		return redirect(url_for('network'))

	return render_template('wificonfig.html', ssid=ssid)


@app.route('/Imageshow/', methods=['GET', 'POST'])
def imageshow():
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
			logging.info(' all image files deleted ')
			
		else:
			monthtoshow=monthlist.index(actiontype)+1


	
	sortedlist=hardwaremod.photolist(MYPATH)
	
	filenamelist=[]
	wlist=[]
	hlist=[]
	titlelist=[]
	for files in sortedlist:
		filemonthnumber=files[2].month
		print filemonthnumber
		if filemonthnumber==monthtoshow :
			filenamelist.append(files[0])
			titlelist.append(files[1])
			(w,h)=hardwaremod.get_image_size(files[0])
			wlist.append(w)
			hlist.append(h)
			
			
	print filenamelist
	selectedmothname=monthdict[monthtoshow]
	print selectedmothname
	return render_template('showimages.html',filenamelist=filenamelist,titlelist=titlelist,wlist=wlist,hlist=hlist,monthlist=monthlist,selectedmothname=selectedmothname)


	
@app.route('/echo/', methods=['GET'])
def echo():
    # read from serial the values for arduino

	teperatura=string.join(random.choice(string.digits) for x in range(2)).replace(" ", "")
	light=string.join(random.choice(string.digits) for x in range(2)).replace(" ", "")
		
	#ret_data = {"tempsensor1": "1", "humidsensor1": "20"}
	
	ret_data = hardwaremod.readallsensors()

	print ret_data
	return jsonify(ret_data)




	

	
@app.route('/doit/', methods=['GET'])
def doit():
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
			pulse=int(argumentlist[idx])
			testpulsetime=str(pulse*1000)
		else:
			testpulsetime=str(20*1000)
		element=request.args['element']		

		print "starting pulse test " , testpulsetime
		answer=hardwaremod.makepulse(element,testpulsetime)
		ret_data = {"answer": answer}



	elif name=="photo":
		print "want to test photo"
		idx=1
		if idx < len(argumentlist):
			video=argumentlist[idx]
		ret_data=hardwaremod.shotit(video,True)
		
	elif name=="mail":
		mailaname=request.args['element']
		mailaddress=request.args['address']
		mailtitle=request.args['title']
		cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,mailaname,hardwaremod.HW_CTRL_CMD)
		print "want to test mail, address=" , mailaddress , " Title=" , mailtitle
		issent=emailmod.send_email_main(mailaddress,mailtitle,cmd)
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
		ret_data = {"answer":"ready"}

	return jsonify(ret_data)

@app.route('/saveit/', methods=['GET'])
def saveit():
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
		phototime=""
		phototime=request.args['time']
		print "save photo setting, time=" , phototime
		hardwaremod.changesavecalibartion(name,hardwaremod.HW_FUNC_TIME,phototime)
	elif name=="light1":
		lighttime=""
		lighttime=request.args['time']
		print "save light setting, time=" , lighttime
		hardwaremod.changesavecalibartion(name,hardwaremod.HW_FUNC_TIME,lighttime)


	ret_data = {"answer": "saved"}
	print "The actuator ", ret_data
	return jsonify(ret_data)
	
	
@app.route('/downloadit/', methods=['GET'])
def downloadit():
    # send command to the actuator for test
	recdata=[]
	ret_data={}
	
	name=request.args['name']
	if name=="downloadlog":
		dstfilename="log"+datetime.now().strftime("%Y-%m-%d-time:%H:%M")+".log"
		filename=hardwaremod.LOGFILENAME
		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		dst=os.path.join(folderpath, dstfilename)
		print "prepare file for download, address=" , filename, "destination " , dst
		try:
			shutil.copyfile(filename, dst)
			answer="ready"
		except:
			answer="problem copying file"
	elif name=="downloadprevlog":
		dstfilename="log"+datetime.now().strftime("%Y-%m-%d-time:%H:%M")+"-prev.log"
		filename=hardwaremod.LOGFILENAME + ".txt"
		folderpath=os.path.join(MYPATH, "static")
		folderpath=os.path.join(folderpath, "download")
		dst=os.path.join(folderpath, dstfilename)
		print "prepare file for download, address=" , filename, "destination " , dst
		try:
			shutil.copyfile(filename, dst)
			answer="ready"
		except:
			answer="problem copying file"
			
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


	ret_data = {"answer": answer, "filename": "download/"+dstfilename}
	print "The actuator ", ret_data
	return jsonify(ret_data)
	
@app.route('/testit/', methods=['GET'])
def testit():
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
	
	
		
@app.route('/ShowRealTimeData/', methods=['GET', 'POST'])
def show_realtimedata():
	sensorlist=sensordbmod.gettablelist()
	unitdict={}
	for item in sensorlist:
		unitdict[item]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,item,hardwaremod.HW_INFO_MEASUREUNIT)
	print "unitdict "  , unitdict
	return render_template('ShowRealTimeSensor.html', sensorlist=sensorlist, unitdict=unitdict)
	
@app.route('/systemmailsetting/', methods=['GET', 'POST'])
def systemmailsetting():
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
	

@app.route('/About/', methods=['GET', 'POST'])
def show_about():
	return render_template('About.html')
	
	
@app.route('/ShowCalibration/', methods=['GET', 'POST'])
def show_Calibration():  #on the contrary of the name, this show the setting menu
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
	videolist=hardwaremod.videodevlist()
	
	#read the sensors data
	print "read sensor data " 
	sensordatadict = hardwaremod.readallsensors()
	unitdict={}
	for item in sensordatadict:
		unitdict[item]=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,item,hardwaremod.HW_INFO_MEASUREUNIT)
	print "unitdict "  , unitdict
	
	initdatetime=clockmod.readsystemdatetime()
	
	#timezone
	countries=countryinfo.countries
	timezone=clockdbmod.gettimezone()
	print "Current timezone ->", timezone
	
	
	return render_template('ShowCalibration.html',videolist=videolist,actuatorlist=actuatorlist,lightsetting=lightsetting,photosetting=photosetting,mailsettinglist=mailsettinglist,sensordatadict=sensordatadict, unitdict=unitdict, initdatetime=initdatetime, countries=countries, timezone=timezone)

	
@app.route('/Sensordata/', methods=['GET', 'POST'])
def show_sensordata():
	#----------------
	datatypelist=["sensor","actuator"]
	periodlist=["Day","Week","Month","Year"]
	perioddaysdict={"Day":1,"Week":7,"Month":31,"Year":365}	

	if request.method == 'POST':
		sensortype=request.form['elementtype']
		periodtype=request.form['period']	
		actiontype=request.form['actionbtn']
	elif request.method == 'GET':
		sensortype = request.args.get('elementtype')
		periodtype = request.args.get('period')
		actiontype = request.args.get('actionbtn')		
		if sensortype==None:
			actiontype="sensor"
			periodtype=periodlist[0]
			sensorlist=sensordbmod.gettablelist()
			sensortype=sensorlist[0]

	sensordata=[]
	if actiontype=="delete":
		print "delete all records"
		sensordbmod.deleteallrow()
		actuatordbmod.deleteallrow()
		actiontype="sensor"
		periodtype=periodlist[0]
		sensorlist=sensordbmod.gettablelist()
		sensortype=sensorlist[0]
	if actiontype=="sensor":
		sensorlist=sensordbmod.gettablelist()
		if not (sensortype in sensorlist) :
			sensortype=sensorlist[0]
		startdate=datetime.now()
		sensordbmod.getSensorDataPeriod(sensortype,sensordata,startdate,perioddaysdict[periodtype])
	if actiontype=="actuator":
		sensorlist=actuatordbmod.gettablelist()
		if not (sensortype in sensorlist) :
			sensortype=sensorlist[0]
		startdate=datetime.now()
		actuatordbmod.getActuatorDataPeriod(sensortype,sensordata,startdate,perioddaysdict[periodtype])

	print "period", periodtype, "sensortype ", sensortype, " actiontype " , actiontype
	return render_template('showsensordata.html',actiontype=actiontype,periodtype=periodtype,periodlist=periodlist,sensortype=sensortype,sensorlist=sensorlist,sensordata=json.dumps(sensordata))


@app.route('/wateringplan/' , methods=['GET', 'POST'])
def wateringplan():

	title = "Watering Schedule"
	elementlist= wateringdbmod.getelementlist()	
	paramlist= wateringdbmod.getparamlist()
	table=wateringdbmod.gettable(1) # watering time multiplieer
	table1=wateringdbmod.gettable(0) # watering schema
	
	#advparamlist= advancedmod.getparamlist()
	schemaementlist= advancedmod.getelementlist()

	
	print "table  --------------------------------------------------- > ",  table
	print "table1  --------------------------------------------------- > ",  table1
		
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
				param=paramlist[j]
				dicttemp[param]=thelist	
				
			wateringdbmod.replacerow(element,dicttemp)		
			flash('Table as been saved')
			table=wateringdbmod.gettable(1) # watering time multiplieer
			table1=wateringdbmod.gettable(0) # watering schema
			#print "after",table
			selectedplanmod.startnewselectionplan()
			
		if actiontype == "advconfig":	
			print "open advanced setting"
			return redirect('/Advanced/')
			
		
	return render_template("wateringplan.html", title=title,paramlist=paramlist,elementlist=elementlist,schemaementlist=schemaementlist,table=table,table1=table1,selectedelement=selectedelement)

@app.route('/fertilizerplan/' , methods=['GET', 'POST'])
def fertilizerplan():

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



@app.route('/Advanced/', methods=['GET', 'POST'])
def advanced():
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

			if not session.get('logged_in'):
				abort(401)
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


	
@app.route('/login', methods=['GET', 'POST'])
def login():

	error = None
	change=False
	username=logindbmod.getusername()
	password=logindbmod.getpassword()
	
	if request.method == 'POST':
		print " here we are"
		reqtype = request.form['button']
		if reqtype=="login":
			if request.form['username'] != username:
				error = 'Invalid Credentials'
			elif request.form['password'] != password:
				error = 'Invalid Credentials'
			else:
				session['logged_in'] = True
				flash('You were logged in')   
				return redirect(url_for('show_entries'))

		elif reqtype=="change":
			print "Display chang password interface"
			change=True
						
		elif reqtype=="save":
			print "saving new login password"
			username=logindbmod.getusername()
			password=logindbmod.getpassword()
			newpassword=request.form['newpassword']
			if request.form['username'] != username:
				error = 'Invalid Credentials'
				change=True
			elif request.form['password'] != password:
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




@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/HardwareSetting/', methods=['GET', 'POST'])
def hardwaresetting():  #on the contrary of the name, this show the setting menu
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
			dstfilename=hardwaremod.DEFHWDATAFILENAME
			filename=os.path.join(MYPATH, selectedpath)

			folderpath=os.path.join(MYPATH, hardwaremod.DATABASEPATH)
			dst=os.path.join(folderpath, dstfilename)
			print "Source selected path ", filename , " Destination ", dst

			try:
				shutil.copyfile(filename, dst)
				answer="ready"
			except:
				answer="problem copying file"
			
			print answer
			if answer=="ready":
				hardwaremod.restoredefault()


	return render_template('hardwaresetting.html',fields=fields, hwdata=hwdata, tablehead=tablehead , HWfilelist=HWfilelist)



def currentpath(filename):
	return os.path.join(MYPATH, filename)


def functiontest():
	print " testing "
	selectedplanmod.startpump("water1","10","20","")

	#done=networkmod.connect_AP()
	#done=selectedplanmod.heartbeat()
	#if done:
	#	answer="executed"
	#else:
	#	answer="error"
	
	#reachgoogle=networkmod.check_internet_connection(10)

	return True


	
if __name__ == '__main__':
	

	# start web server--------------- -------------------------
	print "start web server"	
	global PUBLICPORT
	if PUBLICMODE:
		app.run(debug=DEBUGMODE,use_reloader=False,host= '0.0.0.0',port=networkmod.PUBLICPORT)
		#app.run(host='0.0.0.0', debug=True, port=12345, use_reloader=True)
	else:
		app.run(debug=DEBUGMODE,use_reloader=False,port=80)	

	print "close"
	selectedplanmod.stop()
