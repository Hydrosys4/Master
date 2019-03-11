# ============================================================================
# Adafruit PCA9685 16-Channel PWM Servo Driver
# ============================================================================
import logging
import math
import time


logger = logging.getLogger(__name__)


def get_i2c_device(address, i2c, i2c_bus):
    # Helper method to get a device at the specified address from the I2C bus.
    # If no i2c bus is specified (i2c param is None) then the default I2C bus
    # for the platform will be used.
    if i2c is not None:
        return i2c.get_i2c_device(address)
    else:
        import Adafruit_GPIO.I2C as I2C
        if i2c_bus is None:
            return I2C.get_i2c_device(address)
        else:
            return I2C.get_i2c_device(address, busnum=i2c_bus)


class PWM(object):
    # Registers/etc.
    __MODE1              = 0x00
    __MODE2              = 0x01
    __SUBADR1            = 0x02
    __SUBADR2            = 0x03
    __SUBADR3            = 0x04
    __PRESCALE           = 0xFE
    __LED0_ON_L          = 0x06
    __LED0_ON_H          = 0x07
    __LED0_OFF_L         = 0x08
    __LED0_OFF_H         = 0x09
    __ALL_LED_ON_L       = 0xFA
    __ALL_LED_ON_H       = 0xFB
    __ALL_LED_OFF_L      = 0xFC
    __ALL_LED_OFF_H      = 0xFD

    # Bits
    __RESTART            = 0x80
    __SLEEP              = 0x10
    __ALLCALL            = 0x01
    __INVRT              = 0x10
    __OUTDRV             = 0x04
    
    regvals = {} # new code from me

    @classmethod
    def softwareReset(cls, i2c=None, i2c_bus=None):
        "Sends a software reset (SWRST) command to all the servo drivers on the bus"
        general_call_i2c = get_i2c_device(0x00, i2c, i2c_bus)
        general_call_i2c.writeRaw8(0x06)        # SWRST

    def __init__(self, address=0x40, debug=False, i2c=None, i2c_bus=None):
        self.i2c = get_i2c_device(address, i2c, i2c_bus)
        logger.debug("Reseting PCA9685 MODE1 (without SLEEP) and MODE2")
        self.setAllPWM(0, 0)
        self.write8my(self.__MODE2, self.__OUTDRV)
        self.write8my(self.__MODE1, self.__ALLCALL)
        time.sleep(0.005)                             # wait for oscillator
        mode1 = self.i2c.readU8(self.__MODE1)
        mode1 = mode1 & ~self.__SLEEP                 # wake up (reset sleep)
        self.write8my(self.__MODE1, mode1)
        time.sleep(0.005)                             # wait for oscillator



    def setPWMFreq(self, freq):
        "Sets the PWM frequency"
        prescaleval = 25000000.0    # 25MHz
        prescaleval /= 4096.0       # 12-bit
        prescaleval /= float(freq)
        prescaleval -= 1.0
        logger.debug("Setting PWM frequency to %d Hz" % freq)
        logger.debug("Estimated pre-scale: %d" % prescaleval)
        prescale = math.floor(prescaleval + 0.5)
        logger.debug("Final pre-scale: %d" % prescale)
        oldmode = self.i2c.readU8(self.__MODE1);
        newmode = (oldmode & 0x7F) | 0x10             # sleep
        self.write8my(self.__MODE1, newmode)        # go to sleep
        self.write8my(self.__PRESCALE, int(math.floor(prescale)))
        self.write8my(self.__MODE1, oldmode)
        time.sleep(0.005)
        self.write8my(self.__MODE1, oldmode | 0x80)

    def setPWM(self, channel, on, off):  # got here finally ---------------------------
        "Sets a single PWM channel"
        self.write8my(self.__LED0_ON_L+4*channel, on & 0xFF)
        self.write8my(self.__LED0_ON_H+4*channel, on >> 8)
        self.write8my(self.__LED0_OFF_L+4*channel, off & 0xFF)
        self.write8my(self.__LED0_OFF_H+4*channel, off >> 8)

    def setAllPWM(self, on, off):
        "Sets a all PWM channels"
        self.write8my(self.__ALL_LED_ON_L, on & 0xFF)
        self.write8my(self.__ALL_LED_ON_H, on >> 8)
        self.write8my(self.__ALL_LED_OFF_L, off & 0xFF)
        self.write8my(self.__ALL_LED_OFF_H, off >> 8)

    def write8my(self, reg, value): # new function created by me to optimize the I2C traffic speed up about 5 times the stepper speed!
		if reg not in self.regvals:
			self.i2c.write8(reg, value)		
			self.regvals[reg] = value
		else:
			if self.regvals[reg] != value:
				self.i2c.write8(reg, value)		
				self.regvals[reg] = value
			#else:
			#	print "no need to transfer on I2C"



