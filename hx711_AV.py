"""
This file holds HX711 class
Stripped down version of the original
"""
#!/usr/bin/env python
from __future__ import print_function

from builtins import range
from builtins import object
import time  # this is in python 2.7 which does not have the routine "time.perf_counter" in python 2.7 need a way to operate
import sys





try:
    # Python >= 3.3
    from time import perf_counter
    default_timer = time.perf_counter
    
except ImportError:
    # Python < 3.3
	if sys.platform == "win32":
		# On Windows, the best timer is time.clock()
		default_timer = time.clock
	else:
		# On most other platforms the best timer is time.time()
		default_timer = time.time

import RPi.GPIO as GPIO


class HX711(object):
    """
    HX711 represents chip for reading load cells.
    """

    def __init__(self,dout_pin,pd_sck_pin,gain_channel_A=128,select_channel='A'):
        """
        Init a new instance of HX711

        Args:
            dout_pin(int): Raspberry Pi pin number where the Data pin of HX711 is connected.
            pd_sck_pin(int): Raspberry Pi pin number where the Clock pin of HX711 is connected.
            gain_channel_A(int): Optional, by default value 128. Options (128 || 64) this is given as input by number the input clocks (25/26)
            select_channel(str): Optional, by default 'A'. Options ('A' || 'B')

        Raises:
            TypeError: if pd_sck_pin or dout_pin are not int type
        """
        if (isinstance(dout_pin, int)):
            if (isinstance(pd_sck_pin, int)):
                self._pd_sck = pd_sck_pin
                self._dout = dout_pin
            else:
                raise TypeError('pd_sck_pin must be type int. '
                                'Received pd_sck_pin: {}'.format(pd_sck_pin))
        else:
            raise TypeError('dout_pin must be type int. '
                            'Received dout_pin: {}'.format(dout_pin))

        # Setup of GPIO should come first
        GPIO.setup(self._pd_sck, GPIO.OUT)  # pin _pd_sck is output only
        GPIO.setup(self._dout, GPIO.IN)  # pin _dout is input only                            
        self._wanted_channel = ''
        self._current_channel = ''
        self._gain_channel_A = 0
        self._debug_mode = False
        self.select_channel(select_channel)
        self.set_gain_A(gain_channel_A)


    def select_channel(self, channel):
        """
        select_channel method evaluates if the desired channel
        is valid and then sets the _wanted_channel variable.

        Args:
            channel(str): the channel to select. Options ('A' || 'B')
        Raises:
            ValueError: if channel is not 'A' or 'B'
        """
        channel = channel.capitalize()
        if (channel == 'A'):
            self._wanted_channel = 'A'
        elif (channel == 'B'):
            self._wanted_channel = 'B'
        else:
            raise ValueError('Parameter "channel" has to be "A" or "B". '
                             'Received: {}'.format(channel))
        # after changing channel or gain it has to wait 50 ms to allow adjustment.
        # the data before is garbage and cannot be used.
        self.read()
        time.sleep(0.5)

    def set_gain_A(self, gain):
        """
        set_gain_A method sets gain for channel A.
        
        Args:
            gain(int): Gain for channel A (128 || 64)
        
        Raises:
            ValueError: if gain is different than 128 or 64
        """
        if gain == 128:
            self._gain_channel_A = gain
        elif gain == 64:
            self._gain_channel_A = gain
        else:
            raise ValueError('gain has to be 128 or 64. '
                             'Received: {}'.format(gain))
        # after changing channel or gain it has to wait 50 ms to allow adjustment.
        # the data before is garbage and cannot be used.
        self.read()
        time.sleep(0.5)



    def _ready(self):
        """
        _ready method check if data is prepared for reading from HX711

        Returns: bool True if ready else False when not ready        
        """
        # if DOUT pin is low data is ready for reading
        if GPIO.input(self._dout) == 0:
            return True
        else:
            return False

    def _set_channel_gain(self, num):
        """
        _set_channel_gain is called only from _read method.
        It finishes the data transmission for HX711 which sets
        the next required gain and channel.

        Args:
            num(int): how many ones it sends to HX711
                options (1 || 2 || 3)
        
        Returns: bool True if HX711 is ready for the next reading
            False if HX711 is not ready for the next reading
        """
        for _ in range(num):
            start_counter = default_timer()
            GPIO.output(self._pd_sck, True)
            GPIO.output(self._pd_sck, False)
            end_counter = default_timer()
            # check if hx 711 did not turn off...
            if end_counter - start_counter >= 0.00006:
                # if pd_sck pin is HIGH for 60 us and more than the HX 711 enters power down mode.
                if self._debug_mode:
                    print('Not enough fast while setting gain and channel')
                    print(
                        'Time elapsed: {}'.format(end_counter - start_counter))
                # hx711 has turned off. First few readings are inaccurate.
                # Despite it, this reading was ok and data can be used.
                result = self.get_raw_data_mean(6)  # set for the next reading.
                if result == False:
                    return False
        return True

    def read(self):
        """
        _read method reads bits from hx711, converts to INT
        and validate the data.
        
        Returns: (bool || int) if it returns False then it is false reading.
            if it returns int then the reading was correct
        """
        print('HX711 read function')
        GPIO.output(self._pd_sck, False)  # start by setting the pd_sck to 0
        ready_counter = 0
        while (not self._ready() and ready_counter <= 40):
            time.sleep(0.01)  # sleep for 10 ms because data is not ready
            ready_counter += 1
            if ready_counter == 50:  # if counter reached max value then return False
                if self._debug_mode:
                    print('self._read() not ready after 40 trials\n')
                return False, 0

        # read first 24 bits of data
        data_in = 0  # 2's complement data from hx 711
        for _ in range(24):
            start_counter = default_timer()
            # request next bit from hx 711
            GPIO.output(self._pd_sck, True)
            GPIO.output(self._pd_sck, False)
            end_counter = default_timer()
            if end_counter - start_counter >= 0.00006:  # check if the hx 711 did not turn off...
                # if pd_sck pin is HIGH for 60 us and more than the HX 711 enters power down mode.
                if self._debug_mode:
                    print('Not enough fast while reading data')
                    print('Time elapsed: {}'.format(end_counter - start_counter))
                return False,0
            # Shift the bits as they come to data_in variable.
            # Left shift by one bit then bitwise OR with the new bit.
            data_in = (data_in << 1) | GPIO.input(self._dout)

        if self._wanted_channel == 'A' and self._gain_channel_A == 128:
            if not self._set_channel_gain(1):  # send only one bit which is 1
                return False,0  # return False because channel was not set properly
            else:
                self._current_channel = 'A'  # else set current channel variable
                self._gain_channel_A = 128  # and gain
        elif self._wanted_channel == 'A' and self._gain_channel_A == 64:
            if not self._set_channel_gain(3):  # send three ones
                return False,0  # return False because channel was not set properly
            else:
                self._current_channel = 'A'  # else set current channel variable
                self._gain_channel_A = 64
        else:
            if not self._set_channel_gain(2):  # send two ones
                return False,0  # return False because channel was not set properly
            else:
                self._current_channel = 'B'  # else set current channel variable

        if self._debug_mode:  # print 2's complement value
            print('Binary value as received: {}\n'.format(bin(data_in)))

        #check if data is valid
        if (data_in == 0x7fffff
                or  # 0x7fffff is the highest possible value from hx711
                data_in == 0x800000
           ):  # 0x800000 is the lowest possible value from hx711
            if self._debug_mode:
                print('Invalid data detected: {}\n'.format(data_in))
            return False,0  # rturn false because the data is invalid

        # calculate int from 2's complement
        signed_data = 0
        # 0b1000 0000 0000 0000 0000 0000 check if the sign bit is 1. Negative number.
        if (data_in & 0x800000):
            signed_data = -(
                (data_in ^ 0xffffff) + 1)  # convert from 2's complement to int
        else:  # else do not do anything the value is positive number
            signed_data = data_in

        if self._debug_mode:
            print('Converted 2\'s complement value: {}\n'.format(signed_data))

        return True, signed_data



    def get_current_channel(self):
        """
        get current channel returns the value of current channel.

        Returns: ('A' || 'B')
        """
        return self._current_channel


    def get_current_gain_A(self):
        """
        get current gain A returns the value of current gain on channel A

        Returns: (128 || 64) current gain on channel A
        """
        return self._gain_channel_A



    def power_down(self):
        """
        power down method turns off the hx711.
        """
        GPIO.output(self._pd_sck, False)
        GPIO.output(self._pd_sck, True)
        time.sleep(0.01)

    def power_up(self):
        """
        power up function turns on the hx711.
        """
        GPIO.output(self._pd_sck, False)
        time.sleep(0.01)

    def reset(self):
        """
        reset method resets the hx711 and prepare it for the next reading.

        Returns: True if error encountered
        """
        self.power_down()
        self.power_up()
        result = self.get_raw_data_mean(6)
        if result:
            return False
        else:
            return True

