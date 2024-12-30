from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
import logging
import subprocess
import threading
import emailmod
import networkdbmod
import selectedplanmod
# stuff for the IP detection
import shlex
import re
import urllib.request, urllib.error, urllib.parse
import socket
import time
import wpa_cli_mod
import messageboxmod

logger = logging.getLogger("hydrosys4."+__name__)

localwifisystem=networkdbmod.getAPSSID()
if localwifisystem=="":
	localwifisystem="hydrosys4"
	print("error the name of AP not found, double check the hostapd configuration")
	logger.error("error the name of AP not found, double check the hostapd configuration")
LOCALPORT=5020
PUBLICPORT=networkdbmod.getPORT()
WAITTOCONNECT=networkdbmod.getWAITTOCONNECT()
WIFIENDIS=networkdbmod.getWIFIENDIS()
if WAITTOCONNECT=="":
	WAITTOCONNECT=180 # should be 180 at least
	networkdbmod.changesavesetting('APtime',WAITTOCONNECT) # if field not present it will be added
IPADDRESS =networkdbmod.getIPaddress()
EXTERNALIPADDR=""
DHCP_COUNTER=0
FORCESTATICIP=networkdbmod.getForceStaticIP()

def getCUSTOMURL():
	return networkdbmod.getCUSTOMURL()

def stopNTP():
	#sudo systemctl disable systemd-timesyncd.service
	#sudo service systemd-timesyncd stop
	logger.info("Stop NTP")
	print("Stop NTP (Network Time Protocol)")
	# hostnamectl set-hostname $NewHostName
	cmd = [ 'service' , 'systemd-timesyncd' , 'stop']	
	try:
		output_string = subprocess.check_output(cmd).decode('utf-8').strip()
		return output_string
	except subprocess.CalledProcessError as e:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return "error"
	time.sleep(2)

def disableNTP():
	#sudo systemctl disable systemd-timesyncd.service
	#sudo service systemd-timesyncd stop
	logger.info("Disable NTP")
	print("Disable NTP (Network Time Protocol)")
	# hostnamectl set-hostname $NewHostName
	cmd = [ 'systemctl' , 'disable' , 'systemd-timesyncd.service']	
	try:
		output_string = subprocess.check_output(cmd).decode('utf-8').strip()
		return output_string
	except subprocess.CalledProcessError as e:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return "error"
	time.sleep(2)
	
def wifilist_ssid(retrynumber=1):
	ssids=[]	
	i=0
	while (len(ssids)==0 and i<retrynumber):
		i=i+1
		ssids=[]	
		# get all cells from the air
		network = wpa_cli_mod.get_networks("wlan0")
		for item in network:
			if item["ssid"]:
				ssids.append(item["ssid"])
		logger.info("Number of scan SSID: %d, Attemps %d",len(ssids),i)
	return ssids

def savedwifilist_ssid():
	# get all setting from interfaces file
	return wpa_cli_mod.listsavednetwork('wlan0')	

def savewifi(ssid, password):
	wpa_cli_mod.save_network("wlan0",ssid,password)
	
	
def savewificonnect(ssid, password):
	wpa_cli_mod.save_network("wlan0",ssid,password)	
	connect_network(True, False)
	selectedplanmod.CheckNTPandAdjustClockandResetSched() # instead of waiting the next Heartbeat, it reset master scheduler if clock changes
	
def waitandsavewifiandconnect(pulsesecond,ssid,password):
	print("try to save wifi after " , pulsesecond , " seconds")
	argvect=[]
	argvect.append(ssid)
	argvect.append(password)
	t = threading.Timer(pulsesecond, savewificonnect, argvect).start()

def savedefaultAP():
	ssid='AP'
	#check if scheme already exist
	scheme=Scheme.find('wlan0', ssid)
	if (scheme is None):	
		#defaultstr=["iface wlan0-"+ssid+" inet static", "address 10.0.0.1", "netmask 255.255.255.0", "broadcast 255.0.0.0"]
		scheme = Scheme('wlan0', ssid, "static", APINTERFACEMODE)
		scheme.save() # modify the interfaces file adding the wlano-xx network data on the basis of the network encription type
		print("default AP schema has been saved")
	

