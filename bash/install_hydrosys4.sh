#!/bin/bash


#Debug enable next 3 lines
exec 5> install.txt
BASH_XTRACEFD="5"
set -x
# ------ end debug


function killpython()
{

sudo killall python3

}


function system_update_light()
{

# ---- system_update

sudo apt-get -y update

}

function system_update()
{

# ---- remove unnecessary packages

sudo apt-get remove --purge libreoffice-*
sudo apt-get remove --purge wolfram-engine


# ---- system_update

sudo apt-get -y update
sudo apt-get -y upgrade

}

function system_update_UI()
{

while true; do
    read -p "Do you wish to update the Raspbian system (y/n)?" yn
    case $yn in
        [Yy]* ) system_update; break;;
        [Nn]* ) break;;
        * ) echo "Please answer y or n.";;
    esac
done

}

function install_dependencies()
{


#--- start installing dependencies

sudo apt-get -y install python3-dev || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
sudo apt -y install python3-pip || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
sudo pip3 install flask || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
sudo pip3 install apscheduler || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
sudo pip3 install pyserial || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
sudo apt-get install python3-future

#(for the webcam support)
sudo apt-get -y install fswebcam || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

#(for the image thumbnail support)
sudo apt-get -y install libjpeg-dev || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
sudo apt install libopenjp2-7
sudo pip3 install pillow || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

#(for external IP address, using DNS)
sudo apt-get -y install dnsutils || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

#(encryption)
sudo pip3 install pbkdf2 || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

#(web server)
sudo pip3 install tornado || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

#(GPIO)
sudo pip3 install RPi.GPIO
}

function enable_I2C()
{

# --- Enable I2C and Spi :
# /boot/config.txt

sed -i 's/\(^.*#dtparam=i2c_arm=on.*$\)/dtparam=i2c_arm=on/' /boot/config.txt
sed -i 's/\(^.*#dtparam=spi=on.*$\)/dtparam=spi=on/' /boot/config.txt
sed -i 's/\(^.*#dtparam=i2s=on.*$\)/dtparam=i2s=on/' /boot/config.txt

# --- Add modules:
# /etc/modules
aconf="/etc/modules"

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


# --- install I2C tools
sudo apt-get -y install git build-essential python3-dev python3-smbus || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
sudo apt-get -y install -y i2c-tools  || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

}


# --- enable raspicam

############# MISSING ##############

function modify_RClocal()
{

# --- Real Time Clock (RTC)
# /etc/rc.local

autostart="yes"
# copy the below lines between # START and #END to rc.local
tmpfile=$(mktemp)
sudo sed '/#START/,/#END/d' /etc/rc.local > "$tmpfile" && sudo mv "$tmpfile" /etc/rc.local
# Remove to growing plank lines.
sudo awk '!NF {if (++n <= 1) print; next}; {n=0;print}' /etc/rc.local > "$tmpfile" && sudo mv "$tmpfile" /etc/rc.local
if [ "$autostart" == "yes" ]; then
   if ! grep -Fq '#START HYDROSYS4 SECTION' /etc/rc.local; then
      sudo sed -i '/exit 0/d' /etc/rc.local
      sudo bash -c "cat >> /etc/rc.local" << EOF
#START HYDROSYS4 SECTION
# iptables
sudo iptables-restore < /home/pi/iptables.rules

# clock
echo "HYDROSYS4-set HW clock ****************************************"
echo ds3231 0x68 > /sys/class/i2c-adapter/i2c-1/new_device || true
hwclock -s || true

echo "HYDROSYS4-start system ****************************************"
cd /home/pi/env/autonom/
sudo python3 /home/pi/env/autonom/bentornado.py &

#END HYDROSYS4 SECTION

exit 0
EOF
   else
      tmpfile=$(mktemp)
      sudo sed '/#START/,/#END/d' /etc/rc.local > "$tmpfile" && sudo mv "$tmpfile" /etc/rc.local
      # Remove to growing plank lines.
      sudo awk '!NF {if (++n <= 1) print; next}; {n=0;print}' /etc/rc.local > "$tmpfile" && sudo mv "$tmpfile" /etc/rc.local
   fi

fi

sudo chown root:root /etc/rc.local
sudo chmod 755 /etc/rc.local
# end modification to RC.local

}


