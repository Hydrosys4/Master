# -*- coding: utf-8 -*-
"""
utility for the planning database
"""
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import range
from past.utils import old_div
import logging
import string
from datetime import datetime,date,timedelta
import databasemod
import random
import hardwaremod



# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

global DBFILENAME
DBFILENAME = 'Sensordb.db'
global TIMEFIELD
global DATAFIELD
TIMEFIELD='readtime'
DATAFIELD='data1'
global SENSORQUERYINTERVALMINUTES
SENSORQUERYINTERVALMINUTES=15


# ///////////////// --- END GLOBAL VARIABLES ------


# ///////////////// -- MODULE INIZIALIZATION --- //////////////////////////////////////////
print("SensordDBmod inizialization")
databasemod.init_db(DBFILENAME)
tablelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"input",hardwaremod.HW_INFO_NAME)
databasemod.aligndbtable(DBFILENAME, tablelist)

# ///////////////// --- END init


#-- start DB utility--------////////////////////////////////////////////////////////////////////////////////////	


def init_db():
	databasemod.init_db(DBFILENAME)	

def gettablelist():
	tablelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"input",hardwaremod.HW_INFO_NAME)
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


def rowdescription(deletefirstN):
	return databasemod.rowdescription(DBFILENAME,DBTABLE,deletefirstN)

		
def getvaluelist(field,valuelist):
	databasemod.getvaluelist(DBFILENAME,DBTABLE,field,valuelist)

def getdatafromfields(fieldlist,valuelist):
	databasemod.getdatafromfields(DBFILENAME,DBTABLE,fieldlist,valuelist)
		
def deleterowwithfield(tablename,field,value):
	databasemod.deleterowwithfield(DBFILENAME,tablename,field,value)

def deleteallrow():
	tablelist=gettablelist()
	for tablename in tablelist :
		databasemod.deleteallrow(DBFILENAME,tablename)
	
def insertrowfields(table,rowfield,rowvalue):
	databasemod.insertrowfields(DBFILENAME,table,rowfield,rowvalue)

def gettable(searchfield,searchvalue):
	return databasemod.gettable(DBFILENAME,DBTABLE,searchfield,searchvalue)


#--end --------////////////////////////////////////////////////////////////////////////////////////		

#-- start Plan table utility--------////////////////////////////////////////////////////////////////////////////////////	


		
def getsensordbdata(selsensor,sensordata):
	fieldlist=[]
	fieldlist.append(TIMEFIELD)
	fieldlist.append(DATAFIELD)
	databasemod.getdatafromfields(DBFILENAME,selsensor,fieldlist,sensordata)

def getsensordbdatadays(selsensor,sensordata,days):
	fieldlist=[]
	fieldlist.append(TIMEFIELD)
	fieldlist.append(DATAFIELD)
	sampletime=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,selsensor,hardwaremod.HW_FUNC_TIME)
	schedtype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,selsensor,hardwaremod.HW_FUNC_SCHEDTYPE) # ["oneshot", "periodic"] #scheduling type
	if (sampletime!="")and(schedtype=="periodic"):
		samplingintervalminutes=int(sampletime.split(":")[1])
		if samplingintervalminutes>=1:
			samplesnumber=old_div((days*24*60),samplingintervalminutes)
			databasemod.getdatafromfieldslimit(DBFILENAME,selsensor,fieldlist,sensordata,samplesnumber)
		else:
			databasemod.getdatafromfields(DBFILENAME,selsensor,fieldlist,sensordata)		
	else:
		databasemod.getdatafromfields(DBFILENAME,selsensor,fieldlist,sensordata)

