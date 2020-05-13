from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
import logging
from datetime import datetime , time ,timedelta
import _strptime
import hardwaremod
import os
import subprocess
import weatherAPIdbmod
import autofertilizermod
import statusdataDBmod
import threading
import urllib.request, urllib.error, json
from urllib.parse import urlencode




counterdefaultdata={"IOtype": "input" , "controllercmd": "WeatherAPI", "measure": "Percentage", "name": "RainMultiplier",  "schedulingtype": "periodic", "time": "00:120:00", "unit": "%", "usefor": "watercontrol"}
index0=0

NOWTIMELIST=[]

#In hardware, an internal 10K resistor between the input channel and 3.3V (pull-up) or 0V (pull-down) is commonly used. 
#https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/

logger = logging.getLogger("hydrosys4."+__name__)


waitingtime=1200

# ///////////////// -- STATUS VARIABLES  --  ///////////////////////////////

AUTO_data={} # dictionary of dictionary
AUTO_data["default"]={"lasteventtime":datetime.utcnow()- timedelta(minutes=waitingtime),"lastinterrupttime":datetime.utcnow(),"validinterruptcount":0,"eventactivated":False,"lastactiontime":datetime.utcnow()- timedelta(minutes=waitingtime),"actionvalue":0, "alertcounter":0, "infocounter":0, "status":"ok" , "threadID":None , "blockingstate":False}

SENSOR_data={} # used for the associated sensor in a separate hardwareSetting Row 
SENSOR_data["default"]={"Startcounttime":datetime.utcnow(),"InterruptCount":0}

PIN_attributes={}  # to speed up the operation during interurpt
PIN_attributes["default"]={"logic":"pos","refsensor":"","bouncetimeSec":0.001}

BLOCKING_data={}  # to speed up the operation during interurpt
BLOCKING_data["default"]={"BlockingNumbers":0,"BlockingNumbersThreadID":None}



def APIpresetlist():
	return weatherAPIdbmod.APIpresetlist()
	
def CopytoDatabase(selectedpath):
	return weatherAPIdbmod.CopytoDatabase(selectedpath)
	
def SaveSetting():
	return weatherAPIdbmod.saveWTsetting()

def MakeDictforGUI(params):
	dicttemp={}
	if params:
		if ("name" in params):
			dicttemp["name"]=params["name"]
		if ("value" in params):
			dicttemp["value"]=params["value"]
		else:
			dicttemp["value"]=""
		if ("GUItype" in params):
			dicttemp["GUItype"]=params["GUItype"]
		else:
			dicttemp["GUItype"]="output"
		if ("note" in params):
			dicttemp["note"]=params["note"]
		else:
			dicttemp["note"]=""
		
	return dicttemp		

def RecursiveSearch(subStruct,visiblelist):
	keyword="visible"
	
	if isinstance(subStruct, dict):
		if keyword in subStruct:
			visiblelist.append(MakeDictforGUI(subStruct))
			#print "found ----------------------------------"			
		for key in subStruct:
			RecursiveSearch(subStruct[key],visiblelist)	
			
	elif isinstance(subStruct, list):
		for items in subStruct:
			RecursiveSearch(items,visiblelist)


def GetVisibleParam_no(): # not usable because the dict items are not shown in order, this is a problem of Python
	var=weatherAPIdbmod.WTdata	
	visiblelist=[]	
	RecursiveSearch(var,visiblelist)
	return visiblelist

	
def GetVisibleParam():
	var=weatherAPIdbmod.WTdata	
	visiblelist=[]	
	if var:
		key="visible"
		
		# BasicInfo
		params=var["BasicInfo"]			
		RecursiveSearch(params,visiblelist)		
					
		# QueryGroup
		Itemslist=var["QueryGroup"]
		for items in Itemslist:
			
			# query param
			QueryParam=items["QueryItems"]
			RecursiveSearch(QueryParam,visiblelist)	

			#parse param	
			ParseParam=items["ParseItems"]
			RecursiveSearch(ParseParam,visiblelist)	
							
							
		# CounterInfo
		params=var["CounterInfo"]
		RecursiveSearch(params,visiblelist)	
						
	#print 	"  visiblelist " , visiblelist
	return visiblelist
	
	
def RecursiveSearchSet(subStruct,GUIdata):
	global index0
	keyword="visible"
	
	if isinstance(subStruct, dict):
		if keyword in subStruct:
			#found
			if "name" in subStruct:
				if "value" in subStruct:
					subStruct["value"]=GUIdata[index0]["value"]
				print(subStruct["name"])					
			index0=index0+1
			print("found ----------------------------------",	index0)
		for key in subStruct:
			RecursiveSearchSet(subStruct[key],GUIdata)	
			
	elif isinstance(subStruct, list):
		for items in subStruct:
			RecursiveSearchSet(items,GUIdata)


