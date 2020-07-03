#!/bin/bash
###
# TODO: OpenWeathermap
# TODO: install and uninstall
# TODO: More modules and sensors
###

# Root/sudo check
if [ "$(id -u)" -ne 0 ]; then
	echo ' -->  ERROR ---------------- Please run as root or with sudo privileges ----------------' >&2
	exit 1
fi
# ------ End root/sudo check

function input_UI() {
	IP="0"
	PORT=""
	killall python3 # Kill all processes with python3 that is running.
	mkdir -p /usr/local/share/hydrosys4 # make sure installation directory is present
	
	echo "-->  Welcome to Hydrosys4 install script. The following initial settings are required:"
	while ! valid_ip $IP; do # IP part input
		read -p  "-->  Enter desired IPv4 address (range 192.168.1.100-192.168.1.200) or accept suggested IPv4 address by pressing [ENTER]: " -e -i 192.168.1.172 IP
		if valid_ip $IP; then stat='good'; 
			else stat='bad'; echo "-->  Please enter a valid IPv4 address, ex. 192.168.1.172"
		fi
	done
	echo "-->  Setting $IP as IPv4 address"

	while [[ ! $PORT =~ ^[0-9]+$ ]]; do # PORT part input
		read -p "-->  Enter desired PORT number or accept suggested by pressing [ENTER]: " -e -i 5172 PORT
		if [[ ! $PORT =~ ^[0-9]+$ ]]; then
			echo "-->  Please enter a valid PORT number, ex. 5172";
		fi
	done
	echo "-->  Setting $PORT as port number"
	
	read -p "-->  Enter desired WiFi AP name or accept suggested by pressing [ENTER]: " -e -i Hydrosys4 WiFiAPname # Local WiFi AP name and password setting
	echo "-->  Setting $WiFiAPname as WiFi AP name"
	read -p "-->  Enter desired WiFi AP password or accept suggested by pressing [ENTER]: " -e -i hydrosystem WiFiAPpsw
	echo "-->  Setting $WiFiAPpsw as WiFi password"
	read -p "-->  Do you wish to change hostname? (y,n): " -e -i y ChangeHostName
	#echo "  Confirmed Answer: "$ChangeHostName
	if [ "$ChangeHostName" == "y" ]; then
		read -p "-->  Enter desired hostname or accept suggested by pressing [ENTER]: " -e -i hydrosys4-172 NewHostName
		echo "-->  Setting $NewHostName as hostname"
		hostnamectl set-hostname $NewHostName # change the name in /etc/hostname
		aconf="/etc/hosts"
		cp /etc/hosts /usr/local/share/hydrosys4/hosts_hydrosys.backup
		sed -i "s/127.0.1.1.*/127.0.1.1	"$NewHostName"/" $aconf # Update hosts main config file
	fi
	read -p "-->  Do you wish to change default web page username and password? (y,n): " -e -i y changeDefaults
	if [ "$changeDefaults" == "y" ]; then
		$changeDefaults = "d"
		read -p "-->  Enter new login name or accept suggested by pressing [ENTER]: " -e -i admin newLogin
		read -p "-->  Enter new password or accept suggested by pressing [ENTER}: " -e -i default newPassword
		echo "-->  Setting $newLogin and $newPassword as your new login credentialts"
	fi
}

function valid_ip() {
    local  ip=$1
    local  stat=1
    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then # -- WIFI setup --- STANDARD
        OIFS=$IFS
        IFS='.'
        ip=($ip)
        IFS=$OIFS
        [[ ${ip[0]} -le 255 && ${ip[1]} -le 255 \
            && ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
        stat=$?
    fi
    return $stat
}

function system_update_UI() {
	while true; do
		read -p "-->  Do you wish to update and upgrade the Raspbian system (y/n)?" yn
		case $yn in
			[Yy]* ) system_update; echo "-->  Running a full system update and upgrade"; break;;
			[Nn]* ) system_update_light; echo "-->  Only running system update to fetch the latest packages"; break;;
			* ) echo "-->  Please answer y or n.";;
		esac
	done
}

