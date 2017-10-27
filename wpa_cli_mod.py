import logging
import time
import subprocess

logger = logging.getLogger("hydrosys4."+__name__)

def db2dbm(quality):
    """
    Converts the Radio (Received) Signal Strength Indicator (in db) to a dBm
    value.  Please see http://stackoverflow.com/a/15798024/1013960
    """
    dbm = int((quality / 2) - 100)
    return min(max(dbm, -100), -50)

"""
target is to implement the following:

wpa_cli status

wpa_cli scan

wpa_cli scan_results

wpa_cli list_network 
"""


#SUPPLICANT_LOG_FILE = "wpa_supplicant.log"


def run_program(cmd):
	"""
	Runs a program, and it's paramters (e.g. rcmd="ls -lh /var/www")
	Returns output if successful, or None and logs error if not.
	"""

	try:
		ifup_output = subprocess.check_output(cmd).decode('utf-8')
		time.sleep(0.5)
		return ifup_output
	except subprocess.CalledProcessError as e:
		print "Something wrong: ", e
		return "FAIL"


def wpa_terminate(_iface):
	"""
	Terminates any running wpa_supplicant process, and then starts a new one.
	"""
	cmd=['wpa_cli' , 'terminate']
	run_program(cmd)
	time.sleep(1)



def get_networks(iface, retry=1):
	"""
	Grab a list of wireless networks within range, and return a list of dicts describing them.
	"""
	while retry > 0:
		if "OK" in run_program(['wpa_cli', '-i' + iface , 'scan']):
			time.sleep(1)
			networks=[]
			
			lines = run_program(['wpa_cli', '-i' + iface , 'scan_result']).split("\n")
			if lines:
				for line in lines[1:-1]:
					b, fr, s, f = line.split()[:4]
					ss = line.split()[4]
					networks.append( {"bssid":b, "freq":fr, "sig":s, "ssid":ss, "flag":f} )
				return networks
		retry-=1
		logger.debug("Couldn't retrieve networks, retrying")
		time.sleep(0.5)
	logger.error("Failed to list networks")
	return []


def remove_all(iface):
    """
    Disconnect all wireless networks.
    """
    cmd=['wpa_cli', '-i' + iface , 'list_networks']
    lines = run_program(cmd).split("\n")
    if lines:
        for line in lines[1:-1]:
            net_id=line.split()[0]
            remove_network(iface,net_id) 

def remove_network(iface,net_id):
	cmd=['wpa_cli', '-i' + iface , 'remove_network' , net_id]
	run_program(cmd)  

def disable_all(iface):
    """
    Disable all wireless networks.
    """
    cmd=['wpa_cli', '-i' + iface , 'list_networks']
    lines = run_program(cmd).split("\n")
    if lines:
        for line in lines[1:-1]:
            net_id=line.split()[0]
            disable_network(iface,net_id) 

def disable_network(iface,net_id):
	cmd=['wpa_cli', '-i' + iface , 'disable_network' , net_id]
	run_program(cmd)

def enable_network(iface,net_id):
	cmd=['wpa_cli', '-i' + iface , 'enable_network' , net_id]
	run_program(cmd)

def updateconfig():
	cmd=['wpa_cli','reconfigure']
	run_program(cmd)


def enable_ssid(iface, ssid):

    cmd=['wpa_cli', '-i' + iface , 'list_networks']
    lines = run_program(cmd).split("\n")
    if lines:
        for line in lines[1:-1]:
			strlist = line.split()
			if strlist:
				strlist.pop()
				strlist.pop()
				net_id=strlist.pop(0)				
				ssidout = " ".join(strlist) #Hmm, dirty
				if ssid==ssidout:					
					enable_network(iface,net_id)
					return True
	return False

def listsavednetwork(iface):

    cmd=['wpa_cli', '-i' + iface , 'list_networks']
    lines = run_program(cmd).split("\n")
    data=[]
    if lines:
        for line in lines[1:-1]:
			strlist = line.split()
			if strlist:
				net_id=strlist[0]			
				ssidout=strlist[1]
				if ssidout!="":
					data.append(ssidout)
	return data


def status(iface):
	"""
	Check if we're associated to a network.
	"""
	cmd=['wpa_cli', '-i' + iface , 'status']
	lines = run_program(cmd).split("\n")
	if lines:
		data=[]
		for line in lines[1:-1]:
			strlist = line.split("=")
			if len(strlist)>1:
				itemdict={}
				itemdict[strlist[0]]=strlist[1]
				data.append(itemdict)
	return data

def has_ip(_iface):
    """
    Check if we have an IP address assigned
    """
    status = run_program("wpa_cli -i %s status" % _iface)
    r = re.search("ip_address=(.*)", status)
    if r:
        return r.group(1)
    return False

def do_dhcp(_iface):
    """
    Request a DHCP lease.
    """
    run_program("dhclient %s" % _iface)



if __name__ == "__main__":
	network = get_networks("wlan0")
	for item in network:
		print " ssid : " ,  item["ssid"] , " flags : " , item["flag"]
	print status("wlan0")
	print "saved SSids"
	print listsavednetwork("wlan0")

