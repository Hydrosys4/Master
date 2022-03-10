from faulthandler import is_enabled
import hardwaremod
import time, logging
import statusdataDBmod
from datetime import datetime,date,timedelta

# import paho library only if installed, then set the flag MQTTlib
try:
  __import__("paho")
except:
  MQTTlib=False
else:
  MQTTlib=True	
  import paho.mqtt.client as mqtt

logger = logging.getLogger("hydrosys4."+__name__)




class HASS_Client:

    ClientObj=None
    Workmode="Disabled"

    def __init__(self, datadict):

        self.get_HASS_client_info(datadict)
     
        HASS_Client.ClientObj=MQTT_Client_Management(self.clientid)

        HASS_Client.ClientObj.set_parameters(host=self.host, port=self.port, cleanstart=self.cleanstart,
              keepalive=self.keepalive, newsocket=self.newsocket, protocolName=self.protocolName,
              willFlag=False, willTopic=None, willMessage=None, willQoS=2, willRetain=False, 
              username=self.username, password=self.password)

    def register_received_msg(self,callbeckfunc):
        MQTT_Client_Management.on_message_callback = callbeckfunc

    def is_enabled(self):
        if HASS_Client.Workmode=="Disabled":
          return False
        return True

    def is_send_state(self):
      if self.is_enabled():
        if (HASS_Client.Workmode=="Status") or (HASS_Client.Workmode=="Status+Commands"):
          return True
      return False    

    def is_get_command(self):
      if self.is_enabled():
        if HASS_Client.Workmode=="Status+Commands":
          return True
      return False 


    def connect(self):
      if self.is_enabled():
        isok=HASS_Client.ClientObj.connect() 

    def disconnect(self):
      HASS_Client.ClientObj.disconnect() 

    def subscribe(self, topic):
      if self.is_get_command():
        isok=HASS_Client.ClientObj.connect() 
        HASS_Client.ClientObj.subscribe(topic, qos=2)

    def publish(self, topic, payload):
      if self.is_send_state():
        isok=HASS_Client.ClientObj.connect() 
        HASS_Client.ClientObj.publish(topic, payload) 

    def check_loop_and_connect(self):
      if self.is_enabled():
        return HASS_Client.ClientObj.check_loop_and_connect(self.testtopic)
      return True, True

    def check_changes_and_apply(self,datadict):

      # special case Enable or disable
      reset_connection=False
      disconnect=False

      print (" WorkMode ", datadict.get("Workmode","Disabled"))

      if (HASS_Client.Workmode=="Disabled")and(datadict.get("Workmode","Disabled")!="Disabled"):
         reset_connection=True
      if (HASS_Client.Workmode!="Disabled")and(datadict.get("Workmode","Disabled")=="Disabled"):
         disconnect=True

      HASS_Client.Workmode=datadict.get("Workmode","Disabled")
      if disconnect:
        print("disconnect")
        self.disconnect()

      # this is the case where Workmode is not Disabled
      if self.is_enabled():

        if datadict:

          if not self.host==datadict.get("Host"):
            reset_connection=True

          if not self.port==int(datadict.get("Port")):
            reset_connection=True

          if not self.username==datadict.get("Username"):
            reset_connection=True

          if not self.password==datadict.get("Password"):
            reset_connection=True

          if reset_connection:
            print(" Need to reset connection")
            HASS_Client.ClientObj.disconnect(ignore_feedback=True) 
            self.get_HASS_client_info(datadict)
            HASS_Client.ClientObj.set_parameters(host=self.host, port=self.port, cleanstart=self.cleanstart,
                  keepalive=self.keepalive, newsocket=self.newsocket, protocolName=self.protocolName,
                  willFlag=False, willTopic=None, willMessage=None, willQoS=2, willRetain=False, 
                  username=self.username, password=self.password)
            self.connect()


    def get_HASS_client_info(self,datadict):
        
        # load info from configuration flie

        HASS_Client.Workmode=datadict.get("Workmode", "Disabled")

        clientID="HASSIO"+str(time.time()) # it is necessary to ensure that the clientID is unique. 
        self.clientid = clientID
        self.host=datadict.get("Host","")
        self.port=int(datadict.get("Port",0))
        self.cleanstart=True
        self.keepalive=180
        self.newsocket=True
        self.protocolName=None
        self.username=datadict.get("Username","")
        self.password=datadict.get("Password","")
        self.testtopic=datadict.get("Identifier","")+"/testloop"
        #print(self.host," ", self.port," ",self.username," ",self.password)


 