function system_update() {
	while true; do
		read -p "-->  Do you want to uninstall LibreOffice and Wolfram Engine (if installed) as they are not necessary (y/n)? " yn
		case $yn in
			[Yy]* ) system_uninstall_pkgs; break;;
			[Nn]* ) break;;
			* ) "-->  Please answer y or n.";;
		esac
	done
	apt update && apt -y upgrade
}

function system_update_light() {
	while true; do
		read -p "-->  Do you want to uninstall LibreOffice and Wolfram Engine (if installed) as they are not necessary (y/n)? " yn
		case $yn in
			[Yy]* ) system_uninstall_pkgs; break;;
			[Nn]* ) break;;
			* ) "-->  Please answer y or n.";;
		esac
	done
	apt -y update # ---- system_update only
}

function system_uninstall_pkgs() {
	UNWANTED="libreoffice-* wolfram-engine" # ---- remove unnecessary packages
	for pkg in $UNWANTED; do
		if dpkg --get-selections | grep -q "^$pkg[[:space:]]*install$" >/dev/null; then
			apt remove --purge $pkg
		else
			echo "-->   ---------------- Unnecessary package $pkg not installed ----------------"
		fi
	done
}

function install_dependencies() {
	echo "-->  Installing dependencies, APT packages" #--- start installing dependencies
	INSTALL_APT="python3-dev python3-pip python3-future python3-smbus git build-essential i2c-tools fswebcam libjpeg-dev libopenjp2-7 dnsutils dnsmasq hostapd cmake libjpeg8-dev nginx"
	for pkg in $INSTALL_APT; do
		if dpkg --get-selections | grep -q "^$pkg[[:space:]]*install$" >/dev/null; then
			echo "-->  ---------------- $pkg already installed ----------------"
		else
			apt -y install $pkg || { echo "-->  APT ERROR: $pkg ---------------- Installation failed ----------------" && exit ;}
		fi
	done

	echo "-->  Installing dependencies, PIP3 packages"	
	INSTALL_PIP="flask apscheduler pyserial pillow pbkdf2 tornado RPi.GPIO spidev"
	for pkg in $INSTALL_PIP; do
		if python3 -c "import sys, pkgutil; sys.exit(not pkgutil.find_loader('$pkg'))"; then
			echo "-->  *---------------- $pkg already installed ----------------*"
		else
			pip3 install $pkg || { echo "-->  PIP3 ERROR: $pkg ---------------- Installation failed ----------------" && exit ;}
		fi
	done
}