def SetVisibleParam(GUIdata):  # uses positional system
	global index0
	print("len GUI data ", len(GUIdata)) 
	var=weatherAPIdbmod.WTdata	
	if var:
		index0=0
		key="visible"
		
		# BasicInfo		
		params=var["BasicInfo"]		
		RecursiveSearchSet(params,GUIdata)
		
		
		# querygroup
		Itemslist=var["QueryGroup"]
		for items in Itemslist:

			# query param
			QueryParam=items["QueryItems"]
			RecursiveSearchSet(QueryParam,GUIdata)

			#parse param	
			ParseParam=items["ParseItems"]
			RecursiveSearchSet(ParseParam,GUIdata)

		# CounterInfo		
		params=var["CounterInfo"]
		RecursiveSearchSet(params,GUIdata)


def SetWateractuators(wateringtemsactivelist):
	var=weatherAPIdbmod.WTdata
	if var:
		var["Wateractuators"]=wateringtemsactivelist

def CreateQueryUlr(QueryParam): # evaluate one item of QueryItems
	dicttemp={}	
	URL=""	
	for params in QueryParam:	
		if "usedfor" in params:
			if params["usedfor"]=="url":
				URL=params["value"]
			if params["usedfor"]=="queryparam":
				param=params["param"]
				paramvalue=params["value"]
				# check the format
				if "format" in params:
					formatstring=params["format"]
				else:
					formatstring="%Y/%m/%d"	
				paramvalue = evaluateParam(paramvalue,formatstring)
				dicttemp[param]=paramvalue

	URLstring=URL+urlencode(dicttemp)
	return URLstring

def CreateQueryUrlall():

	var=weatherAPIdbmod.WTdata	
	if var:
		Querystringlist=[]

		# QueryGroup
		Itemslist=var["QueryGroup"]
		for items in Itemslist:
			# query param
			QueryParam=items["QueryItems"]			
			Querystringlist.append(CreateQueryUlr(QueryParam))
					
	return Querystringlist


def createquerystring(dicttemp):
	if "url" in dicttemp:
		thestring=dicttemp["url"]
		for item in dicttemp:
			paramstring=""
			if item!="url":
				paramstring=item+"="+dicttemp[item]+"&"
			thestring=thestring+paramstring
		thestring=thestring.rstrip("&")
		print("url string ", thestring)
		return thestring
	else:
		return ""
	
def evaluateParam(paramvalue,formatstring):
	specialparam=["Time Now","Time +1 day","Time +2 days","Time -1 day","Time -2days"]
	if paramvalue in specialparam:
		thetime=datetime.now()
		if paramvalue=="Time +1 day":
			thetime=thetime + timedelta(days=1)
		if paramvalue=="Time +2 days":
			thetime=thetime + timedelta(days=2)
		if paramvalue=="Time -1 day":
			thetime=thetime - timedelta(days=1)
		if paramvalue=="Time -2 days":
			thetime=thetime- timedelta(days=2)

		# check the format
		paramvalue=thetime.strftime(formatstring)
	
	return paramvalue


def parseJsondataItem(ParseParam,jsondata): # parse for sinlge param item
	isok=False
	dicttemp={}	
	print("jsondata " ,jsondata )		
	for params in ParseParam:	
		# for each of this set of params there is a value to be extracted
		itemname=params["name"]
		searchpathlist=params["searchpath"]
		subStruct=jsondata
		for searchitems in searchpathlist:
			gonext=False
			keyword=searchitems["keyword"]
			datamatch=""
			if "match" in searchitems:
				datamatch=searchitems["match"]
				formatstring=""
				if "format" in searchitems:
					formatstring=searchitems["format"]
				datamatch=evaluateParam(datamatch,formatstring)
			print("Searchitems " ,keyword , "  " , datamatch)
			# enter the json data structure to search
			if isinstance(subStruct, dict):
				if keyword in subStruct:
					subStruct=subStruct[keyword]
					gonext=True
			elif isinstance(subStruct, list):
				for items in subStruct:
					print("list items " , items[keyword])
					if items[keyword]==datamatch:
						subStruct=items
						gonext=True
						break
			if gonext==False:
				print(" Search Path finished before finding the Object  ........")
				break
	if gonext:
		print(" ========> item found ", 	subStruct)
		dicttemp["name"]=itemname
		dicttemp["value"]=subStruct
		isok=True
		
	return isok, dicttemp


	