def removewifi(ssid):
	wpa_cli_mod.remove_network_ssid("wlan0",ssid)


def restoredefault():
	ssids=savedwifilist_ssid()
	for ssid in ssids:
		removewifi(ssid)
	connect_AP()


def connect_savedwifi(thessid):
	# get all cells from the air
	print("connecting to saved wifi network")
	flushIP("wlan0")
	isok=False
	ifup("wlan0") # set the wlan0 up as it seems that stopping the hostapd brings the wlan down
	isok=wpa_cli_mod.enable_ssid("wlan0",thessid)
	time.sleep(1)
	return isok

	
def connect_preconditions():
	print("checking preconditions for WiFi connection")
	# get list of saved networks
	savedssids = wpa_cli_mod.listsavednetwork("wlan0")
	print("Saved ssID =", savedssids)
	if savedssids:
		# get all cells from the air
		ssids=[]
		ssids=wifilist_ssid(3)

		print("ssID on air =", ssids)
		logger.info("Final Number of scan SSID: %d",len(ssids))

		for ssid in savedssids:
			#print " Scheme ", scheme
			if ssid in ssids:
				print("At least one of WIFI network detected have saved credentials, ssid=" , ssid)
				logger.info("At least one of WIFI network can be connected, ssid=%s" , ssid)
				return ssid
	else:
		print("No Saved wifi network to connect to")
		logger.info("No Saved wifi network to connect to")
	print("No conditions to connect to wifi network")
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
	print("Connected to ", ssids)
	return ssids

def iwcommand(cmd,wordtofind):
	ssids=[]	
	try:
		#scanoutput = subprocess.check_output(cmd).decode('utf-8')
		result=subprocess.run(cmd, capture_output="True", text="True")
		scanoutput=result.stdout
	
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return ssids

	#scanoutput = subprocess.check_output('iw ' , 'wlan0 ' , 'info ', stderr=subprocess.STDOUT)
	#print (scanoutput)

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
	
def CheckandUnlockWlan():
	cmd = ['rfkill']
	wordtofind="wlan"
	wordtofindinrow="blocked"
	
	isblocked=ExecCLIandFindOutput(cmd,wordtofind,wordtofindinrow)
	time.sleep(0.1)
	
	if isblocked:
		print("Warning WiFi locked, try to unlock")
		logger.warning("wlan status locked, try to unlock, please double check the wifi locale setting")
		cmd = ['rfkill', 'unblock', 'wifi']
		try:
			scanoutput = subprocess.check_output(cmd).decode('utf-8')
		except:
			print("error to execute the command" , cmd)
			logger.error("error to execute the command %s",cmd)
			return False
		time.sleep(0.1)
		isblocked=ExecCLIandFindOutput(cmd,wordtofind,wordtofindinrow)		
		time.sleep(0.1)


	if isblocked: # check if the command worked
		logger.error("Not able to unlock WiFi")
		print("Error WiFi still locked after attempt to unlock")
	else:
		logger.info("wifi status unlocked :)")
		print("Wifi Unlocked  ***************+")

	return not isblocked
	
	
def ExecCLIandFindOutput(cmd,wordtofind,wordtofindinrow):
	wordfound=False
	try:
		scanoutput = subprocess.check_output(cmd).decode('utf-8')
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return wordfound

	for line in scanoutput.split('\n'):
		strstart=line.find(wordtofind)
		if strstart>-1:
			strstart2=line.find(wordtofindinrow)
			if strstart2>-1:
				wordfound=True
	return wordfound	

def gethostname():
	print("Get hostname")
	cmd = ['hostname']	
	try:
		output_string = subprocess.check_output(cmd).decode('utf-8').strip()
		time.sleep(0.5)	
		print(output_string)
		return output_string
	except subprocess.CalledProcessError as e:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return "error"

def setnewhostname(HOSTNAME):
	print("Set hostname")
	# hostnamectl set-hostname $NewHostName
	cmd = [ "hostnamectl" , 'set-hostname' , HOSTNAME]	
	try:
		output_string = subprocess.check_output(cmd).decode('utf-8').strip()
		return output_string
	except subprocess.CalledProcessError as e:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return "error"