function uninstall() {
	REMOVE_APT="python3-dev python3-pip python3-future python3-smbus git build-essential i2c-tools fswebcam libjpeg-dev libopenjp2-7 dnsutils dnsmasq hostapd cmake libjpeg8-dev nginx"
	REMOVE_PIP="flask apscheduler pyserial pillow pbkdf2 tornado RPi.GPIO spidev"
	echo "-->  Uninstalling APT and PIP3 packages"
	echo "-->  This will uninstall Hydrosys4 and all packages installed during installation including Nginx, Python 3 and Tornado, Flask aso."
	while true; do
		read -p "-->  Would you like to KEEP all packages (y/n)?" yn
		case $yn in
			[Yy]* )
				echo "-->  Keeping ALL packages, both APT and PIP3. Uninstall instruction: 'apt remove [package]' and 'pip3 uninstall [package]'."
				echo "-->  Installed APT packages: $REMOVE_APT"
				echo "-->  Installed PIP3 packages: $REMOVE_PIP"
				echo ""
				echo "-->  Uninstalling and reverting Hydrosys4. Changes made to files will be reverted to version backed up when installing Hydrosys4."
				echo "-->  Reverting changes made to /etc/hosts. Moving backed up config file to /etc/hosts. Saving running file to ~/hosts_hydrosys.backup"
				mv /etc/hosts ~/hosts_hydrosys.backup
				mv /usr/local/share/hydrosys4/hosts_hydrosys.backup /etc/hosts
				echo "-->  Reverting changes made to default zone file. Moving backed up file to /etc/nginx/sites-enabled/default. Saving running file to ~/nginx_hydrosys.backup"
				mv /etc/nginx/sites-enabled/default ~/nginx_hydrosys.backup
				mv /usr/local/share/hydrosys4/nginx_hydrosys.backup /etc/nginx/sites-enabled/default
				echo "-->  Reverting changes made to rc.local. Moving backed up config file to /etc/rc.local. Saving running file to ~/rc_hydrosys.backup"
				mv /etc/rc.local ~/rc_hydrosys.backup
				mv /usr/local/share/hydrosys4/rc_hydrosys.backup /ect/rc.local
				echo "-->  Reverting changes made to /boot/config.txt. Moving backed up config file to /boot/config.txt. Saving running file to ~/boot_config_hydrosys.backup"
				mv /boot/config.txt ~/boot_config_hydrosys.backup
				mv /usr/local/share/hydrosys4/boot_config_hydrosys.backup /boot/config.txt
				echo "-->  Reverting changes made to /etc/modules. Moving backed up config file to /etc/modules. Saving running file to ~/etc_modules_hydrosys.backup"
				mv /etc/modules ~/etc_modules_hydrosys.backup
				mv /usr/local/share/hydrosys4/etc_modules_hydrosys.backup /etc/modules
				echo "-->  Reverting changes made to hostapd.conf. Moving backed up config file to /etc/hostapd/hostapd.conf. Saving running file to ~/hostapd_hydrosys.backup"
				mv /etc/hostapd/hostapd.conf ~/hostapd_hydrosys.backup
				mv /usr/local/share/hydrosys4/hostapd_hydrosys.backup /etc/hostapd/hostapd.conf
				echo "-->  Reverting changes made to dnsmasq.conf. Moving backed up config file to /etc/dnsmasq.conf. Saving running file to ~/dnsmasq_hydrosys.backup"
				mv /etc/dnsmasq.conf ~/dnsmasq_hydrosys.backup
				mv /usr/local/share/hydrosys4/dnsmasq_hydrosys.backup /etc/dnsmasq.conf
				echo "-->  Reverting changes made to dhcpcd.conf. Moving backed up config file to /etc/dhcpcd.conf. Saving running file to ~/dhcpcd_hydrosys.backup"
				mv /etc/dhcpcd.conf ~/dhcpcd_hydrosys.backup
				mv /usr/local/share/hydrosys4/dhcpcd_hydrosys.backup /etc/dhcpcd.conf
				echo "-->  Removing Hydrosys4 installation folder and configuration files."
				rm -rf /usr/local/share/hydrosys4
				ask_reboot
				break
				;;
			[Nn]* )
				echo "-->  Removing ALL packages, both APT and PIP3 including all configurations"
				pip3 uninstall $REMOVE_PIP || { echo "-->  PIP3 ERROR: ---------------- Uninstallation failed ----------------" && exit ;}
				apt -y remove --purge $REMOVE_APT || { echo "-->  APT ERROR: ---------------- Uninstallation failed ----------------" && exit ;}
				apt autoremove
				echo "-->  Uninstalling and reverting Hydrosys4. Changes made to files will be reverted to version backed up when installing Hydrosys4."
				echo "-->  Reverting changes made to /etc/hosts. Moving backed up config file to /etc/hosts. Saving running file to ~/hosts_hydrosys.backup"
				mv /etc/hosts ~/hosts_hydrosys.backup
				mv /usr/local/share/hydrosys4/hosts_hydrosys.backup /etc/hosts
				echo "-->  Reverting changes made to default zone file. Moving backed up file to /etc/nginx/sites-enabled/default. Saving running file to ~/nginx_hydrosys.backup"
				mv /etc/nginx/sites-enabled/default ~/nginx_hydrosys.backup
				mv /usr/local/share/hydrosys4/nginx.default /etc/nginx/sites-enabled/default
				echo "-->  Reverting changes made to rc.local. Moving backed up config file to /etc/rc.local. Saving running file to ~/rc_hydrosys.backup"
				mv /etc/rc.local ~/rc_hydrosys.backup
				mv /usr/local/share/hydrosys4/rc_hydrosys.backup /ect/rc.local
				echo "-->  Reverting changes made to /boot/config.txt. Moving backed up config file to /boot/config.txt. Saving running file to ~/boot_config_hydrosys.backup"
				mv /boot/config.txt ~/boot_config_hydrosys.backup
				mv /usr/local/share/hydrosys4/boot_config_hydrosys.backup /boot/config.txt
				echo "-->  Reverting changes made to /etc/modules. Moving backed up config file to /etc/modules. Saving running file to ~/etc_modules_hydrosys.backup"
				mv /etc/modules ~/etc_modules_hydrosys.backup
				mv /usr/local/share/hydrosys4/etc_modules_hydrosys.backup /etc/modules
				echo "-->  Reverting changes made to hostapd.conf. Moving backed up config file to /etc/hostapd/hostapd.conf. Saving running file to ~/hostapd_hydrosys.backup"
				mv /etc/hostapd/hostapd.conf ~/hostapd_hydrosys.backup
				mv /usr/local/share/hydrosys4/hostapd_hydrosys.backup /etc/hostapd/hostapd.conf
				echo "-->  Reverting changes made to dnsmasq.conf. Moving backed up config file to /etc/dnsmasq.conf. Saving running file to ~/dnsmasq_hydrosys.backup"
				mv /etc/dnsmasq.conf ~/dnsmasq_hydrosys.backup
				mv /usr/local/share/hydrosys4/dnsmasq_hydrosys.backup /etc/dnsmasq.conf
				echo "-->  Reverting changes made to dhcpcd.conf. Moving backed up config file to /etc/dhcpcd.conf. Saving running file to ~/dhcpcd_hydrosys.backup"
				mv /etc/dhcpcd.conf ~/dhcpcd_hydrosys.backup
				mv /usr/local/share/hydrosys4/dhcpcd_hydrosys.backup /etc/dhcpcd.conf
				echo "-->  Removing Hydrosys4 installation folder and configuration files."
				rm -rf /usr/local/share/hydrosys4
				break
				;;
			* )
				echo "-->  Please answer y or n."
				;;
		esac
	done	

}

