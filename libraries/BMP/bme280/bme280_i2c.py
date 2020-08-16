# -*- coding: utf-8 -*-



try:
    import smbus
except ImportError:
    smbus = None

default_i2c_address = None
default_bus_number = None
default_bus = None


def set_default_i2c_address(i2c_address):
    global default_i2c_address
    default_i2c_address = i2c_address

def set_default_bus_number(bus_number):
    global default_bus_number
    default_bus_number=bus_number

def create_bus(i2c_address,bus_number):
    global default_bus
    global default_bus_number    
    global default_i2c_address    

    default_i2c_address = i2c_address
    default_bus_number=bus_number
        
    if smbus is None:
        print('smbus is not available, please ensure it is installed correctly')
        return False
    if default_bus is None:
        default_bus = smbus.SMBus(default_bus_number)
    return True


def read_byte_data(cmd, bus=None, i2c_address=None):
    isok=False
    if bus is None:
        bus = default_bus
    if i2c_address is None:
        i2c_address = default_i2c_address    
    try:
        read=bus.read_byte_data(i2c_address, cmd)
        isok=True
    except:
        read=0		
    return isok, read


def write_byte_data(cmd, value, bus=None, i2c_address=None):
    isok=False
    if bus is None:
        bus = default_bus
    if i2c_address is None:
        i2c_address = default_i2c_address
    try:
        result=bus.write_byte_data(i2c_address, cmd, value)
        isok=True
    except:
        result=0 		    
    #print(isok, hex(i2c_address), hex(cmd), hex(value))        
    return isok