### -- WIFI setup --- STANDARD

function valid_ip()
{
    local  ip=$1
    local  stat=1

    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
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


input_UI ()
{

echo "Hello, following initial setting is requested:"

# IP part input

IP="0"
while ! valid_ip $IP; do
	read -p "Local IP address (range 192.168.0.100-192.168.1.200), to confirm press [ENTER] or modify: " -e -i 192.168.1.172 IP
	if valid_ip $IP; then stat='good'; 
	else stat='bad'; echo "WRONG FORMAT, please enter a valid value for IP address"
	fi

done
	echo "Confirmed IP address: "$IP

PORT=""
while [[ ! $PORT =~ ^[0-9]+$ ]]; do
read -p "Local PORT, to confirm press [ENTER] or modify: " -e -i 5172 PORT
	if [[ ! $PORT =~ ^[0-9]+$ ]];
	then echo "WRONG FORMAT, please enter a valid value for PORT";
	fi
done
	echo "Confirmed PORT: "$PORT
	
# Local WiFi AP name and password setting	

read -p "System WiFi AP name, to confirm press [ENTER] or modify: " -e -i Hydrosys4 WiFiAPname
echo "Confirmed Name: "$WiFiAPname

read -p "System WiFi AP password, to confirm press [ENTER] or modify: " -e -i hydrosystem WiFiAPpsw
echo "Confirmed Password: "$WiFiAPpsw

read -p "Do you want to change hostname? (y,n): " -e -i y ChangeHostName
echo "Confirmed Answer: "$ChangeHostName

if [ "$ChangeHostName" == "y" ]; then
	read -p "System Hostname, to confirm press [ENTER] or modify: " -e -i hydrosys4-172 NewHostName
	echo "Confirmed Hostname: "$NewHostName
fi

read -p "Do you want to install MQTT support? (y,n): " -e -i y MQTTsupport
echo "Confirmed Answer: "$MQTTsupport

}


install_MQTTsupport ()
{

# --- change system hostname
if [ "$MQTTsupport" == "y" ]; then

	sudo apt-get -y install mosquitto || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
	sudo pip3 install paho-mqtt
	
fi

}


apply_newhostname ()
{

# --- change system hostname
if [ "$ChangeHostName" == "y" ]; then
	sudo hostnamectl set-hostname $NewHostName # change the name in /etc/hostname

	aconf="/etc/hosts"
	# Update hostapd main config file
	sudo sed -i "s/127.0.1.1.*/127.0.1.1	"$NewHostName"/" $aconf
	
fi

}


ask_reboot ()
{


read -p "Do you want to reboot the system? (y,n): " -e -i y doreboot
echo "Confirmed Answer: "$doreboot

if [ "$doreboot" == "y" ]; then
	sudo reboot
fi

}







install_DHT22lib ()
{

# --- installing the DHT22 Sensor libraries	
sudo apt-get -y install build-essential python3-dev python3-setuptools || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

# This is just going to install the lybrary present in local folder
aconf="/home/pi/env/autonom/libraries/DHT22/master.zip"
if [ -f $aconf ]; then

	cd /home/pi/env/autonom/libraries/DHT22
	unzip master.zip
	cd Adafruit_Python_DHT-master
	sudo python3 setup.py install
	cd /home/pi

fi
}


install_SPIlib ()
{


# --- INSTALL SPI library:

sudo apt-get -y install python3-dev || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
sudo pip3 install spidev

}





install_hydrosys4 ()
{
# --- INSTALL Hydrosys4 software
sudo apt-get -y install git || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}


# check if file exist in local folder
#aconf="/home/pi/env/autonom"
#if [ -d $aconf ]; then  # if the directory exist
#	cd /home/pi
#else
	cd /home/pi
	sudo killall python3	
	sudo rm -r env
	mkdir env
	cd env
	#sudo rm -r autonom
	git clone https://github.com/Hydrosys4/Master.git
	mv Master autonom
	cd ..
	cd ..

#fi

}






