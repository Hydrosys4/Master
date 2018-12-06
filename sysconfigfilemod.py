# -*- coding: utf-8 -*-
"""
file storage utility
"""
import logging
import os
import os.path
import filestoragemod




# to change the static IP address it is necessary to modify several system configuration files in the RPI system:
# 1) dhcpcd config file -> this is the DHCP client
# 2) dnsmasq -> here the dhcp server the range of IP addresses provided should be in the same subnet of the static IP


def modifydhcpcdconfigfile(oldIP, newIP):

	# change the relevant section in the dhcpcd file
	afterkeyword="START HYDROSYS4 SECTION"
	beforekeyword="END HYDROSYS4 SECTION"
	#conffilepath="/home/anona/env/prova/dhcpcd.conf" #fake path
	conffilepath="/etc/dhcpcd.conf" #real path
	keyword="static ip_address"
	separator="="
	isok=modifyfilestring(conffilepath, oldIP, newIP, afterkeyword, beforekeyword, keyword, separator)
	return isok


def modifydnsmasqconfigfile(oldIP, newIP):
	# change the relevant section in the dnsmasq file
	oldstring=calculaterange(oldIP)
	newstring=calculaterange(newIP)	
	if not(oldstring and newstring):
		return False
	
	# implement
	afterkeyword="START HYDROSYS4 SECTION"
	beforekeyword="END HYDROSYS4 SECTION"
	#conffilepath="/home/anona/env/prova/dnsmasq.conf" #fake path
	conffilepath="/etc/dnsmasq.conf" #real path
	keyword="dhcp-range"
	separator="="
	isok=modifyfilestring(conffilepath, oldstring, newstring, afterkeyword, beforekeyword, keyword, separator)
	return isok

def calculaterange(IPaddress):
	# the IP range if made using the followinf formula:
	b=1
	c=9
	IPlist=IPaddress.split(".")
	
	if len(IPlist)==4:
		IPSTART=IPlist[:]
		IPEND=IPlist[:]		
		if int(IPlist[3])>244:		
			IPSTART[3]=str(int(IPlist[3])-c)
			IPEND[3]=str(int(IPlist[3])-b)
		else:
			IPSTART[3]=str(int(IPlist[3])+b)
			IPEND[3]=str(int(IPlist[3])+c)				
		IPSTARTstring=".".join(IPSTART)
		IPENDstring=".".join(IPEND)
		print " result ", IPSTARTstring+","+IPENDstring
		return IPSTARTstring+","+IPENDstring
	else:
		return ""





def modifyfilestring(filename, oldstring, newstring, afterkeyword, beforekeyword, keyword, separator):
		
	filedata=[]
	filestoragemod.readfiledata_plaintext(filename,filedata)
	#print "text File /n" , filedata
	can_modify=False
	for i in range(len(filedata)):
		line=filedata[i]
		if afterkeyword in line:
			can_modify=True
		if (beforekeyword!="") and (beforekeyword in line):
			can_modify=False		
		if (keyword in line) and (can_modify):
			print " row found ------------ !!!!!!!!! " , line
			if oldstring in line:
				# isolate and change the string
				#print " oldstring ", oldstring, " new ", newstring
				
				filedata[i]=line.replace(oldstring,newstring)
						
				print " new row  ------------ !!!!!!!!! " , filedata[i]
				filestoragemod.savefiledata_plaintext(filename,filedata)
				return True
			else:
				print "String value not found ", oldstring
				
	return False


def hostapdsavechangerow(searchkey,newvalue):
	BASICDATAFILENAME="/etc/hostapd/hostapd.conf"
	newrow=searchkey+"="+newvalue
	filestoragemod.savechangerow_plaintext(BASICDATAFILENAME,searchkey,newrow)

def hostapdsavechangerow_spec(data):
	BASICDATAFILENAME="/etc/hostapd/hostapd.conf"
	identifier="# HERE->"
	datastring=filestoragemod.disct2text(data[0])
	newrow=identifier+datastring
	filestoragemod.savechangerow_plaintext(BASICDATAFILENAME,identifier,newrow)	





#-- start DB utility--------////////////////////////////////////////////////////////////////////////////////////	




	
	
if __name__ == '__main__':

	oldstring="192.168.1.1"
	newstring="192.168.10.10"
	modifydhcpcdconfigfile(oldstring, newstring)
	modifydnsmasqconfigfile("192.168.1.172", newstring)
	#calculaterange("192.168.1.245")






