import logging
import subprocess
import threading
import emailmod
import networkdbmod
# stuff for the IP detection
import shlex
import re
import urllib2
import socket
import time
import wpa_cli_mod

logger = logging.getLogger("hydrosys4."+__name__)

localwifisystem=networkdbmod.getAPSSID()
if localwifisystem=="":
	localwifisystem="hydrosys4"
	print "error the name of AP not found, double check the hostapd configuration"
	logger.error("error the name of AP not found, double check the hostapd configuration")
LOCALPORT=5020
PUBLICPORT=networkdbmod.getPORT()
WAITTOCONNECT=networkdbmod.getWAITTOCONNECT()
if WAITTOCONNECT=="":
	WAITTOCONNECT=180 # should be 180 at least
	networkdbmod.changesavesetting('APtime',WAITTOCONNECT) # if field not present it will be added
IPADDRESS =networkdbmod.getIPaddress()
EXTERNALIPADDR=""




	
def wifilist_ssid():
	# get all cells from the air
	ssids=[]
	network = wpa_cli_mod.get_networks("wlan0",2)
	for item in network:
		ssids.append(item["ssid"])
	return ssids

def savedwifilist_ssid():
	# get all setting from interfaces file
	return wpa_cli_mod.listsavednetwork('wlan0')	

def savewifi(ssid, password):
	wpa_cli_mod.save_network("wlan0",ssid,password)

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
	wpa_cli_mod.remove_network_ssid("wlan0",ssid)


def restoredefault():
	ssids=savedwifilist_ssid()
	for ssid in ssids:
		removewifi(ssid)
	connect_AP()


def connect_savedwifi(thessid):
	# get all cells from the air
	print "connecting to saved wifi network"
	flushIP("wlan0")
	isok=False
	#ifdown("wlan0")
	isok=wpa_cli_mod.enable_ssid("wlan0",thessid)
	time.sleep(1)
	#ifup("wlan0")			
	addIP("wlan0")	
	return isok

	
def connect_preconditions():
	print "checking preconditions for WiFi connection"
	# get all cells from the air
	ssids=[]
	i=0
	while (len(ssids)==0 and i<3):
		i=i+1
		ssids=wifilist_ssid()

	print "ssID on air =", ssids
	logger.info("Number of scan SSID: %d",len(ssids))
	savedssids = wpa_cli_mod.listsavednetwork("wlan0")
	for ssid in savedssids:
		#print " Scheme ", scheme
		if ssid in ssids:
			print "At least one of WIFI network detected have saved credentials, ssid=" , ssid
			logger.info("At least one of WIFI network can be connected, ssid=%s" , ssid)
			return ssid
	print "No conditions to connect to wifi network"
	logger.info("No conditions to connect to wifi network")
	return ""

	
def connectedssid():
	cmd = ['iw', 'dev', 'wlan0', 'info']
	wordtofind="ssid"
	ssids=iwcommand(cmd,wordtofind)
	if not ssids:
		cmd = ['iw', 'dev', 'wlan0', 'link']
		wordtofind="SSID"
		ssids=iwcommand(cmd,wordtofind)
	print "Connected to ", ssids
	return ssids

def iwcommand(cmd,wordtofind):
	ssids=[]	
	try:
		scanoutput = subprocess.check_output(cmd).decode('utf-8')
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
		return ssids

	#scanoutput = subprocess.check_output('iw ' , 'wlan0 ' , 'info ', stderr=subprocess.STDOUT)
	#print scanoutput

	for line in scanoutput.split('\n'):
		#print " line ",line
		strstart=line.find(wordtofind)
		if strstart>-1:
			substr=line[(strstart+len(wordtofind)):]
			ssid=substr.strip()
			ssid=ssid.strip(":")
			ssid=ssid.strip()
			ssids.append(ssid)
	return ssids



def start_hostapd():
	done=False
	print "try to start hostapd"
	# systemctl restart dnsmasq.service
	cmd = ['systemctl' , 'restart' , 'hostapd.service']	
	try:
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(2)	
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
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
	print "try to stop hostapd"
	# systemctl restart dnsmasq.service
	cmd = ['systemctl' , 'stop' , 'hostapd.service']	
	try:		
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
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
	print "try to start DNSmasq"
	# systemctl restart dnsmasq.service
	cmd = ['systemctl' , 'restart' , 'dnsmasq.service']	
	try:
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
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
	print "try to stop dnsmasq"
	# systemctl restart dnsmasq.service
	cmd = ['systemctl' , 'stop' , 'dnsmasq.service']	
	try:
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
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
	cmd = ['ip' , 'link' , 'set', interface, 'down']	
	try: 
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)		
		print "ifdown OK "
		#sudo ifdown --force wlan0 #seems to work
		return True
	except subprocess.CalledProcessError as e:
		print "ifdown failed: ", e
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
		return False