fn_hostapd ()
{

sudo apt-get -y install hostapd || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

# unmask the service
sudo systemctl unmask hostapd.service
	
# create hostapd.conf file
aconf="/etc/hostapd/hostapd.conf"
if [ -f $aconf ]; then
   cp $aconf $aconf.1
   sudo rm $aconf
   echo "remove file"
fi


sudo bash -c "cat >> $aconf" << EOF
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


aconf="/etc/init.d/hostapd"
# Update hostapd main config file
sudo sed -i "s/\(^.*DAEMON_CONF=.*$\)/DAEMON_CONF=\/etc\/hostapd\/hostapd.conf/" $aconf

aconf="/etc/default/hostapd"
# Update hostapd main config file
sudo sed -i "s/\(^.*DAEMON_CONF=.*$\)/DAEMON_CONF=\/etc\/hostapd\/hostapd.conf/" $aconf

sudo systemctl enable hostapd.service 

}


fn_dnsmasq ()
{
	
sudo apt-get -y install dnsmasq || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

	
# edit /etc/dnsmasq.conf file
aconf="/etc/dnsmasq.conf"

# delete rows between #START and #END
sed -i '/^#START HYDROSYS4 SECTION/,/^#END HYDROSYS4 SECTION/{/^#START HYDROSYS4 SECTION/!{/^#END HYDROSYS4 SECTION/!d}}' $aconf
sed -i '/#START HYDROSYS4 SECTION/d' $aconf
sed -i '/#END HYDROSYS4 SECTION/d' $aconf

# calculation of the range starting from assigned IP address
IFS="." read -a a <<< $IP
IFS="." read -a b <<< 0.0.0.1
IFS="." read -a c <<< 0.0.0.9
IPSTART="$[a[0]].$[a[1]].$[a[2]].$[a[3]+b[3]]"
IPEND="$[a[0]].$[a[1]].$[a[2]].$[a[3]+c[3]]"
if [[ a[3] -gt 244 ]]; then
IPSTART="$[a[0]].$[a[1]].$[a[2]].$[a[3]-c[3]]"
IPEND="$[a[0]].$[a[1]].$[a[2]].$[a[3]-b[3]]"
fi

echo $IPSTART $IPEND



# -----



sudo bash -c "cat >> $aconf" << EOF
#START HYDROSYS4 SECTION
interface=wlan0
dhcp-range=$IPSTART,$IPEND,12h
#no-resolv
#END HYDROSYS4 SECTION
EOF

sudo systemctl enable dnsmasq.service
 

}


fn_dhcpcd ()
{
	
# edit /etc/dnsmasq.conf file
aconf="/etc/dhcpcd.conf"

# delete rows between #START and #END
sed -i '/^#START HYDROSYS4 SECTION/,/^#END HYDROSYS4 SECTION/{/^#START HYDROSYS4 SECTION/!{/^#END HYDROSYS4 SECTION/!d}}' $aconf
sed -i '/#START HYDROSYS4 SECTION/d' $aconf
sed -i '/#END HYDROSYS4 SECTION/d' $aconf


sudo bash -c "cat >> $aconf" << EOF
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

fn_ifnames ()
{
# this is to preserve the network interfaces names, becasue staring from debian stretch (9) the ifnames have new rules 	
# edit /etc/dnsmasq.conf file
aconf="/boot/cmdline.txt"

APPEND=' net.ifnames=0'
echo "$(cat $aconf)$APPEND" > $aconf
 
}









install_mjpegstr ()
{
cd /home/pi

sudo rm -r mjpg-streamer

sudo apt-get -y install cmake 
sudo apt-get -y install libjpeg9-dev 
sudo apt-get -y install git

sudo git clone https://github.com/jacksonliam/mjpg-streamer.git

cd mjpg-streamer/mjpg-streamer-experimental

sudo make

sudo make install

cd ..
cd ..

}



install_nginx ()
{
# this function is used
cd /home/pi

sudo apt-get -y install nginx

# create default file
aconf="/etc/nginx/sites-enabled/default"
if [ -f $aconf ]; then
   cp $aconf /home/pi/$aconf.1
   sudo rm $aconf
   echo "remove file"
fi


sudo bash -c "cat >> $aconf" << EOF
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

    location /static/download/configdownload/logincred.txt {
        return 302 https://$server_name$request_uri;
    }


    location /favicon.ico {
        alias /home/pi/env/autonom/static/favicon.ico;
    }
}
EOF

sudo service nginx start

cd ..
cd ..

}


