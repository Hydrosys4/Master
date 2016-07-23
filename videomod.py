import time
from time import sleep
import datetime
import os
import sys

from subprocess import Popen, PIPE


def StartServerTimer(lasttime):
        shottaken=False
        currentdate=datetime.datetime.now().strftime("%y-%m-%d-%H:%M")
        print "Current date and time: " , currentdate

        myproc = Popen('mjpg_streamer -i "/usr/lib/input_uvc.so -d /dev/video0 -r 320x240 -f 15" -o "/usr/lib/output_http.so -p 8090 -w /usr/www"', shell=True, stdout=PIPE, stderr=PIPE)

        #sleep(10)
        print myproc.stdout.readline()
        print 'Return code was ', myproc.returncode
        sleep(2)


        return shottaken

def StopServerTimer(lasttime):
        shottaken=False
        currentdate=datetime.datetime.now().strftime("%y-%m-%d-%H:%M")
        print "Current date and time: " , currentdate

        myproc = Popen('killall mjpg_streamer', shell=True, stdout=PIPE, stderr=PIPE)

        #sleep(10)
        print myproc.stdout.readline()
        print 'Return code was ', myproc.returncode
        sleep(2)


        return shottaken


if __name__ == '__main__':

        """
        prova funzioni di video
        """
        StartServerTimer(10)



