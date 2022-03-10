import logging
import hardwaremod
import emailmod
import actuatordbmod
import autofertilizermod
import REGandDBmod


logger = logging.getLogger("hydrosys4."+__name__)

def activateactuator(target, value, command_override=""):  # return true in case the state change: activation is >0 or a different position from prevoius position.
    # all the transaction are supposed to be strings
    value=str(value)
    # check the actuator 
    isok=False
    out=""
    if not command_override:
        actuatortype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,target,hardwaremod.HW_CTRL_CMD)
        actuatortypelist=actuatortype.split("/")
        if actuatortypelist:
            actuatortype=actuatortypelist[0]
    else:
        actuatortype=command_override

    print (" Actuator " + actuatortype + "  target " +  target)
    supportedactuators=["pulse","servo","stepper"]
    # stepper motor
    if actuatortype=="stepper":
        out, isok = hardwaremod.GO_stepper_position(target,value)
        if isok:
            actuatordbmod.insertdataintable(target,value)

    # hbridge motor
    if actuatortype=="hbridge":
        realvalue=value
        isok=False
        out=""
        if value=="OPEN":
            realvalue=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, target, hardwaremod.HW_CTRL_MAX)

        elif value=="CLOSE":
            realvalue=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, target, hardwaremod.HW_CTRL_MIN)

        if value=="STOP":
            out, isok = hardwaremod.gpio_stop_hbridge(target) 
        else:
            out, isok = hardwaremod.GO_hbridge_position(target,realvalue)           
        if isok:
            REGandDBmod.register_output_value(target,out,saveonDB=True)
            
    # pulse
    if actuatortype=="pulse":
        duration=hardwaremod.toint(value,0)
        if value=="ON" or duration>0:
            if value=="ON":
                # act like a switch
                out, isok=hardwaremod.makepulse(target,value)
                # salva su database
                if isok:
                    REGandDBmod.register_output_value(target,value)

            else:
                # check the fertilizer doser flag before activating the pulse
                doseron=autofertilizermod.checkactivate(target,duration)
                # start pulse
                out, isok=hardwaremod.makepulse(target,value)
                # salva su database
                if isok:
                    REGandDBmod.register_output_value(target,value)
        else:
            if value=="OFF":
                out , isok =hardwaremod.switchOFF(target)
            else:
                out, isok =hardwaremod.stoppulse(target)

            print ("value is: ", value , " isOK :" , isok)   
            if isok:
                REGandDBmod.register_output_value(target,"0",saveonDB=False)

        
    # servo motor 
    if actuatortype=="servo":
        out, isok = hardwaremod.servoangle(target,value,0.5)
        if isok:
            actuatordbmod.insertdataintable(target,value)
            
    # photo 
    if actuatortype=="photo":
        duration=hardwaremod.toint(value,0)
        if duration>0:
            isok=hardwaremod.takephoto(True)
            # save action in database
            if isok:
                actuatordbmod.insertdataintable(target,1)	

    # mail 
    if (actuatortype=="mail+info+link")or(actuatortype=="mail+info"):
        duration=hardwaremod.toint(value,0)
        if duration>0:
            mailtext=value			
            isok=emailmod.sendmail(target,"info","Automation Value:" + mailtext)
            # save action in database
            if isok:
                actuatordbmod.insertdataintable(target,1)				
                
            
    return out , isok




if __name__ == '__main__':
    
    """
    prova functions
    """
    target="Relay1_1"
    value="10"


    
