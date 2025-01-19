#!/usr/bin/python3
# -*- coding: UTF-8 -*-


import paho.mqtt.client as mqtt 
import threading
from red_diode_clases import  End_Run, Butt, VButt, MCP23017
from time import sleep



class MQTT_client:
   
   mqtt_obj = None   #MQTT object to be used. 
   
   def __init__(self, username_="", password_="", broker_address_ = "" ,broker_port_ = 9999, broker_keepalive_ = 60, mqttUname_="", topic_="red", hrtbit_=5):
      MQTT_client.broker_address = broker_address_          #MQTT broker ip addres
      MQTT_client.broker_port = broker_port_                #MQTT broker port
      MQTT_client.broker_keepalive = broker_keepalive_      #MQTT broker keepalive flag
      self.client = mqtt.Client(mqttUname_, False)                 #create new instance, False for persistent mode  # check this MQTT_name <<<<<
      self.client.username_pw_set(username_, password_)       #MQTT broker client creation with uname and pass
      self.client.on_message=self.on_message_               #MQTT broker on_message function
      self.client.connect(MQTT_client.broker_address, port=MQTT_client.broker_port, keepalive=MQTT_client.broker_keepalive, bind_address="" )
      self.client.loop_start()
      self.main_topic = topic_[0]                        #Main topic to be used. most likely "red"
#      self.topics = topic_
      for topic in topic_:
         self.client.subscribe(topic)              #subscribing to the list of topics
      self.hartbit = hrtbit_                       #preparing hartbit topic and starting it as a thread 'hrtbt'

      hrtbt = threading.Thread (name='RedDiodeHartbit' ,  target =  self.mqtt_hartbit_publish, args= ())
      hrtbt.setDaemon(True)
      hrtbt.start()
#      self.subscribe()
   
#   def __str__(self):
#     return self.name
   
#   def  htqq_topics_add(self, dic):
#      for el in dic:
#         if isinstance(dic[0],str):
#            MQTT_client.topic_list.append()
   
   
   @classmethod
   def mqttobj(mqtt_cls):            #returns MQTT object
      try:
         return mqtt_cls.mqtt_obj
      except:
         return 0
   
   
                                                      #on_message is callback function processing incoming messages subscribet to self.main_topic
   def on_message_(self, client, userdata, message):
      global End_Run
      self.messg=str(message.payload.decode("utf-8")) #message received 
      self.topic=message.topic #message topic
      self.qos=message.qos  #message qos
      self.retain=message.retain #message retain flag
#      print("MQTT receive topic ", self.topic, self.messg)  #prints for log and review
      # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>. expand to variety of procedure depending on load via def message_process
      try:                                   #tries to use VButt functions
         VButt.butt(self.messg).v_push()
      except:
         for vbt in VButt.Butt_instance.values():        #this is to call VButt with the same prefix, works for auto_night_on_1 auto_night_on_2 etc
            if vbt.name.startswith(self.messg): vbt.v_push()
         pass
      try:                                   #tries to use regular Butt name
         Butt.butt(self.messg).v_push()
      except:
         pass                                #can be extended to eny other requests
      if self.messg == "End_Run": 
         End_Run.setEndRun()      #to end rediode program 
#         print("End_Run")
   
   
   def message_process(topic, message): # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>. expand to variety of procedure depending on load
      pass
   
   
   
   def MQTT_publish(self, topic, load, retain=False):            #simple publish topics
#      print("MQTT send topic ", topic, load, retain )  #prints for log and review
      self.client.publish(topic,load, retain)
   
   
   def mqtt_hartbit_publish(self):                 # function to be used as a thread to send hartbit (mainly to keep arduino alive)
      cnt=0
      while True:
         self.MQTT_publish(self.main_topic+'/hartbit/main','alive-'+str(cnt))
         sleep(self.hartbit)
         cnt = cnt + 1 if cnt < 999 else 0
   
   
   def statuses(self):
      pass
      
