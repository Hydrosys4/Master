import sqlite3
import os
from datetime import datetime
import basicSetting  # for the database path


# database class -----------



class _DataBase:
	
	def __init__(self,databasetable):
		databasepath=basicSetting.data["DATABASEPATH"]
		databaseschemapath=basicSetting.data["SCHEMAFILEPATH"]
		dbfilename="msgdb.db"
		descfilename="msgschema.sql"
		self.dbpathfile=os.path.join(databasepath, dbfilename)	
		self.dbscpathfile=os.path.join(databasepath,databaseschemapath, descfilename)
		self.init_db(self.dbpathfile, self.dbscpathfile) # initialize db in case the file does not exist
		self.databasetable=databasetable
		

	def init_db(self, dbpathfile, dbscpathfile):

		if not os.path.isfile(dbpathfile): #file is there
			print("create empty database")			
			conn = sqlite3.connect(dbpathfile)
			print('Creating schema from file ' ,dbscpathfile)
			if os.path.isfile(dbscpathfile):
				print('Schema file found')
				with open(dbscpathfile, 'rt') as f:
					schema = f.read()
				conn.executescript(schema)
		else:
			print(dbpathfile, "database exists")



	def get_db_connection(self):
		conn = sqlite3.connect(self.dbpathfile)
		conn.row_factory = sqlite3.Row
		return conn

	def get_row(self,post_id):
		conn = self.get_db_connection()
		dictitem = conn.execute('SELECT * FROM "' + self.databasetable + '" WHERE id = ?',(post_id,)).fetchone()
		conn.close()
		return dictitem
		
	def get_allrows(self):
		conn = self.get_db_connection()
		dictlist = conn.execute('SELECT * FROM "' + self.databasetable + '"').fetchall()
		conn.close()
		return dictlist
		
	def add_row(self,dictlist):			
		conn = self.get_db_connection()
		if conn:
			rowvalue=list(dictlist.values())
			listfield=[]
			for itemfield in dictlist.keys():
				listfield.append("'"+itemfield+"'")
			questionmarks=', '.join('?' * len(rowvalue))
			var_string = ', '.join(listfield)
			query_string = "INSERT INTO '{}' ({}) VALUES ({});" .format(self.databasetable, var_string, questionmarks)
			conn.execute(query_string, rowvalue)
			#conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
            #             (dictlist['title'], dictlist['content']))
			conn.commit()
			conn.close()

	def delete_row(self,index):			
		conn = self.get_db_connection()
		if conn:
			conn.execute('DELETE FROM "' + self.databasetable + '" WHERE id = ?', (index,))
			conn.commit()
			conn.close()

	def delete_last_Nrows(self,number):			
		conn = self.get_db_connection()
		if conn:
			# example --> delete from tb_news where newsid IN (SELECT newsid from tb_news order by newsid desc limit 10)

			conn.execute('DELETE FROM "' + self.databasetable + '" WHERE id IN (SELECT id FROM "' + self.databasetable + '" ORDER BY id ASC LIMIT "' + str(number) + '")')
			conn.commit()
			conn.close()



class _MessageBox:
	def __init__(self,databasetable):
		self.maxitems=50
		self.database=_DataBase(databasetable)
		#dictitem={'title':"eccolo", 'content': " bla bla bla bla", 'created':" "}
		#self.database.add_row(dictitem)
		self.RemoveExceeding()

	def RemoveExceeding(self):
		msglist = self.database.get_allrows()
		totalnum=len(msglist)
		toremove= totalnum - self.maxitems
		if toremove>0:
			DeleteLastNMessage(toremove)

	def GetMessages(self):
		return self.database.get_allrows()

	def SaveMessage(self,dictitem):
		self.database.add_row(dictitem)
		self.RemoveExceeding()
		return	

	def DeleteMessage(self,index):
		return self.database.delete_row(index)	

	def DeleteLastNMessage(self,number):
		return self.database.delete_last_Nrows(number)	



# single instantiation

_MessageBoxIst=_MessageBox("posts")

# Interface functions

def GetMessages():
	return _MessageBoxIst.GetMessages()

def SaveMessage(dictitem):
	DATEFORMAT="%d/%m/%Y - %H:%M:%S"
	dictitem['created']=datetime.now().strftime(DATEFORMAT)
	return _MessageBoxIst.SaveMessage(dictitem)
	
def DeleteMessage(index):
	return _MessageBoxIst.DeleteMessage(index)

def DeleteLastNMessage(number):
	return _MessageBoxIst.DeleteLastNMessage(number)

def PrintMessages():
	messages = _MessageBoxIst.GetMessages()
	print("number of items ", len(messages))
	for row in messages:
		rowstr=""
		for item in row:
			rowstr=rowstr+" " +str(item)
		print (rowstr)

# maintenance Function




if __name__ == '__main__':
	
	print(" Add two rows and delete them")
	PrintMessages()
	dictitem=[]
	dictitem.append({'title':"eccolo", 'content': " bla bla bla bla", 'created':" "})
	dictitem.append({'title':"secondo", 'content': " bla bla bla", 'created':" "})
	for item in dictitem:
		SaveMessage(item)
	PrintMessages()
	#DeleteLastNMessage(1)
	#PrintMessages()