def start_hostapd():
	done=False
	print("try to start hostapd")
	# systemctl restart dnsmasq.service
	cmd = ['systemctl' , 'restart' , 'hostapd.service']	
	try:
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(2)	
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("Hostapd error failed to start the service ")
		return False
	else:
		strstart=output.find("failed")
		if strstart>-1:
			print("failed to start hostapd")
			done=False
		else:
			done=True
	return done

def stop_hostapd():
	done=False
	print("try to stop hostapd")
	# systemctl restart dnsmasq.service
	cmd = ['systemctl' , 'stop' , 'hostapd.service']	
	try:		
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("Hostapd error, failed to stop the service ")
		return False
	else:
		strstart=output.find("failed")
		if strstart>-1:
			print("failed to stop hostapd")
			done=False
		else:
			done=True
	return done

def start_dnsmasq():
	done=False
	print("try to start DNSmasq")
	# systemctl restart dnsmasq.service
	cmd = ['systemctl' , 'restart' , 'dnsmasq.service']	
	try:
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("DNSmasq error, failed to start ")
		return False
	else:
		strstart=output.find("failed")
		if strstart>-1:
			print("DNSmasq error, failed to start ")
			done=False
		else:
			done=True
	return done


def stop_dnsmasq():
	done=False
	print("try to stop dnsmasq")
	# systemctl restart dnsmasq.service
	cmd = ['systemctl' , 'stop' , 'dnsmasq.service']	
	try:
		output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)	
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("DNSmasq error, failed to stop ")
		return False
	else:
		strstart=output.find("failed")
		if strstart>-1:
			print("DNSmasq error, failed to stop ")
			done=False
		else:
			done=True
	return done



# ip link set wlan0 down
def ifdown(interface):
	print("try ifdown")
	cmd = ['ip' , 'link' , 'set', interface, 'down']	
	try: 
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(1)		
		print("ifdown OK ")
		#sudo ifdown --force wlan0 #seems to work
		return True
	except subprocess.CalledProcessError as e:
		print("ifdown failed: ", e)
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return False

def ifup(interface):
	print("try ifup")
	cmd = ['ip' , 'link' , 'set', interface, 'up']	
	try:
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		#isup=waituntilIFUP(interface,15) to be reevaluated
		time.sleep(2)	
		return True
	except subprocess.CalledProcessError as e:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("ifup failed: ", e)
		return False
		
def waituntilIFUP(interface,timeout): # not working properly, to be re-evaluated
	i=0
	done=False
	while (i<timeout)and(not done):
		cmd = ['ip' , 'link' , 'show', interface, 'up']
		try:
			ifup_output = subprocess.check_output(cmd).decode('utf-8')
		except:
			print("error to execute the command" , cmd)
			logger.error("error to execute the command %s",cmd)
			ifup_output=""
			
		if not ifup_output:
			print("interface ", interface , " still down, check again in one second")			
			time.sleep(1)
			i=i+1
		else:
			done=True
			print("interface ", interface , " UP after seconds: ", i)
			print("output ", ifup_output)
	return done
		

def flushIP(interface): #-------------------
	print("try flush IP")
	cmd = ['ip', 'addr' , 'flush' , 'dev', interface]	
	try:
		# sudo ip addr flush dev wlan0

		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		print("FlushIP: ", interface , " OK ", ifup_output)
		time.sleep(0.5)
		return True
	except subprocess.CalledProcessError as e:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("IP flush failed: ", e)
		return False

def resetDHCP(): 
	print("try to reset DHCP")
	cmd = ['dhclient', '-v' ]	
	try:
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		print("Reset DHCP ")
		time.sleep(0.5)
		return True
	except subprocess.CalledProcessError as e:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("Reset DHCP Failed: ", e)
		return False

		
		
		