function install_mjpegstr() {
	aconf="/usr/local/share/hydrosys4/mjpg-streamer" # create hostapd.conf file
	if [ -f $aconf ]; then
	   rm -rf /usr/local/share/hydrosys4/mjpg-streamer
	fi
	mkdir -p /usr/local/share/hydrosys4
	cd /usr/local/share/hydrosys4
	git clone https://github.com/jacksonliam/mjpg-streamer.git
	cd mjpg-streamer/mjpg-streamer-experimental
	make
	make install
}

function install_hydrosys4() {
	aconf="/usr/local/share/hydrosys4/env/autonom" # check if file exist in local folder
	if [ -d $aconf ]; then  # if the directory exist
		rm -rf /usr/local/share/hydrosys4/env
	else
		mkdir -p /usr/local/share/hydrosys4/env # --- INSTALL Hydrosys4 software
		cd /usr/local/share/hydrosys4/env
		git clone https://github.com/Hydrosys4/Master.git
		mv Master autonom
	fi
	if [ -f "changeDefaults" == "d" ]; then
		bash -c "cat >> /usr/local/share/hydrosys4/env/autonom/database/logincred.txt" <<-EOF
		{"name": "login", "password": "$newPassword", "username": "$newLogin"}
		EOF
	fi
}

function install_DHT22lib() {
	aconf="/usr/local/share/hydrosys4/env/autonom/libraries/DHT22/master.zip" # This is just going to install the library present in local folder
	if [ -f $aconf ]; then # --- installing the DHT22 Sensor libraries
		cd /usr/local/share/hydrosys4/env/autonom/libraries/DHT22
		unzip master.zip
		cd Adafruit_Python_DHT-master
		python3 setup1plus.py install # setup1plus is file that make the DTH22 work with both RaspberryPi zero,1 and model 2,3
	fi
}

