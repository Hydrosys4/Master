
from GPIOEXPI2Ccontrol import toint
import hardwaremod
import HASSintegrMQTT
import json
import time
import REGandDBmod
import jsonFormUtils
import threading
import ActuatorControllermod
import statusdataDBmod

# Raspberry
HWCONTROLLIST=["tempsensor","humidsensor","pressuresensor","analogdigital","lightsensor","pulse","pinstate","servo",
"stepper","stepperstatus","photo","mail+info+link","mail+info","returnzero","stoppulse","readinputpin","hbridge","empty",
"DS18B20","Hygro24_I2C","HX711","SlowWire","InterrFreqCounter","WeatherAPI","BME280_temperature","BME280_humidity",
"BME280_pressure","BMP180_temperature","RPI_Core_temperature"]

# MQTT (the other not the HASSIO)
HWCONTROLLIST=["pulse/MQTT","stoppulse/MQTT","readinput/MQTT","pinstate/MQTT","hbridge/MQTT"]
# HC12 
HWCONTROLLIST=["readinput/HC12","pulse/HC12","stoppulse/HC12","pinstate/HC12"]

"""
Supported components

air_quality
alarm_control_panel
binary_sensor
camera
calendar
climate
conversation
cover
device_tracker
fan
light
lock
media_player
notify
remote
switch
sensor
vacuum
water_heater
weather
webhook

"""
Component={}
Component["sensor"]=["tempsensor","humidsensor","pressuresensor","analogdigital","lightsensor",
"DS18B20","Hygro24_I2C","HX711","SlowWire","InterrFreqCounter","WeatherAPI","BME280_temperature","BME280_humidity",
"BME280_pressure","BMP180_temperature","RPI_Core_temperature","readinput/HC12","readinput/MQTT",]
Component["binary_sensor"]=["pinstate","readinputpin"]
Component["switch"]=["pulse", "pulse/I2CGPIOEXP" , "pulse/HC12", "pulse/MQTT"]
Component["cover"]=["hbridge", "hbridge/I2CGPIOEXP" , "hbridge/MQTT"]

MEASURELIST=["Temperature", "Humidity" , "Light" , "Pressure" , "Time", "Quantity", "Moisture","Percentage","Events"]

device_class_sensor={}
device_class_sensor["temperature"]=["Temperature"]
device_class_sensor["humidity"]=["Humidity","Moisture"]
device_class_sensor["frequency"]=["InterrFreqCounter"]
device_class_sensor["voltage"]=["analogdigital"]
device_class_sensor["pressure"]=["Pressure"]
device_class_sensor["illuminance"]=["Light"]
device_class_sensor[""]=["Time", "Quantity","Percentage","Events"]


device_class_binary_sensor={}
device_class_binary_sensor["light"]=["Temperature"]
device_class_binary_sensor["moisture"]=["Humidity","Moisture"]
device_class_binary_sensor["light"]=["InterrFreqCounter"]
device_class_binary_sensor["light"]=["analogdigital"]
device_class_binary_sensor["light"]=["Pressure"]
device_class_binary_sensor["light"]=["Light"]
device_class_binary_sensor["light"]=["Time", "Quantity","Percentage","Events"]


MEASUREUNITLIST=["C", "%" , "Lum" , "hPa" , "Sec", "Pcs", "Volt","F"]

Trasnslate_units={"C":"°C", "%":"%"  , "Lum":"lm" , "hPa":"hPa"  , "Sec":"s", "Pcs":"", "Volt":"V","F":"°F"}


# <discovery_prefix>/<component>/[<node_id>/]<object_id>/config
Prefix="homeassistant"
NodeID="Hydrosys4"





"""
Example of sensor configuration

sensor:
  - platform: mqtt
    name: "Temperature"
    state_topic: "office/sensor1"
    unit_of_measurement: "°C"
    value_template: "{{ value_json.temperature }}"


'{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/binary_sensor/garden/state"}'

{
   "name":Name,
   "device_class":"temperature",
   "state_topic":State_topic,
   "unit_of_measurement":"°C",
   "value_template":"{{value_json.temperature}}"
}

# state_calss link:
# https://community.home-assistant.io/t/where-can-we-find-the-available-device-classes/121785/7


mosquitto_pub -h 192.168.1.96 -p 1883 -t "homeassistant/sensor/emon/power-import/config" -m '{"device_class" : "power","name" : "Imported power","state_topic" :"emon/power/import","unit_of_measurement" : "W"}'
"""