class Adafruit_StepperMotor:
    MICROSTEPS = 8
    MICROSTEP_CURVE = [0, 50, 98, 142, 180, 212, 236, 250, 255]

    #MICROSTEPS = 16
    # a sinusoidal curve NOT LINEAR!
    #MICROSTEP_CURVE = [0, 25, 50, 74, 98, 120, 141, 162, 180, 197, 212, 225, 236, 244, 250, 253, 255]

    def __init__(self, controller, num, steps=200):
        self.MC = controller
        self.revsteps = steps
        self.motornum = num
        self.sec_per_step = 0.1
        self.steppingcounter = 0
        self.currentstep = 0

        num -= 1

        if (num == 0):
            self.PWMA = 8
            self.AIN2 = 9
            self.AIN1 = 10
            self.PWMB = 13
            self.BIN2 = 12
            self.BIN1 = 11
        elif (num == 1):
            self.PWMA = 2
            self.AIN2 = 3
            self.AIN1 = 4
            self.PWMB = 7
            self.BIN2 = 6
            self.BIN1 = 5
        else:
            raise NameError('MotorHAT Stepper must be between 1 and 2 inclusive')

    def setSpeed(self, rpm):
        self.sec_per_step = 60.0 / (self.revsteps * rpm)
        self.steppingcounter = 0

    def oneStep(self, dir, style):
        pwm_a = pwm_b = 255

        # first determine what sort of stepping procedure we're up to
        if (style == Adafruit_MotorHAT.SINGLE):
            if ((self.currentstep//(self.MICROSTEPS//2)) % 2):
                # we're at an odd step, weird
                if (dir == Adafruit_MotorHAT.FORWARD):
                    self.currentstep += self.MICROSTEPS//2
                else:
                    self.currentstep -= self.MICROSTEPS//2
            else:
                # go to next even step
                if (dir == Adafruit_MotorHAT.FORWARD):
                    self.currentstep += self.MICROSTEPS
                else:
                    self.currentstep -= self.MICROSTEPS
        if (style == Adafruit_MotorHAT.DOUBLE):
            if not (self.currentstep//(self.MICROSTEPS//2) % 2):
                # we're at an even step, weird
                if (dir == Adafruit_MotorHAT.FORWARD):
                    self.currentstep += self.MICROSTEPS//2
                else:
                    self.currentstep -= self.MICROSTEPS//2
            else:
                # go to next odd step
                if (dir == Adafruit_MotorHAT.FORWARD):
                    self.currentstep += self.MICROSTEPS
                else:
                    self.currentstep -= self.MICROSTEPS
        if (style == Adafruit_MotorHAT.INTERLEAVE):
            if (dir == Adafruit_MotorHAT.FORWARD):
                self.currentstep += self.MICROSTEPS//2
            else:
                self.currentstep -= self.MICROSTEPS//2

        if (style == Adafruit_MotorHAT.MICROSTEP):
            if (dir == Adafruit_MotorHAT.FORWARD):
                self.currentstep += 1
            else:
                self.currentstep -= 1

                # go to next 'step' and wrap around
                self.currentstep += self.MICROSTEPS * 4
                self.currentstep %= self.MICROSTEPS * 4

            pwm_a = pwm_b = 0
            if (self.currentstep >= 0) and (self.currentstep < self.MICROSTEPS):
                pwm_a = self.MICROSTEP_CURVE[self.MICROSTEPS - self.currentstep]
                pwm_b = self.MICROSTEP_CURVE[self.currentstep]
            elif (self.currentstep >= self.MICROSTEPS) and (self.currentstep < self.MICROSTEPS*2):
                pwm_a = self.MICROSTEP_CURVE[self.currentstep - self.MICROSTEPS]
                pwm_b = self.MICROSTEP_CURVE[self.MICROSTEPS*2 - self.currentstep]
            elif (self.currentstep >= self.MICROSTEPS*2) and (self.currentstep < self.MICROSTEPS*3):
                pwm_a = self.MICROSTEP_CURVE[self.MICROSTEPS*3 - self.currentstep]
                pwm_b = self.MICROSTEP_CURVE[self.currentstep - self.MICROSTEPS*2]
            elif (self.currentstep >= self.MICROSTEPS*3) and (self.currentstep < self.MICROSTEPS*4):
                pwm_a = self.MICROSTEP_CURVE[self.currentstep - self.MICROSTEPS*3]
                pwm_b = self.MICROSTEP_CURVE[self.MICROSTEPS*4 - self.currentstep] 


        # go to next 'step' and wrap around
        self.currentstep += self.MICROSTEPS * 4 #??
        self.currentstep %= self.MICROSTEPS * 4

        # only really used for microstepping, otherwise always on!
        self.MC._pwm.setPWM(self.PWMA, 0, pwm_a*16)  #
        self.MC._pwm.setPWM(self.PWMB, 0, pwm_b*16)

        # set up coil energizing!
        coils = [0, 0, 0, 0]

        if (style == Adafruit_MotorHAT.MICROSTEP):
            if (self.currentstep >= 0) and (self.currentstep < self.MICROSTEPS):
                coils = [1, 1, 0, 0]
            elif (self.currentstep >= self.MICROSTEPS) and (self.currentstep < self.MICROSTEPS*2):
                coils = [0, 1, 1, 0]
            elif (self.currentstep >= self.MICROSTEPS*2) and (self.currentstep < self.MICROSTEPS*3):
                coils = [0, 0, 1, 1]
            elif (self.currentstep >= self.MICROSTEPS*3) and (self.currentstep < self.MICROSTEPS*4):
                coils = [1, 0, 0, 1]
        else:
            step2coils = [     [1, 0, 0, 0],
                [1, 1, 0, 0],
                [0, 1, 0, 0],
                [0, 1, 1, 0],
                [0, 0, 1, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 1],
                [1, 0, 0, 1] ]
            coils = step2coils[self.currentstep//(self.MICROSTEPS//2)]

        #print "coils state = " + str(coils)
        self.MC.setPin(self.AIN2, coils[0])  # this call the setPIN which then call the pwm class
        self.MC.setPin(self.BIN1, coils[1])
        self.MC.setPin(self.AIN1, coils[2])
        self.MC.setPin(self.BIN2, coils[3])

        return self.currentstep

    def step(self, steps, direction, stepstyle):
        s_per_s = self.sec_per_step
        lateststep = 0

        if (stepstyle == Adafruit_MotorHAT.INTERLEAVE):
            s_per_s = s_per_s / 2.0
        if (stepstyle == Adafruit_MotorHAT.MICROSTEP):
            s_per_s /= self.MICROSTEPS
            steps *= self.MICROSTEPS

        print("{} sec per step".format(s_per_s))

        for s in range(steps): #--------------------------------------------------------------- cycle on steps
            lateststep = self.oneStep(direction, stepstyle)
            time.sleep(s_per_s)

        if (stepstyle == Adafruit_MotorHAT.MICROSTEP):
            # this is an edge case, if we are in between full steps, lets just keep going
            # so we end on a full step
            while (lateststep != 0) and (lateststep != self.MICROSTEPS):
                lateststep = self.oneStep(direction, stepstyle)
                time.sleep(s_per_s)

class Adafruit_DCMotor:
    def __init__(self, controller, num):
        self.MC = controller
        self.motornum = num
        pwm = in1 = in2 = 0

        if (num == 0):
                 pwm = 8
                 in2 = 9
                 in1 = 10
        elif (num == 1):
                 pwm = 13
                 in2 = 12
                 in1 = 11
        elif (num == 2):
                 pwm = 2
                 in2 = 3
                 in1 = 4
        elif (num == 3):
                 pwm = 7
                 in2 = 6
                 in1 = 5
        else:
            raise NameError('MotorHAT Motor must be between 1 and 4 inclusive')
        self.PWMpin = pwm
        self.IN1pin = in1
        self.IN2pin = in2

    def run(self, command):
        if not self.MC:
            return
        if (command == Adafruit_MotorHAT.FORWARD):
            self.MC.setPin(self.IN2pin, 0)
            self.MC.setPin(self.IN1pin, 1)
        if (command == Adafruit_MotorHAT.BACKWARD):
            self.MC.setPin(self.IN1pin, 0)
            self.MC.setPin(self.IN2pin, 1)
        if (command == Adafruit_MotorHAT.RELEASE):
            self.MC.setPin(self.IN1pin, 0)
            self.MC.setPin(self.IN2pin, 0)
    def setSpeed(self, speed):
        if (speed < 0):
            speed = 0
        if (speed > 255):
            speed = 255
        self.MC._pwm.setPWM(self.PWMpin, 0, speed*16)


class Adafruit_MotorHAT:
    FORWARD = 1
    BACKWARD = 2
    BRAKE = 3
    RELEASE = 4

    SINGLE = 1
    DOUBLE = 2
    INTERLEAVE = 3
    MICROSTEP = 4

    def __init__(self, addr = 0x60, freq = 1600, i2c=None, i2c_bus=None):
        self._frequency = freq
        self.motors = [ Adafruit_DCMotor(self, m) for m in range(4) ]
        self.steppers = [ Adafruit_StepperMotor(self, 1), Adafruit_StepperMotor(self, 2) ]
        self._pwm = PWM(addr, debug=False, i2c=i2c, i2c_bus=i2c_bus)
        self._pwm.setPWMFreq(self._frequency)

    def setPin(self, pin, value):
        if (pin < 0) or (pin > 15):
            raise NameError('PWM pin must be between 0 and 15 inclusive')
        if (value != 0) and (value != 1):
            raise NameError('Pin value must be 0 or 1!')
        if (value == 0):
            self._pwm.setPWM(pin, 0, 4096)
        if (value == 1):
            self._pwm.setPWM(pin, 4096, 0)

    def getStepper(self, steps, num):
        if (num < 1) or (num > 2):
            raise NameError('MotorHAT Stepper must be between 1 and 2 inclusive')
        return self.steppers[num-1]

    def getMotor(self, num):
        if (num < 1) or (num > 4):
            raise NameError('MotorHAT Motor must be between 1 and 4 inclusive')
        return self.motors[num-1]

    def reset(self):
        self._pwm.softwareReset()