function config_I2C() {
	echo "-->  Enabling I2C and SPI and adding modules"
	aconf="/boot/config.txt" # --- Enable I2C and Spi: /boot/config.txt
	if [ -f $aconf ]; then
		cp $aconf /usr/local/share/hydrosys4/boot_config_hydrosys.backup
	fi
	sed -i 's/\(^.*#dtparam=i2c_arm=on.*$\)/dtparam=i2c_arm=on/' $aconf
	sed -i 's/\(^.*#dtparam=spi=on.*$\)/dtparam=spi=on/' $aconf
	sed -i 's/\(^.*#dtparam=i2s=on.*$\)/dtparam=i2s=on/' $aconf

	aconf="/etc/modules" # --- Add modules: /etc/modules
	if [ -f $aconf ]; then
		cp $aconf /usr/local/share/hydrosys4/etc_modules_hydrosys.backup
	fi
	sed -i '/i2c-bcm2708/d' $aconf
	sed -i -e "\$ai2c-bcm2708" $aconf
	sed -i '/i2c-dev/d' $aconf
	sed -i -e "\$ai2c-dev" $aconf
	sed -i '/i2c-bcm2835/d' $aconf
	sed -i -e "\$ai2c-bcm2835" $aconf
	sed -i '/rtc-ds1307/d' $aconf
	sed -i -e "\$artc-ds1307" $aconf
	sed -i '/bcm2835-v4l2/d' $aconf
	sed -i -e "\$abcm2835-v4l2" $aconf
}

function config_RClocal() {
	echo "-->  Modifying rc.local for autostart actions"
	aconf="/etc/rc.local"
	if [ -f $aconf ]; then
		cp $aconf /usr/local/share/hydrosys4/rc_hydrosys.backup
	fi
	autostart="yes"
	tmpfile=$(mktemp)
	sed '/#START/,/#END/d' /etc/rc.local > "$tmpfile" && mv "$tmpfile" /etc/rc.local # copy the below lines between #START and #END to rc.local
	awk '!NF {if (++n <= 1) print; next}; {n=0;print}' /etc/rc.local > "$tmpfile" && mv "$tmpfile" /etc/rc.local # Remove to growing plank lines.
	if [ "$autostart" == "yes" ]; then
		if ! grep -Fq '#START HYDROSYS4 SECTION' /etc/rc.local; then # --- Real Time Clock (RTC) /etc/rc.local
			sed -i '/exit 0/d' /etc/rc.local
			bash -c "cat >> /etc/rc.local" <<-EOF
			#START HYDROSYS4 SECTION
			# iptables
			sudo iptables-restore < /usr/local/share/hydrosys4/iptables.rules

			# clock
			echo "HYDROSYS4-set HW clock ****************************************"
			echo ds3231 0x68 > /sys/class/i2c-adapter/i2c-1/new_device || true
			hwclock -s || true

			echo "HYDROSYS4-start system ****************************************"
			cd /usr/local/share/hydrosys4/env/autonom/
			sudo python3 /usr/local/share/hydrosys4/env/autonom/bentornado.py &
			#END HYDROSYS4 SECTION
			exit 0
			EOF
		else
			tmpfile=$(mktemp)
			sed '/#START/,/#END/d' /etc/rc.local > "$tmpfile" && mv "$tmpfile" /etc/rc.local
			awk '!NF {if (++n <= 1) print; next}; {n=0;print}' /etc/rc.local > "$tmpfile" && mv "$tmpfile" /etc/rc.local # Remove to growing plank lines.
		fi
	fi
	sudo chown root:root /etc/rc.local
	sudo chmod 755 /etc/rc.local
}