def checkGWsubnet(interface): #-------------------
	print("Check  if the Gateway IP address has same subnet of statip ip")
	logger.info("Check  if the Gateway IP address has same subnet of statip ip")	
	# the command -ip route- will provide the -default- gateway address, when in AP mode or this will not be present
	# when connected to the WIFi router the "wlan0" will be present
	# the check shoudl be: exec ip route, search for "default" and "wlan0" in the same row, the first IP address of thisrow id the GW IP
	# if the GW IP has same subnet continue assigning static IP, otherwise raise issue.
	# if no IP GW then proceed assigning static IP
	
	cmd = ['ip', 'route']
	ifup_output=""
	try:
		time.sleep(1)
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(0.5)
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		return True, ipaddr
		
	wordtofind1="default"
	wordtofind2=interface
	isaddress=False
	ipaddr=""
	for line in ifup_output.split('\n'):
		logger.info("IP route Output Line = %s", line)
		if (wordtofind1 in line) and (wordtofind2 in line):
			isaddress , ipaddr = IPv4fromString(line) # provide only the first IP address
			break	

	if isaddress:
		print("got default Gateway for ",interface)
		logger.info("got default Gateway for wlan0 = %s", ipaddr)
		#check if same subnet
		staticIPlist=IPADDRESS.split(".")
		gwIPlist=ipaddr.split(".")
		samesubnet=False
		i=0
		minlen=min(len(staticIPlist), len(gwIPlist))
		while (staticIPlist[i]==gwIPlist[i]) and (i<minlen):
			print(staticIPlist[i] , "   " , gwIPlist[i])			
			i=i+1
		
		newstaticIP=""	
		if minlen==4:
			newstaticIP=str(gwIPlist[0])+"."+str(gwIPlist[1])+"."+str(gwIPlist[2])+"."+str(staticIPlist[3])

		if i<3:
			# not same subnet
			print("Warning: not same subnet gw ip = ", ipaddr , " static ip =" , IPADDRESS)
			logger.warning("Warning: not same subnet gw ip = %s , static ip = %s", ipaddr , IPADDRESS)
			logger.warning("STATIC ip address will not be set")
			message="Warning: Last wifi connection, subnet not matching gateway ip = "+ ipaddr +" static ip =" + IPADDRESS +". Change the static IP address to match the Wifi GW subnet e.g " + newstaticIP
			networkdbmod.storemessage(message)
			dictitem={'title': "System Message (Alert)", 'content': message, 'color': "purple" }
			messageboxmod.SaveMessage(dictitem)
			return False , ipaddr
		else:
			logger.info("ok: same subnet")	
			print("ok: same subnet")	
			message=""
			networkdbmod.storemessage(message)	
		
		
	else:
		print("No default Gateway for wlan0")
		logger.info("No default Gateway for wlan0")	
		message=""
		ipaddr=""
		networkdbmod.storemessage(message)	

	return True, ipaddr

def addIP(interface, brd=True): #-------------------

	goON, GWipaddr=checkGWsubnet(interface)
	
	if not goON:
		return
	
	print("Set Local Static IP " , IPADDRESS)
	logger.info("Set Local Static IP: %s" , IPADDRESS)
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
		print("ADD IP address: ", interface , " OK ", ifup_output)
		time.sleep(0.5)
		return True
	except subprocess.CalledProcessError as e:
		logger.info("Failed to set local Static IP: %s" , IPADDRESS)
		print("ADD ip address Fails : ", e)
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
			print("wifi access point up, wait " ,WAITTOCONNECT, " sec before try to connect to wifi network")
			logger.warning('wifi access point up, wait %s sec before try to connect to wifi network',WAITTOCONNECT)
			return True
		else:
			return False
	else:
		waitandconnect("2") # try to connet immeditely to netwrok as the AP failed
		print("Not able to connect wifi access point , wait 2 sec before try to connect to wifi network")
		logger.warning('Not able to connect wifi access point , wait 2 sec before try to connect to wifi network')
		return True
	
def waitandconnect(pulsesecond):
	print("try to connect to wifi after " , pulsesecond , " seconds")
	try:
		f=float(pulsesecond)
		secondint=int(f)
	except:
		secondint=180
	t = threading.Timer(secondint, connect_network_init , [True, False]).start()