def parseJsondata():
	jsondataold={"location":{"name":"Rome","region":"Lazio","country":"Italy","lat":41.9,"lon":12.48,"tz_id":"Europe/Rome","localtime_epoch":1587903198,"localtime":"2020-04-26 14:13"},"current":{"last_updated_epoch":1587902415,"last_updated":"2020-04-26 14:00","temp_c":21.0,"temp_f":69.8,"is_day":1,"condition":{"text":"Partly cloudy","icon":"//cdn.weatherapi.com/weather/64x64/day/116.png","code":1003},"wind_mph":0.0,"wind_kph":0.0,"wind_degree":256,"wind_dir":"WSW","pressure_mb":1011.0,"pressure_in":30.3,"precip_mm":0.0,"precip_in":0.0,"humidity":43,"cloud":25,"feelslike_c":21.0,"feelslike_f":69.8,"vis_km":10.0,"vis_miles":6.0,"uv":7.0,"gust_mph":3.6,"gust_kph":5.8},"forecast":{"forecastday":[{"date":"2020-04-28","date_epoch":1588032000,"day":{"maxtemp_c":20.7,"maxtemp_f":69.3,"mintemp_c":12.8,"mintemp_f":55.0,"avgtemp_c":16.4,"avgtemp_f":61.5,"maxwind_mph":11.6,"maxwind_kph":18.7,"totalprecip_mm":1.8,"totalprecip_in":0.07,"avgvis_km":9.0,"avgvis_miles":5.0,"avghumidity":74.0,"condition":{"text":"Light rain shower","icon":"//cdn.weatherapi.com/weather/64x64/day/353.png","code":1240},"uv":7.3},"astro":{"sunrise":"06:10 AM","sunset":"08:06 PM","moonrise":"09:43 AM","moonset":"12:27 AM"}}]},"alert":{}}

	jsondata={"location":{"name":"Rome","region":"Lazio","country":"Italy","lat":41.9,"lon":12.48,"tz_id":"Europe/Rome","localtime_epoch":1588338436,"localtime":"2020-05-01 15:07"},"current":{"last_updated_epoch":1588338016,"last_updated":"2020-05-01 15:00","temp_c":21.0,"temp_f":69.8,"is_day":1,"condition":{"text":"Partly cloudy","icon":"//cdn.weatherapi.com/weather/64x64/day/116.png","code":1003},"wind_mph":8.1,"wind_kph":13.0,"wind_degree":210,"wind_dir":"SSW","pressure_mb":1012.0,"pressure_in":30.4,"precip_mm":0.0,"precip_in":0.0,"humidity":56,"cloud":25,"feelslike_c":21.0,"feelslike_f":69.8,"vis_km":10.0,"vis_miles":6.0,"uv":7.0,"gust_mph":9.2,"gust_kph":14.8},"forecast":{"forecastday":[{"date":"2020-05-03","date_epoch":1588464000,"day":{"maxtemp_c":24.8,"maxtemp_f":76.6,"mintemp_c":13.5,"mintemp_f":56.3,"avgtemp_c":18.7,"avgtemp_f":65.7,"maxwind_mph":8.7,"maxwind_kph":14.0,"totalprecip_mm":0.0,"totalprecip_in":0.0,"avgvis_km":10.0,"avgvis_miles":6.0,"avghumidity":70.0,"condition":{"text":"Partly cloudy","icon":"//cdn.weatherapi.com/weather/64x64/day/116.png","code":1003},"uv":11.0},"astro":{"sunrise":"06:03 AM","sunset":"08:11 PM","moonrise":"03:19 PM","moonset":"04:08 AM"}}]},"alert":{}}
	var=weatherAPIdbmod.WTdata	
	if var:

		# QueryGroup
		Itemslist=var["QueryGroup"]
		for items in Itemslist:
			

			# parse param
			ParseParam=items["ParseItems"]			
			isok, datadict = parseJsondataItem(ParseParam,jsondata)
			if isok:
				print("DATA : " ,datadict["name"], "    " , datadict["value"])
			else:
				print("data not found")

def getJsonfromWeb(url):
	data={}
	#print("url=", url)
	try:
		response = urllib.request.urlopen(url)
		data = json.loads(response.read())
	except:
		logger.warning("WeatherAPI : Site returned error code")
	#print data
	return data