function config_hostapd() {
	echo "-->  Adding network configuration for $WiFiAPname"
	systemctl unmask hostapd.service # unmask the service
	aconf="/etc/hostapd/hostapd.conf" # create hostapd.conf file
	if [ -f $aconf ]; then
	   cp $aconf /usr/local/share/hydrosys4/hostapd_hydrosys.backup
	   echo "-->  Backed up /etc/hostapd/hostapd.conf to /usr/local/share/hydrosys4/hostapd_hydrosys.backup"
	fi
	bash -c "cat >> $aconf" <<-EOF
	# HERE-> {"name": "IPsetting", "LocalIPaddress": "$IP", "LocalPORT": "$PORT", "LocalAPSSID" : "$WiFiAPname"}
	ieee80211n=1
	interface=wlan0
	ssid=$WiFiAPname
	hw_mode=g
	channel=6
	macaddr_acl=0
	auth_algs=1
	ignore_broadcast_ssid=0
	wpa=2
	wpa_passphrase=$WiFiAPpsw
	wpa_key_mgmt=WPA-PSK
	wpa_pairwise=TKIP
	rsn_pairwise=CCMP
	EOF
	aconf="/etc/init.d/hostapd" # Update hostapd main config file
	sed -i "s/\(^.*DAEMON_CONF=.*$\)/DAEMON_CONF=\/etc\/hostapd\/hostapd.conf/" $aconf
	aconf="/etc/default/hostapd" # Update hostapd main config file
	sed -i "s/\(^.*DAEMON_CONF=.*$\)/DAEMON_CONF=\/etc\/hostapd\/hostapd.conf/" $aconf
	systemctl enable hostapd.service 
}

function config_dnsmasq() {
	echo "-->  Configuring DNS parameters"
	aconf="/etc/dnsmasq.conf" # edit /etc/dnsmasq.conf file
	if [ -f $aconf ]; then
		cp $aconf /usr/local/share/hydrosys4/dnsmasq_hydrosys.backup
	fi
	sed -i '/^#START HYDROSYS4 SECTION/,/^#END HYDROSYS4 SECTION/{/^#START HYDROSYS4 SECTION/!{/^#END HYDROSYS4 SECTION/!d}}' $aconf # delete rows between #START and #END
	sed -i '/#START HYDROSYS4 SECTION/d' $aconf
	sed -i '/#END HYDROSYS4 SECTION/d' $aconf
	IFS="." read -a a <<< $IP # calculation of the range starting from assigned IP address
	IFS="." read -a b <<< 0.0.0.1
	IFS="." read -a c <<< 0.0.0.9
	IPSTART="$[a[0]].$[a[1]].$[a[2]].$[a[3]+b[3]]"
	IPEND="$[a[0]].$[a[1]].$[a[2]].$[a[3]+c[3]]"
	if [[ a[3] -gt 244 ]]; then
		IPSTART="$[a[0]].$[a[1]].$[a[2]].$[a[3]-c[3]]"
		IPEND="$[a[0]].$[a[1]].$[a[2]].$[a[3]-b[3]]"
	fi
	echo $IPSTART $IPEND
	bash -c "cat >> $aconf" <<-EOF
	#START HYDROSYS4 SECTION
	interface=wlan0
	dhcp-range=$IPSTART,$IPEND,12h
	#no-resolv
	#END HYDROSYS4 SECTION
	EOF
	systemctl enable dnsmasq.service
 }

function config_dhcpcd() {
	echo "-->  Configuring DHCP parameters"
	aconf="/etc/dhcpcd.conf" # edit /etc/dnsmasq.conf file
	if [ -f $aconf ]; then
		cp $aconf /usr/local/share/hydrosys4/dhcpcd_hydrosys.backup
	fi
	sed -i '/^#START HYDROSYS4 SECTION/,/^#END HYDROSYS4 SECTION/{/^#START HYDROSYS4 SECTION/!{/^#END HYDROSYS4 SECTION/!d}}' $aconf # delete rows between #START and #END
	sed -i '/#START HYDROSYS4 SECTION/d' $aconf
	sed -i '/#END HYDROSYS4 SECTION/d' $aconf
	bash -c "cat >> $aconf" <<-EOF
	#START HYDROSYS4 SECTION
	profile static_wlan0
	static ip_address=$IP/24
	#static routers=192.168.1.1
	#static domain_name_servers=192.169.1.1
	# fallback to static profile on wlan0
	interface wlan0
	fallback static_wlan0
	#END HYDROSYS4 SECTION
	EOF
}