def waitandremovewifi(pulsesecond,ssid):
	print("try to switch to AP mode after " , pulsesecond , " seconds")
	argvect=[]
	argvect.append(ssid)
	t = threading.Timer(pulsesecond, removewifiarg, argvect).start()

def removewifiarg(arg):
	removewifi(arg)

def waitandconnect_AP(pulsesecond):
	print("try to switch to AP mode after " , pulsesecond , " seconds")
	t = threading.Timer(pulsesecond, connect_AP).start()


def connect_AP(firsttime=False):
	print("try to start system as WiFi access point")
	logger.info('try to start system as WiFi access point')
	if localwifisystem=="":
		print("WiFi access point SSID name is an empty string, problem with network setting file")
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
		print("Already working as access point, only reset IP address ",ssid)
		logger.info('Already working as access poin %s',ssid)
		currentipaddr=get_local_ip_raw()
		logger.info('Target IP address= %s. Current access point IP addresses= %s', IPADDRESS,currentipaddr)		
		if IPADDRESS not in currentipaddr:
			#set IP address
			logger.warning('Set Target IP address')
			addIP("wlan0")
		else:
			logger.warning('No need to set static IP address')
		start_hostapd() # this become necessary in the RaspiOS rel 11, for unknown reasons, even if the hostapd starts without errors the SSID is not boradcastg
		
		if (not firsttime)or(IPADDRESS not in currentipaddr):	
			#restart DNSmask, this should help to acquire the new IP address (needed for the DHCP mode)
			start_dnsmasq()
		return True
	
	
	# disable connected network with wpa_supplicant
	logger.info('Try to disable current network %s',ssid)
	print("try to disable other network")
	isOk=wpa_cli_mod.disable_all("wlan0")	
	if not isOk:
		logger.warning('Problem to disable network')
		print("try to disable other network")
	#ifdown("wlan0")
	#ifup("wlan0")			
	#start_dnsmasq()	# it is recommended that the dnsmasq shoudl start after the wlan0 is up	
	#start_hostapd()
	time.sleep(3)
	
	
	
	i=0	
	while (i<2)and(not done):
		print(" loop ", i)
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
			print("Access point established:", localwifisystem)
			logger.info('Access point established: %s',localwifisystem)
		else:
			done=False
			print("Access point failed to start, attempt: ", i)
			logger.info('Access point failed to start, attempt %d ',i)
		i=i+1
	return done
	
	

def applyparameterschange(newlocalwifisystem, newpassword, newIPaddress):

	# check what action to make
	global localwifisystem
	global IPADDRESS

	print(" New Data " , newlocalwifisystem ," ", newpassword," " , newIPaddress)
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
		print("Currently working as access point",localwifisystem)
		logger.info('Currently working as access point %s',localwifisystem)

	# update global variables with new paramaeters:
	localwifisystem=newlocalwifisystem
	IPADDRESS=newIPaddress


	if isAPconnected:
		if restartAP: # restart AP
			print("restart AP")
			logger.info('restart AP')
			# action
				
			i=0	
			done=False
			while (i<2)and(not done):
				print(" loop ", i)
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
					print("Access point established:", localwifisystem)
					logger.info('Access point established: %s',localwifisystem)
				else:
					done=False
					print("Access point failed to start, attempt: ", i)
					logger.info('Access point failed to start, attempt %d ',i)
				i=i+1
		else:
			print(" No need AP restart")
				
	else:
		if restartWiFi:
			# try to reset WiFi network
			thessid=ssid
			done=False
			ssids=[]
			i=0
			while (i<3) and (len(ssids)==0):
				done=connect_savedwifi(thessid) # return true when the command is executed
				i=i+1					
				if done:
					time.sleep(1+i*5)				
					print("wifi connection attempt ",i)
					print("check connected SSID")
					logger.info('Connection command executed attempt %d, check connected SSID ',i)
				else:
					print("Connection command NOT executed properly , attempt ",i)
					logger.info('Connection command NOT executed properly , attempt %d ',i)							
				ssids=connectedssid()
		

			if len(ssids)>0:
				ssid=ssids[0]
			else:
				ssid=""
				logger.info('NO connected SSID')
			print("Connected to the SSID ", ssid)
			logger.info('Connected SSID: %s -- ', ssid)	
			if FORCESTATICIP=="True":
				addIP("wlan0")	

		else:
			print(" No need WiFi restart")
				
	# update global variable values
	
	localwifisystem=newlocalwifisystem
	IPADDRESS=newIPaddress
		
		
	return True

