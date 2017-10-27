# -*- coding: utf-8 -*-
"""
utility for the planning database
"""

import logging
import string
from datetime import datetime,date,timedelta
import databasemod
import random
import hardwaremod

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

global DBFILENAME
DBFILENAME = 'Actuatordb.db'
global TIMEFIELD
global DATAFIELD
TIMEFIELD='readtime'
DATAFIELD='data1'

# ///////////////// --- END GLOBAL VARIABLES ------


# ///////////////// -- MODULE INIZIALIZATION --- //////////////////////////////////////////

databasemod.init_db(DBFILENAME)
tablelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"output",hardwaremod.HW_INFO_NAME)
databasemod.aligndbtable(DBFILENAME, tablelist)

# ///////////////// --- END init




#-- start DB utility--------////////////////////////////////////////////////////////////////////////////////////	


def init_db():
	databasemod.init_db(DBFILENAME)


def gettablelist():
	tablelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"output",hardwaremod.HW_INFO_NAME)
	return tablelist

def gettablenameapprox(stringtofind):
	valuelist=[]
	outlist=[]
	hardwaremod.getfieldinstringvalue(hardwaremod.HW_INFO_NAME,stringtofind,valuelist)
	tablelist=gettablelist()	
	for value in valuelist:
		if 	value in tablelist:
			outlist.append(value)
	return outlist


def columninfo():
	databasemod.columninfo(DBFILENAME,DBTABLE)
	
def insertdataintable(table,datavalue):
	rowfield=[]
	rowfield.append(TIMEFIELD)
	rowfield.append(DATAFIELD)	
	rowvalue=[]
	rowvalue.append(datetime.now().replace(microsecond=0))
	rowvalue.append(datavalue)
	databasemod.insertrowfields(DBFILENAME,table,rowfield,rowvalue)

def deleterowwithfield(tablename,field,value):
	databasemod.deleterowwithfield(DBFILENAME,tablename,field,value)


#--end --------////////////////////////////////////////////////////////////////////////////////////		

#-- start specific actuator utility--------////////////////////////////////////////////////////////////////////////////////////	

def deleteallrow():
	tablelist=gettablelist()
	for tablename in tablelist :
		databasemod.deleteallrow(DBFILENAME,tablename)

def getActuatordbdata(selsensor,sensordata):
	fieldlist=[]
	fieldlist.append(TIMEFIELD)
	fieldlist.append(DATAFIELD)
	databasemod.getdatafromfields(DBFILENAME,selsensor,fieldlist,sensordata)
	
def getActuatorDataPeriod(selsensor,sensordata,enddate,pastdays):
	tdelta=0;
	num = int(pastdays)
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta
	#print startdate
	#print enddate
	allsensordata=[]
	getActuatordbdata(selsensor,allsensordata)
	del sensordata[:]
	for rowdata in allsensordata:
		dateref=datetime.strptime(rowdata[0].split(".")[0],'%Y-%m-%d %H:%M:%S')
		if (dateref>=startdate)and(dateref<=enddate):
			try:
				value=float(rowdata[1])
				templist=[rowdata[0], value]
				sensordata.append(templist)
			except ValueError:
				print "Error in database reading ",rowdata

	# sensor data --------------------------------------------
	
def getAllActuatorDataPeriodv2(enddate,pastdays):
	usedsensorlist=[]
	num = int(pastdays)
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta
	print " stratdate " ,startdate
	print " enddate ", enddate
	outputallsensordata=[]
	sensorlist=gettablelist()
	for selsensor in sensorlist:
		allsensordata=[]
		getActuatordbdata(selsensor,allsensordata)
		sensordata=[]
		# fetch raw data from database
		for rowdata in allsensordata:
			dateref=datetime.strptime(rowdata[0].split(".")[0],'%Y-%m-%d %H:%M:%S')
			if (dateref>=startdate)and(dateref<=enddate):
				try:
					value=float(rowdata[1])/1000
					dateinsecepoch=(dateref - datetime(1970,1,1)).total_seconds()
					templist=[rowdata[0], value]
					sensordata.append(templist)
				except ValueError:
					print "Error in database reading ",rowdata
		if len(sensordata)>0:
			outputallsensordata.append(sensordata)
			usedsensorlist.append(selsensor)
	
		
	return outputallsensordata,usedsensorlist
	# sensor data --------------------------------------------	
	
	
	


