import logging
import subprocess
from wifiscan import Cell
import wifischeme
import threading
import emailmod
import logging
# stuff for the IP detection
import shlex
import re
import urllib2
import socket
import time
import wpa_cli_mod

CELLSLIST=[]
localwifisystem="HydroSys4"
PUBLICPORT=5012
WAITTOCONNECT=180
IPADDRESS ='192.168.0.172'




def wifilist_ssid():
	# get all cells from the air
	ssids=[]
	global CELLSLIST
	CELLSLIST=Cell.all('wlan0')
	if CELLSLIST:
		for cell in CELLSLIST:
			ssids.append(cell.ssid)
	return ssids

def savedwifilist_ssid():
	# get all setting from interfaces file
	return wpa_cli_mod.listsavednetwork('wlan0')	

def savewifi(ssid, password):
	global CELLSLIST
	for cell in CELLSLIST:
		if cell.ssid==ssid:	
			wifischeme.save(cell, password)
			print "schema has been saved"
	wpa_cli_mod.updateconfig()

def savedefaultAP():
	ssid='AP'
	#check if scheme already exist
	scheme=Scheme.find('wlan0', ssid)
	if (scheme is None):	
		#defaultstr=["iface wlan0-"+ssid+" inet static", "address 10.0.0.1", "netmask 255.255.255.0", "broadcast 255.0.0.0"]
		scheme = Scheme('wlan0', ssid, "static", APINTERFACEMODE)
		scheme.save() # modify the interfaces file adding the wlano-xx network data on the basis of the network encription type
		print "default AP schema has been saved"
	
def removewifi(ssid):
	#check if scheme already exist
	isthere, delindex = wifischeme.findssid(ssid)
	if isthere: #"This scheme already exists"
		wifischeme.delete(delindex)
	wpa_cli_mod.updateconfig()

def restoredefault():
	ssids=savedwifilist_ssid()
	for ssid in ssids:
		removewifi(ssid)
	connect_AP()


def connect_savedwifi(thessid):
	# get all cells from the air
	print "connecting to saved wifi network"
	isok=False
	ifdown("wlan0")
	isok=wpa_cli_mod.enable_ssid("wlan0",thessid)
	time.sleep(1)
	ifup("wlan0")			
	addIP("wlan0")	
	return isok

	
def connect_preconditions():
	print "checking preconditions for WiFi connection"
	# get all cells from the air
	ssids=[]
	i=0
	while (len(ssids)==0 and i<3):
		i=i+1
		cells=Cell.all('wlan0')
		time.sleep(1)
		if cells:
			for cell in cells:
				ssids.append(cell.ssid)
	
	print "ssID on air =", ssids
	savedssids = wpa_cli_mod.listsavednetwork("wlan0")
	for ssid in savedssids:
		#print " Scheme ", scheme
		if ssid in ssids:
			print "At least one of WIFI network detected have saved credentials, ssid=" , ssid
			return ssid
	print "No conditions to connect to wifi network"	
	return ""

	
def connectedssid():
	cmd = ['iw', 'wlan0', 'info']
	scanoutput = subprocess.check_output(cmd).decode('utf-8')
	time.sleep(1.5)	
	#scanoutput = subprocess.check_output('iw ' , 'wlan0 ' , 'info ', stderr=subprocess.STDOUT)
	#print scanoutput
	ssids=[]
	for line in scanoutput.split('\n'):
		#print " line ",line
		strstart=line.find("ssid")
		if strstart>-1:
			substr=line[(strstart+len("ssid")):]
			ssid=substr.strip()
			ssids.append(ssid)
	print "Connected to ", ssids
	return ssids


def start_hostapd():
	done=False
	try:
		print "try to start hostapd"
		# systemctl restart dnsmasq.service
		cmd = ['systemctl' , 'restart' , 'hostapd.service']
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(2)	
	except:
		print "Hostapd error failed to start the service "
		return False
	else:
		strstart=output.find("failed")
		if strstart>-1:
			print "failed to start hostapd"
			done=False
		else:
			done=True
	return done

def stop_hostapd():
	done=False
	try:		
		print "try to stop hostapd"
		# systemctl restart dnsmasq.service
		cmd = ['systemctl' , 'stop' , 'hostapd.service']
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	
	except:
		print "Hostapd error, failed to stop the service "
		return False
	else:
		strstart=output.find("failed")
		if strstart>-1:
			print "failed to stop hostapd"
			done=False
		else:
			done=True
	return done

def start_dnsmasq():
	done=False
	try:
		print "try to start DNSmasq"
		# systemctl restart dnsmasq.service
		cmd = ['systemctl' , 'restart' , 'dnsmasq.service']
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	
	except:
		print "DNSmasq error, failed to start "
		return False
	else:
		strstart=output.find("failed")
		if strstart>-1:
			print "DNSmasq error, failed to start "
			done=False
		else:
			done=True
	return done