def QueryParse(GUIdata):
	var=weatherAPIdbmod.WTdata	
	resultdict={}
	if var:
		
		
		# QueryGroup
		Itemslist=var["QueryGroup"]
		for items in Itemslist:
			
			# query param
			QueryParam=items["QueryItems"]			
			QueryURL = CreateQueryUlr(QueryParam)			

			# ask server
			jsondata=getJsonfromWeb(QueryURL)

			# parse param
			ParseParam=items["ParseItems"]			
			isok, datadict = parseJsondataItem(ParseParam,jsondata)
		
			if isok:
				resultdict[datadict["name"]]=datadict["value"]

	
	for item in GUIdata:
		if item["name"] in resultdict:
			item["value"] = resultdict[item["name"]]
			
	print("GUIdata " , GUIdata)
				
def CalculateRainMultiplier():
	isok=True
	var=weatherAPIdbmod.WTdata	
	if var:
		
		WeaterData=[]
		# QueryGroup
		Itemslist=var["QueryGroup"]
		for items in Itemslist:
			
			# query param
			QueryParam=items["QueryItems"]			
			QueryURL=CreateQueryUlr(QueryParam)			

			# ask server
			jsondata=getJsonfromWeb(QueryURL)

			# parse param
			ParseParam=items["ParseItems"]			
			isok, datadict = parseJsondataItem(ParseParam,jsondata)
		
			if isok:
				WeaterData.append(datadict["value"])
			else:
				WeaterData.append("0")

	CalculationResult=0
	WeightParam=var["CounterInfo"]
	minvalue=0
	maxvalue=100
	initialValue=0
	queryintervalmin=180
	if ("min" in WeightParam):
		minvalue=tonumber(WeightParam["min"]["value"],0)	
	if ("max" in WeightParam):
		maxvalue=tonumber(WeightParam["max"]["value"],100)
	if ("initialValue" in WeightParam):		
		initialValue=tonumber( WeightParam["initialValue"]["value"],0)
	if ("queryintervalmin" in WeightParam):
		queryintervalmin=tonumber( WeightParam["queryintervalmin"]["value"]	,180)	
		
	Itemslist=WeightParam["weights"]
	i=0
	for item in Itemslist:
		if i < len(WeaterData):
			weight=tonumber(item["value"],0)
			dataint=tonumber(WeaterData[i], 0)
			CalculationResult=CalculationResult+weight*dataint
			i=i+1
		else:
			print("Mismatch between number of weights and parameters") 

	CalculationResult=initialValue+CalculationResult

	if CalculationResult<minvalue:
		CalculationResult=minvalue
	if CalculationResult>maxvalue:
		CalculationResult=maxvalue

	print("CalculationResult " , CalculationResult)
	return isok , CalculationResult

def getactivewatering():
	# "Wateractuators"
	WaterDatalist=[]
	var=weatherAPIdbmod.WTdata	
	if var:
		WaterDatalist=var["Wateractuators"]
	return WaterDatalist


def ProvideHWsettingFields(datarow):
	global counterdefaultdata

	# update some data field
	for key in counterdefaultdata:
		if key in datarow:
			datarow[key]=counterdefaultdata[key]
			
	var=weatherAPIdbmod.WTdata	
	if var:
		WeightParam=var["CounterInfo"]
		if ("queryintervalmin" in WeightParam):
			queryintervalmin=WeightParam["queryintervalmin"]["value"]	
	
	timestr="00:"+queryintervalmin+":00"
	datalist= hardwaremod.separatetimestringint(timestr)
	timestr=str(datalist[0])+":"+str(datalist[1])+":"+str(datalist[2])
	
	print(timestr)
	if "time" in datarow:
		datarow["time"]=timestr
	
	
	return True
	
def DefaultCounterName():
	return counterdefaultdata["name"]

def ActiveActuatorList():
	var=weatherAPIdbmod.WTdata
	if var:
		return var["Wateractuators"]

def tonumber(thestring, outwhenfail):
	try:
		n=float(thestring)
		return n
	except:
		return outwhenfail

def gen_dict_extract(key, var):  # not used but very interesting search function
    if hasattr(var,'items'): # should be "items" in python 3
        for k, v in var.items():
            if k == key:
                yield var
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result
	

def readstatus(element,item):
	return statusdataDBmod.read_status_data(AUTO_data,element,item)
	
def savedata(sensorname,sensorvalue):
	sensorvalue_str=str(sensorvalue)
	sensorvalue_norm=hardwaremod.normalizesensordata(sensorvalue_str,sensorname)
	sensordbmod.insertdataintable(sensorname,sensorvalue_norm)
	return	


def isNowInTimePeriod(startTime, endTime, nowTime):
	#print "iNSIDE pERIOD" ,startTime," ",  endTime," " ,  nowTime
	if startTime < endTime:
		return nowTime >= startTime and nowTime <= endTime
	else: #Over midnight
		return nowTime >= startTime or nowTime <= endTime

			



if __name__ == '__main__':
	
	"""
	prova functions
	"""

	