def RemoveActuatorDataPeriod(removebeforedays):
	sensordata=[]
	field=TIMEFIELD
	startdate=datetime.now()
	num = removebeforedays
	tdelta=timedelta(days=num)
	enddate=startdate-tdelta
	pastdays=364
	
	actuatorlist=gettablelist()
	for selsensor in actuatorlist:
		getActuatorDataPeriod(selsensor,sensordata,enddate,pastdays)
		#print "page ", selsensor
		#print sensordata
		for data in sensordata:
			deleterowwithfield(selsensor,field,data[0])

	# sensor data --------------------------------------------
	
	
	

	
def EvaluateDataPeriod(sensordata,startdate,enddate):
	# sensor data --------------------------------------------
	outputdata={}
	summa=0
	inde=0
	for data in sensordata:
		dateref=datetime.strptime(data[0],'%Y-%m-%d %H:%M:%S')
		if (dateref>=startdate)and(dateref<=enddate):
			try:
				number=float(data[1])
				if inde==0:
					mini=number
					maxi=number
				else:
					if mini>number:
						mini=number
					if maxi<number:
						maxi=number
				summa=summa+number
				inde=inde+1
			except ValueError:
				print "Error in database reading ",dateref , "  " ,data[1]
	
	
	if inde>0:
		average=summa/inde
	else:
		average=0
		mini=0
		maxi=0
		
	outputdata["sum"]=summa		
	outputdata["average"]=average
	outputdata["min"]=mini
	outputdata["max"]=maxi	
	return outputdata
	
	
	
def SumProductDataPeriod(sensordata,startdate,enddate,timeinterval):
	# sensor data --------------------------------------------
	sum=0
	for data in sensordata:
		dateref=datetime.strptime(data[0],'%Y-%m-%d %H:%M:%S')
		if (dateref>=startdate)and(dateref<=enddate):
			try:
				sum=sum+float(data[1])*timeinterval
			except ValueError:
				print data[1]
	return sum

	
	
def insertrandomrecords(recordnumber):
	rowfield=databasemod.rowdescription(DBFILENAME,DBTABLE,1)
	for i in range(recordnumber):
		randomvalues=[]
		randomvalues.append(datetime.now().replace(microsecond=0))
		for j in range(len(rowfield)-1):
			randomvalues.append(random.randrange(1,101,1))
		# waste time
		for j in range(20000):
			a=1
		insertrowfields(rowfield,randomvalues)

#--end --------////////////////////////////////////////////////////////////////////////////////////	


def sensorsysinfomatrix():
	# first row includes headers
	matrix=[]
	row=[]
	row.append("Name")
	row.append("Use")
	row.append("Unit")
	row.append("Average 24H")	
	matrix.append(row)
	
	namelist=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD,"pulse",hardwaremod.HW_INFO_NAME)
	for name in namelist:
		row=[]
		row.append(name)
		row.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_FUNC_USEDFOR))
		row.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT))

		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		data=[]
		getActuatordbdata(name,data)
		evaluateddata=EvaluateDataPeriod(data,starttime,endtime)	#set date interval for average

		row.append(str('%.1f' % (evaluateddata["sum"]/1000)))

		matrix.append(row)
	
	return matrix


def consistencycheck():
	# this routine align the database table elements with the Hardware available elements "IOtype" labelled with usedfor "input"
	tablelist=gettablelist()
	databasemod.aligndbtable(DBFILENAME, tablelist)


if __name__ == '__main__':

	DBFILENAME='Sensordb.db'
	init_db()
	insertrandomrecords(5)
	sensordata=[]
	getsensordbdata("temp1",sensordata)
	getSensorDataPeriod("temp1",sensordata,datetime.now(),1)
	print "data: "
	print sensordata
	rowvalue=[]
	teperatura=10
	PHreading=10
	ECreading=10
	light=10
	rowvalue.append(datetime.now().replace(microsecond=0))
	rowvalue.append(teperatura)
	rowvalue.append(PHreading)
	rowvalue.append(ECreading)
	rowvalue.append(light)
	rowfield=[]
	rowfield.append("readtime")
	rowfield.append("temp1")
	rowfield.append("ph1")
	rowfield.append("ec1")
	rowfield.append("light1")
	insertrowfields(rowfield,rowvalue)


	




