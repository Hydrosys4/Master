# -*- coding: utf-8 -*-
"""
Database utility
"""
import basicSetting
import logging
import os
import os.path
import string
from datetime import datetime,date,timedelta
import sqlite3

# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

global DATABASEPATH
DATABASEPATH=basicSetting.data["DATABASEPATH"]
global SCHEMAFILEPATH
SCHEMAFILEPATH=basicSetting.data["SCHEMAFILEPATH"]
global REFERENCETABLE
REFERENCETABLE="referencetable"


# ///////////////// --- END GLOBAL VARIABLES ------



#-- start DB utility--------////////////////////////////////////////////////////////////////////////////////////	
def dbpath(filename):
	return os.path.join(DATABASEPATH, filename)	

def schemapath(filename):
	schemapath=os.path.join(DATABASEPATH, SCHEMAFILEPATH)
	return os.path.join(schemapath, filename)	

def init_db(filename):
	"""Creates the database tables."""
	if not os.path.isfile(dbpath(filename)): #file is there
		conn = sqlite3.connect(dbpath(filename))
		print "create empty database"
		print 'Creating schema from file'
		schemafilename = os.path.splitext(filename)[0]+'sc.sql'
		if os.path.isfile(schemapath(schemafilename)):
			with open(schemapath(schemafilename), 'rt') as f:
				schema = f.read()
			conn.executescript(schema)
	else:
		print filename, "database exists"



def aligndbtable(filename, endtablelist):
	starttablelist=tablenameninfo(filename)
	endtablelist.append(REFERENCETABLE)
	tabletoadd=[]
	for tablename1 in endtablelist:
		found=False
		for tablename2 in starttablelist:
			if tablename1==tablename2 :
				found=True
		if not(found) :
			tabletoadd.append(tablename1)
			
	tabletoremove=[]
	for tablename1 in starttablelist:
		found=False
		for tablename2 in endtablelist:
			if tablename1==tablename2 :
				found=True
		if not(found) :
			tabletoremove.append(tablename1)

	#print "to add ", tabletoadd
	#print "to remove " , tabletoremove
	
	for tablename in tabletoadd :
		createtablefromreference(filename,tablename)
	for tablename in tabletoremove :
		removetable(filename,tablename)		



def createtablefromreference(filename,tablename):
	with sqlite3.connect(dbpath(filename)) as conn:
		cursor = conn.cursor()
		cursor.execute('CREATE TABLE IF NOT EXISTS "' + tablename + '" AS SELECT * FROM "' + REFERENCETABLE + '";')
	conn.commit()

def removetable(filename,tablename):
	with sqlite3.connect(dbpath(filename)) as conn:
		cursor = conn.cursor()
		cursor.execute('DROP TABLE IF EXISTS "' + tablename + '";')
	conn.commit()


def tablenameninfo(filename):
	with sqlite3.connect(dbpath(filename)) as conn:
		cursor = conn.cursor()
		cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\';')
		#print 'tables:'
		tablenamelist=cursor.fetchall()
		tablenameout=[]
		for table in tablenamelist:
			tablenameout.append( str(table[0]))
		return tablenameout
		

def columninfo(filename,table):
	with sqlite3.connect(dbpath(filename)) as conn:
		cursor = conn.cursor()
		cursor.execute('select * from "' + table + '"')
		print 'table has these columns:'
		for colinfo in cursor.description:
			print colinfo
			
			
def rowdescription(filename,table,deletefirstN):
	with sqlite3.connect(dbpath(filename)) as conn:
		cursor = conn.cursor()
		cursor.execute('select * from "' + table + '"')
		print 'table has these columns:'
		rowdata=[]
		for colinfo in cursor.description:
			rowdata.append( colinfo [0])
		for i in range(deletefirstN):
			del rowdata[0]
		print rowdata
		return rowdata

def get_db(filename):
	conn = None
	try:
		conn = sqlite3.connect(dbpath(filename))
		return conn
	except lite.Error, e:
		print "Error %s:" % e.args[0]
		