def ifup(interface):
	print "try ifup"
	cmd = ['ip' , 'link' , 'set', interface, 'up']	
	try:
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		#isup=waituntilIFUP(interface,15) to be reevaluated
		time.sleep(2)	
		return True
	except subprocess.CalledProcessError as e:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
		print "ifup failed: ", e
		return False
		
def waituntilIFUP(interface,timeout): # not working properly, to be re-evaluated
	i=0
	done=False
	while (i<timeout)and(not done):
		cmd = ['ip' , 'link' , 'show', interface, 'up']
		try:
			ifup_output = subprocess.check_output(cmd).decode('utf-8')
		except:
			print "error to execute the command" , cmd
			logger.error("error to execute the command %s",cmd)
			ifup_output=""
			
		if not ifup_output:
			print "interface ", interface , " still down, check again in one second"			
			time.sleep(1)
			i=i+1
		else:
			done=True
			print "interface ", interface , " UP after seconds: ", i
			print "output ", ifup_output
	return done
		

def flushIP(interface): #-------------------
	print "try flush IP"
	cmd = ['ip', 'addr' , 'flush' , 'dev', interface]	
	try:
		# sudo ip addr flush dev wlan0

		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		print "FlushIP: ", interface , " OK ", ifup_output
		time.sleep(0.5)
		return True
	except subprocess.CalledProcessError as e:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
		print "IP flush failed: ", e
		return False

def addIP(interface, brd=True): #-------------------
	print "try to set Static IP " , IPADDRESS
	logger.info("try to set Static IP: %s" , IPADDRESS)
	try:
		if brd:
			# ip addr add 192.168.0.77/24 broadcast 192.168.0.255 dev eth0
			BROADCASTIPvect=IPADDRESS.split(".")
			BROADCASTIPvect[3]="255"
			BROADCASTIP=".".join(BROADCASTIPvect)
			cmd = ['ip', 'addr' , 'add' , IPADDRESS+'/24' , 'broadcast' , BROADCASTIP , 'dev', interface]
		else:
			# ip addr add 192.168.0.172/24 dev wlan0
			cmd = ['ip', 'addr' , 'add' , IPADDRESS+'/24' , 'dev', interface]		
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		print "ADD IP address: ", interface , " OK ", ifup_output
		time.sleep(0.5)
		return True
	except subprocess.CalledProcessError as e:
		print "ADD ip address Fails : ", e
		return False

def replaceIP(interface):
	flushIP(interface)
	addIP(interface, True)
	

def findinline(line,string):
	strstart=line.find(string)
	if strstart>-1:
		substr=line[strstart:]
		return substr
	return ""
	
def init_network():
	# initiate network connection as AP, then start a thread to switch to wifi connection if available
	step1=connect_AP(True)
	if step1:
		thessid=connect_preconditions() # get the first SSID of saved wifi network to connect with
		if not thessid=="":
			waitandconnect(WAITTOCONNECT) # parameter is the number of seconds, 5 minutes = 300 sec
			print "wifi access point up, wait " ,WAITTOCONNECT, " sec before try to connect to wifi network"
			logger.warning('wifi access point up, wait %s sec before try to connect to wifi network',WAITTOCONNECT)
	else:
		waitandconnect("2") # try to connet immeditely to netwrok as the AP failed
		print "Not able to connect wifi access point , wait 2 sec before try to connect to wifi network"
		logger.warning('Not able to connect wifi access point , wait 2 sec before try to connect to wifi network')
	
def waitandconnect(pulsesecond):
	print "try to connect to wifi after " , pulsesecond , " seconds"
	try:
		f=float(pulsesecond)
		secondint=int(f)
	except:
		secondint=180
	t = threading.Timer(secondint, connect_network , [True, False]).start()

