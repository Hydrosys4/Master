# Hydrosystem

The hydrosys4 project aim to create a platform for the raspbery pi 3 which let you easily controls and record sensors data, use actuators through the GPIO and play with analog by using external ADC the supported hardware and wiring can be found in the Documentation folder. The platform is developed in python and is based on web server interface. The system can control the WiFi interface and work either in Access point mode than connected to wifi network. The webserver interface can be adjusted to support several purposes, the current development is a small irrigation system, GIU is made to support planning and conditional irrigation based on temperature and humidity, relays control the valve and pumps, the system also support email notifications, cameras and video. Latest upgrade include possibility to mount camera over servo.
The SW platform is based on a web interface where the webserver is running locally on the raspberry. The SW is designed to be used with smartphone and to be reachable from internet without need of external servers or dynamic DNS. 
The basic concept is to develop a platoform for the internet of things which is not centralized, then to avoid extra fees, Static IP fees, Dynamic DNS fees. Every time the IP address is updated the system will send an email with relevant link to itself. 
NOTE: The mainstream IoT products relies on central server architecture which binds user to annual fees, the server is also a single point of failure and a poses high security problems. 
For the designed applications the supporting hardware platform and sensors are choosen to be inexpensive.

More details can be found on my webpage https://hydrosysblog.wordpress.com/

# Installation

For installation please follow the installation guide in the website:

https://hydrosysblog.wordpress.com/configuration/

two installation methods are possible:

1) For easy installation it is possible to directly download the SD image.

2) For a more traditional installation it is possible to download a bash installer 


# Access to the System

The systems run on the RPI3 which will act as access point, wait few seconds after the system is restarted, you will se a new wifi network. 
Once connected to the wifi network, open the webbrowser and type the address indicated in the guide.

https://hydrosysblog.wordpress.com/configuration/


# Login

the login credential are:
Username: admin
Password: default

it is strongly suggested to modify the password.


