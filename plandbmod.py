# -*- coding: utf-8 -*-
"""
utility for the planning database
"""

import logging
import string
from datetime import datetime,date,timedelta
import databasemod

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

global DBFILENAME
global DBTABLE
global TABLENAMEFIELD
global ITEMWEEKSROW
DBTABLE='nutrients'
TABLENAMEFIELD='planname'
ITEMWEEKSROW=2
DBFILENAME="Nutrientdb.db"

# ///////////////// --- END GLOBAL VARIABLES ------


#-- start DB utility--------////////////////////////////////////////////////////////////////////////////////////	


def init_db():
	databasemod.init_db(DBFILENAME)
		

def columninfo():
	databasemod.columninfo(DBFILENAME,DBTABLE)
			
			
def rowdescription(deletefirstN):
	return databasemod.rowdescription(DBFILENAME,DBTABLE,deletefirstN)

		
def getvaluelist(field,valuelist):
	databasemod.getvaluelist(DBFILENAME,DBTABLE,field,valuelist)

		
def deleterowwithfield(field,value):
	databasemod.deleterowwithfield(DBFILENAME,DBTABLE,field,value)

	
def insertrowfields(rowfield,rowvalue):
	databasemod.insertrowfields(DBFILENAME,DBTABLE,rowfield,rowvalue)


	
def gettable(searchfield,searchvalue):
	return databasemod.gettable(DBFILENAME,DBTABLE,searchfield,searchvalue)

def getplantable(searchvalue):
	return gettable("planname",searchvalue)

#--end --------////////////////////////////////////////////////////////////////////////////////////		

#-- start Plan table utility--------////////////////////////////////////////////////////////////////////////////////////	

def getcolumntitle(table):
	sumweek=0
	coltitle=[]
	row=table[0]
	for row in table:
		try:
			nextsumweek=sumweek+row[ITEMWEEKSROW]
			coltitle.append(str(sumweek+1) + " - " + str(nextsumweek))
		except TypeError:
			nextsumweek=sumweek
			coltitle.append("-")
		sumweek=nextsumweek
	return coltitle

def emptycolumntitle():
	coltitle=[]
	for i in range(6):
		coltitle.append("-")
	return coltitle
	
	
def deletetablewithname(value):
	deleterowwithfield(TABLENAMEFIELD,value)
	
def getplanlist():
	valuelist=[]
	getvaluelist(TABLENAMEFIELD,valuelist)
	return valuelist


#--end --------////////////////////////////////////////////////////////////////////////////////////	
	
if __name__ == '__main__':

	DBFILENAME='Nutrientdb'

	




