#!/bin/bash


#Debug enable next 3 lines
exec 5> install.txt
BASH_XTRACEFD="5"
set -x
# ------ end debug


function killpython()
{

sudo killall python

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

sudo apt-get -y install python-dev
sudo apt-get -y install python-pip
sudo pip install flask
sudo pip install apscheduler
sudo pip install pyserial

#(for the webcam support)
sudo apt-get -y install fswebcam 

#(for external IP address, using DNS)
sudo apt-get -y install dnsutils

#(encryption)
sudo pip install pbkdf2 

#(web server)
sudo pip install tornado

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
sudo apt-get -y install git build-essential python-dev python-smbus
sudo apt-get -y install -y i2c-tools

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
# clock
echo ds3231 0x68 > /sys/class/i2c-adapter/i2c-1/new_device || true
hwclock -s || true

cd /home/pi/env/autonom/
sudo python /home/pi/env/autonom/bentornado.py &

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
	read -p "Local IP address, to confirm press [ENTER] or modify: " -e -i 192.168.0.172 IP
	if valid_ip $IP; then stat='good'; 
	else stat='bad'; echo "WRONG FORMAT, please enter a valid value for IP address"
	fi

done
	echo "Confirmed IP address: "$IP

PORT=""
while [[ ! $PORT =~ ^[0-9]+$ ]]; do
read -p "Local PORT, to confirm press [ENTER] or modify: " -e -i 5012 PORT
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

}


install_DHT22lib ()
{

# --- installing the DHT22 Sensor libraries	
sudo apt-get -y install build-essential python-dev

# check if file exist in local folder
aconf="/home/pi/env/autonom/libraries/DHT22/master.zip"
if [ -f $aconf ]; then

	cd /home/pi/env/autonom/libraries/DHT22
	unzip master.zip
	cd Adafruit_Python_DHT-master
	# setup1+2 is file that try to make the DTH22 work with both RaspberryPi zero,1 and model 2,3 
	sudo python setup1+2.py install
	cd /home/pi
else
	cd /home/pi
	sudo rm -r DHT22
	mkdir DHT22
	cd DHT22
	wget https://github.com/adafruit/Adafruit_Python_DHT/archive/master.zip
	unzip master.zip
	cd Adafruit_Python_DHT-master
	sudo python setup.py install
	cd /home/pi
fi
}


install_SPIlib ()
{


# --- INSTALL SPI library:

sudo apt-get -y install python2.7-dev 

# check if file exist in local folder
aconf="/home/pi/env/autonom/libraries/SPI/master.zip"
if [ -f $aconf ]; then

	cd /home/pi/env/autonom/libraries/SPI
	unzip master.zip
	cd py-spidev-master
	sudo python setup.py install
	cd /home/pi
else

cd /home/pi
sudo rm -r SPIDEV
mkdir SPIDEV
cd SPIDEV

wget https://github.com/Gadgetoid/py-spidev/archive/master.zip

unzip master.zip

rm master.zip

cd py-spidev-master

sudo python setup.py install

cd ..
cd ..

fi
}


install_BMPlib ()
{

# --- INSTALL BMP180 library (pressure sensor)

sudo apt-get -y install build-essential python-dev python-smbus


# check if file exist in local folder
aconf="/home/pi/env/autonom/libraries/BMP/master.zip"
if [ -f $aconf ]; then

	cd /home/pi/env/autonom/libraries/BMP
	unzip master.zip
	cd Adafruit_Python_BMP-master
	sudo python setup.py install
	cd /home/pi
else

cd /home/pi
sudo rm -r bmp180
sudo mkdir bmp180
cd bmp180
wget https://github.com/adafruit/Adafruit_Python_BMP/archive/master.zip
cd Adafruit_Python_BMP-master
sudo python setup.py install
cd ..
cd ..

fi
}


install_hydrosys4 ()
{
# --- INSTALL Hydrosys4 software
sudo apt-get -y install git


# check if file exist in local folder
aconf="/home/pi/env/autonom"
if [ -d $aconf ]; then  # if the directory exist
	cd /home/pi
else
	cd /home/pi
	sudo rm -r env
	mkdir env
	cd env
	sudo rm -r autonom
	git clone https://github.com/Hydrosys4/Master.git
	sudo killall python
	mv Master autonom
	cd ..

fi

}






fn_hostapd ()
{

sudo apt-get -y install hostapd	
	
	
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
wpa=3
wpa_passphrase=$WiFiAPpsw
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF


aconf="/etc/init.d/hostapd"
# Update hostapd main config file
sudo sed -i "s/\(^.*DAEMON_CONF=.*$\)/DAEMON_CONF=\/etc\/hostapd\/hostapd.conf/" $aconf

sudo systemctl enable hostapd.service 

}


fn_dnsmasq ()
{
	
sudo apt-get -y install dnsmasq

	
# edit /etc/dnsmasq.conf file
aconf="/etc/dnsmasq.conf"

# delete rows between #START and #END
sed -i '/^#START HYDROSYS4 SECTION/,/^#END HYDROSYS4 SECTION/{/^#START HYDROSYS4 SECTION/!{/^#END HYDROSYS4 SECTION/!d}}' $aconf
sed -i '/#START HYDROSYS4 SECTION/d' $aconf
sed -i '/#END HYDROSYS4 SECTION/d' $aconf



sudo bash -c "cat >> $aconf" << EOF
#START HYDROSYS4 SECTION
interface=wlan0
dhcp-range=192.168.0.100,192.168.0.200,12h
#no-resolv
#END HYDROSYS4 SECTION
EOF

sudo systemctl enable dnsmasq.service
 

}












install_mjpegstr ()
{
cd /home/pi

sudo rm -r mjpg-streamer

sudo apt-get -y install cmake libjpeg8-dev git

sudo git clone https://github.com/jacksonliam/mjpg-streamer.git

cd mjpg-streamer/mjpg-streamer-experimental

sudo make

sudo make install

cd ..
cd ..

}



install_nginx ()
{
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
    server_name localhost hydrosys4.local;

    access_log off;
    error_log off;

    location / {
        proxy_pass http://127.0.0.1:5020;
    }

    location /stream {
        rewrite ^/stream(.*) /$1 break;
        proxy_pass http://127.0.0.1:5022;
        proxy_buffering off;
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


# --- RUN the functions
killpython
input_UI
system_update_UI
install_dependencies
enable_I2C
modify_RClocal
fn_hostapd
fn_dnsmasq
install_mjpegstr
install_nginx
install_hydrosys4 # this should be called before the DHT22 , SPI and BMP due to local library references
install_DHT22lib
install_SPIlib
install_BMPlib
edit_defaultnetworkdb
edit_networkdb

sudo apt-get -y install fswebcam 

