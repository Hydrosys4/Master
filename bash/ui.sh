

#!/bin/bash


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


prova_UI ()
{

echo "Hello, following initial setting is requested:"



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

}



edit_defaultnetworkdb ()
{


aconf="/home/pi/env/autonom/database/default/defnetwork.txt "

# if file already exist then no action, otherwise create it
if [ -f $aconf ]; then
   echo "network default file already exist"
   else
   sudo bash -c "cat >> $aconf" << EOF
{"name": "IPsetting", "LocalIPaddress": "192.168.0.172", "LocalPORT": "5012"}
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
{"name": "IPsetting", "LocalIPaddress": "$IP", "LocalPORT": "$PORT"}
EOF


}


# --- RUN the functions

prova_UI
edit_defaultnetworkdb
edit_networkdb