class MQTT_Client_Management:

  MQTTregister={}
  on_message_callback = None

  def __init__(self, clientid):
    self.clientid = clientid
    # auxiliary variables
    self.connected=False     
    # create paho client, associate the callbacks
    self.clientobj=mqtt.Client(clientid) # create client object

    self.clientobj.on_message = self.on_message
    self.clientobj.on_connect = self.on_connect
    self.clientobj.on_disconnect = self.on_disconnect
    self.clientobj.on_publish = self.on_publish
    self.clientobj.on_subscribe = self.on_subscribe


  def set_parameters(self,host="localhost", port=1883, cleanstart=True, keepalive=180, newsocket=True, protocolName=None,
              willFlag=False, willTopic=None, willMessage=None, willQoS=2, willRetain=False, username=None, password=None,
              properties=None, willProperties=None):
    self.host=host
    self.port=port
    self.cleanstart=cleanstart
    self.keepalive=keepalive
    self.newsocket=newsocket
    self.protocolName=protocolName
    self.username=username
    self.password=password


#  @staticmethod
  def on_connect(self,mqttc, obj, flags, rc):
    self.registerwrite("on_connect","answer",str(rc))
    if rc==0:
      self.connected=True
      print(self.clientid + "  " + "Connection Succesfull")		
    """
    RC values:
    0: Connection successful
    1: Connection refused – incorrect protocol version
    2: Connection refused – invalid client identifier
    3: Connection refused – server unavailable
    4: Connection refused – bad username or password
    5: Connection refused – not authorised
    """
  
  
  def on_disconnect(self, mqttc, obj, rc):
    self.registerwrite("on_disconnect","answer",str(rc))
    if rc==0:
      self.connected=False
      print(self.clientid + "  " + "Disconnection Succesfull")	 
    
       
  def on_message(self,mqttc, obj, msg):
    payload=msg.payload.decode('utf-8')
    self.registerwrite("on_message",msg.topic,payload)
    print("ON-Message: Topic-->" , msg.topic, " payload -->", payload)
    if MQTT_Client_Management.on_message_callback:
      MQTT_Client_Management.on_message_callback(msg.topic,payload,msg.retain)
    else:
      print(" NO callback for on_message  ***")
    

  def on_publish(self,mqttc, obj, mid):
    self.registerwrite("on_publish","mid",str(mid))
    print("ON-Publish: " , self.registerread("on_publish"))

  def on_subscribe(self,mqttc, obj, mid, granted_qos):
    self.registerwrite("on_subscribe","mid",str(mid))

  def on_log(self, mqttc, obj, level, string):
    print(self.clientid + "  " +string)
    

  def registerwrite(self, call, infotype,data):
      if call not in self.MQTTregister:
        self.MQTTregister[call]={}
        if infotype not in self.MQTTregister[call]:
            self.MQTTregister[call][infotype]={}
      self.MQTTregister[call][infotype]=data
      self.MQTTregister[call]["timestamp"]=timestamp=datetime.utcnow()
      return

  def registerread(self, call, infotype=""):
      data={}
      if infotype: 
          if (call in self.MQTTregister):
              if infotype in self.MQTTregister[call]:
                data=self.MQTTregister[call][infotype]
      else:
        if (call in self.MQTTregister):
            data=self.MQTTregister[call]
      
      return data


  def check_loop_and_connect(self,topic):
    current_connect=False
    previous_connect=False
    if not self.connected:
      if not self.connect():
        return current_connect , previous_connect
      else:
        current_connect=True
        return current_connect , previous_connect
    
    self.clientobj.subscribe(topic)
    payload="test"+str(time.time())
    self.clientobj.publish(topic,payload)
    # wait for Answer Message
    waitsec=5
    while (not self.registerread("on_message",topic)==payload) and (waitsec>0):
        time.sleep(1)
        waitsec=waitsec-1
    if not self.registerread("on_message",topic)==payload:
        logger.error("MQTT Test Loop Failed , Try to reconnect")
        print("MQTT Test Loop Failed, Try to reconnect")
        # try to connect as last attempt
        isok= self.connect(ignore_connected=True,ignore_feedback=False)
        if not isok:
          logger.error("MQTT not able to recover connection")
          print("MQTT not able to recover connection")
          return current_connect , previous_connect
        else:
          logger.error("MQTT able to recover connection")
          print("MQTT able to recover connection")
          current_connect=True
          return current_connect , previous_connect
    
    current_connect=True
    previous_connect=True
    logger.info("MQTT Test Loop passed")
    print("MQTT Test Loop passed")
    return current_connect , previous_connect


  def connect(self,ignore_connected=False, ignore_feedback=False):
    if self.connected and not ignore_connected:
        #logger.warning("already connected, no action")
        #print("already connected, no action")
        return False
    try:
      if self.password and self.username:
        self.clientobj.username_pw_set(username=self.username, password=self.password)
      self.clientobj.connect(host=self.host, port=self.port, keepalive=self.keepalive) # connection
      self.clientobj.loop_start() # start loop to enable the callbacks
    except:
      print ("MQTT connection Failed "  + self.clientid)
      logger.error("MQTT Connection failed")
      return False
    
    # wait for broker confirmation
    if not ignore_feedback:
      waitsec=5
      while (not self.connected) and (waitsec>0):
          time.sleep(1)
          waitsec=waitsec-1
      if not self.connected:
          logger.warning("Not able to connect to MQTT broker, no feedback")
          print("Not able to connect to MQTT broker, no feedback")
          return False
    return True



  def subscribe(self, topic="", options=None, properties=None, qos=2):
    if topic=="":
      return		
    print("try to su scribe " + topic)
    self.clientobj.subscribe(topic, qos)

  def unsubscribe(self, topic):
    self.clientobj.unsubscribe(topic)


  def publish(self, topic, payload, qos=0, retained=False, properties=None):
    self.clientobj.publish(topic, payload, qos, retained)


  def publish_wait_QoS2(self, topic, payload, retained=False, properties=None):
    infot=self.clientobj.publish(topic, payload, qos=2)
    infot.wait_for_publish() 
    (rc, mid)=infot
    print(self.clientid + "  " + "Topic: " + topic + " Payload " + payload)

  def run_loop(self, timesec=1):
    self.clientobj.loop_start()
    time.sleep(timesec)
    self.clientobj.loop_stop()

  def loop_start(self, timesec=1):
    self.clientobj.loop_start()

  def loop_stop(self, timesec=1):
    self.clientobj.loop_stop()


  def disconnect(self, ignore_feedback=False):
    if not self.connected:
        logger.warning("try to disconnect, but already disconnected")
        print("try to disconnect, but already disconnected")
        self.connected=True
    try:
      self.clientobj.disconnect()
    except:
      print ("disconnection Failed ")
      logger.error("MQTT DisConnection failed")
      return False
    # wait fof broker confirmation
    if not ignore_feedback:
      waitsec=5
      while (self.connected) and (waitsec>0):
          time.sleep(1)
          waitsec=waitsec-1
      if self.connected:
          return False
    
    print ("MQTT disconnection Succesfull ")
    logger.info("MQTT DisConnection Succesfull")
    self.clientobj.loop_stop()
    self.connected=False
    return True




if __name__ == "__main__":

  print(MQTTlib)
  aclient=HASS_Client()

  aclient.connect()
  time.sleep(2)
  aclient.subscribe("prova")
  time.sleep(2)
  aclient.publish("prova","sono il testo")
  time.sleep(3)
  aclient.disconnect() 

  
  """aclient.ClientObj.subscribe("prova", qos=2)  
  time.sleep(2)
  aclient.ClientObj.publish("prova", "qos 0")
  aclient.ClientObj.publish("prova", "qos 1", 1)
  aclient.ClientObj.publish_wait_QoS2("prova", "qos 2") 
  
  time.sleep(3)


  aclient.ClientObj.disconnect()  """

  print (" Hello")


