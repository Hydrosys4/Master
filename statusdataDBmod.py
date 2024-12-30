from __future__ import print_function
from builtins import str
import logging
import filestoragemod

logger = logging.getLogger("hydrosys4."+__name__)


DATAFILENAME="statusdata.txt"

# ///////////////// --- UTILITY FOR STATUS VARIABLES ------


def read_status_data(data,element,variable,permanent=False, storeid=""):
	output=""
	if element in data:
		elementdata=data[element]

		if variable in elementdata:
			output=elementdata[variable]
			#logger.debug("Element found. Set output for %s/%s to %s", str(element), str(variable), str(output))

	else:
		print(" element NOT present")
		# element not present in the data use the default
		data[element]=data["default"].copy()
		elementdata=data[element]

		if variable in elementdata:
			output=elementdata[variable]
			#logger.debug("Element not found. Set output for %s/%s to %s", str(element), str(variable), str(output))

	# check with persistent element
	isok=False
	if permanent:
		if not storeid == "":
			isok, persistentoutput=readstoredvariable(storeid, element, variable)

	if isok:
		if not (persistentoutput == output):
			print("status",str(element),"variable",str(variable),
				"output mismatch between current value",str(output),
				"and stored value",str(persistentoutput))
			#logger.warning("status '%s' variable '%s' output mismatch between current value '%s' and stored value '%s'",
			#	str(element), str(variable), str(output) , str(persistentoutput))
			output=persistentoutput

	return output

def read_status_levels(data,element="",from_file=False, storeid=""):
	output=""
	if not from_file:
		output=data
		if (element)and(element in data):
			#print " element present"
			output=data[element]

	else:
		# check with persistent element
		if not storeid=="":
			isok, persistenooutput=readstoredvariable(storeid,element)

		if isok:
			output=persistenooutput

	return output


def write_status_data(data,element,variable,value,permanent=False, storeid=""):
	if element in data:
		data[element][variable]=value
	else:
		if "default" in data:
			data[element]=data["default"].copy()
			data[element][variable]=value
		else:
			print("ERROR: There is no default data for element", element,"/",variable)
			#logger.error('ERROR: There is no default data for element %s/%s', element, variable)

			return

	# in case of permanent option
	if permanent:
		if not storeid=="":
			storevariable(storeid,element,variable,value)
	

def remove_element_status_data(data,element,permanent=False, storeid=""):
	if element in data:
		del data[element]
			
	# in case of permanent option
	if permanent:
		if not storeid=="":
			remove_stored_element(storeid,element)


# ///////////////// --- END STATUS VARIABLES ------

# the status variable is a dictionary of dictionary, the first is the element, for each element there is a dictionary of variables
# the same status procedures apply to several different variables. At this module level there is no identification possible of this variables
# the variable identification is needed in case the elements are the same. No unique identification possible.
# when the status is set to be permanent, then to have a unique copy saved on file, it is needed to specify the unique identifier then coincide with the variable name normally


#AUTO_data={} # dictionary of dictionary
#AUTO_data["default"]={"lasteventtime":datetime.utcnow()- timedelta(minutes=waitingtime),"lastactiontime":datetime.utcnow()- timedelta(minutes=waitingtime),"actionvalue":0, "alertcounter":0, "infocounter":0, "status":"ok" , "threadID":None , "blockingstate":False}

# model of data to store:
#{"storeid":"mystoreid", "element1":{"variable1":"xx", "variable2":"yy"}, "element2":{"variable1":"xx1", "variable2":"yy2"}}


def storevariable(storeid,element,variable,value):
	filedata=[] # list of dictionaries
	readok=filestoragemod.readfiledata(DATAFILENAME,filedata)
	# even if readok  is not True, the below procedure creates a new file
	#search for the storeid and elemet
	storeidfound=False

	for thedict in filedata:
		if "storeid" in thedict:
			if thedict["storeid"]==storeid:
				storeidfound=True
				#search for elemet
				if element in thedict:
					thedict[element][variable]=value
				else:
					#create element
					dicttemp={}
					dicttemp[variable]=value
					thedict[element]=dicttemp
					

	if not storeidfound:
		# add another row to the dictionary
		dicttemp={}
		dicttemp["storeid"]=storeid
		dicttemp[element]={}
		dicttemp[element][variable]=value
		filedata.append(dicttemp)
	
	filestoragemod.savefiledata(DATAFILENAME,filedata)

	return True	



def remove_stored_element(storeid,element):
	filedata=[] # list of dictionaries
	readok=filestoragemod.readfiledata(DATAFILENAME,filedata)
	# even if readok  is not True, the below procedure creates a new file
	#search for the storeid and elemet

	elementfound=False
	for thedict in filedata:
		if "storeid" in thedict:
			if thedict["storeid"]==storeid:
				#search for elemet
				if element in thedict:
					elementfound=True
					del thedict[element]
					
				else:
					print(" no elelemt, nothing to delete ")

	if elementfound:
		filestoragemod.savefiledata(DATAFILENAME,filedata)

	return True	


def readstoredvariable(storeid,element="",variable=""):
	filedata=[] # list of dictionaries
	readok=filestoragemod.readfiledata(DATAFILENAME,filedata)
	# even if readok  is not True, the below procedure creates a new file
	#search for the storeid and elemet
	isok=False
	value=""
	for thedict in filedata:
		if "storeid" in thedict:
			if thedict["storeid"]==storeid:
				value=thedict
				isok=True
				if element:
					isok=False
					#search for elemet
					if element in thedict:
						value=thedict[element]
						isok=True
						if variable:
							isok=False
							if variable in thedict[element]:
								value=thedict[element][variable]
								isok=True

	return isok, value	

	
if __name__ == '__main__':
	# comment
	a=10
	PROVA_data={} # dictionary of dictionary
	PROVA_data["default"]={"actionvalue":0, "alertcounter":0, "infocounter":0, "status":"ok" , "threadID":None , "blockingstate":False}
	
	element="laprova"
	variable="comefare"
	value="adesso"
	permanent=True
	storeid="PROVA_data"
	write_status_data(PROVA_data,element,variable,value,permanent, storeid)
	element="laprova2"
	variable="comefare"
	value="adesso"
	permanent=True
	storeid="PROVA_data"
	write_status_data(PROVA_data,element,variable,value,permanent, storeid)	
	element="laprova2"
	variable="comefare"
	value="adesso"
	permanent=True
	storeid="PROVA_data2"
	write_status_data(PROVA_data,element,variable,value,permanent, storeid)		
	print(read_status_data(PROVA_data,element,variable,permanent, storeid))
	value="nonadesso"	
	write_status_data(PROVA_data,element,variable,value)	
	print(read_status_data(PROVA_data,element,variable,permanent, storeid))	