def getvaluelist(filename,table,field,valuelist):
	print "visualizzazione field ", field
	db = get_db(filename)
	cur = db.execute('select distinct "' + field + '" from "' + table + '" order by "' + field + '"')
	namelistsql = cur.fetchall()
	del valuelist[:]
	for na in namelistsql:
		valuelist.append(str(na[0]))

		
def getdatafromfields(filename,table,fieldlist,valuelist):
	db = get_db(filename)
	fieldsstr= ', '.join(fieldlist)
	query_string = 'select %s from %s' % (fieldsstr, table)	
	cur = db.execute(query_string)
	db.commit()
	datarow = cur.fetchall()
	del valuelist[:]
	for rowdata in datarow:
		row=[]
		for i in range(len(fieldlist)):
			row.append(str(rowdata[i]))
		valuelist.append(row)

def getdatafromfieldslimit(filename,table,fieldlist,valuelist,limit):
	db = get_db(filename)
	fieldsstr= ', '.join(fieldlist)
	limitstr=str(limit)
	query_string = 'select %s from %s ORDER BY ROWID DESC LIMIT %s' % (fieldsstr, table,limitstr)	
	cur = db.execute(query_string)
	db.commit()
	datarow = cur.fetchall()
	del valuelist[:]
	for rowdata in datarow:
		row=[]
		for i in range(len(fieldlist)):
			row.append(str(rowdata[i]))
		valuelist.append(row)



		
def deleterowwithfield(filename,table,field,value):
	print "delete field ", field , " with value ", value
	db = get_db(filename)
	#remove old items from database in case the same name is already present
	db.execute('DELETE FROM "' + table + '" WHERE "' + field + '"="%s" ' % value.strip())
	db.commit()
	
def deleteallrow(filename,table):
	print "delete all row in table  ", table
	db = get_db(filename)
	#remove old items from database in case the same name is already present
	db.execute('DELETE FROM ' + table)
	db.commit()

def insertrowfields(filename,table,rowfield,rowvalue):
	db = get_db(filename)
	listfield=[]
	for itemfield in rowfield:
		listfield.append("'"+itemfield+"'")
	questionmarks=', '.join('?' * len(rowvalue))
	var_string = ', '.join(listfield)
	query_string = 'INSERT INTO %s (%s) VALUES (%s);' % (table, var_string, questionmarks)
	print query_string
	print var_string
	db.execute(query_string, rowvalue)					
	db.commit()

	
def gettable(filename,dbtable,searchfield,searchvalue):  #get table with column the values of searchfiled, and row the database row values, serchvalue is the output table
	db = get_db(filename)
	cur = db.execute('select * from "' + dbtable + '" WHERE "' + searchfield +'"="' + searchvalue +'"')
	table = cur.fetchall()
	return table






#--end --------////////////////////////////////////////////////////////////////////////////////////		
	
	
if __name__ == '__main__':

	DATABASEDUMMYFILE = 'dummydb.db'
	
	tablenameninfo(DATABASEDUMMYFILE)
	
	TABLE="dummytable"
	init_db(DATABASEDUMMYFILE)
	listfield=rowdescription(DATABASEDUMMYFILE,TABLE,1)
	valuelist=[]

	'''
	db = get_db(DATABASENUTRIENT)
	var_string="'one','two','three'"
	questionmarks=', '.join('?' * len(listdata))
	query_string = 'INSERT INTO %s (%s) VALUES (%s);' % (TABLE, var_string, questionmarks)
	print query_string
	db.execute(query_string, listdata)
	db.commit()
	#db.execute('INSERT INTO "' + TABLE + '" VALUES (%s))
	'''
	valuelist=[]
	start = datetime.now()
	getdatafromfieldslimit(DATABASEDUMMYFILE,TABLE,["two"],valuelist,4)
	end = datetime.now()
	timeperiod = end - start		
	print valuelist
	print timeperiod
	
	start = datetime.now()	
	getdatafromfields(DATABASEDUMMYFILE,TABLE,["two"],valuelist)
	end = datetime.now()
	timeperiod = end - start		
	print valuelist
	print timeperiod
	
	# database reading