def connect_network_init(internetcheck=False, backtoAP=False):
	connected=connect_network(internetcheck, backtoAP)
		
	# section relevant to start of MAstercallback

	logger.info('After init_network. Synch clock and start mastercallback')		
	if not selectedplanmod.CheckNTPandAdjustClockandResetSched():
		selectedplanmod.resetmastercallback()
	selectedplanmod.HASScompMatrix.HASSIOintegr.check_loop_and_connect()
	
	return connected

def Disable_WiFi():
	logger.info('Try to disable WiFi network')
	print("try to disable WiFi network")
	isOk=wpa_cli_mod.disable_all("wlan0")	
	#ifdown("wlan0")		
	stop_dnsmasq()	
	stop_hostapd()



def connect_network(internetcheck=False, backtoAP=False):
	# this is the procedure that disable the AP and connect to wifi network 
	connected=False
	
	if WIFIENDIS=="Disabled":  # WIFI disables setting
		logger.info('Wifi set to disabled')	
		Disable_WiFi()	
		return connected
	
	
	thessid=connect_preconditions() # get the first SSID of saved wifi network to connect with and see if the SSID is on air
	
	
	if not thessid=="":
		print("preconditions to connect to wifi network are met")				
		logger.info('preconditions to connect to wifi network are met')
		ssids=connectedssid() # get the SSID currently connected
		if len(ssids)>0:
			ssid=ssids[0]
		else:
			ssid=""		
				
			
		if not ssid==thessid:
			print("try to connect to wifi network")
			logger.info('try to connect to wifi network %s ' ,thessid)			
			print("try to stop AP services, hostapd, dnsmasq")
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
			while (i<2) and (len(ssids)==0):
				done=connect_savedwifi(thessid) # return true when the command is executed
				i=i+1					
				if done:
					maxiter=10
					while (not connectedssid())and(maxiter>0):
						time.sleep(1)				
						maxiter-=1
						print (maxiter)
					print("wifi connection attempt ",i)
					print("check connected SSID")
					logger.info('Connection command executed attempt %d, check connected SSID ',i)
				else:
					print("Connection command NOT executed properly , attempt ",i)
					logger.info('Connection command NOT executed properly , attempt %d ',i)							
				ssids=connectedssid()
		

			if len(ssids)>0:
				ssid=ssids[0]
			else:
				ssid=""
				logger.info('NO connected SSID')
			print("Connected to the SSID ", ssid)
			logger.info('Connected SSID: %s -- ', ssid)		
			if FORCESTATICIP=="True":
				addIP("wlan0")	

		else:
			print("already connected to the SSID ", ssid)
		
		
		if len(ssids)==0:
			print("No SSID established, fallback to AP mode")
			# go back and connect in Access point Mode
			logger.info('No Wifi Network connected, no AP connected, going back to Access Point mode')
			connect_AP()
			connected=False
		else:
			logger.info('Connected to Wifi Network %s' , ssid )
			print('Connected to Wifi Network '  , ssid) 

		
			
			# here it is needed to have a real check of the internet connection as for example google 
			if internetcheck:
				connected=check_internet_connection(3)
				if connected:
					print("Google is reacheable !")
					logger.info('Google is reacheable ! ')
					#send first mail
					print("Send first mail !")
					logger.info('Send first mail ! ')
					emailmod.sendallmail("alert", "System has been reconnected to wifi network")				
				else:
					if backtoAP: # in case connection to Internet not working
						print("Connectivity problem with WiFi network " ,ssid[0] , "going back to wifi access point mode")
						logger.info('Connectivity problem with WiFi network, %s, gong back to wifi access point mode' ,ssid )
						connect_AP()
			else:
				connected=True

			# ALL below not needed anymore since I disabled the NTP network time protocal daemon *****

	else:
		print("No Saved Wifi Network available")
		logger.info('No Saved Wifi Network available')	
		print("try to fallback to AP mode")
		# go back and connect in Access point Mode
		logger.info('Going back to Access Point mode')
		connect_AP()
		connected=False

	return connected