install_squid3 ()
{
# this function is NOT USED
cd /home/pi

sudo apt-get install squid3 -y || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}

# add configuration to squid.conf, the file should already exist if installation is succesful
adir="/etc/squid3"
if [ -d $adir ]; then
	aconf="/etc/squid3/squid.conf"
fi
adir="/etc/squid"
if [ -d $adir ]; then
	aconf="/etc/squid/squid.conf"
fi

if [ -f $aconf ]; then
   cp $aconf $aconf.1
   sudo rm $aconf
   echo "remove file"
fi



sudo bash -c "cat >> $aconf" << EOF
# hydrosys4 configurations

http_port $PORT accel defaultsite=hydrosys4 vhost

acl Safe_ports port $PORT  # unregistered ports

acl videostream urlpath_regex \?action=stream

cache_peer localhost parent 5020 0 no-query originserver name=server1
cache_peer_access server1 deny videostream

cache_peer localhost parent 5022 0 no-query originserver name=server2
cache_peer_access server2 allow videostream
cache_peer_access server2 deny all

http_access allow Safe_ports

# default configurations

#	WELCOME TO SQUID 3.5.12
acl SSL_ports port 443
acl Safe_ports port 80		# http
acl Safe_ports port 21		# ftp
acl Safe_ports port 443		# https
acl Safe_ports port 70		# gopher
acl Safe_ports port 210		# wais
acl Safe_ports port 1025-65535	# unregistered ports
acl Safe_ports port 280		# http-mgmt
acl Safe_ports port 488		# gss-http
acl Safe_ports port 591		# filemaker
acl Safe_ports port 777		# multiling http
acl CONNECT method CONNECT
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow localhost manager
http_access deny manager
http_access allow localhost
http_access deny all
coredump_dir /var/spool/squid
refresh_pattern ^ftp:		1440	20%	10080
refresh_pattern ^gopher:	1440	0%	1440
refresh_pattern -i (/cgi-bin/|\?) 0	0%	0
refresh_pattern (Release|Packages(.gz)*)$      0       20%     2880
refresh_pattern .		0	20%	4320
EOF

sudo service squid3 start

cd ..
cd ..

}



edit_defaultnetworkdb ()
{


aconf="/home/pi/env/autonom/database/default/defnetwork.txt "

# if file already exist then no action, otherwise create it
if [ -f $aconf ]; then
   echo "network default file already exist"
   else
   sudo bash -c "cat >> $aconf" << EOF
{"name": "IPsetting", "LocalIPaddress": "192.168.0.172", "LocalPORT": "5012" , "LocalAPSSID" : "Hydrosys4"}
EOF
   
fi

}

edit_networkdb ()
{


aconf="/home/pi/env/autonom/database/network.txt "

# if file already exist then delete it
if [ -f $aconf ]; then
   sudo rm $aconf
   echo "remove file"
fi

sudo bash -c "cat >> $aconf" << EOF
{"name": "IPsetting", "LocalIPaddress": "$IP", "LocalPORT": "$PORT", "LocalAPSSID" : "$WiFiAPname"}
EOF


}


iptables_blockports ()
{
sudo apt-get install iptables -y || { echo "ERROR --------------------------Installation failed ----------------" && exit ;}
    
sudo iptables -A INPUT -p tcp -s localhost --dport 5020 -j ACCEPT
sudo iptables -A INPUT -p tcp -s localhost --dport 5022 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5020 -j DROP
sudo iptables -A INPUT -p tcp --dport 5022 -j DROP

sudo iptables-save > /home/pi/iptables.rules

}


# --- RUN the functions
killpython
input_UI
system_update_light
#system_update_UI
install_dependencies
enable_I2C
modify_RClocal
fn_hostapd
fn_dnsmasq
fn_dhcpcd
fn_ifnames
install_mjpegstr
#install_squid3
install_nginx
install_hydrosys4 # this should be called before the DHT22 , SPI and BMP due to local library references
install_DHT22lib
install_SPIlib
install_MQTTsupport
edit_defaultnetworkdb
#edit_networkdb
iptables_blockports
apply_newhostname
echo "installation is finished!!! "
ask_reboot
