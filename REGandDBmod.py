# in this modiule the register is created and the data is then send to  the DB.
# this module provides callback function to the modules that registers.


import logging
import actuatordbmod
import sensordbmod
import statusdataDBmod


logger = logging.getLogger("hydrosys4."+__name__)
REGISTER={}

callbacklist=[]

def register_input_value(name,value,saveonDB=True):
    print ("register calls here")
    statusdataDBmod.write_status_data(REGISTER,"input",name,value)
    for callback in callbacklist:
        print("start callback")
        callback("input",name,value)
    if saveonDB:
        sensordbmod.insertdataintable(name,value)


def register_output_value(name,value,saveonDB=True):
    statusdataDBmod.write_status_data(REGISTER,"output",name,value)
    for callback in callbacklist:
        callback("output",name,value)
    if saveonDB:
        if value=="ON":
            value="1"
        actuatordbmod.insertdataintable(name,value)

def register_callback(callback_func):
    print("append the callback ----------------------------")
    global callbacklist
    callbacklist.append(callback_func)

if __name__ == '__main__':
    
    print("Hello")