def waitandremovewifi(pulsesecond,ssid):
	print "try to switch to AP mode after " , pulsesecond , " seconds"
	argvect=[]
	argvect.append(ssid)
	t = threading.Timer(pulsesecond, removewifiarg, argvect).start()

def removewifiarg(arg):
	removewifi(arg)

def waitandconnect_AP(pulsesecond):
	print "try to switch to AP mode after " , pulsesecond , " seconds"
	t = threading.Timer(pulsesecond, connect_AP).start()


def connect_AP(firsttime=False):
	print "try to start system as WiFi access point"
	logger.info('try to start system as WiFi access point')
	if localwifisystem=="":
		print "WiFi access point SSID name is an empty string, problem with network setting file"
		logger.info('WiFi access point SSID name is an empty string, problem with network setting file')	
		return False	


	done=False
	
	ssids=connectedssid()
	if len(ssids)>0:
		ssid=ssids[0]
	else:
		ssid=""
	if ssid==localwifisystem:
		done=True
		print "Already working as access point, only reset IP address ",ssid
		logger.info('Already working as access poin %s',ssid)
		currentipaddr=get_local_ip_raw()
		logger.info('Target IP address= %s. Current access point IP addresses= %s', IPADDRESS,currentipaddr)		
		if IPADDRESS not in currentipaddr:
			#set IP address
			logger.warning('Set Target IP address')
			addIP("wlan0")

		
		if (not firsttime)or(IPADDRESS not in currentipaddr):	
			#restart DNSmask, this should help to acquire the new IP address (needed for teh DHCP mode)
			start_dnsmasq()
		return True
	
	
	# disable connected network with wpa_supplicant
	logger.info('Try to disable current network %s',ssid)
	print "try to disable other network"
	isOk=wpa_cli_mod.disable_all("wlan0")	
	if not isOk:
		logger.warning('Problem to disable network')
		print "try to disable other network"
	#ifdown("wlan0")
	#ifup("wlan0")			
	#start_dnsmasq()	# it is recommended that the dnsmasq shoudl start after the wlan0 is up	
	#start_hostapd()
	time.sleep(3)
	
	
	
	i=0	
	while (i<2)and(not done):
		print " loop ", i
		#ifdown("wlan0")
		#ifup("wlan0")			
		start_dnsmasq()	
		start_hostapd()
		ssids=connectedssid()
		replaceIP("wlan0")
		j=0
		while (len(ssids)<=0)and(j<4):
			j=j+1
			time.sleep(2+(j-1)*2)
			logger.info('SSID empty, try again to get SSID')							
			ssids=connectedssid()
		
			
		if len(ssids)>0:			
			ssid=ssids[0]
		else:
			ssid=""
			
		if ssid==localwifisystem:
			done=True
			print "Access point established:", localwifisystem
			logger.info('Access point established: %s',localwifisystem)
		else:
			done=False
			print "Access point failed to start, attempt: ", i
			logger.info('Access point failed to start, attempt %d ',i)
		i=i+1
	return done
	
	