def internet_on_old():
	try:
		response=urllib.request.urlopen('http://www.google.com',timeout=1)
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
				response=urllib.request.urlopen(site,timeout=timeout)
				return True
			except:
				print("internet_on: Error to connect")
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
		out=out.decode()
		logger.info('Got reply from openDNS')
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("External IP Error ")
		logger.error('Error to get External IP')
		return ""
	logger.info('Reply from openDNS: %s', out)
	isaddress , ipaddr = IPv4fromString(out)
	if not isaddress:
		print("External IP Error ")
		logger.error('Error to get external IP , wrong syntax')
		return ""
	
	
	print("External IP address " , ipaddr)
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
		print("IP addresses " , ipaddrlist)
		#hostname -I
		#s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		#s.connect(("gmail.com",80))
		#ipaddr=s.getsockname()[0]
		#s.close()			
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("Local IP Error ")
		logger.error('Error to get local IP')
		return ""
	global IPADDRESS
	if IPADDRESS in ipaddrlist:
		return IPADDRESS
	isaddress , ipaddr = IPv4fromString(ipaddrlist)
	if not isaddress:
		print("Local IP Error with Sintax")
		logger.error('Error to get local IP, wrong suntax')
		return ""
	print(ipaddr)
	return ipaddr
	
	
def get_local_ip_list():
	cmd = ["hostname -I"]	
	try:
		cmd_output = subprocess.check_output(cmd, shell=True).decode('utf-8')	
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("Local IP Error ")
		logger.error('Error to get local IP')
		return ""
	ipaddrlist=[]
	stringlist=cmd_output.split(" ")
	for ipstrings in stringlist:
		isaddress , ipaddr = IPv4fromString(ipstrings)
		if isaddress:
			ipaddrlist.append(ipaddr) 
			print(ipaddr)
	return ipaddrlist
	
def get_local_ip_raw():
	cmd = ["hostname -I"]	
	try:
		ipaddrlist = subprocess.check_output(cmd, shell=True).decode('utf-8')
		print("IP addresses " , ipaddrlist)			
	except:
		print("error to execute the command" , cmd)
		logger.error("error to execute the command %s",cmd)
		print("Local IP Error ")
		logger.error('Error to get local IP')
		return ""
	print(ipaddrlist)
	return ipaddrlist


def multiIPv4fromString(ipaddrlist):
	addresslist=[]
	isaddress=True
	while isaddress:
		isaddress , ipaddr = IPv4fromString(ipaddrlist)
		if isaddress:
			addresslist.append(ipaddr)
			rightposition= ipaddrlist.index(ipaddr) + len(ipaddr) - 1
			ipaddrlist=ipaddrlist[rightposition :]
	return addresslist

def IPv4fromString(ip_string): #extract the first valid IPv4 address in the string
	print(" Start -- ")
	iprows=ip_string.split('\n')
	ip_address=""
	for ip in iprows:
		print("String IP address ", ip)
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
								print("IP extracted succesfully " , ip_address)
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
					print("IP extracted succesfully " , ip_address)
					return True, ip_address

	return False , ""
	

def checkstringIPv4(thestring):
	print(thestring)
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
	connect_AP()
	ssids=connectedssid()
	print(ssids)
	connect_network(internetcheck=True, backtoAP=False)
	#done=stop_hostapd()
	#done=stop_dnsmasq()
	#flushIP("wlan0")
	#isok=wpa_cli_mod.enable_ssid("wlan0","AngeloAnnnie")
	#ifup("wlan0") # not present before
	#addIP("wlan0")	
	#time.sleep(5)
	ssids=connectedssid()
	print(ssids)
	get_external_ip()