def getsensordbdatadaysV2(selsensor,sensordata,startdate, enddate): # V2 try to optimize access to database
	fieldlist=[]
	fieldlist.append(TIMEFIELD)
	fieldlist.append(DATAFIELD)
	#sampletime=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,selsensor,hardwaremod.HW_FUNC_TIME)
	
	timelist=hardwaremod.gettimedata(selsensor) # return list of int [0] sec, [1] min, [2] hours
	samplingintervalminutes=timelist[0]*60+timelist[1]

	schedtype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,selsensor,hardwaremod.HW_FUNC_SCHEDTYPE) # ["oneshot", "periodic"] #scheduling type
	#samplingintervalminutes=hardwaremod.toint(sampletime.split(":")[1],0)	# return zero in case of problems
	if (samplingintervalminutes>=1)and(schedtype=="periodic"):
		
		#minutessperiod=((enddate-startdate).total_seconds()+1 ) // 60		
		minutessperiod=((datetime.now()-startdate).total_seconds()+1 ) // 60	# sub optima approach
		# in this case we know the number of samples per day, so we query only the last samples of the database, this makes query way faster
		samplesnumber=minutessperiod//samplingintervalminutes
		# WARNING: with offset, there is an issue, every day the system loose some saple at midnight rescheduling only if the sample interval is less than 5 min.
		# in case of holes in the data sampling, it also provides wrong offset. Decided to use the non optimal approach
		offset=0
		#lastdata=databasemod.returnrowdatafromfieldslimitV2(DBFILENAME,selsensor,fieldlist,1,0)
		#if lastdata:
		#	dateref=datetime.strptime(lastdata[0][0].split(".")[0],'%Y-%m-%d %H:%M:%S')
		#	print( " dataref ", dateref , " enddate ", enddate)
		#	if dateref>enddate:
		#		minutessoffset=int( (dateref-enddate).total_seconds() / 60) 
		#		dayssoffset=minutessoffset//(24*60)
		#		print ("dayssoffset", dayssoffset , " minutessoffset ", minutessoffset)
		#		offset=int(minutessoffset/samplingintervalminutes) - (dayssoffset*10) # assume to loose max 10 samples per day
		#		samplesnumber=samplesnumber+ 2 * (dayssoffset*10) # allunga il periodo di samples
		#		offset=max(offset,0)
		#		print ("Defined samplesnumber ", samplesnumber , " offset ", offset)
		print (selsensor, " Get Database Data : samplesnumber ", samplesnumber, " offset ", offset , " Type " , schedtype , "samplingintervalminutes ", samplingintervalminutes)
		rowdata=databasemod.returnrowdatafromfieldslimitV2(DBFILENAME,selsensor,fieldlist,samplesnumber,offset)
		#print( " rowdata ", rowdata)	
	else:
		# no info about number of samples per day try with a number
		samplingintervalminutes=5 # assumption
		#samplesnumber=int(days*24*60/samplingintervalminutes)
		samplesnumber=1000
		offset=0
		lastitem=2
		dateref=enddate
		rowdata=[]
		while (dateref>startdate)and(lastitem>0):
			print (selsensor, " Get Database Data : samplesnumber ", samplesnumber, " offset ", offset)
			partrowdata=databasemod.returnrowdatafromfieldslimitV2(DBFILENAME,selsensor,fieldlist,samplesnumber,offset)	
			lastitem=len(partrowdata)
			if lastitem>=samplesnumber:
				offset=offset+lastitem
				dateref=datetime.strptime(partrowdata[lastitem-1][0].split(".")[0],'%Y-%m-%d %H:%M:%S')
			else:
				lastitem=0
			#print( " dataref ", dateref)			
			#print( " rowdata ", rowdata)
			print (selsensor, " Get Database Data : dateref ", dateref, " DB part lenght ", lastitem)
			rowdata.extend(partrowdata)
		# check the last value of the returned array

	# return only the data in right datetime interval and in list form (instead of tuple)
	for data in rowdata:
		try:
			dateref=datetime.strptime(data[0].split(".")[0],'%Y-%m-%d %H:%M:%S')
			if (dateref>=startdate)and(dateref<=enddate):
				value=float(data[1])
				templist=[data[0], value]
				sensordata.append(templist)
				
		except:
			print("Error in database reading ")
 


def getsensordbdatasamplesN(selsensor,sensordata,samplesnumber):
	fieldlist=[]
	fieldlist.append(TIMEFIELD)
	fieldlist.append(DATAFIELD)
	databasemod.getdatafromfieldslimit(DBFILENAME,selsensor,fieldlist,sensordata,samplesnumber)

def readallsensorsdatabase():
	#sensorlist=searchdatalist(HW_INFO_IOTYPE,"input",HW_INFO_NAME)
	sensorlist=gettablelist()
	sensorvalues={}
	sensortimestamp={}
	for sensorname in sensorlist:
		#sensorvalues[sensorname]=getsensordata(sensorname,3)
		databasevalues=[]
		samplesnumber=1
		getsensordbdatasamplesN(sensorname,databasevalues,samplesnumber)
		for value in databasevalues:
			sensorvalues[sensorname]=value[1]
			sensortimestamp[sensorname]=value[0]
	return sensorvalues
	
def getSensorDataPeriod(selsensor,sensordata,enddate,pastdays):
	num = int(pastdays)
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta
	#print " stratdate " ,startdate
	#print " enddate ", enddate
	allsensordata=[]
	#getsensordbdata(selsensor,allsensordata)
	getsensordbdatadaysV2(selsensor,sensordata,startdate,enddate)

	# sensor data --------------------------------------------

def getSensorDataPeriodXminutes(selsensor,datax,datay,startdate,enddate): # return sensordata in form of a matrix Nx2
	# x value is in minutes, y value is float. Shifted to have average Zero
	allsensordata=[]
	getsensordbdata(selsensor,allsensordata)
	del datax[:]	
	del datay[:]
	lenght=0
	for rowdata in allsensordata:
		try:
			dateref=datetime.strptime(rowdata[0].split(".")[0],'%Y-%m-%d %H:%M:%S')
			if (dateref>=startdate)and(dateref<=enddate):
				valuex=timediffinminutes(startdate, dateref)
				valuey=float(rowdata[1])
				datax.append(valuex)
				datay.append(valuey)
				lenght=lenght+1				
		except ValueError:
			print("Error in database reading ",rowdata)

	return lenght