def applyparameterschange(newlocalwifisystem, newpassword, newIPaddress):

	# check what action to make
	global localwifisystem
	global IPADDRESS

	print " New Data " , newlocalwifisystem ," ", newpassword," " , newIPaddress
	restartAP=False
	restartWiFi=False
	if newlocalwifisystem!=localwifisystem:
		restartAP=True
	if newpassword!="":
		restartAP=True
	if newIPaddress!=IPADDRESS:
		restartAP=True
		restartWiFi=True		

	isAPconnected=False
	ssids=connectedssid()
	if len(ssids)>0:
		ssid=ssids[0]
	else:
		ssid=""
	if ssid==localwifisystem:
		isAPconnected=True
		print "Currently working as access point",localwifisystem
		logger.info('Currently working as access point %s',localwifisystem)

	# update global variables with new paramaeters:
	localwifisystem=newlocalwifisystem
	IPADDRESS=newIPaddress


	if isAPconnected:
		if restartAP: # restart AP
			print "restart AP"
			logger.info('restart AP')
			# action
				
			i=0	
			done=False
			while (i<2)and(not done):
				print " loop ", i
				#ifdown("wlan0")
				#ifup("wlan0")			
				start_dnsmasq()	
				start_hostapd()
				ssids=[]
				replaceIP("wlan0")
				j=0
				while (len(ssids)<=0)and(j<3):
					j=j+1
					time.sleep(2+(j-1)*2)
					logger.info('SSID empty, try again to get SSID')							
					ssids=connectedssid()
				
					
				if len(ssids)>0:			
					ssid=ssids[0]
				else:
					ssid=""
					
				if ssid==localwifisystem:
					done=True
					print "Access point established:", localwifisystem
					logger.info('Access point established: %s',localwifisystem)
				else:
					done=False
					print "Access point failed to start, attempt: ", i
					logger.info('Access point failed to start, attempt %d ',i)
				i=i+1
		else:
			print " No need AP restart"
				
	else:
		if restartWiFi:
			# try to reset WiFi network
			done=False
			ssids=[]
			i=0
			while (i<3) and (len(ssids)==0):
				done=connect_savedwifi(thessid) # return true when the command is executed
				i=i+1					
				if done:
					time.sleep(1+i*5)				
					print "wifi connection attempt ",i
					print "check connected SSID"
					logger.info('Connection command executed attempt %d, check connected SSID ',i)
				else:
					print "Connection command NOT executed properly , attempt ",i
					logger.info('Connection command NOT executed properly , attempt %d ',i)							
				ssids=connectedssid()
		

			if len(ssids)>0:
				ssid=ssids[0]
			else:
				ssid=""
				logger.info('NO connected SSID')
			print "Connected to the SSID ", ssid
			logger.info('Connected SSID: %s -- ', ssid)

		else:
			print " No need WiFi restart"
				
	# update global variable values
	
	localwifisystem=newlocalwifisystem
	IPADDRESS=newIPaddress
		
		
	return True





def connect_network(internetcheck=False, backtoAP=False):
	# this is the procedure that disable the AP and connect to wifi network 
	connected=False
	print " try to connect to wifi network"
	thessid=connect_preconditions() # get the first SSID of saved wifi network to connect with and see if the SSID is on air
	
	
	
	if not thessid=="":
		print "preconditions to connect to wifi network are met"				
		logger.info('preconditions to connect to wifi network are met')
		ssids=connectedssid() # get the SSID currently connected
		if len(ssids)>0:
			ssid=ssids[0]
		else:
			ssid=""		
				


			
		if not ssid==thessid:
			print "try to connect to wifi network"
			logger.info('try to connect to wifi network %s ' ,thessid)			
			print "try to stop AP services, hostapd, dnsmasq"
			logger.info('try to stop AP services, hostapd, dnsmasq ')
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
						

			done=False
			ssids=[]
			i=0
			while (i<3) and (len(ssids)==0):
				done=connect_savedwifi(thessid) # return true when the command is executed
				i=i+1					
				if done:
					time.sleep(1+i*5)				
					print "wifi connection attempt ",i
					print "check connected SSID"
					logger.info('Connection command executed attempt %d, check connected SSID ',i)
				else:
					print "Connection command NOT executed properly , attempt ",i
					logger.info('Connection command NOT executed properly , attempt %d ',i)							
				ssids=connectedssid()
		

			if len(ssids)>0:
				ssid=ssids[0]
			else:
				ssid=""
				logger.info('NO connected SSID')
			print "Connected to the SSID ", ssid
			logger.info('Connected SSID: %s -- ', ssid)

		else:
			print "already connected to the SSID ", ssid
		
		
		if len(ssids)==0:
			print "No SSID established, fallback to AP mode"
			# go back and connect in Access point Mode
			logger.info('No Wifi Network connected, no AP connected, going back to Access Point mode')
			connect_AP()
			connected=False
		else:
			logger.info('Connected to Wifi Network %s' , ssid )
			print 'Connected to Wifi Network '  , ssid 
			# here it is needed to have a real check of the internet connection as for example google 
			if internetcheck:
				connected=check_internet_connection(3)
				if connected:
					print "Google is reacheable !"
					logger.info('Google is reacheable ! ')
					#send first mail
					print "Send first mail !"
					logger.info('Send first mail ! ')
					emailmod.sendallmail("alert", "System has been reconnected to wifi network")				
				else:
					if backtoAP:
						print "Connectivity problem with WiFi network " ,ssid[0] , "going back to wifi access point mode"
						logger.info('Connectivity problem with WiFi network, %s, gong back to wifi access point mode' ,ssid )
						connect_AP()
			else:
				connected=True

	else:
		print "No Saved Wifi Network available"
		logger.info('No Saved Wifi Network available')	
		print "try to fallback to AP mode"
		# go back and connect in Access point Mode
		#logger.info('Going back to Access Point mode')
		#connect_AP()
		connected=False
			
	return connected


