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
WAITTOCONNECT=180 # should be 180 at least
IPADDRESS =networkdbmod.getIPaddress()





	
def wifilist_ssid():
	# get all cells from the air
	ssids=[]
	network = wpa_cli_mod.get_networks("wlan0")
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
			return ssid
	print "No conditions to connect to wifi network"	
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
	scanoutput = subprocess.check_output(cmd).decode('utf-8')
	time.sleep(1.5)	
	#scanoutput = subprocess.check_output('iw ' , 'wlan0 ' , 'info ', stderr=subprocess.STDOUT)
	#print scanoutput
	ssids=[]
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
		#isup=waituntilIFUP(interface,15) to be reevaluated
		time.sleep(2)	
		return True
	except subprocess.CalledProcessError as e:
		print "ifup failed: ", e
		return False
		
def waituntilIFUP(interface,timeout): # not working properly, to be re-evaluated
	i=0
	done=False
	while (i<timeout)and(not done):
		cmd = ['ip' , 'link' , 'show', interface, 'up']
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
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
	try:
		# sudo ip addr flush dev wlan0
		cmd = ['ip', 'addr' , 'flush' , 'dev', interface]
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		print "FlushIP: ", interface , " OK ", ifup_output
		time.sleep(0.5)
		return True
	except subprocess.CalledProcessError as e:
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
	step1=connect_AP()
	if step1:
		thessid=connect_preconditions() # get the first SSID of saved wifi network to connect with
		if not thessid=="":
			waitandconnect(WAITTOCONNECT) # parameter is the number of seconds, 5 minutes = 300 sec
			print "wifi access point up, wait 180 sec before try to connect to wifi network"
			logger.warning('wifi access point up, wait 180 sec before try to connect to wifi network')
	else:
		waitandconnect(2) # try to connet immeditely to netwrok as the AP failed
		print "Not able to connect wifi access point , wait 2 sec before try to connect to wifi network"
		logger.warning('Not able to connect wifi access point , wait 2 sec before try to connect to wifi network')
	
def waitandconnect(pulsesecond):
	print "try to connect to wifi after " , pulsesecond , " seconds"
	t = threading.Timer(pulsesecond, connect_network).start()

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


def connect_AP():
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
		print "Already working as access point, only reset IP address ",localwifisystem
		logger.info('Already working as access poin %s',localwifisystem)
		addIP("wlan0")
		#restart DNSmask, this should help to acquire the new IP address (needed for teh DHCP mode)
		start_dnsmasq()
		return True
	
	
	# disable connected network with wpa_supplicant
	wpa_cli_mod.disable_network_ssid("wlan0",ssid)	
			
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
		while (len(ssids)<=0)and(j<8):
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
	
	


def connect_network():
	# this is the procedure that disable the AP and connect to wifi network 
	connected=False
	print " try to connect to wifi network"
	thessid=connect_preconditions() # get the first SSID of saved wifi network to connect with
	
	
	
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
				
			
			i=0
			done=False
			while (i<3) and (not done):
				done=connect_savedwifi(thessid)
				i=i+1
				print " wifi connection attempt ",i
				
			print "check connected SSID"

			logger.info('check connected SSID ')
			
			ssids=connectedssid()
			i=0
			while (i<2) and (len(ssids)==0):
				time.sleep(1+i*5)
				ssids=connectedssid()
				i=i+1			

			if len(ssids)>0:
				ssid=ssids[0]
			else:
				ssid=""	
			print "connected to the SSID ", ssid
			logger.info('connected SSID %s ', ssid)

		else:
			print "already connected to the SSID ", ssid
		
		
		if len(ssids)==0:
			print "No SSID established, fallback to AP mode"
			# go back and connect in Access point Mode
			logger.info('No Wifi Network connected, no AP connected, going back to Access Point mode')
			connect_AP()
			connected=False
		else:
			logger.info('Connected to Wifi Network %s, now testing connectivity' , ssid )
			print 'Connected to Wifi Network '  , ssid  ,' now testing connectivity'
			# here it is needed to have a real check of the internet connection as for example google 
			connected=check_internet_connection(3)

			if connected:
				print "Google is reacheable !"
				logger.info('Google is reacheable ! ')
				#send first mail
				print "Send first mail !"
				logger.info('Send first mail ! ')
				emailmod.sendallmail("alert", "System has been reconnected to wifi network")				
			else:
				#logger.info('Connectivity problem with WiFi network, %s' ,ssid[0] )
				print "Connectivity problem with WiFi network " ,ssid[0] , "going back to wifi access point mode"
				logger.info('Connectivity problem with WiFi network, %s, gong back to wifi access point mode' ,ssid[0] )
				connect_AP()

	else:
		print "No Saved Wifi Network available"
		logger.info('No Saved Wifi Network available')	
		print "try to fallback to AP mode"
		# go back and connect in Access point Mode
		logger.info('Going back to Access Point mode')
		connect_AP()
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
    for timeout in [1,5,10,15]:
        try:
            response=urllib2.urlopen('http://google.com',timeout=timeout)
            return True
        except urllib2.URLError as err: pass
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
		logger.info('Got reply from openDNS')
	except:
		print "External IP Error "
		logger.error('Error to get External IP')
		return ""

	ipaddr=out.split('\n')[0]
	if not is_ipv4(ipaddr):
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
	return ipaddr

def get_local_ip():
	try:
		cmd = ["hostname -I"]
		ipaddrlist = subprocess.check_output(cmd, shell=True).decode('utf-8')
		ipaddr=ipaddrlist.split(" ")[0]
		print "IP addresses " , ipaddrlist
		#hostname -I
		#s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		#s.connect(("gmail.com",80))
		#ipaddr=s.getsockname()[0]
		#s.close()			
	except:
		print "Local IP Error "
		logger.error('Error to get local IP')
		return ""
	if not is_ipv4(ipaddr):
		print "Local IP Error "
		logger.error('Error to get local IP, wrong suntax')
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