class HASS_entity_config:

    config_reg={}
    config_reg["default"]={"device":""}

    def __init__(self,dataManagement):
        
        self.dataManagement=dataManagement      
        self.datadict=dataManagement.readDataFile()
        # create an istance of the HASSintegrMQTT class
        self.MQTT_client=HASSintegrMQTT.HASS_Client(self.datadict)
        # register callback (when sensor data is updated, this callback is called)
        REGandDBmod.register_callback(self.send_state_data)
        self.register_received_msg()


    def subscribe_cmd_topics(self):
        # get all the outputs
        entity_list=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE, "output", hardwaremod.HW_INFO_NAME)
        for elem_name in entity_list:
            topics=self.create_topics(elem_name)
            if topics:
                # subscribe to the set topic
                cmd_topic=topics.get("cmd","")
                if cmd_topic:
                    for cmds in cmd_topic:
                        self.MQTT_client.subscribe(cmd_topic[cmds])

    def register_received_msg(self):
        self.MQTT_client.register_received_msg(self.exec_HASSIO_cmd)

    def exec_HASSIO_cmd(self,topic,msg,retained):
        # commands coming from HASSIO
        if self.datadict.get("Workmode","Disabled")=="Status+Commands":
            cmdexe=True
            print (" execute Hassio commands")
            print("Received Message from HASSIO ------ > toipc ", topic , " Message ", msg , " Retained ", retained)

            subtopic_list=topic.split("/")
            value=msg
            # translation required

            selcomponent=""
            if len(subtopic_list)>1:
                selcomponent=subtopic_list[1]

            # homeassistant/switch/Hydrosys4/water1/set
            
            if len(subtopic_list)>3:
                elem_name=subtopic_list[3]

                if selcomponent=="cover":
                    valueint=self.tonumber(value,-1)
                    if valueint>-1:
                        min_str=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_MIN)
                        max_str=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_MAX)
                        min=toint(min_str,0)
                        max=toint(max_str,100)
                        value=str(self.Cento_to_Range(valueint,min,max))
                    else: # value is not numerical ("STOP", "OPEN", "CLOSE")
                        if retained:
                            # do not execute the command
                            cmdexe=False
                            print ("do not execute")

                if cmdexe:
                    cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_CMD)
                    ActuatorControllermod.activateactuator(elem_name,value)      

                
                 

    def Cento_to_Range(self,valueint,min,max):
        return int(valueint*(max-min)/100 + min)

    def Range_to_Cento(self,valueint,min,max):
        return int((valueint-min)*100/(max-min))

    def tonumber(self,thestring, outwhenfail):
        try:
            n=float(thestring)
            return n
        except:
            return outwhenfail

    def check_loop_and_connect(self):
        curok , prevok = self.MQTT_client.check_loop_and_connect()
        print (" Connect test Loop =======>", curok , " previous ", prevok)
        if curok:
            if not prevok:
                self.subscribe_cmd_topics()
        return curok

    def connect_MQTT(self):
        self.MQTT_client.connect()

    def saveDataFileAndApply(self,datadict):
        if datadict:
            self.datadict=datadict
            self.dataManagement.saveDataFile(datadict)
            self.MQTT_client.check_changes_and_apply(datadict)
            return True
        return False    


    def send_state_data(self,element_type,elem_name,value):
        topics=self.create_topics(elem_name)
        if topics:
            state_topic_dict=topics.get("state")
            state_topic=state_topic_dict.get("state")
            selcomponent=topics.get("component")     
            

            isJson=True
            messages={}
            payload={elem_name:value}              
            messages[state_topic]=json.dumps(payload)
          
            if selcomponent=="binary_sensor":               
                if self.tonumber(value,0)>0:
                    payload={elem_name:"ON"}
                else:
                    payload={elem_name:"OFF"}
                messages[state_topic]=json.dumps(payload)

            elif selcomponent=="switch":
                valueint=self.tonumber(value,0)
                if value=="ON" or valueint>0:
                    payload={elem_name:"ON"}
                    if valueint>0:
                        # start the timer to set the OFF
                        NewthreadID=threading.Timer(valueint, self.send_state_data, [element_type , elem_name , "0" ])
                        NewthreadID.start()
                else:
                    payload={elem_name:"OFF"}
                messages[state_topic]=json.dumps(payload)

            elif selcomponent=="cover":
                position_topic=state_topic_dict.get("position")
                isJson=False
                valueint=self.tonumber(value,0)
                min_str=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_MIN)
                max_str=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_MAX)
                min=toint(min_str,0)
                max=toint(max_str,100)
                #print (" MINMAX " ,min_str, " ", max_str)
                valueint=self.Range_to_Cento(valueint,min,max)
                messages[position_topic]=json.dumps({"position":valueint})
                #messages[state_topic]={"value":"stopped"}
                del messages[state_topic]
                """
                cmd_topic_dict=topics.get("cmd")
                cmd_topic=cmd_topic_dict.get("cmd")
                cmd_topic_position=cmd_topic_dict.get("set_position")
                messages[cmd_topic]="STOP"
                messages[cmd_topic_position]=valueint
                """

            for item in messages:         
                topic=item
                payload=messages[item] 
                # here the MQTT part
                #print("Topic ", topic, " send payload to HASSIO: " , payload)
                self.MQTT_client.publish(topic,payload)


    def get_item_list(self):
        item_list=[]
        data=statusdataDBmod.read_status_levels(HASS_entity_config.config_reg,"device", True, "HASSIO_device_config")
        if data:
            for item in data: 
                item_list.append(item)
        return item_list       


    def remove_configuration(self,override_flag=False):
        # check if connection is UP
        isok=False
        if self.MQTT_client.ClientObj.connected:
            if (self.datadict.get("Discovery","No")=="Yes")or(override_flag):
                data=statusdataDBmod.read_status_levels(HASS_entity_config.config_reg,"device", True, "HASSIO_device_config")
                if data:
                    for item in data:
                        self.remove_item_config(data[item])
                    isok=True
                    return "Removed" , isok
                else:
                    return "No Stored configuration to remove", isok
        return "Not connected with the MQTT broker", isok

    def remove_item_config(self,item_info):
        isok=False
        topics=item_info.get("topics",{})
        config_topic=topics.get("config","")
        if config_topic:
            config_payload=''
            self.MQTT_client.publish(config_topic,json.dumps(config_payload))
            statusdataDBmod.remove_element_status_data(HASS_entity_config.config_reg,"device",True, "HASSIO_device_config")
            isok=True      
        return isok  


    def remove_and_update_config(self):
        print(" MQTT HASSIO Remove and Update config")
        if self.datadict.get("Discovery","No")=="Yes":
            isok = self.check_loop_and_connect()
            if isok:
                self.configure_and_remove_smart()
                self.subscribe_cmd_topics()


    def configure_and_remove_smart(self):
        isok=False
        if self.MQTT_client.ClientObj.connected:
            if (self.datadict.get("Discovery","No")=="Yes"):
                # get configurations sent to the Hassio
                data=statusdataDBmod.read_status_levels(HASS_entity_config.config_reg,"device", True, "HASSIO_device_config")
                # get all names in hardware table
                entity_list=hardwaremod.getItemlist(hardwaremod.HW_INFO_NAME)
                # update/create configuration
                for entity in entity_list:
                    print ("Send MQTT configuration ", entity)
                    HASSIOintegr.create_config_entity(entity)
                    # check if the item was already in previous configuration
                    if entity in data:
                        # remove from the list
                        del data[entity]
                # now remove the items belonging to the previous configuration but not present in current config
                for item in data:
                    self.remove_item_config(data[item])                
                isok=True
                return "Done, Refresh the Home assistant page", isok
        return "MQTT connection error", isok



    def configure_device(self, override_flag=False):

        # see this link for device configuration
        # https://community.home-assistant.io/t/mqtt-device-with-multiple-entities/224675/5
        isok=False

        if self.MQTT_client.ClientObj.connected:

            if (self.datadict.get("Discovery","No")=="Yes")or(override_flag):
                entity_list=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE, "input", hardwaremod.HW_INFO_NAME)
                for entity in entity_list:
                    print ("Send MQTT configuration ", entity)
                    HASSIOintegr.create_config_entity(entity)

                entity_list=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE, "output", hardwaremod.HW_INFO_NAME)
                for entity in entity_list:
                    print ("Send MQTT configuration  ", entity)
                    HASSIOintegr.create_config_entity(entity)
                
                #data=statusdataDBmod.read_status_levels(HASS_entity_config.config_reg,"device", True, "HASSIO_device_config")
                isok=True

                return "Done, Refresh the Home assistant page", isok
        return "MQTT connection error", isok


    def create_config_entity(self, elem_name):  # used for the MQTT Discovery
        if self.datadict.get("Discovery",""):
            topics=self.create_topics(elem_name)
            #print(topics)
            if topics:
                IOtype=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_INFO_IOTYPE)
                component=topics["component"]


                config_payload={}
                if component=="sensor":
                    config_payload=self.sensors_conf_payload(elem_name,topics)
                if component=="binary_sensor":
                    config_payload=self.binary_sensors_conf_payload(elem_name,topics)
                if component=="switch":
                    config_payload=self.switch_conf_payload(elem_name,topics)
                if component=="cover":
                    config_payload=self.cover_conf_payload(elem_name,topics)


                # here the MQTT part
                #print("Topic ", topics["config"], " send payload: " , config_payload)
                self.MQTT_client.publish(topics["config"],json.dumps(config_payload))

                data_to_store={"topics" : topics, "config_payload": config_payload}
                statusdataDBmod.write_status_data(HASS_entity_config.config_reg,"device", elem_name,data_to_store,permanent=True, storeid="HASSIO_device_config")

    def topic_list(self,elem_name):
        topic_list=[]
        if elem_name:
            data=statusdataDBmod.read_status_levels(HASS_entity_config.config_reg,"device", True, "HASSIO_device_config")
            if data:
                if elem_name in data:
                    topics=data[elem_name].get("topics",{})
                    topic_list.append(topics.get("config",""))
                    config_cmd=topics.get("cmd",{})
                    topic_list.append(config_cmd.get("cmd",""))
                    config_state=topics.get("state",{})
                    topic_list.append(config_state.get("state",""))

        return topic_list



    def configure_device_test(self):  # used for testing purposes only
        if self.datadict.get("Discovery",""):
            elem_name="prova_cover"
            # topics function
                
            cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_CMD)
            selcomponent=self.get_componenet(elem_name)

            selcomponent="cover"
            objectID=elem_name

            base_topic=Prefix+"/"+selcomponent+"/"+NodeID+"/"+objectID
            config_topic=base_topic+"/config"
            state_topic=base_topic+"/state"
            cmd_topic=base_topic+"/set"
            topics= {"component":selcomponent,"config":config_topic, "state":{"state":state_topic}, "cmd": {"cmd":cmd_topic}, "base":base_topic}
            
            #print(topics)
            if topics:
                
                component=selcomponent
                config_payload={}
                if component=="sensor":
                    config_payload=self.sensors_conf_payload(elem_name,topics)
                if component=="binary_sensor":
                    config_payload=self.binary_sensors_conf_payload(elem_name,topics)
                if component=="switch":
                    config_payload=self.switch_conf_payload(elem_name,topics)
                if component=="cover":
                    config_payload=self.cover_conf_payload(elem_name,topics)



                # here the MQTT part
                #print("Topic ", topics["config"], " send payload: " , config_payload)
                self.MQTT_client.publish(topics["config"],json.dumps(config_payload))

                data_to_store={"topics" : topics, "config_payload": config_payload}
                statusdataDBmod.write_status_data(HASS_entity_config.config_reg,"device", elem_name,data_to_store,permanent=True, storeid="HASSIO_device_config")



    def sensors_conf_payload(self,elem_name,topics):
        Name=elem_name
        cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_INFO_MEASURE)
        sel_device_class=""
        for item in device_class_sensor:
            if cmd in device_class_sensor[item]:
                sel_device_class=item
                break        
        state_topic=topics["state"]["state"]
        # measurement units
        unit=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_INFO_MEASUREUNIT)
        unit_of_measurement=Trasnslate_units[unit]
        device_name=self.datadict.get("Identifier","")

        payload={
                    "name":Name,
                    "device_class":sel_device_class,
                    "state_topic":state_topic,
                    "unit_of_measurement":unit_of_measurement,
                    "value_template":"{{value_json['"+Name+"']}}",
                    "unique_id": device_name + "-" + Name
                    #"device":{"name":device_name,"model":"aa","manufacturer":"daje","identifiers":["hydrosys4"]}
                }

        return payload

    def binary_sensors_conf_payload(self,elem_name,topics):
        Name=elem_name
        cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_INFO_MEASURE)
        sel_device_class=""
        for item in device_class_binary_sensor:
            if cmd in device_class_binary_sensor[item]:
                sel_device_class=item
                break        
        state_topic=topics["state"]["state"]
        # measurement units
        unit=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_INFO_MEASUREUNIT)
        unit_of_measurement=Trasnslate_units[unit]
        device_name=self.datadict.get("Identifier","")

        payload={
                    "name":Name,
                    "device_class":sel_device_class,
                    "state_topic":state_topic,
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "value_template":"{{value_json['"+Name+"']}}",
                    "unique_id":  device_name + "-" + Name
                    #"device":{"name":device_name,"model":"aa","manufacturer":"daje","identifiers":["hydrosys4"]}
                }

        return payload


    def switch_conf_payload(self,elem_name,topics):
        Name=elem_name
        state_topic=topics["state"]["state"]
        command_topic=topics["cmd"]["cmd"]
        # measurement units
        device_name=self.datadict.get("Identifier","")

        payload={
                    "name":Name,
                    "unique_id":  device_name + "-" + Name,
                    "state_topic":state_topic,
                    "command_topic":command_topic,
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "state_ON":"ON",
                    "state_OFF":"OFF",
                    "optimistic":False,
                    "value_template":"{{value_json['"+Name+"']}}",
                    "qos":0
                    #"device":{"name":device_name,"model":"aa","manufacturer":"daje","identifiers":["hydrosys4"]}
                }

        return payload



    def cover_conf_payload(self,elem_name,topics): # covers: uch as blinds, a roller shutter or a garage door
        Name=elem_name
        state_topic=topics["state"]["state"]
        command_topic=topics["cmd"]["cmd"]
        position_topic=topics["state"]["position"]
        set_position_topic=topics["cmd"]["set_position"]
        # measurement units
        device_name=self.datadict.get("Identifier","")
        minrange=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_MIN)
        maxrange=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_MAX)

        payload={
                    "name":Name,
                    "unique_id":  device_name + "-" + Name,
                    "state_topic":state_topic,
                    "command_topic":command_topic,
                    "value_template": "{{ value_json['value'] }}",
                    "position_topic": position_topic,
                    "set_position_topic" : set_position_topic,
                    "position_template":"{{value_json['position']}}",
                    "payload_open": "OPEN",
                    "payload_close": "CLOSE",
                    "payload_stop": "STOP",
                    "position_open": 100,
                    "position_closed": 0,
                    "optimistic":False,
                    "retain":True,
                    "qos":0
#"device":{"name":device_name,"model":"aa","manufacturer":"daje","identifiers":["hydrosys4"]}
                }

        return payload





    def get_componenet(self, elem_name):
        # understand the component from elem_name
        cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_CMD)
        selcomponent=""
        for item in Component:
            if cmd in Component[item]:
                selcomponent=item
                break
        return selcomponent

    def create_topics(self, elem_name):
        # understand the command from elem_name

        cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, elem_name, hardwaremod.HW_CTRL_CMD)
        selcomponent=self.get_componenet(elem_name)

        if not selcomponent:
            print("Error, no component identified for this command :", cmd )
            return {}

        objectID=elem_name

        base_topic=Prefix+"/"+selcomponent+"/"+NodeID+"/"+objectID

        # manage multiple topics beside the default
        topics={}

        topics["component"]=selcomponent
        topics["config"]=base_topic+"/config"
        topics["state"]={}
        topics["state"]["state"]=base_topic+ "/state"
        topics["cmd"]={}
        topics["cmd"]["cmd"]=base_topic + "/set"
        topics["base"]=base_topic

        if selcomponent=="cover":
            topics["state"]["position"]=base_topic+ "/position"
            topics["cmd"]["set_position"]=base_topic + "/position/set"


        return topics
    





# single instantiation

_FormAndSettingManagement=jsonFormUtils.utils('HASSIOform')
HASSIOintegr=HASS_entity_config(_FormAndSettingManagement)


if __name__ == "__main__":

    entity_list=cmd=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE, "input", hardwaremod.HW_INFO_NAME)
    for entity in entity_list:
        print ("Loop ", entity)
        HASSIOintegr.create_config_entity(entity)

    entity_list=cmd=hardwaremod.searchdatalist(hardwaremod.HW_CTRL_CMD, "pulse", hardwaremod.HW_INFO_NAME)
    for entity in entity_list:
        print ("Loop ", entity)
        HASSIOintegr.create_config_entity(entity)