def internet_on_old():
	try:
		response=urllib2.urlopen('http://www.google.com',timeout=1)
		logger.info('Internet status ON')
		return True
	except:
		logger.error('Internet status OFF')
		return False

def internet_on():
	websites=['http://google.com','https://www.wikipedia.org']
	timeouts=[1,5]
	for site in websites:
		for timeout in timeouts:
			try:
				response=urllib2.urlopen(site,timeout=timeout)
				return True
			except:
				print "internet_on: Error to connect"
	return False

def check_internet_connection(ntimes=3):
	i=1
	reachgoogle=internet_on()
	while ((not reachgoogle) and (i<ntimes)):
		i=i+1
		time.sleep(1)
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
		logger.info('Got reply from openDNS')
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
		print "External IP Error "
		logger.error('Error to get External IP')
		return ""
	logger.info('Reply from openDNS: %s', out)
	isaddress , ipaddr = IPv4fromString(out)
	if not isaddress:
		print "External IP Error "
		logger.error('Error to get external IP , wrong syntax')
		return ""
	
	
	print "External IP address " , ipaddr
	logger.info("External IP address %s" , ipaddr)
	#myip = urllib2.urlopen("http://myip.dnsdynamic.org/").read()
	#print myip
	#cross check 
	#if out==myip:
	#	print "same addresses"
	#else:
	#	print "check failed"
	global EXTERNALIPADDR
	EXTERNALIPADDR=ipaddr
	return ipaddr

def get_local_ip():
	cmd = ["hostname -I"]	
	try:
		ipaddrlist = subprocess.check_output(cmd, shell=True).decode('utf-8')
		print "IP addresses " , ipaddrlist
		#hostname -I
		#s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		#s.connect(("gmail.com",80))
		#ipaddr=s.getsockname()[0]
		#s.close()			
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
		print "Local IP Error "
		logger.error('Error to get local IP')
		return ""
	isaddress , ipaddr = IPv4fromString(ipaddrlist)
	if not isaddress:
		print "Local IP Error with Sintax"
		logger.error('Error to get local IP, wrong suntax')
		return ""
	print ipaddr
	return ipaddr
	
def get_local_ip_raw():
	cmd = ["hostname -I"]	
	try:
		ipaddrlist = subprocess.check_output(cmd, shell=True).decode('utf-8')
		print "IP addresses " , ipaddrlist			
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
		print "Local IP Error "
		logger.error('Error to get local IP')
		return ""
	print ipaddrlist
	return ipaddrlist


def IPv4fromString(ip_string):
	print " Start -- "
	iprows=ip_string.split('\n')
	ip_address=""
	for ip in iprows:
		print "String IP address ", ip
		countdigit=0
		countdot=0
		start=-1
		inde=0		
		for i in ip:
			if i.isdigit():
				countdigit=countdigit+1
				if countdigit==1:
					start=inde						
			else:
				if countdigit>0: 
					if i==".":
						countdot=countdot+1
					else:
						#check numbers of dots
						if countdot==3:
							thestring=ip[start:inde]
							if checkstringIPv4(thestring):
								ip_address=thestring
								print "IP extracted succesfully " , ip_address
								return True , ip_address
						
						start=-1	
						countdigit=0
						countdot=0

			inde=inde+1


		# check in case the IP is in the end of the string
		if countdigit>0: 
			#check numbers of dots
			if countdot==3:
				thestring=ip[start:inde]
				if checkstringIPv4(thestring):
					ip_address=thestring
					print "IP extracted succesfully " , ip_address
					return True, ip_address

	return False , ""
	

def checkstringIPv4(thestring):
	print thestring
	numbers=thestring.split(".")
	if len(numbers)==4:
		try:
			if int(numbers[0])<1:
				return False
		except:
			return False		
		for num in numbers:
			try:
				value=int(num)
			except:
				return False
			if value <0 or value >255:
				return False
	else:
		return False
	return True


	

	
if __name__ == '__main__':
	# comment
	#a=[]
	ip_string="sad 23.3.2. ceh ca2cchio 12.2.0.12ma chi siete"
	ip_address=""
	isok, string = IPv4fromString(ip_string)
	print isok
	print "the extracted string ",  string
