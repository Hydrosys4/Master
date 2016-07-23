import re
import itertools
import os

import subprocess


# wpa_supplicant file
interfaces = "/etc/wpa_supplicant/wpa_supplicant.conf"
#interfaces = "wpa_supplicant/wpa_supplicant.conf"

def ensure_file_exists(filename):
	# permission is give only to superusers
	try:
		if not os.path.exists(filename):
			open(filename, 'a').close()
	except:
		print "File wpa_supplicant.cong does not exist, not possible to create a new file"
		return False
	
	return True


def configuration(cell, passkey=None):
    """
    Returns a dictionary of configuration options for cell

    Asks for a password if necessary
    """
    if not cell.encrypted:
        return {
                'ssid': cell.ssid,
				'key_mgmt':'NONE'
        }
    else:
        if cell.encryption_type.startswith('wpa'):
            #if len(passkey) != 64:
            #    passkey = PBKDF2(passkey, cell.ssid, 4096).hexread(32)

            return {
                'ssid': cell.ssid,
                'psk': passkey
            }
            
        elif cell.encryption_type == 'wep':
            # Pass key lengths in bytes for WEP depend on type of key and key length:
            #
            #       64bit   128bit   152bit   256bit
            # hex     10      26       32       58
            # ASCII    5      13       16       29
            #
            # (source: https://en.wikipedia.org/wiki/Wired_Equivalent_Privacy)
            #
            # ASCII keys need to be prefixed with an s: in the interfaces file in order to work with linux' wireless
            # tools

            ascii_lengths = (5, 13, 16, 29)
            if len(passkey) in ascii_lengths:
                # we got an ASCII passkey here (otherwise the key length wouldn't match), we'll need to prefix that
                # with s: in our config for the wireless tools to pick it up properly
                passkey = "s:" + passkey

            return {
                'ssid': cell.ssid,
				'key_mgmt':'NONE',                
                'wep_key0': passkey,
				'wep_tx_keyidx':'0'                
            }
        else:
            raise NotImplementedError


def formatconfig(itemsdict):

#example:
#network={
#    ssid="MYSSID"
#    psk="passphrase"
#}

	print "Network to be added ->" , itemsdict

	string="network={\n"
	for key, value in itemsdict.iteritems():
		string=string+'    ' + key + '=' + '"' + value + '"' + '\n'
	string=string+"}"
	return string






def readallschemes():
	"""
	Returns an generator of saved schemes.
	"""
	lines=[]
	if ensure_file_exists(interfaces):
		with open(interfaces, 'r') as f:
			for line in f:
				lines.append(line)
		return extract_schemes(lines)
		#return a list of dictionaries with options
	return "{}"


def findssid(ssidname):
	recordkey="ssid"
	recordvalue=ssidname
	IOdata=readallschemes()
	position=0
	for ln in IOdata:
		position+=1
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				return (True, position)
	return (False, -1)



def getsavedssid():
	recordkey="ssid"
	IOdata=readallschemes()
	datalist=[]
	for ln in IOdata:
		if recordkey in ln:
			datalist.append(ln[recordkey])	
	return datalist






def save(cell, passkey=None):
	"""
	Writes the configuration to the :attr:`interfaces` file.
	"""
	isthere, delindex = findssid(cell.ssid)

	if isthere: #"This scheme already exists"
		delete(delindex)
		
	print "saving network ", cell.ssid
	linetosave=formatconfig(configuration(cell, passkey))

	with open(interfaces, 'a') as f:
		f.write('\n')
		f.write(linetosave)

def savestr(self,strlist):
	"""
	Writes the configuration to the :attr:`interfaces` file.
	"""
	assert not self.find(self.interface, self.name), "This scheme already exists"

	with open(self.interfaces, 'a') as f:
		for line in strlist:
			f.write('\n')
			f.write(line)


def delete(delindex):
	"""
	Deletes the configuration at index.
	"""
	content = ''
	
	with open(interfaces, 'r') as f:
		skip = False
		index=0
		for line in f:
						
			matchstart = line.find("network={")

			if matchstart>-1:
				index+=1
				if index==delindex:			
					skip = True	
									
			if not skip:
				content += line
				
			if line.find("}")>-1:
				skip = False				
			
	
	with open(interfaces, 'w') as f:
		f.write(content)


"""
def activate(selscheme):

	subprocess.check_output(['/sbin/ifdown', 'wlan0'], stderr=subprocess.STDOUT)
	ifup_output = subprocess.check_output(['/sbin/ifup'] + 'wlan0', stderr=subprocess.STDOUT)
	ifup_output = ifup_output.decode('utf-8')
	return self.parse_ifup_output(ifup_output)
"""

def parse_ifup_output(self, output):
	matches = bound_ip_re.search(output)
	if matches:
		return Connection(scheme=self, ip_address=matches.group('ip_address'))
	else:
		raise ConnectionError("Failed to connect to %r" % self)
		return False




def extract_schemes(lines):

	schemes=[]
	while lines:
		line = str(lines.pop(0))
		
		if line.startswith('#') or not line:
			continue

		matchstart = line.find("network={")
		
		if matchstart>-1: 
			options = {}

			while lines and lines[0].find("}"):
				
				line = lines.pop(0)
				commentline = line.find("#")
				equalchar= line.find("=")

				if commentline>0 or equalchar<0:
					continue				
				
				
				key, value = line.split('=', 1)
				key=key.strip().strip('"')
				value=value.strip().strip('"')
				options[key] = value

			#print "options ->", options

			schemes.append(options)
			
	return schemes
		
		
if __name__ == '__main__':

	print readallschemes()
	print getsavedssid()
	isthere, delindex = findssid("MYSSID")
	delete(delindex)