function config_ifnames() {
	aconf="/boot/cmdline.txt" # this is to preserve the network interfaces names, becasue staring from debian stretch (9) the ifnames have new rules
	APPEND=' net.ifnames=0'
	echo "$(cat $aconf)$APPEND" > $aconf
}

function config_nginx() {
	echo "-->  Configuring Nginx server settings and default zone file"
	aconf="/etc/nginx/sites-enabled/default" # create default file
	if [ -f $aconf ]; then
		mv $aconf /usr/local/share/hydrosys4/nginx_hydrosys.backup
		echo "-->  Backed up /etc/nginx/sites-enabled/default to /usr/local/share/hydrosys4/nginx_hydrosys.backup"
	fi
	bash -c "cat >> $aconf" <<-EOF
	server {
		# for a public HTTP server:
		listen $PORT;
		server_name localhost;

		access_log off;
		error_log off;

		location / {
			proxy_pass http://127.0.0.1:5020;
		}

		location /stream {
			rewrite ^/stream/(.*) /$1 break;
			proxy_pass http://127.0.0.1:5022;
			proxy_buffering off;
		}

		location /favicon.ico {
			alias /usr/local/share/hydrosys4/env/autonom/static/favicon.ico;
		}
	}
	EOF
	systemctl restart nginx
}

function config_defaultnetworkdb() {
	aconf="/usr/local/share/hydrosys4/env/autonom/database/default/defnetwork.txt "
	if [ -f $aconf ]; then # if file already exist then no action, otherwise create it
		echo "-->  Default network file already exist, no changes where made"
	else
		bash -c "cat >> $aconf" <<-EOF
		{"name": "IPsetting", "LocalIPaddress": "192.168.0.172", "LocalPORT": "5012" , "LocalAPSSID" : "Hydrosys4"}
		EOF
	fi
}

function config_iptables_ports() {
	iptables -A INPUT -p tcp -s localhost --dport 5020 -j ACCEPT
	iptables -A INPUT -p tcp -s localhost --dport 5022 -j ACCEPT
	iptables -A INPUT -p tcp --dport 5020 -j DROP
	iptables -A INPUT -p tcp --dport 5022 -j DROP
	iptables-save > /usr/local/share/hydrosys4/iptables.rules
	echo "-->  installation finished!!!"
}

function ask_reboot() {
	read -p "-->  Do you want to reboot the system, required for all changes to be applied? (y,n): " -e -i y doreboot
	echo "  Confirmed Answer: "$doreboot
	if [ "$doreboot" == "y" ]; then
		reboot
	fi
}

function show_help() {
	cat <<-EOF
	Usage: ${0##*/} [-i] [-u] [-h]...
	Please use one of options given below to continue

			-h|-help       Display this help and exit
			-i|-install    Install Hydrosys4
			-u|-uninstall  Completely remove Hydrosys4 and revert all changes
			-d|-debug      Log install or uninstall actions to debug_messages.log
	EOF
}

while :; do
	case $1 in
		-h|-\?|--help)
			show_help
			exit 1
			;;
		-d|-debug|--debug)
			exec 5> debug_messages.log
			BASH_XTRACEFD="5"
			set -x
			;;
		-i|-install|--install)
			input_UI
			system_update_UI
			install_dependencies
			install_hydrosys4 # this should be called before the DHT22 due to local library references
			install_mjpegstr
			install_DHT22lib
			config_I2C
			config_RClocal
			config_hostapd
			config_dnsmasq
			config_dhcpcd
			config_ifnames
			config_nginx
			config_defaultnetworkdb
			config_iptables_ports
			ask_reboot
			exit 1
			;;
		-u|-uninstall|--uninstall)
			uninstall
			exit 1
			;;
		--) # End of all options.
			shift
			break
			;;
		-?*)
			printf 'WARNING: Unknown option: %s\n\n' "$1" >&2
			show_help
			exit 1
			;;
		*)
			printf "ERROR: No option given, exiting\n\n" >&2
			show_help
			exit 1
			;;
	esac
	shift
done