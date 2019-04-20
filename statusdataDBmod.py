import logging

logger = logging.getLogger("hydrosys4."+__name__)



# ///////////////// --- UTILITY FOR STATUS VARIABLES ------


def read_status_data(data,element,variable):
	print data
	if element in data:
		print " element present"
		elementdata=data[element]
		if variable in elementdata:
			return elementdata[variable]
		else:
			# variable not in elementdata
			return ""
	else:
		print " element NOT present"
		# element not present in the data use the default
		data[element]=data["default"].copy()
		elementdata=data[element]
		print data
		if variable in elementdata:
			return elementdata[variable]
		else:
			# variable not in elementdata
			return ""
		
		
def write_status_data(data,element,variable,value):
	if element in data:
		data[element][variable]=value
	else:
		if "default" in data:
			data[element]=data["default"].copy()
			data[element][variable]=value
		else:
			logger.error('ERROR: There is no default data for element %s ', element )


# ///////////////// --- END STATUS VARIABLES ------




	
if __name__ == '__main__':
	# comment
	a=10
	