def stop_dnsmasq():
	done=False
	try:

		print "try to stop dnsmasq"
		# systemctl restart dnsmasq.service
		cmd = ['systemctl' , 'stop' , 'dnsmasq.service']
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	

	except:
		print "DNSmasq error, failed to stop "
		return False
	else:
		strstart=output.find("failed")
		if strstart>-1:
			print "DNSmasq error, failed to stop "
			done=False
		else:
			done=True
	return done



# ip link set wlan0 down
def ifdown(interface):
	print "try ifdown"
	try: 
		cmd = ['ip' , 'link' , 'set', interface, 'down']
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)		
		print "ifdown OK "
		#sudo ifdown --force wlan0 #seems to work
		return True
	except subprocess.CalledProcessError as e:
		print "ifdown failed: ", e
		return False

def ifup(interface):
	print "try ifup"
	try:
		cmd = ['ip' , 'link' , 'set', interface, 'up']
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(2)		
		print "ifup OK "
		return True
	except subprocess.CalledProcessError as e:
		print "ifup failed: ", e
		return False

def flushIP(interface): #-------------------
	print "try flush IP"
	try:
		# sudo ip addr flush dev wlan0
		cmd = ['ip', 'addr' , 'flush' , 'dev', interface]
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		print "FlushIP: ", interface , " OK ", ifup_output
		time.sleep(1.5)
		return True
	except subprocess.CalledProcessError as e:
		print "IP flush failed: ", e
		return False

def addIP(interface): #-------------------
	print "try to set IP"
	try:
		# sudo ip addr add 192.168.0.172/24 dev wlan0
		cmd = ['ip', 'addr' , 'add' , IPADDRESS+'/24' , 'dev', interface]
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		print "ADD IP address: ", interface , " OK ", ifup_output
		time.sleep(1)
		return True
	except subprocess.CalledProcessError as e:
		print "ADD ip address Fails : ", e
		return False



def findinline(line,string):
	strstart=line.find(string)
	if strstart>-1:
		substr=line[strstart:]
		return substr
	return ""
	
def init_network():
	# initiate network connection as AP, then start a thread to switch to wifi connection if available
	step1=connect_AP()
	addIP("wlan0")
	if step1:
		waitandconnect(WAITTOCONNECT) # parameter is the number of seconds, 5 minutes = 300 sec
		print "wifi access point up, wait 180 sec before try to connect to wifi network"
		logging.warning('wifi access point up, wait 180 sec before try to connect to wifi network')
	else:
		waitandconnect(2) # try to connet immeditely to netwrok as the AP failed
		print "Not able to connect wifi access point , wait 2 sec before try to connect to wifi network"
		logging.warning('Not able to connect wifi access point , wait 2 sec before try to connect to wifi network')
	
def waitandconnect(pulsesecond):
	t = threading.Timer(pulsesecond, connect_network).start()

def connect_AP():
	print "try to start system as WiFi access point"
	logging.info('try to start system as WiFi access point')
	i=0
	done=False
	
	ssids=connectedssid()
	if len(ssids)>0:
		ssid=ssids[0]
	else:
		ssid=""
	if ssid==localwifisystem:
		done=True
		print "Already working as access poin Hydrosys4"
		logging.info('Already working as access poin Hydrosys4')
	

	while (i<2)and(not done):
		# disable all connected network with wpa_supplicant
		wpa_cli_mod.disable_all("wlan0")		
		ifdown("wlan0")
		ifup("wlan0")
		addIP("wlan0")				
		start_dnsmasq()	
		start_hostapd()
		time.sleep(1)
		ssids=connectedssid()
		j=0
		while (len(ssids)<=0)and(j<3):
			j=j+1
			time.sleep(1)
			logging.info('SSID empty, try again to get SSID')							
			ssids=connectedssid()
		
			
		if len(ssids)>0:			
			ssid=ssids[0]
		else:
			ssid=""
			
		if ssid==localwifisystem:
			done=True
			print "Access point established: Hydrosys4"
			logging.info('Access point established: Hydrosys4')
		else:
			done=False
			print "Access point failed to start, attempt: ", i
			logging.info('Access point failed to start, attempt %d ',i)
		i=i+1
	return done
	
	
	
	
def connect_network_nocheck():
	# this is the procedure that disable the AP and connect to wifi network 
	print " try to connect to wifi network"
	thessid=connect_preconditions()
	i=0
	done=False
	while (i<2) and (not done):
		done=stop_hostapd()
		i=i+1
	i=0
	done=False
	while (i<2) and (not done):
		done=stop_dnsmasq()
		i=i+1

	print "try to connect to wifi network"
	i=0
	done=False
	while (i<2) and (not done):
		done=connect_savedwifi(thessid)
		i=i+1
		print " wifi connection attempt ",i
				


