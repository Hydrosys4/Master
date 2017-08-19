# Hydrosystem

The hydrosys4 project aim to create a platform for the raspbery pi 3 which let you easily controls and record sensors data, use actuators through the GPIO and play with analog by using external ADC the supported hardware and wiring can be found in the Documentation folder. The platform is developed in python and is based on web server interface. The system can control the WiFi interface and work either in Access point mode than connected to wifi network. The webserver interface can be adjusted to support several purposes, the current development is a small irrigation system, GIU is made to support planning and conditional irrigation based on temperature and humidity, relays control the valve and pumps, the system also support email notifications, cameras and video. Latest upgrade include possibility to mount camera over servo.
The SW platform is based on a web interface where the webserver is running locally on the raspberry. The SW is designed to be used with smartphone and to be reachable from internet without need of external servers or dynamic DNS. 
The basic concept is to develop a platoform for the internet of things which is not centralized, then to avoid extra fees, Static IP fees, Dynamic DNS fees. Every time the IP address is updated the system will send an email with relevant link to itself. 
NOTE: The mainstream IoT products relies on central server architecture which binds user to annual fees, the server is also a single point of failure and a poses high security problems. 
For the designed applications the supporting hardware platform and sensors are choosen to be inexpensive.

More details can be found on my webpage https://hydrosysblog.wordpress.com/

# Installation

For installation please download the installer in the bash folder and run it on the fresh installation of the raspbian jessie lite. Before installation please remember to enable the camera (if you are using the raspicam). Camera canbe enables using the raspi-config command and searching for camera.
Below the required steps to install the hydrosys4 on you jessie raspbian lite:

wget https://raw.githubusercontent.com/Hydrosys4/Master/master/bash/install_hydrosys4.sh

sudo chmod u+x install_hydrosys4.sh

sudo ./install_hydrosys4.sh

The installation will take same time.
During the installation the script will ask to confirm or modify the following parameters, please take note of them:
IP address (default: 192.168.0.172) NOTE: some wifi routers assigns the IP addressed starting from 192.168.1.xxx in this case it is suggested to change the IP address to 192.168.1.172.
port (default: 5012)
Wifi name (default: Hydrosys4)
Wifi password (default: hydrosystem)

when installation is completed, Reboot the system (or power off/on)

# Access to the System

The systems run on the RPI3 which can act as access point, wait few seconds after the system is restarted, you will se a new wifi network, the name is Hydrosys4 the Password is specified above, in case these values have been changed during installation the new values have to be used.
Once the network is connected, open any web browser and type the URL as follow:
192.168.0.172:5012 (please note that in case you have modified the IP address and port during the installation, you require to use the new values).

Great, now the hydrosys4 web interface should be up on your smartphone or PC.


# Login

the login credential are:
Username: admin
Password: default

it is strongly suggested to modify the password.

# First Setting

Even if not necessary, it is suggested to connect the system to your wifi network, in this case the system can enable the email alert feature and can be reaacheable from the internet. 
From the menu, go to the network page, the visible wifi networks will be listed.
Click on the network link and insert the passwrod. 
The system will now stop its own wifi network and connect to selected wifi.
Remark, in case the system lost the wifi connectivity it will restart its own wifi network.

for other settings and more complete information please conside to visi the site https://hydrosysblog.wordpress.com/
