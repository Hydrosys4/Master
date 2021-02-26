import sqlite3
import os

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
		print(post)
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



class _MessageBox:
	def __init__(self,databasetable):
		self.database=_DataBase(databasetable)
		#dictitem={'title':"eccolo", 'content': " bla bla bla bla"}
		#self.database.add_row(dictitem)
		self.RemoveExceeding(13)

	def RemoveExceeding(self, maxitems):
		msglist = self.database.get_allrows()
		index=0
		for items in reversed(msglist):
			index=index+1
			print(items['id'])
			if index > maxitems:
				self.DeleteMessage(items['id'])

		
	def GetMessages(self):
		return self.database.get_allrows()

	def SaveMessage(self,dictitem):
		return self.database.add_row(dictitem)		

	def DeleteMessage(self,index):
		return self.database.delete_row(index)	




# single instantiation

_MessageBoxIst=_MessageBox("posts")

def GetMessages():
	return _MessageBoxIst.GetMessages()

def SaveMessage(dictitem):
	return _MessageBoxIst.SaveMessage(dictitem)
	
def DeleteMessage(index):
	return _MessageBoxIst.DeleteMessage(index)