def connect_network():
	# this is the procedure that disable the AP and connect to wifi network 
	print " try to connect to wifi network"
	thessid=connect_preconditions()
	if not thessid=="":
				
		ssids=connectedssid()
		if len(ssids)>0:
			ssid=ssids[0]
		else:
			ssid=""		
				
		print "preconditions to connect to wifi network are met"
		print "try to stop AP services, hostapd, dnsmasq"
		
		i=0
		done=False
		while (i<2) and (not done):
			done=stop_hostapd()
			i=i+1
		i=0
		done=False
		while (i<2) and (not done):
			done=stop_dnsmasq()
			i=i+1
			
		if not ssid==thessid:
			print "try to connect to wifi network"
			i=0
			done=False
			while (i<2) and (not done):
				done=connect_savedwifi(thessid)
				i=i+1
				print " wifi connection attempt ",i
				
			print "check if connection has been established"
		else:
			print "already connected to the SSID ", ssid
						
		ssid=connectedssid()
		
		if len(ssid)==0:
			print "No SSID established, fallback to AP mode"
			# go back and connect in Access point Mode
			logging.info('No Wifi Network connected, no AP connected, going back to Access Point mode')
			connect_AP()
		else:
			logging.info('Connected to Wifi Network %s, now testing connectivity' , ssid[0] )
			print 'Connected to Wifi Network '  , ssid[0]  ,' now testing connectivity'
			# here it is needed to have a real check of the internet connection as for example google 
			connected=check_internet_connection(8)

			if connected:
				print "Google is reacheable !"
				logging.info('Google is reacheable ! ')
				#send first mail
				emailmod.sendallmail()				
			else:
				print "Connectivity problem with WiFi network " ,ssid[0] , "going back to wifi access point mode"
				logging.info('Connectivity problem with WiFi network, %s, gong back to wifi access point mode' ,ssid[0] )
				connect_AP()

	else:
		print "No Saved Wifi Network available"
		logging.info('No Saved Wifi Network available')	
		ssid=connectedssid()
		if len(ssid)==0:
			print "No SSID established, try to fallback to AP mode"
			# go back and connect in Access point Mode
			logging.info('No Wifi Network connected, no AP connected, going back to Access Point mode')
			connect_AP()

	return True

def internet_on():
	try:
		response=urllib2.urlopen('http://www.google.com',timeout=1)
		logging.error('Internet status ON')
		return True
	except:
		logging.error('Internet status OFF')
		return False


def check_internet_connection(ntimes=3):
	i=0
	reachgoogle=internet_on()
	while ((not reachgoogle) and (i<ntimes)):
		i=i+1
		time.sleep(3)
		reachgoogle=internet_on()
	if not reachgoogle:
		return False 
	else:
		return True





def get_external_ip():
	cmd='dig +short myip.opendns.com @resolver1.opendns.com'
	# cmd='dig @ns1.netnames.net www.rac.co.uk CNAME'
	try:
		proc=subprocess.Popen(shlex.split(cmd),stdout=subprocess.PIPE)
		out,err=proc.communicate()
	except:
		print "External IP Error "
		logging.error('Error to get External IP')
		return ""
	ipaddr=out.split('\n')[0]
	if not is_ipv4(ipaddr):
		print "External IP Error "
		logging.error('Error to get external IP , wrong syntax')
		return ""
	
	print ipaddr
	#myip = urllib2.urlopen("http://myip.dnsdynamic.org/").read()
	#print myip
	#cross check 
	#if out==myip:
	#	print "same addresses"
	#else:
	#	print "check failed"
	return out

def get_local_ip():
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(("gmail.com",80))
		ipaddr=s.getsockname()[0]
		s.close()		
	except:
		print "Local IP Error "
		logging.error('Error to get local IP')
		return ""
	if not is_ipv4(ipaddr):
		print "Local IP Error "
		logging.error('Error to get local IP, wrong suntax')
		return ""
	print ipaddr
	return ipaddr
	
	
def is_ipv4(ip):
	match = re.match("^(\d{0,3})\.(\d{0,3})\.(\d{0,3})\.(\d{0,3})$", ip)
	if not match:
		return False
	quad = []
	for number in match.groups():
		quad.append(int(number))
	if quad[0] < 1:
		return False
	for number in quad:
		if number > 255 or number < 0:
			return False
	return True
	


	

	
if __name__ == '__main__':
	# comment
	#a=[]
	#print a
	#connectedssid()
	schemes = list(Scheme.all())
	for scheme in schemes:
		print " Scheme ", scheme
		ssid = scheme.options.get('wpa-ssid', scheme.options.get('wireless-essid'))
		print "ssid " , ssid
