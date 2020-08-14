
import time, logging
import statusdataDBmod
from datetime import datetime,date,timedelta

try:
  __import__("paho")

except:
  MQTTlib=False
else:
  MQTTlib=True	
  import paho.mqtt.client as mqtt


SubscriptionLog={}
SubscriptionLog["default"]={}

logger = logging.getLogger("hydrosys4."+__name__)


def Create_connections_and_subscribe(CLIENTSLIST):
  if MQTTlib:
  # expected CLIENTLIST structure: {clientid1:{"broker":"","port":"" ...} ,clientid2:{"broker":"","port":"" ...}, clientid3:{"broker":"","port":"" ...} }
    for clientname in CLIENTSLIST:
      clientinfo=CLIENTSLIST[clientname]
      broker=clientinfo["broker"]
      if broker=="":
        broker="localhost"
        clientinfo["broker"]=broker
      port=clientinfo["port"]
      subtopic=clientinfo["subtopic"]
      clientID=clientname+str(time.time()) # it is necessary to ensure that the clientID is unique. 
      # If the clientID is not disconnected and same clientID is connected then there will be a look where both sessions try to kick out each other
      # If clientID is already connected when the same clientID try to connect then previous clientID is kicked-out. Unfortunately the system will try to reconnect it doing so it will kick-out the second session, in a infinite loop 
      aclient = Client(clientID,subtopic=subtopic, host=broker, port=port)
      clientinfo["clientobj"]=aclient
      clientinfo["clientID"]=clientID
      aclient.connect() 
      aclient.subscribe() # subscribe to default subtopic
      aclient.subscribe(clientinfo["subtopicstat5"])
      aclient.loop_start() 

def Disconnect_clients(CLIENTSLIST):
  if MQTTlib:
  # expected CLIENTLIST structure: {clientid1:{"broker":"","port":"" ...} ,clientid2:{"broker":"","port":"" ...}, clientid3:{"broker":"","port":"" ...} }
    for clientname in CLIENTSLIST:
      clientinfo=CLIENTSLIST[clientname]
      if "clientobj" in clientinfo:
        aclient=clientinfo["clientobj"]
        aclient.loop_stop() 
        aclient.disconnect() 

 
    
 
class Client:

#  @staticmethod
  def on_connect(self,mqttc, obj, flags, rc):
    print(self.clientid + "  " + "Connect: " + "rc: " + str(rc))
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
    print(self.clientid + "  " + "DisConnect: " +"rc: " + str(rc))
    if rc==0:
      self.connected=True
      print(self.clientid + "  " + "Disconnection Succesfull")	 
    
       
  def on_message(self,mqttc, obj, msg):
    global SubscriptionLog
    payload=msg.payload.decode('utf-8')
    print(self.clientid + "  " + "Message: "+ msg.topic + " " + str(msg.qos) + " " + payload)
    statusdataDBmod.write_status_data(SubscriptionLog,msg.topic,"jsonstring",payload)
    timestamp=datetime.utcnow()
    statusdataDBmod.write_status_data(SubscriptionLog,msg.topic,"timestamp",timestamp)    

  def on_publish(self,mqttc, obj, mid):
    print(self.clientid + "  " + "Published: "+ "  " +"mid: " + str(mid))
    pass


  def on_subscribe(self,mqttc, obj, mid, granted_qos):
    print(self.clientid + "  " +"Subscribed: " + str(mid) + " " + str(granted_qos)+ " " + str(obj))


  def on_log(self, mqttc, obj, level, string):
    print(self.clientid + "  " +string)
    
  

  def __init__(self, clientid, subtopic="" ,host="localhost", port=1883, cleanstart=True, keepalive=180, newsocket=True, protocolName=None,
              willFlag=False, willTopic=None, willMessage=None, willQoS=2, willRetain=False, username=None, password=None,
              properties=None, willProperties=None):
    self.clientid = clientid
    self.subtopic = subtopic
    self.host=host
    self.port=port
    self.cleanstart=cleanstart
    self.keepalive=keepalive
    self.newsocket=newsocket
    self.protocolName=protocolName
    self.username=username
    self.password=password

    # auxiliary variables
    self.connected=False 
    
    
    # create paho client
    self.clientobj=mqtt.Client(clientid) # create client object
    self.clientobj.on_message = self.on_message
    self.clientobj.on_connect = self.on_connect
    self.clientobj.on_disconnect = self.on_disconnect
    self.clientobj.on_publish = self.on_publish
    self.clientobj.on_subscribe = self.on_subscribe
    



  def connect(self):
    try:
      self.clientobj.connect(host=self.host, port=self.port, keepalive=self.keepalive) # connection
    except:
      print ("connection Failed "  + self.clientid)
      logger.error("MQTT Connection failed", self.clientid)


  def subscribe(self, topic="", options=None, properties=None, qos=2):
    if topic=="":
      topic=self.subtopic		
    #self.clientobj.loop_start()  
    print("try to su scribe " + topic)
    self.clientobj.subscribe(topic, qos)
    #time.sleep(0.2)
    #self.clientobj.loop_stop()


  def unsubscribe(self, topics):
    self.clientobj.unsubscribe(topics)



  def publish(self, topic, payload, qos=0, retained=False, properties=None):
    print ("Publishing " + topic )
    #self.clientobj.loop_start()
    self.clientobj.publish(topic, payload, qos, retained)
    #time.sleep(0.3)
    #self.clientobj.loop_stop()

  def publish_wait_QoS2(self, topic, payload, retained=False, properties=None):
    self.clientobj.loop_start()
    infot=self.clientobj.publish(topic, payload, qos=2)
    infot.wait_for_publish() 
    self.clientobj.loop_stop()
    (rc, mid)=infot
    #print(self.clientid + "  " + "Published: rc " + str(rc) + " message ID " + str(mid))

  def run_loop(self, timesec=1):
    self.clientobj.loop_start()
    time.sleep(timesec)
    self.clientobj.loop_stop()

  def loop_start(self):
    self.clientobj.loop_start()

  def loop_stop(self):
    self.clientobj.loop_stop()

  def disconnect(self, properties=None):
    self.clientobj.disconnect()




if __name__ == "__main__":

  print(MQTTlib)
  CLIENTSLIST={}
  client={}		
  client["broker"]= "localhost"
  client["port"]=1883 
  client["subtopic"]="topic"
  
  CLIENTSLIST["primocliente"]=client
  client={}		
  client["broker"]= "localhost"
  client["port"]=1883 
  client["subtopic"]="topic1" 
  CLIENTSLIST["secondocliente"]=client

  
  #print(CLIENTSLIST)  
  Create_connections_and_subscribe(CLIENTSLIST)



  aclient=CLIENTSLIST["primocliente"]["clientobj"]
  
  
  aclient.clientobj.loop_start()  
  
  #aclient.subscribe("topic", 2)
  aclient.publish("topic", "qos 0")
  aclient.publish("topic", "qos 1", 1)
  #aclient.clientobj.loop_stop()   
  
  aclient.publish_wait_QoS2("topic", "qos 2") 
  
  #Provide loop time to update the callbacks 
  #aclient.clientobj.loop_start()  
  #time.sleep(3)
  #aclient.clientobj.loop_stop()    
  

  #aclient.disconnect()  

  print (" Hello")


