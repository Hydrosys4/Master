import logging
import hardwaremod
import emailmod
import actuatordbmod
import autofertilizermod


logger = logging.getLogger("hydrosys4."+__name__)

def activateactuator(target, value):  # return true in case the state change: activation is >0 or a different position from prevoius position.
    # check the actuator 
    isok=False
    out=""
    actuatortype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,target,hardwaremod.HW_CTRL_CMD)
    actuatortypelist=actuatortype.split("/")
    if actuatortypelist:
        actuatortype=actuatortypelist[0]
    print (" Actuator " + actuatortype + "  target " +  target)
    supportedactuators=["pulse","servo","stepper"]
    # stepper motor
    if actuatortype=="stepper":
        out, isok = hardwaremod.GO_stepper_position(target,value)
        if isok:
            actuatordbmod.insertdataintable(target,value)

    # hbridge motor
    if actuatortype=="hbridge":
        out, isok = hardwaremod.GO_hbridge_position(target,value)
        if isok:
            actuatordbmod.insertdataintable(target,value)
            
    # pulse
    if actuatortype=="pulse":
        duration=hardwaremod.toint(value,0)
        # check the fertilizer doser flag before activating the pulse
        doseron=autofertilizermod.checkactivate(target,duration)
        # start pulse
        out, isok=hardwaremod.makepulse(target,duration)	
        # salva su database
        if isok:
            actuatordbmod.insertdataintable(target,duration)
        
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
        if value>0:
            mailtext=str(value)			
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


    