def timediffinminutes(data2, data1):
	diff =  data1 - data2
	return abs(diff.days*1440 + old_div(diff.seconds,60))


def timediffdays(data2, data1):
	diff =  data1 - data2
	return abs(diff.days)


def getAllSensorsDataPeriodv2(enddate,pastdays):

	num = int(pastdays)
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta


	outputallsensordata=[]
	usedsensorlist=[]
	sensorlist=gettablelist()

	for selsensor in sensorlist:
		sensordata=[]

		getsensordbdatadaysV2(selsensor,sensordata,startdate, enddate)

		if len(sensordata)>0:
			outputallsensordata.append(sensordata)
			usedsensorlist.append(selsensor)

	return outputallsensordata,usedsensorlist
	# sensor data --------------------------------------------




def RemoveSensorDataPeriod(removebeforedays, maxremovepersensor=300):
	sensordata=[]
	field=TIMEFIELD
	startdate=datetime.now()
	num = removebeforedays
	tdelta=timedelta(days=num)
	enddate=startdate-tdelta
	pastdays=364
	
	sensorlist=gettablelist()
	for selsensor in sensorlist:
		getSensorDataPeriod(selsensor,sensordata,enddate,pastdays)
		#print "page ", selsensor
		#print sensordata
		itemnum=min(maxremovepersensor, len(sensordata))
		for i in range(itemnum):
			deleterowwithfield(selsensor,field,sensordata[i][0])
	# sensor data --------------------------------------------
	
	
def EvaluateDataPeriod(sensordata,startdate,enddate):
	# sensor data --------------------------------------------
	isok=False
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
				print("Evaluation : Error in database reading ",dateref , "  " ,data[1])
	
	
	if inde>0:
		average=old_div(summa,inde)
		isok=True
	else:
		average=0
		mini=0
		maxi=0
		
	outputdata["sum"]=summa		
	outputdata["average"]=average
	outputdata["min"]=mini
	outputdata["max"]=maxi	
	return isok , outputdata
	
def SumProductDataPeriod(sensordata,startdate,enddate,timeinterval):
	# sensor data --------------------------------------------
	sum=0
	for data in sensordata:
		dateref=datetime.strptime(data[0],'%Y-%m-%d %H:%M:%S')
		if (dateref>=startdate)and(dateref<=enddate):
			try:
				sum=sum+float(data[1])*timeinterval
			except ValueError:
				print(data[1])
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
	row.append("Sensor Name")
	row.append("Measure")
	row.append("Unit")
	row.append("Average 24H")	
	row.append("Min 24H")	
	row.append("Max 24H")	
	matrix.append(row)
	
	namelist=gettablelist()
	for name in namelist:
		row=[]
		row.append(name)
		row.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASURE))
		row.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT))

		sensordata=[]
		getsensordbdatadays(name,sensordata,1)
		#set date interval for average
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		isok, evaluateddata=EvaluateDataPeriod(sensordata,starttime,endtime)
		row.append(str('%.1f' % evaluateddata["average"]))
		row.append(str('%.1f' % evaluateddata["min"]))
		row.append(str('%.1f' % evaluateddata["max"]))
		matrix.append(row)
	
	return matrix



def consistencycheck():
	# this routine align the database table elements with the Hardware available elements "IOtype" labelled with usedfor "input"
	tablelist=gettablelist()
	databasemod.aligndbtable(DBFILENAME, tablelist)

			

if __name__ == '__main__':
	import time
	DBFILENAME='Sensordb.db'
	table="tempsensor1"
	# insert a number of random values in table "tempsensor1"
	
	print( " Add random rows to the table ")	
	start = time.time()
	for i in range(0,0):
		rowvalue=[]
		teperatura=random.randrange(1,101,1)
		rowvalue.append(datetime.now().replace(microsecond=0))
		rowvalue.append(teperatura)
		rowfield=[]
		rowfield.append(TIMEFIELD)
		rowfield.append(DATAFIELD)
		insertrowfields(table,rowfield,rowvalue)	
	end = time.time()
	print(end - start)	

	print( " read only the N samples ")
	start = time.time()
	sensordata=[]
	getsensordbdatadaysV2(table,sensordata,datetime.now()-timedelta(days=4),datetime.now()-timedelta(days=2))
	print("lenght list ", len(sensordata))
	#print(" list ", sensordata)
	end = time.time()
	print(" TIMER : --- ", end - start)	

	print( " read All samples ")	
	start = time.time()	
	sensordata=[]
	#getsensordbdata(table,sensordata)
	print("lenght list ", len(sensordata))
	end = time.time()
	print(" TIMER : --- ", end - start)	

	print( " read All samples ")	
	start = time.time()	
	#getAllSensorsDataPeriodv2(datetime.now(),2)
	end = time.time()
	print(" TIMER : --- ", end - start)	



