#!/usr/bin/python3
# -*- coding: UTF-8 -*-


from time import sleep, perf_counter, localtime
import smbus
import threading
import os, re
from sys import exit
from sun_rise_set import f_sun_rise_set
from ServoPi import PWM #AB Electronics UK Python library to talk to the Servo PWM Pi Zero.
                        #

def time_str():      #return string with time in YYYY-MM-DD_HH-MM-SS format
   return str("{}-{:02d}-{:02d}_{:02d}-{:02d}-{:02d}".format(\
   localtime()[0],\
   localtime()[1],\
   localtime()[2],\
   localtime()[3],\
   localtime()[4],\
   localtime()[5]))

global longitude, latitude
#longitude = 0
#latitude = 0
                 #global in red_diode_clases.py
                  #location of installation to calculate sunrise and sunset
                  

#global alarmStartDelay
                 #global in red_diode_clases.py
                 #global parameters for alarm

global rdlog
               #global log file 

global i2c  
i2c={}        #i2c is a global in red_diode_clases.py
               #key: bus number, value: smbus.SMBus(key) instance
                     #bus 1 is hardware and use to manage MCP23017
                     #bus 3 is software on rPi ZERO and is used for AM2320 sensor
                     #for future adding more i2c buses. never use bus 0 nor 2. 
                     #the i2c is the dictionary with i2c bus number as a key and smbus object as value
                     #if more buses required, use Rpi B or any other with I2C hardware suported


class End_Run:       #global var to end rediode program running via MQTT, see red_diode_procedures/def rolling/
#End_Run.setEndRun() = False    
   end_run = False
   
   def __init__(self):
#      print("end run start")
      pass

   @classmethod
   def setEndRun(clEnd_Run):
      clEnd_Run.end_run=True
      
   @classmethod
   def WhatEndRun(clEnd_Run):
      return clEnd_Run.end_run


class I2C_ini:
   '''
            initialize i2c busses from the config file
            init() check for 0 or 2 bus that are forbitten 
            bus 1 is hardware and use to manage MCP23017
            bus 3 is software (read sloooow) on rPico and is used for AM2320 sensor, On Rpi B is hardware and it is OK.
            for future adding more i2c buses. never use bus 0 nor 2. 
            the i2c is the dictionary with i2c bus number as a key and smbus object as value
            if more buses required, use Rpi B or any other with I2C hardware suported
   '''
   def __init__(self, i2c_bus_dictionary):
         #i2c_bus_dictionary is a dictionary of key: bus number, value: smbus.SMBus(key) instance
      global i2c , rdlog
      for k in i2c_bus_dictionary.keys():
         if int(k) not in (0,2): i2c.update({int(k):i2c_bus_dictionary[k]})
      rdlog.info('I2C_ini: {}'.format(i2c))

class Alarm:

   '''
   class for alarm actions and managment.  
   '''

   alarm_StartDelay = 0   #delay of arming alarm (time to leave)
   alarm_Longivity  = 0            #time of alarm 
   alarm_EnterDelay = 0     #delay of alerting when alarm detected (time to enter)
   alarm_outputs = []      #list of outputs used to alarm, set up in 
   alarm_detected_event = threading.Event()  #alarm event - 0-no alarm detection 1-alarm detected
   a_seq_5 = None       #holders for sequence function
   a_seg_6 = None


   def __init__(self, startdelay,alaramLenght,timeToEnter, s5, s6):
      Alarm.alarm_initiator(startdelay,alaramLenght,timeToEnter, s5, s6)
   
   '''
   function "alarm_initiator" initiate alarm. It is called in MCP23017_reading_thread()
   it set failure off, attack (napad) off, fire off
   it set detection end
   '''
   @classmethod
   def alarm_initiator(Alarm_class,startdelay,alaramLenght,timeToEnter, s5, s6):  #initiating status of the alarm outputs, run in config procedures
      Alarm_class.alarm_StartDelay = startdelay   #delay of arming alarm (time to leave)
      Alarm_class.alarm_Longivity=alaramLenght            #time of alarm 
      Alarm_class.alarm_EnterDelay=timeToEnter     #delay of alerting when alarm detected (time to enter)
      VButt.butt('alarm_intruder_end').v_push()    #initiating state of alarm connection to the monitoring device
      VButt.butt('alarm_failure_off').v_push()
      VButt.butt('alarm_attack_off').v_push()
      VButt.butt('alarm_fire_off').v_push()
      VButt.butt('alarm_detection_end').v_push()
      Alarm_class.a_seq_5 = s5      #set the sequence functions 
      Alarm_class.a_seq_6 = s6
         #intruder - alarm
         #failure - awaria
         #attack - napad
         #fire - pożar   
         #detection - czuwanie/uzbrojenie
      Alarm_class.alarm_detected_event.clear()        #clears the alarm event
      alarm_thread = threading.Thread (name='alarm_thread', target=Alarm_class.alarm_th_class_function)    #sett and start alarm thread
      alarm_thread.setDaemon(True)
      alarm_thread.start()


   @classmethod
   def arm_alarm_class_function(Alarm_class, seq_l4, seq_l6, control_output):      #arming alarm: 'ARM_ALARM': arm_alarm, called from red_diode_procedures/arm_alarm
                                                               #seq_l4 is seq_4 (togle), seq_l6 is seq_6 (all on) - but can be smth differnt
                                                               #control_output is an output use to signal alarm detection status.
#      global rdlog

#      MovDetected.set_alarm(1)
      Butt.tog_motion_detection_all(0)
      Alarm_class.alarm_detected_event.clear()                             #clears alarm event
      for cnt in range (Alarm_class.alarm_StartDelay,0,-1):        #time to leave before alarm is on  
            seq_l4(0,"",control_output)                           #control output is blinking
#            print("time to left", cnt);
            sleep(1)
      #
#      print("time to left {} seconds".format(Alarm_class.alarm_StartDelay))
#      seq_l14(Alarm_class.alarm_StartDelay,"",control_output)
      
#      print("OK left")
      
      '''
      put here other actions to be performed before arming the alarm
         switch off the lights - but leave the outside lights...
         # CHECK IF WINDOWS ARE CLOSED!!!!!                <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
      '''

      Butt.set_alarm_detection(1)
#      Butt.tog_motion_detection_all(0)       
      seq_l6(0, "", control_output)
      VButt.butt('alarm_detection_start').v_push()

      Alarm_class.alarm_detected_event.clear()                             #clears alarm event
      lgstr = " {} ALARM ARMED  class method ".format(time_str())
      rdlog.info(lgstr)
#      print(lgstr)
      Butt.tog_motion_detection_all(1)

   @classmethod
   def darm_alarm_class_function(Alarm_class, seq_l5, seq_l13, control_output):     #disarming alarm: 'DARM_ALARM': darm_alarm, called from red_diode_procedures/darm_alarm
                                                               #seq_l5 is seq_5 (all of)
      global rdlog
#      MovDetected.set_alarm(0)
      Alarm_class.alarm_detected_event.clear()
      Butt.set_alarm_detection(0)
#      Butt.tog_motion_detection_all(0)

      VButt.butt('alarm_detection_end').v_push()
      VButt.butt('alarm_intruder_end').v_push()

      lgstr = " {} ALARM disarmed".format(time_str())
      rdlog.info(lgstr)
#      print(lgstr)

      seq_l5(0,"",Alarm_class.alarm_outputs)          #switch off all alarm outputs
      seq_l5(0,"",control_output)                   #switch off control_output
      seq_l13(300,"on",["L1_Hol_1"])
#      Butt.tog_motion_detection_all(1)


   @classmethod   
   def class_alarm_function(Alarm_class, action):       #run when alarm is detected 
      global rdlog

      if action=='on':

         lgstr = " {} ALARM DETECTED: action {} alarm_Longivity {} alarm_outputs {}".format(time_str(), action, Alarm.alarm_Longivity, Alarm.alarm_outputs)
         rdlog.info(lgstr)
#         print(lgstr)
#
#         MQTT_client.mqtt_obj.MQTT_publish('red/alarm','ALARM DETECTED'+time_str(), True)

         Alarm_class.alarm_detected_event.set()

      elif action=='off':

         lgstr=' {} ALARM ended '.format(time_str())
         rdlog.info(lgstr)
#         print(lgstr)
#
#         MQTT_client.mqtt_obj.MQTT_publish('red/alarm','ALARM ended ' + time_str(), True)

         Alarm_class.alarm_detected_event.clear()
         VButt.butt('alarm_intruder_end').v_push()

      else:
         lgstr = " {} ERROR IN ALARM".format(time_str())
         rdlog.error(lgstr) 


   @classmethod
   def alarm_th_class_function(Alarm_class): #threading function 
      t_start = perf_counter()      #to make timeout to avoid endless loop

      while Butt.run_loop:                                                 #the loop is controlled by Butt class run_loop controll.
         Alarm_class.alarm_detected_event.wait()          #wait for the event
         lgstr=' {} ALARM thread Butt.alarm_on: {} event {}'.format(time_str(),Butt.alarm_on,Alarm_class.alarm_detected_event.isSet())
         rdlog.info(lgstr)
#         print(lgstr)
         t_start = perf_counter()                               #to count time to enter
         while ( perf_counter() - t_start < Alarm_class.alarm_EnterDelay ) and Butt.alarm_on : sleep(1)   #counts time to enter - no alarm if triggered before 
         while ( perf_counter() - t_start < Alarm.alarm_Longivity ) and Butt.alarm_on :          #counts time to end alarm  
            if Alarm_class.alarm_detected_event.isSet():             #continue alarm if event is still set
               t_start = perf_counter()                               #advance starting time
               Alarm_class.alarm_detected_event.clear()               #clears alarm event
               VButt.butt('alarm_intruder_start').v_push()           #send START ALARM signal to the external device
            for out in Alarm_class.alarm_outputs:                 #blinks the alarm lights
               Alarm_class.a_seq_6(0, "", [out])                 #set the output on
               sleep(1)
               Alarm_class.a_seq_5(0, "", [out])                 #set the output off
         if not Butt.alarm_on: Alarm_class.alarm_detected_event.clear()          #clear alarm event at the end in case Butt.alarm_on is false - mean the status changed while running.
         VButt.butt('alarm_intruder_end').v_push()                #send END ALARM signal to the external device



class Geo:
   '''
   initialize global value for geolocalisation
   '''
   def __init__(self, long,lat):
      global longitude, latitude
      latitude = lat
      longitude = long  

class Red_diode_clases_log:
   '''
   initialize logging globaly for classes
   '''
   def __init__(self, log):
      global rdlog
      rdlog=log

class TempHumI2CSensors:
   
   '''
            for I2C AM2320 sensors
            pinout: 3-5v SDA GND SCL
   '''
   
   th_sens_list={}    #key: sensor id, sensor pointer 
   sl=0.1   #sleeping time between reads - read the I2C AM2320 manual for detail
   
   def __init__(self, name, i2c_bus, adres, sfreq):
      self.name=name       #human readable name
      self.bus=int(i2c_bus)     #i2c bus number
      self.addres=int(adres,16)    #device i2c address
      TempHumI2CSensors.sens_frequency = int(sfreq) #sensor reading frequency in seconds
      TempHumI2CSensors.th_sens_list.update({self.name: self})
   
   @classmethod
   def publish_all_temp_hum(the_clas, mqtt_ob):  #to be run as thread
      while True:
         for key in the_clas.th_sens_list:
            the_clas.publish_temp_hum(the_clas.th_sens_list[key],mqtt_ob)
            sleep(the_clas.sens_frequency)
            
   def publish_temp_hum(self, mqtt_ob):
      temp_val=self.read_AM2320_temp()
      temp_str = str('{:6.2f}°C'.format(temp_val))
      hum_val=self.read_AM2320_humidity()
      hum_str = str('{:6.2f} % H20'.format(hum_val))
      
      if ( temp_str != '') :
         mqtt_ob.MQTT_publish('red/temp/'+self.name+'/val',temp_val, False)  #false is for mqtt messge retain
         mqtt_ob.MQTT_publish('red/temp/'+self.name+'/str',temp_str, False)  #sends two topics: value and string
      if ( hum_str != '') :
         mqtt_ob.MQTT_publish('red/humi/'+self.name+'/val',hum_val, False)  #false is for mqtt messge retain
         mqtt_ob.MQTT_publish('red/humi/'+self.name+'/str',hum_str, False)  #sends two topics: value and string
         
   
   def read_AM2320_temp(self):      #reads tempetarure
      sleep(TempHumI2CSensors.sl)
      return self.read_AM2320(2)
      
   def read_AM2320_humidity(self):      #reads humidity
      sleep(TempHumI2CSensors.sl)
      return self.read_AM2320(0)
   
   def read_AM2320(self, ar):    #algorythm to read the AM2320 registers, as a sensor requires wake up call and then read.
      global rdlog
      sleep(TempHumI2CSensors.sl*2)  
      try:
         i2c[self.bus].read_byte(0x5c)    #wake up sensor - this function should return error, but the sensor is waking up
      except:
         pass
      try:
         sleep(TempHumI2CSensors.sl)
         i2c[self.bus].write_i2c_block_data(0x5c, 0x03, [ ar, 2])    #ask for data
         sleep(TempHumI2CSensors.sl)
         r=i2c[self.bus].read_i2c_block_data(0x5c, 0x3, 0x06)        #read data
         ok=1
      except:
         ok=0
      if ok:
         if ar==0: 
            #print('relative humidity (%)  : ',end= ' ')
            res=(r[2]*256+r[3])/10
         elif ar==2: 
            #print('temperature in Celsius : ',end= ' ')
            res = (r[2]*256+r[3])/10
            res = 32768 - res if res >= 32768 else res #calculates values below 0 Celsius
      elif not ok: 
         rdlog.error(' {} AM2320 sensor reading error'.format(time_str()))
         res=9999  #means error
      return res




class TempSensors:
   
   '''
            1-wire Temterature sensors class management
            send measurements via MQTT
            DS18B20 sensors are in use. For other modifications may require
   '''
   
   temp_sens_list={}    #key: sensor id, path to w1_slave
   
   
   
   def __init__(self, name, file, sfreq):
      self.name = name       #human readable name
      self.file = file        #file to read temperature
      TempSensors.sens_frequency = int(sfreq) #sensor reading frequency in seconds
      self.check_temp_sensors()   #check if the sensor really exist
      self.temp_list = []        #list of recent temp read to drow chart
      self.last_read = perf_counter() - 21*60   #last read of the temp for the chart
      
#   
   @classmethod
   def publish_all_temp(my_class, mqtt_ob):
      while True:
         for val in my_class.temp_sens_list.values():
#            print('reach this point')
            my_class.publish_temp(val, mqtt_ob) 
            sleep(my_class.sens_frequency) 
   
   @classmethod
   def publish_all_temp_chart(my_class, mqtt_ob):
      while True:
         for key in my_class.temp_sens_list:
#            print('reach this point - temp cart')
            my_class.publish_temp_chart(my_class.temp_sens_list[key], mqtt_ob) 
            sleep(my_class.sens_frequency)   
      
   def read_temp(self):
      try:
         f = open(self.file, "r")
         f.seek(0,0);
         return int(f.readline().rsplit('\n',1)[0])/1000
      except:
         return -100 #that means err
         
   def publish_temp(self, mqtt_ob):
      temp_val=self.read_temp()
      temp_str = str('{:6.2f}°C'.format(temp_val))
      if ( temp_str != '') :
#         print('red/temperature/'+self.name+'/val',temp_val)
         mqtt_ob.MQTT_publish('red/temp/'+self.name+'/val',temp_val, False)  #false is for mqtt messge retain
         mqtt_ob.MQTT_publish('red/temp/'+self.name+'/str',temp_str, False)  #false is for mqtt messge retain
         lsgtr = " {} Temperature at {} {} {}".format(time_str(), self.name, temp_val,temp_str)
         rdlog.info(lsgtr)
   
   def publish_temp_chart(self, mqtt_ob): #send list of temp measures vto drow the chart of temp
      if perf_counter() - self.last_read > 20*60: 
         self.last_read = perf_counter()
         temp_val=self.read_temp()
         temp_str = str('{:6.2f}°C'.format(temp_val))
         if ( temp_str != ''): self.temp_list.append(temp_val)  
         if len(self.temp_list) >20: self.temp_list = self.temp_list[1:]
#         print('red/temperature/'+self.name+'/val',temp_val)
      if 1 <= len(self.temp_list) < 5: 
         for i in range(1,5): self.temp_list.append(self.temp_list[0])
      if len(self.temp_list) >= 5: 
         mqtt_ob.MQTT_publish('red/temp/'+self.name+'/chart',str(self.temp_list), False)  #false is for mqtt messge retain
   
   def check_temp_sensors(self):       #check if the sensor really exist
      #check the termometer exist.
      if os.path.exists(self.file):
         TempSensors.temp_sens_list.update({self.name:  self})
               
   def list_sensors(self):
      global rdlog
      for key in self.temp_sens_list:
         ldstr=" time_str() sendors: {} {}".format(key, self.temp_sens_list[key])
         rdlog.info(ldstr)
   
   
class VButt:
   
   '''
            Vbutt is virtual button class to manage action not on physical buttons 
            
   '''
   
   Butt_instance = {}                      # Class dictionary dictionary of buttons { name:str; button_object:pointer} 
   
   def __init__(self, hum_name, cfunction, param):
      self.name = hum_name #human readable name
      self.call=cfunction      #calling functions
      self.param=param     #list of parameteres, usualy outputs.
      self.auto_night_on = True if self.name.startswith('auto_night_on')  else False   #setting the auto_night bool trigger for day_night procedure,    
                                                                                       #startwith() method search in string
      self.auto_night_off = True if self.name.startswith('auto_night_off')  else False #setting the auto_night bool trigger for day_night procedure,
      #self.schedule_b        #bool - True when VBUtt runs as cron/scheduler. Set up in read_config_vbutt/red_diode_config_procedures.py
      #self.schedule_s        # list with strings with cron info [mon, mday, hour, min, wday, yday]. Set up in read_config_vbutt/red_diode_config_procedures.py
      VButt.Butt_instance.update({self.name: self})    #updated Butt Class dictionary 
#      print('VButt INIT info ',hum_name, b_out, param,self.call,self.param)
   
   def update(self, hum_name, b_out, param):
#      self.name = hum_name #human readable name
      self.call=b_out      #calling functions
      self.param=param     #list of parameteres, usualy outputs.
#      VButt.Butt_instance.update({self.name: self})    #updated Butt Class dictionary
#      print('VButt UPDATE info ',hum_name, b_out, param,self.call,self.param)
   
   
   @classmethod
   def butt(butt_cls, hum_str):            #returns VButt object
      try:
         return butt_cls.Butt_instance[hum_str]
      except:
         return 0
         
   def butt_action(self):
      global rdlog
      lgstr=(' {} VButt.butt_action name: {} callf: {} param: {}'.format(time_str(), self.name, self.call, self.param))
      rdlog.info(lgstr)
      try:
#         print(" {} butt_action 01 {} {} {}".format(time_str(), self.name, self.call, self.param))
         self.call(self.param)
#         print("butt_action 01 post")
      except:
         try:
#            print(" {} butt_action 02 {} {} {}".format(time_str(), self.name, self.call, self.param))
            self.call()
#            print("butt_action 02 post")
         except:
#            print("butt_action 03 {} {} {}".format(self.name, self.call, self.param))
            lgstr=(' {} VButt.butt_action failed name: {} callf: {} param: {}\n'.format(time_str(), self.name, self.call, self.param))
            rdlog.error(lgstr)
   
   def v_push(self):       #helper function  
      self.butt_action()
   
   
   
   
class MovDetected(threading.Thread):
   
   '''
            Class for movement/motion detection and actions to be taken
            to be more configurable by config files <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
            motion detection to turn on/off lights and alarm (switchable)
            use as thread:
            thr=MovDetected(p_time, holdtime, detected_ev, self.action1, 'on','off', self.outputs, self.outputs_dimm)
            thr.setDaemon(True)
            thr.set_end_time(p_time)
            thr.start()
   '''
   
   def __init__(self, h_name, ldt, ts,  event_, alarm_function_, func, act1, act2, outputs, dimms):
      self.sensor_name=h_name          #human readable name
      self.last_detect_time=ldt        #last time motion detected
      self.detection_start_time=ldt    #last detection start time
      self.l_time=ts                   #lasting time, how long actionis kept after detection 
      self.ll_time=ts                  #lasting time for normal move detection- to restore after alarm mode
      self.runcondition = False        #bool if 1: run, if 0: pass see set_runcondition function below for more details
      self.detectedEventExternl=event_                #threating event to control action, value set at Butt detected_ev
      self.function=func               #function pointer, action to be taken when motion is detected
#      self.regular_function=func           #normal operating function (not alarm) - v_pres
      self.alarm_function=alarm_function_  #alarm operating function - alarm_function
      self.action1=act1                #string - action (on, off, toggle) at the start
      self.action2=act2                #string - action (on, off, toggle) at the end
      self.outputs=outputs             #outputs (relays)
      self.outputs_dimm=dimms          #outputs PWM
      self.light_set_on_flag = False      #internal boolien 1 if light was set, 0 if off.
#      self.eventInternal = threading.Event()
#      self.eventInternal.clear()
#      self.lock = threading.RLock()
      self.alarm = False               #alarm is off by default
      super(MovDetected, self).__init__()
      
      
   def set_ld_time(self, ldt):         #setting time of the last detection, this advance action time
      self.last_detect_time = ldt if self.runcondition else 0                          #setting time of the last detection
      
   def set_detection_start_time(self, ldt):  #setting the start time of the detected motion. For use with alarm
      self.detection_start_time = ldt
      
   def set_runcondition(self, rc):     #set the run condition bool if 1: run, if 0: pass
      self.runcondition = rc           #if night is false, motion detection is not working
                                       #if button.motion_on is false, motion detection is not working
                                       #if alarm is on motion detection is working
                                       #runcondition is set up outside to control motion detection, 
                                       #or runcondition is on and the alarm is set on
   
   
   def set_l_time(self, ts):     #for reconfiguration: set the lasting time, how long action is kept after detection
      self.l_time=ts 
   
   
#   def set_alarm(self, on_off):     #for setting the motion detector into alarm mode
#      if self.alarm != on_off:      #check if alarm is in a required status. If not, runs the routine.
#         self.l_time = 0        #set the lasting time to 0 to force timeout
#         self.runcondition = False 
#         self.alarm = on_off
#         self.eventInternal.wait()
#         self.alarmChanged = False
#         self.eventInternal.clear()
#         self.detectedEventExternl.clear()
#         if self.alarm:
#            self.l_time = Alarm.alarm_Longivity                  #set the lasting time for alarm 
#            #self.l_time = 1                                       #set the lasting time for alarm for given seconds - this keeps alarm on when repeateng detection on one sensor
#            #self.runcondition = 1            #make sure motion detection works if alarm armed
#            self.function = self.alarm_function      #use alarm function
#         elif not self.alarm:
#            self.function = self.regular_function        #use normal function
#            self.l_time = self.ll_time               #set the lasting time back to normal value


   def set_alarm(self, on_off):     #for setting the motion detector into alarm mode
      if self.alarm != on_off:      #check if alarm is in a required status. If not, runs the routine.
         self.alarm = on_off
         if self.alarm:
            self.l_time = Alarm.alarm_Longivity                  #set the lasting time for alarm 
         elif not self.alarm:
            self.l_time = self.ll_time               #set the lasting time back to normal value



   def takeStartAction(self):
      global rdlog
      self.function([self.action1] + [0] + self.outputs + self.outputs_dimm)        #execute action at the start
                                                                                          # the [0] element for compatibility with vbutt function
                                                                                          #Parameters are: an action ( on, off, togle, dimm ) + numeric value (delay time or dimm) + output list
      if self.alarm: self.alarm_function([self.action1] + [0] + self.outputs)
      self.light_set_on_flag=True                                                   #internal boolien 1 if light was set, 0 if off.
      
      lsgtr = " {} Motion start action {}".format(time_str(), self.sensor_name)
      rdlog.info(lsgtr)
#      print(lsgtr)

   def takeEndAction(self):
      global rdlog
      self.function([self.action2] + [0] + self.outputs + self.outputs_dimm)           #action at the end
                                                                                       # the [0] element for compatibility with vbutt function
                                                                                    #Parameters are: an action ( on, off, togle, dimm ) + numeric value (delay time or dimm) + output list
      if self.alarm: self.alarm_function([self.action2] + [0] + self.outputs)
      self.light_set_on_flag=False                                                     #internal boolien 1 if light was set, 0 if off.
      
#               self.eventInternal.set()
      lsgtr = " {} Motion end   action {}".format(time_str(), self.sensor_name )
      rdlog.info(lsgtr)
#      print(lsgtr)

   
   def run(self):
      global rdlog
      cond1, cond2, condT = False, False, False
      cond1_prev, cond2_prev, condT_prev = False, False, False
#      self.alarmChanged = False
      while True:
#        self.detectedEventExternl.wait(self.l_time)                       #waits for detectedEventExternl, but with timeout (timeout to run action closing)
        self.detectedEventExternl.wait(2)                       #waits for detectedEventExternl, but with timeout (timeout to run action closing)

        cond1 = ( self.detectedEventExternl.isSet() and self.runcondition and not self.light_set_on_flag )          #runcondition is on AND no start action taken yet. #light_set_on_flag  - True if light is on   
        cond2 = (( not self.detectedEventExternl.isSet() or not self.runcondition ) and self.light_set_on_flag )    # if there is no event or runcondition and ligh was set on
        condT = (( perf_counter()-self.last_detect_time  ) > self.l_time)                                            #if action time is out
 
# #for testing
#        if ( cond1_prev != cond1 ) or \
#           ( cond2_prev != cond2 ) or \
#           ( condT_prev != condT):
#           cond1_prev = cond1
#           cond2_prev = cond2
#           condT_prev = condT
#           print (" {} MovDetectedRUN {}, c1: {}, c2: {}, c_tm {}, event {}, runc {}, LighFlag {},".format\
#                     (self.sensor_name, self.alarm, cond1, cond2,condT,self.detectedEventExternl.isSet(),self.runcondition,self.light_set_on_flag)) 
# #for testing end
 
        if cond1:                      #runcondition is on AND no start action taken yet. #light_set_on_flag  - True if light is on   
           self.takeStartAction()

        if condT:    # if there is no event or runcondition and ligh was set on
#        if  not self.detectedEventExternl.isSet() and self.light_set_on_flag :                                 # if there is no event and ligh was set on
            if cond2:                         #if action time is out
               self.takeEndAction()
               
#        if self.alarmChanged:
#            self.takeEndAction()
#            self.eventInternal.set()
#            if ( perf_counter()-self.last_detect_time  ) > max(self.ll_time, Alarm.alarm_Longivity): self.eventInternal.set()
#            print("executed ", self.sensor_name)
   
   
class Butt:
   
   '''
               Butt_instance - Class dictionary with list of buttons { name:str: button_object:pointer}  
               to_chip: integer: MCP27017 adress within I2C bus. Can be 8 adreses on one I2C bus.
               to_pin: integer 0-15: the input pin on MCP27017 that button is connected to
               pin_b is 2**to_pin !!!!! binary pin adress
               name: string: human readable name
               outputs: string:list of outputs  button is servicing: Relays or ServoPWM
               is_con > rev_log: bool: is the button open by default or closed for contactrons. Relay controls reverse logic for fail safe in different manner
               is_mov - is this motion sensor
               is_night_only_motion - is this motion sensor working only during night
               classmethod butt - returning object pointer, takes str argument with name of the button
               b_read - method to read button
   '''
   
   
   '''
            Class dictionary dictionary with list of buttons { name:str: button_object:pointer} 
   '''
   Butt_instance = {}
#   Butt_alarm_outputs = []
   
   def __init__(self, hum_name, to_chip, to_pin, b_out, is_con, is_mov, is_night_only_motion, htime, dly_v, act, sun_rise_delta, sun_set_delta):
      '''
                  string name, pointer to chip, pin number 0-15, list of outputs [str,str], contactron, motion detection, night only motion detection, hold time, delay time in seconds, sun rise corectiom, sun set correction
                  hum_name, - string name,
                  to_chip, - pointer to chip
                  to_pin, - pin number 0-15
                  b_out, - list of outputs string,
                  is_con, - is it contactron
                  is_mov, - is motion detection
                  is_night_only_motion, -  is night only motion detection
                  htime, - time to hold the button to long hold
                  dly_v, - delay time is seconds
                  act, - action (for sequences required action definition))
                  sun_rise_delta, sun rise corecton
                  sun_set_delta -  sun set correction
      '''
      Butt.run_loop=True               #global bool to controll the loop ending - required to stop the button iterators
      self.chip = MCP23017.chip(to_chip)
      self.pin = int(to_pin)        # to_pin: integer 0-15
      self.pin_b = 2**self.pin      # binary pin adres
      self.name = hum_name          # human readable name
      self.is_pwm = False           # True if there are pwm outputs - it is set True in procedure output_what()
      self.output_what( b_out )      # setting up lisf outputs (self.outputs  and self.outputs_dimm)with or without PWM
      #self.outputs                  # lisf outputs  without PWM    - append in output_what()  
      #self.outputs_dimm             # lisf outputs  with  PWM      - append in output_what()   
      self.is_con = is_con          # True if this is contactron are reverse
      self.is_mov = is_mov          # True if this is motion detector
#      self.mov_action1,self.mov_action2  #action for mov detection, set up in read_config_inputs(confign_str)
      self.is_night_only_motion = is_night_only_motion          # True if this is motion detector working only during night
      self.holdtime = htime         # time to hold button pushed to take log-press action (action2)
      Butt.Butt_instance.update({self.name: self})    #updated Butt Class dictionary
      Butt.alarm_on = False         # controls Alarm on/off for all inputs, set in @classmethod def set_alarm_detection(cls, onof=1), called in Alarm class
      self.delay_time = dly_v       # None or number of seconds to delay for S8 and S11 actions
      self.delay_action = act       # None or name of action (dimm, on, off, pass, togle)s for S8 and S11 actions
      self.sun_rise_d = int(sun_rise_delta)
      self.sun_set_d = int(sun_set_delta)
      self.butt_self_update()       # sets physical inputs on the chip
#      if self.is_con:              # if contactron, use reverse logic
#         self.chip.op_log(self.pin)
#      self.butt_action_iterator=''        # iterator function ( motion_action,  contactron_action or butt_action), set by 'def MCP23017_reading_thread(): '
#      self.function1=''            # short press sequence seq_1..8, set up by 'def read_config_inputs_actions(confign_str):' or for MOV v_press
#      self.function2=''            # long press sequence seq_1..8, set up by 'def read_config_inputs_actions(confign_str):' 
#      self.alarm_function = ''      # alarm function set up by 'def read_config_inputs_actions(confign_str):' 
#      self.timeaftermove=0        # time of activity after move, setup in read_config_inputs
#      self.mov_action1         #function data string (on, off, togle, pass) or alarm trigers (ARM_ALARM to set on, DARM_ALARM to set off)
#      self.mov_action2         #set in def read_config_inputs in red_diode_config_procedures.py
      
      
      
      
   def update(self, hum_name, to_chip, to_pin, b_out, is_con, is_mov,is_night_only_motion, htime, dly_v, act, sun_rise_delta, sun_set_delta):
      self.chip=MCP23017.chip(to_chip)
      self.pin=int(to_pin)      # to_pin: integer 0-15
      self.pin_b=2**int(to_pin) #binary pin adres
#      self.name=hum_name      #human readable name
      self.is_pwm = False                  #True if there are pwm outputs - it is set up in procedure output_what()
      self.output_what( b_out)   #setting up lisf outputs with or without PWM
      self.is_con = is_con            #True if this is contactron are reverse
      self.is_mov = is_mov             #True if this is motion detector
      self.is_night_only_motion = is_night_only_motion            #True if this is motion detector working only during night
#      self.motion_on = True               #True if the motion detection is on
      self.holdtime = htime            # time to hold button pushed to take log-press action (function2)
      self.delay_time = dly_v       # None or number of seconds to delay for S8 and S11 functions
      self.delay_action = act       # None or number for (dimm, on, off, pass, togle)s for S8 and S11 functions
      self.sun_rise_d = int(sun_rise_delta)
      self.sun_set_d = int(sun_set_delta)
#      Butt.Butt_instance.update({self.name: self})    #updated Butt Class dictionary
      self.butt_self_update()          # sets physical inputs on the chip
#      if self.is_con:                  #if contactron, use reverse logic
#         self.chip.op_log(self.pin)
#      self.butt_action_iterator=''        #this will be iterator function
#      self.function1=''            #short press function 
#      self.function2=''            #long press function
#      self.timeaftermove=0       #time of activity after move         
   
   @classmethod
   def butt(butt_cls,hum_str):            #returns Butt object, parameter str with name
      try:
         return butt_cls.Butt_instance[hum_str]
      except:
         return 0
   
   
   
   def output_what(self, out_list):    #checking if the output is Relay or ServoPWM
                                             #out_list list of outputs, dly - if there is a delay value add it to the list on first position
      self.outputs, self.outputs_dimm = [], [] 
      for el in out_list:
         if el in Relay.Relay_outputs:
            self.outputs.append(el)        #if yes adding to the list
         elif el in PWMout.PWMout_instance.keys():        #check if output is a PWM on servo
#            self.outputs_dimm.append(el)         #if yes adding to the list
            self.outputs.append(el)
            self.is_pwm = True       #marking as  pwm
   
   def butt_self_update(self):
      self.chip.set_input(self.pin, self)          #enabling input on the MCP23017 chip
      if self.is_con:                  #if contactron, use reverse logic
         self.chip.op_log(self.pin)
   
   
   def __str__(self):
     return self.name
     
   def b_read(self):          #helper function reading physical button, true if pressed
      global rdlog
      try:
         return (self.butt(self.name).chip.read_chip('GPIO') & self.pin_b) == self.pin_b
      except:
         lgstr = " {} b_read error {} pin {}".format(time_str(), self.name, "pin:", self.pin)
         rdlog.error(lgstr)
   
   
   def short_push(self):      #action when pressed shortly
      try:
         if len(self.outputs_dimm) > 0: self.function1(self.delay_time, self.delay_action, self.outputs_dimm)
      except:
         pass
      try:
         if len(self.outputs) > 0: self.function1(self.delay_time, self.delay_action, self.outputs)
      except:
         pass
   
   
   def long_push(self):    #action when hold
      try:
         if len(self.outputs_dimm) > 0: self.function2(self.delay_time, self.delay_action, self.outputs_dimm)
      except:
         pass
      try:
         if len(self.outputs) > 0: self.function2(self.delay_time, self.delay_action, self.outputs)
      except:
         pass
   
   
   def v_push(self):       #helper function to keep unity with vbutton  class
      self.short_push()   
   
   @classmethod
   def set_alarm_detection(cls, onof=1):     #togling on off alarm, 
                           #use without arg to set on, use  Butt.set_alarm_detection_all(0) to set off
                           #onof - bool 0-off 1-on 
     
      cls.alarm_on=onof
#      cls.tog_motion_detection_all(onof)        #make sure all motion detections works if alarm is on (change it if you need different setup)
      
      
   
   @classmethod
   def tog_motion_detection_all(cls, onof=1):     #togling on off motion detection, 
                           #use without arg to set on, use  Butt.on_motion_detection_all(0) to set off
                           #onof - bool 0-off 1-on 
      for but in cls.Butt_instance.values():
         if but.is_mov or but.is_night_only_motion: 
            but.motion_on=bool(onof)            #True if this is motion detector
            but.function1([but.mov_action2] + [0] + but.outputs + but.outputs_dimm)           #action at the end
   
   
   @classmethod
   def stop_motion_detection(cls):     #to finish, ending up motion detection iterators
      global rdlog
      cls.run_loop=False
      lgstr = " {} stop_motion_detection".format(time_str())
      rdlog.info(lgstr)
   
   
   
   
   
                  #iterator motion detector function run from main button reading thread
                  #the iterator is self.butt_action_iterator 
   def motion_action(self,data):
      global   rdlog
      INTF, GPIO, p_time = data #interup, gpio and time of capture
      my_t=p_time    #keeps the previously given time
      ldtime = self.timeaftermove if self.timeaftermove !=0 else 5 #set time to be active after mov detection. If the time was not set up it will be 5 seconds
      pressed = False   #true if the action was triggered
      detected=False    #true if the motion was detected
      p_pressed, p_detected = False, False #for logging action, see code below
      detected_ev=threading.Event() #event controlling the trigered action
      detected_ev.clear() #closing the event
      thr_MovDetected=MovDetected(self.name, p_time, ldtime,  detected_ev, self.alarm_function, self.function1, self.mov_action1, self.mov_action2, self.outputs, self.outputs_dimm)
                  #name, time of capture, hold time,  event, procedure to trigger, functions 1, 2 , outputs
                  #MovDetected is threading class controlling receiver behavior by the detected_ev 
      thr_MovDetected.setDaemon(True)
      thr_MovDetected.set_ld_time(p_time)       #setting the last detection time for the MovDetected thread
      thr_MovDetected.start()
      self.motion_on=True              #boolien to controll if the motion detection should be on (1) or off (0) 
#      print('motion setup',thr_MovDetected.is_alive(),  threading.enumerate())
#      Butt.run_loop=True               #global bool to controll the loop ending
      while Butt.run_loop:
         thr_MovDetected.set_alarm(Butt.alarm_on)

         if ( self.is_night_only_motion and not Butt.alarm_on ):               #if motion to be detected at night only and if alarm_on is False
            day, night, sl_t, sr, ss = f_sun_rise_set(longitude, latitude, self.sun_rise_d, self.sun_set_d )
         else:
            night = True               #this is for always on
#         print('{} ITER M_A night {}  motion {} AND {}'.format(self.name, night, self.motion_on, night & self.motion_on))
         thr_MovDetected.set_runcondition(night & self.motion_on)         #if night is false, motion detection is not working
                                                               #if motion_on is false, motion detection is not working
#         if not self.motion_on: print("self.motion_on >>>>>>>>>>>>>>>>>>>>>>>>>>", self.motion_on)
         if ( ( GPIO & self.pin_b ) ) :  
            #if  GPIO                           >>> (motion detected)
            detected=True
#            my_t=p_time
            thr_MovDetected.set_ld_time(p_time)                #setting time of the last detection, this advance action time
         elif ((INTF & self.pin_b) and (not ( GPIO & self.pin_b ))):  
            #if INTERUPT and not GPIO           >>>>  (motion stopped) 
            detected=False
            
         if (( detected ) and ( not pressed )) : 
            #motion detected but no action taken yet 
            if self.motion_on:   
               detected_ev.set()
            else: detected_ev.clear()
            pressed=True
         if (( not detected ) and (  pressed )):  
            #motion ended and action to be stoped
            detected_ev.clear()
            pressed  = False
            
#         if pressed or detected: print('chip {} pin {} pressed {} detected {}'.format(self.chip, self.pin, pressed, detected))      
         
#         if p_detected != detected:    #FOR LOGGING prints action on change
#            p_detected = detected
#            b_event = "detected" if detected else "ended"
#            lgstr = " {} Motion action {} {}".format(time_str(), b_event, self.name)
#            rdlog.info(lgstr) 
            #print(lgstr)
              
         (INTF, GPIO, p_time) = yield
         
         if not thr_MovDetected.is_alive():     #check if thread is still alive
            self.run_loop=False
            lgstr = " {} MOTION THREAD IS DEAD".format(time_str())
            rdlog.error(lgstr)
      lgstr = " {} motion_action finished {}".format(time_str(),self.name)
      rdlog.info(lgstr)
   
   
   
                  #iterator contactron function run from main button reading thread
                  #the iterator is self.butt_action_iterator 
   def contactron_action(self, data):
      global rdlog
      INTF, GPIO, p_time = data
      hold = False
      cont_open, p_cont_open = False, False
      
                     #this part iterates
      while True:
      
         if ((not (INTF & self.pin_b)) and ( GPIO & self.pin_b ) and (not cont_open)):  
               #if not INTERUPT and GPIO  >>> (hold)
            cont_open=True
            self.long_push() 
         elif ((INTF & self.pin_b) and (not ( GPIO & self.pin_b ))):  
               #if INTERUPT and not GPIO           >>>>  (released)
            if cont_open: self.short_push() #for buttons
            cont_open=False
#         if cont_open: print('chip {} pin {} cont_open {} '.format(self.chip, self.pin, cont_open))
         
         if p_cont_open != cont_open:    #FOR LOGGING prints action
            p_cont_open = cont_open
            b_event = "open" if cont_open else "closed"
            lgstr = " {} Contactron action {}  {}".format(time_str(), self.name, b_event)
            rdlog.info(lgstr) 
            
         (INTF, GPIO, p_time) = yield 
   
   
   
                     #iterator function for regular buttons run from main button reading thread
                  #the iterator is self.butt_action_iterator 
   def butt_action(self, data):
      global rdlog
      INTF, GPIO, p_time = data
      my_t=p_time
      pressed = False
      hold = False
      p_pressed, p_hold = False, False    #for logging action, see code below
      holdT=self.holdtime
                     #this part iterates
      while True:
#         print('name {} holdT {} pwm? {}'.format(self.name, holdT,self.is_pwm))
         if ((INTF & self.pin_b) and ( GPIO & self.pin_b )):  
            #if INTERUPT and  GPIO    >>> ( pressed )
            pressed = True
            hold = False
            my_t = p_time
         elif ((not (INTF & self.pin_b)) and ( GPIO & self.pin_b )):  
            #if not INTERUPT and GPIO    >>> (hold)
            if ( p_time - my_t ) > holdT:
               self.long_push()
               my_t=p_time
               hold = True   
               if self.is_pwm: holdT = 0.001          #if buttin is hold for dimming, hold time is minimal to run smootly
         elif ((INTF & self.pin_b) and (not ( GPIO & self.pin_b ))) :  
            #if INTERUPT and not GPIO           >>>>  (released)
            if pressed and (not hold): self.short_push() #for buttons
            pressed = False
            hold = False
            my_t = p_time 
            holdT=self.holdtime                 #return normal hold time
         if p_pressed != pressed or p_hold !=hold:    #FOR LOGGING prints action
            p_pressed, p_hold = pressed, hold
            b_event = "hold" if hold else ("pressed" if pressed else "released") 
            lgstr = " {} Button {} {}".format(time_str(), self.name ,  b_event)
            rdlog.info(lgstr)
         (INTF, GPIO, p_time) = yield 
         
   
   
   

class Relay:
   
   
   '''
   # light (or any other receiver) is connected to relay, and relay is connected to MCP23017, so MCP chip I2C adres is needed: 
   #   Relay_instance               - instances of relay, dictionary with string name and object pointer
   #                             example {name:str: <object pointer>}
   #  self.chip=MCP23017.chip(to_chip)  - address to chip object connected with relay
   #  self.pin=ch_pin             - pin on chip connected with relay 0-15
   #  self.relay=to_relay        - human readble number of the relay, so one can figure out phisical/electrical connection
   #  self.name=hum_name         - human readable name of the output/receiver connected to relay
   #  self.is_PWM=PWM               - bool defining if the receiver is a PWM device. 
   #  self.REV                   -bool - define if the relay works in reverse logic - usefull for failsafe lights. It is for RELAY control - INPUTS have reverse logic controlled differently'''
   
   Relay_instance = {}           #list of Relay instaness, name and pointer
   Relay_outputs= []          #list of all relay outputs
   
   def __init__(self, to_chip, ch_pin, to_relay, hum_name, is_PWM, is_rev):
      global rdlog
      self.chip = MCP23017.chip(to_chip)  #pointer to the MCP23017 object Realay is connected to
      self.pin = int(ch_pin)  #0-15 pin on MCP23017
      self.relay = to_relay   #human readble name of the relay - not realy in use, just to reference physical connection
      self.name = hum_name    # human readable name of the output/receiver connected to relay
      self.is_PWM = is_PWM    #is this PWM #############################    check if this is on any use
      self.REV = is_rev       #reverse logic
         #adding the object to the list of relay objects
      Relay.Relay_instance.update({self.name: self})   
      Relay.Relay_outputs.append(self.name)
      try:
         self.chip.set_output(self.pin)
         self.off()
         self.state=False    #parameter saying 'off' when False, 'on' when True
      except:
         lgstr = " {} output setup error {}".format(time_str(), self.name)
         rdlog.error(lgstr)
         
   def update(self, to_chip, ch_pin, to_relay, hum_name, is_PWM, is_rev):
      global rdlog
#      self.chip = MCP23017.chip(to_chip) 
#      self.pin = int(ch_pin) #0-15
      self.relay = to_relay
#      self.name = hum_name
      self.is_PWM = is_PWM
      self.REV = is_rev
         #adding the object to the list of relay objects
#      Relay.Relay_instance.update({self.name: self})       
      try:
         self.chip.set_output(self.pin)
         if self.state :
            self.on()
         else:
            self.off()
#         self.off()
#         self.state=False    #parameter saying off when False, on when True
      except:
         lgstr = " {} output re-setup error {}".format(time_str(), self.name)
         rdlog.error(lgstr)       
   
   
   def relay_self_update(self):        #set chip settings for output
      global rdlog
      try:
         self.chip.set_output(self.pin)
         if self.state :
            self.on()
         else:
            self.off()
      except:
         lgstr = " {} relay_self_update error {}".format(time_str(), self.name)
         rdlog.error(lgstr)
   
   
   @classmethod
   def relay(cls,hum_str):            #returns relay object by the human readable str name 
      try:
         return cls.Relay_instance[hum_str]
      except:
         return 0
   
   
   @classmethod
   def all_off(cls):         
      for R in cls.Relay_instance:
         if not ( R.startswith('alarm') or R.startswith('ALARM') or R.startswith('Alarm') ):
            cls.Relay_instance[R].off()
   
   
   def __str__(self):
        return self.name
   
   
   '''
                 on and off methods are turning on and off devices connected to realay
                 if REV is True, the device is on if the relay is off. It is the physical connection of relay that do the negative logig, but only on mechanical relays, not SSR.
   '''
   
   def r_pass(self):
      pass
   
   def on(self):
      global rdlog
      if self.REV: self.chip.set_output_off(self.pin)
      else: self.chip.set_output_on(self.pin)
      self.state=True
      logstr="{} Relay on {} ".format(time_str(), self.name)
      rdlog.info(logstr)
   
   
   def off(self):
      global rdlog
      if self.REV: self.chip.set_output_on(self.pin)
      else: self.chip.set_output_off(self.pin)
      self.state=False
      logstr="{} Relay off {} ".format(time_str(), self.name)
      rdlog.info(logstr)
   
   
   def togle(self):
      global rdlog
      self.chip.togle_output(self.pin)
      self.state = not self.state
      logstr="{} Relay toggle {} ".format(time_str(), self.name)
      rdlog.info(logstr)
   
   
   def is_on(self):        #helper function returning true if the relay is open - it check hardware. not parameter
      st=self.chip.is_output_on(2**self.pin) #pin should be given here as binary
#      st=self.chip.is_output_on(self.pin)
      if self.REV: return (not st)
      else: return st
   
   
   '''
   PWM output class, define single output of PCA9685 Servo PWM
   '''
class PWMout:
   
   PWMout_instance = {}            #list of instances key: PWM out name, pointer to the object
   PWMout_powersupply = {}          # list of power supplies to control them: powerSupplyName as key and tuple of numbers
                                    # (cout_n, state_binarr) "cout_" is number of PWMouts connected to the same powersupply, "binarr" is binary array with state of PWMouts
   
            #human readable name, chip name, channel number, powSup, max pwm range, dimming steps 
   def __init__(self, name, chip, channel, powrSuply, ch_resolution, st):
      self.name= name                                       #human readable name
      self.chip=ServoPWM.ServoPWM_instance[chip]              #pointer to the PWM chip
      self.channel=int(channel)                             #channel on PWM chip
      self.powerSupplyName = powrSuply                               #name of the relay controlling PowerSupply. pin_relay output_name
      self.last_value=0                             #last value of brighness
      self.last_direction=1                          #last brighnest chnage direction -1 or +1
      self.maximum_pwm=int(ch_resolution)  #max channel power, if it have to be limited. the value is set in red_diode_config_procedure read_dimming()
      self.bright_prcnt=100                                 #allowed brightness percentage 0-100 (use for sleep_mode, deep_night, away functions)
      self.step=st                                          #bright change step
#      self.th_dimm_ident = None                             #set the id of thread: change_brightness_th
      self.change_brightness_run = threading.Event()        #controls thread behavior
      self.change_brightness_run.clear()                    #default state as clear - no thread is running
      self.powerSupplyNumber = 0                            #information of the position in the bit array at PWMout_powersupply
      PWMout.PWMout_instance.update({self.name: self})
   
   
   
   def update(self, name, chip, channel, l_v, l_d, ch_resolution, st):
#         self.name= name                                       #human readable name
      self.chip=ServoPWM.ServoPWM_instance[chip]              #pointer to the PWM chip
      self.channel=int(channel)                             #channel on PWM chip
      self.last_value=int(l_v)                              #last value of brighness
      self.last_direction=int(l_d)                          #last brighnest chnage direction -1 or +1
      self.maximum_pwm=int(ch_resolution)  #max channel power, if it have to be limited. the value is set in red_diode_config_procedure read_dimming()
      self.bright_prcnt=100                                 #allowed brightness percentage 0-100 (use for sleep_mode, deep_night, away functions)
      self.step=st         #bright change step
#         PWMout.PWMout_instance.update({self.name: self})
   
   
   
   @classmethod
   def checkRange(cls, last_val, direction, max_range):  #check if value is within ServoResol and if out changing the direction   
                                       #last_val - the last value
                                       #direction - direction values can be -1 or 1
                                       #max_range - max range for the channel
#      print(cls, last_val, direction, max_range)
      if last_val < 0:       #if value is in range
         direction = 1        #changing direction
         last_val = 0
      elif last_val > max_range:
         direction = -1
         last_val = max_range
      return last_val, direction 
   
   
   @classmethod
   def all_dark(pwmout_cls):
      for key in pwmout_cls.PWMout_instance:
         if not ( key.startswith('alarm') or key.startswith('ALARM') or key.startswith('Alarm') ):
            pwmout_cls.PWMout_instance[key].pwm_min()
   
   @classmethod
   def pwmout(cls,hum_str):            #returns PWMout object by the human readable str name 
      try:
         return cls.PWMout_instance[hum_str]
      except:
         return 0
   
   
   @classmethod
   def servo_powersupply_setup(pwmout_cls):             #building the dictionary of power supplies , run from red_diode_config_procedures/read_dimming()
      for pwm in pwmout_cls.PWMout_instance.values():    
         if pwm.powerSupplyName not in pwmout_cls.PWMout_powersupply.keys():           #if the power supply name is new
            pwmout_cls.PWMout_powersupply.update({pwm.powerSupplyName:(0,0)})          #adding item to dicionary
         else:                                                                            #if power supply name was set up, it just adding to number of powered pwmouts.
            pwmout_cls.PWMout_powersupply[pwm.powerSupplyName] = (pwmout_cls.PWMout_powersupply[pwm.powerSupplyName][0]+1,0)
         pwm.powerSupplyNumber = pwmout_cls.PWMout_powersupply[pwm.powerSupplyName][0]     #adding information about position in the bitarray 
   
      
   @classmethod 
   def powersupply_manage(pwmout_cls,pwmout):
      global rdlog
      count, bitarr = pwmout_cls.PWMout_powersupply[pwmout.powerSupplyName]         #copy to local vars for clear code
      bitarr_last = bitarr                                                          #record initial value to see if changed
#      print("PWM Power 01 {} cnt {} bit {}".format(pwmout.powerSupplyName,count, bitarr))
#      wrnstr = '{} PWM Power 01 {} cnt {} bit {}'.format(time_str(), pwmout.powerSupplyName, count, bitarr)
#      rdlog.warning(wrnstr)
      if pwmout.last_value == 0:                                                    #if pwm is 0, removing its value from bitarray 
         bitarr = ( ( ~(2**pwmout.powerSupplyNumber) & (2**(count+1)-1)) & bitarr)     # Bitwise bit removal ((~0b101 & 0b11111111) & 0b10101110) > '0b10101010'
      elif pwmout.last_value > 0:                                                  #if pwm is >0, adding its value from bitarray 
         bitarr = bitarr | 2**pwmout.powerSupplyNumber       #Bitwise bit add (0 | 2**0) > '0b1'
      if bitarr_last != bitarr:                                                     #if bitarray changed, manage relays connected to power supplies
         pwmout_cls.PWMout_powersupply[pwmout.powerSupplyName]=(count, bitarr)      #changing values of PWMout_powersupply
         if bitarr >0: 
         
            Relay.Relay_instance[pwmout.powerSupplyName].on()             #turn on/off relays - power supply

         elif bitarr == 0: 

            Relay.Relay_instance[pwmout.powerSupplyName].off()          #turn on/off relays - power supply

#      print(" {} PWM Power 02 {} chanel {} lval {} cnt {} bit1 {} bit2 {}".format(time_str(), pwmout.powerSupplyName,pwmout.channel, pwmout.last_value, count, bin(bitarr_last), bin(bitarr)))
#      wrnstr = ' {} PWM Power 02 {} chanel {} lval {} cnt {} bit1 {} bit2 {} '.format(time_str(), pwmout.powerSupplyName,pwmout.channel, pwmout.last_value, count, bin(bitarr_last), bin(bitarr))
#      rdlog.warning(wrnstr)

   @classmethod
   def powersupply_all_stop(pwmout_cls):         #switvhing off all power supplies, called from ServoPWM class when stopping all pwms
      for pwrsup in pwmout_cls.PWMout_powersupply.keys():
         Relay.Relay_instance[pwrsup].off()        #switch off the power supply 
         pwmout_cls.PWMout_powersupply[pwrdup]=(pwmout_cls.PWMout_powersupply[pwrdup][0],0)     #changing the PWMout_powersupply values to keep updated status

   
   def __str__(self):
     return self.name
   
   
   def change_brightness(self,br):        #setting thread to change dim to the brightness of 'br'
      global rdlog
      while self.change_brightness_run.is_set():      #while event set
         for n in threading.enumerate():              #check if thread is not already running adn if yes, clear it to start new
            if n.name == self.name: 
               self.change_brightness_run.clear()    #clear the thread event
               sleep(0.5)
               break
      th_dimm = threading.Thread(name=self.name, target = self.change_brightness_th, args=(br,))
      th_dimm.setDaemon(True)
      self.change_brightness_run.set()    #event set to OK
      th_dimm.start()
      rdstr='{} change_brightness {} from {} to {}'.format(time_str(),self.name, self.last_value, br)
      rdlog.info(rdstr)
#      print("change_brightness end")
   
   
   def change_brightness_th(self,br):        #change dim to the brightness of 'br', waiting at max and min, run as thread 
      global rdlog
      self.last_direction = -1 if br < self.last_value else 1
      while ( self.last_value != br ) and self.change_brightness_run.is_set():
         if self.last_value in range(br-self.step-1,br+self.step+2): self.last_value = br     #if the current brightnes is within Step value to target value, just set target value
         self.last_value, self.last_direction = \
                        PWMout.checkRange(self.last_value + self.step*self.last_direction, self.last_direction, self.maximum_pwm)
#         wrnstr = '{} change_brightness _thread {}: lastVal {} br {}'.format(time_str(),self.name, self.last_value, br)
#         rdlog.warning(wrnstr)
         PWMout.powersupply_manage(self)              #manage power supplies
         self.chip.pwm.set_pwm(self.channel, 0, self.last_value*self.bright_prcnt//100)   #set_pwm() is function from library ServoPi import PWM
      
      if br < self.step : self.last_value = 0
      if br > self.maximum_pwm - self.step: self.last_value = self.maximum_pwm
#      self.chip.set_bright(self.channel, self.last_value*self.bright_prcnt//100)   #make sure the self.last_value is 0 or max if required.
      
      self.chip.pwm.set_pwm(self.channel, 0, self.last_value*self.bright_prcnt//100)   #set_pwm() is function from library ServoPi import PWM

      PWMout.powersupply_manage(self)

      self.change_brightness_run.clear()     #clear the thread event
      
      
#      rdstr='{} change_brightness_iter last valu {} direction {} br {} max {}'.format(self.name, self.last_value, self.last_direction,br,self.maximum_pwm)
#      print('{} change_brightness_iter last valu {} direction {} br {} max {}'.format(self.name, self.last_value, self.last_direction,br,self.maximum_pwm) )

   
   def set_brightness(self,br_pc):        #change brightness to br - br is % of full brightness
      global rdlog
      self.bright_prcnt = br_pc
      self.change_brightness(self.maximum_pwm)
      rdstr='{} PWMout set_p_brightness {} {}'.format(time_str(),self.name, br_pc)
      rdlog.info(rdstr)
   
   def pwm_pass(self):
      pass
   
   def dim(self):          #set channel to the new value of brightness
      self.change_brightness(self.last_value + self.step*self.last_direction)
   
   
   def pwm_max(self):      #setting channel to max
      self.bright_prcnt = 100
      self.change_brightness(self.maximum_pwm)
   
   
   def pwm_min(self):      #setting channel to min
      self.change_brightness(0)
   
   
   def pwm_tog(self):      #channel on or off - toging  
      if self.last_value > 0:
         self.pwm_min()
      else:
         self.pwm_max()
   
   
   
   
class ServoPWM:
   
   '''
                 to use PCA9685 Servo PWM for RPi https://www.abelectronics.co.uk/p/72/servo-pwm-pi 
                 The Servo controls PWM signals to dim lights/LED 
   '''
   #              ServoPWM_instance : Class dictionary: list of  PCA9685 (instances). 
   #               ServoPWM objects are created automaticaly - there is no object identity
   ServoPWM_instance = {}  #list of instances key: chip name, pointer to the object
   
   
   def __init__(self, name, i2cbus, i2c_addres, channels, sresolution):
            #  chip-name | bus-number | adres-on-bus | max num of channels 1-16 |servo range  
      self.name=name    #human readable name of the output, mind DRA40 connected to channel 1
      self.bus=int(i2cbus)   #i2c bus connected to the Servo
#      if i2cbus not in i2c.keys():
#         i2c[i2cbus] = smbus.SMBus(i2cbus)   #opening i2c bus if neccecery
      self.bus_adrs=int(i2c_addres,16)      #i2c bus adres to access the servo
      self.channels=int(channels)        #max number of channels on the Servo chip
      ServoPWM.ServoPWM_instance.update({self.name: self})
      self.ServoResol=int(sresolution)          #servo pwm resolution 2**n, for PCA9685 maximum is 4095 or 2**12
      self.pwm = PWM(self.bus_adrs, self.bus)       #setting the pwm object accordng to imported module  ServoPi library ServoPi import PWM
      self.set_pwm_outputs()        #set pwm general parameters and all channels to 0

   
   
   def __str__(self):
        return self.name
   
   @classmethod
   def servopwm(srv_cls,name_str):            #returns Object pointer, argument is name string
      try:
         return srv_cls.ServoPWM_instance[name_str]
      except:
         return 0 
         
   @classmethod
   def servo_stop_pwm(srv_cls):            #stops all PWM, set to 0 and set the servo to sleep
#      sleep(5)
      for key in srv_cls.ServoPWM_instance:
         srv_cls.ServoPWM_instance[key].pwm.set_all_pwm(0,0) 
         srv_cls.ServoPWM_instance[key].pwm.sleep()
         sleep(0.02)
      PWMout.powersupply_all_stop()       #switching off power supplies
         

                              #check if the device is powered
   def check_pwmservo_is_powered(self):
      i=3
      r=0
      while i>0:
         if self.pwm.is_sleeping():
            self.pwm.wake()
            sleep(0.3)
            i-=1
         else:
            r=1 
            i=0
      return r
      
      
   def set_pwm_outputs(self,):      #initiate servo chip parameters
      global rdlog
      #
      if self.check_pwmservo_is_powered():
         self.pwm.set_pwm_freq(1000)
         self.pwm.set_all_pwm(0,0)            #dimming all channels to 0
      else: rdlog.error("PWM SERVO is not waking up")
   
   
class MCP23017:
   
   '''
                 to manipulate MCP23017 chips on board. 
   
   name: str: chip human readable name of the chip, example c_B1_20 - for chip on BUS 1 with adres 0x20
   bus: int: I2C bus number, default 1, but it is possible to set up multiple i2c busses or use another bus,
   
                     DO NOT USE BUS 0 (ZERO)!!!!
           unlesss you are absolutely sure what you are doing
           
           
   i2c_addres : hex: chip adres on the bus, can be 8 different addresses from 0x20 to 0x27
   MCP_instnc : Class dictionary: list of  MCP23017 objects (instances). They are created automaticaly as there is no ident
   ConReg_dic : Class dictionary: dictionary of adreses of Control Registers.
   Pin adresing:
         The MCP class here is using word read/write, meaning there is no side A and B pins (see below  comment on GpioAdr_dic)
         Register adreses are taken from  ConReg_dic dictionary and Pin adressing is simply 2**0 - 2**15 or 
         from '0b0000000000000001' to '0b1000000000000000' - alwas only one bit on(1).
   
   self.inputs={}                #inputs dictionary, key: pin (binary), value: butt pointer
   self.inputs_b              #binary representation of inputs
   self.oposit_logic           #binary representation of oposit logic pins
   
   @classmethod    def chip(mcp_cls,name_str):            #returns Object pointer, argument is name string
   def read_chip(self, ConRe):      read from chip, to be used to read input pins or get the chip status
   def write_chip(self, ConRe, val):      write to chip, 
   def pin_adr(self, pin):       return pin hex adres,argument
   def set_input(self,pin, input_dev_pointer):     setting inputs pin
   def set_output(self,*pin):    clear inputs pin - if no argument provided all inputs will be cleared    
   def togle_output(self,*pin):     togle output status for pins or for all
   def op_log(self,pin):   set up oposit logic for pin, usefull for contactrons or reverse logic inputs
   def norm_log(self,pin):    set up normal logic for pin
   def set_output_on(self,*pin):    set outpin pin ON
   def set_output_off(self,*pin):      set outpin pin OFF
   def is_output(self, *pin):  check if PIN is IN or OUT, for single pin in argument returns True if pin is OUTPUT
#                   return string with the whole list if more pins or no pins in argument, 
   def is_input(self, *pin):  check if PIN is IN or OUT, for single pin in argument returns True if pin is INPUT
                    return string with the whole list if more pins or no pins in argument, 
   
   def is_output_on(self,pin):    returning status of and if Output. reverse logic handled in Relay classs
   

   '''
   
#              MCP23017_instance : Class dictionary: list of  MCP23017 objects (instances). 
#              MCP23017 objects are created automaticaly - there is no object identity
   MCP23017_instance = {}
   
#              ConReg_dic - PIO_Control Registers: same names, values and function as described in 
#              MCP27017 dosc https://ww1.microchip.com/downloads/en/DeviceDoc/20001952C.pdf 
#              The MCP23017 is using word read/write, meaning there is no side A and B pins
   ConReg_dic={
         'GPPU':   0x0C,
         'IODIR':  0x00,
         'OLAT':   0x14,
         'GPIO':   0x12,
         'IPOL':   0x02,
         'GPINTEN':0x04,
         'INTCON': 0x08,
         'DEFVAL': 0x06,
         'INTF':   0x0E,
         'INTCAP': 0x10
          }
          
#     The MCP23017 is using word read/write, meaning there is no side A and B pins. the below is for refernece only
#     Register adreses are taken from  ConReg_dic dictionary and Pin adressing is from 2**0 to 2**15 or 
#      from '0b0000000000000001' to '0b1000000000000000'
# GPIO_Adres number: GPIO,  adres, 
#   GpioAdr_dic={
#   0:  ('A0', 0x01),
#   1:  ('A1', 0x02),
#   2:  ('A2', 0x04),
#   3:  ('A3', 0x08),
#   4:  ('A4', 0x10),
#   5:  ('A5', 0x20),
#   6:  ('A6', 0x40),
#   7:  ('A7', 0x80),
#   8:  ('B0', 0x01),
#   9:  ('B1', 0x02),
#   10: ('B2', 0x04),
#   11: ('B3', 0x08),
#   12: ('B4', 0x10),
#   13: ('B5', 0x20),
#   14: ('B6', 0x40),
#   15: ('B7', 0x80)
#   }
   
   def __init__(self, name, i2cbus, i2c_addres):
      self.name=name    #str: chip human readable name
      self.bus=int(i2cbus)   #int: I2C bus number
#      if i2cbus not in i2c.keys():
#         i2c[i2cbus] = smbus.SMBus(i2cbus)
      self.bus_adrs=int(i2c_addres,16)       #hex adres on the i2c bus
      MCP23017.MCP23017_instance.update({self.name: self})
      self.clean()
      self.inputs_b=0               #binary representation of inputs
      self.inputs={}                #inputs dictionary, key: pin, value: butt pointer
      self.oposit_logic=0           #binary representation of oposit logic pins
   
   def __str__(self):
        return self.name
   
   @classmethod
   def chip(mcp_cls,name_str):            #returns Object pointer, argument is name string
      try:
         return mcp_cls.MCP23017_instance[name_str]
      except:
         return 0 
         
   @classmethod
   def clean_all(mcp_cls):    #resetting all chips
      for key in mcp_cls.MCP23017_instance:
         chip=mcp_cls.MCP23017_instance[key]
         chip.clean()
#      print('chips are clean')
      
         
   def clean(self):                 #cleaning the MCP23017 chip setup. 
      self.write_chip('GPPU',  0b0) #no pull ups for inputs
      self.write_chip('IODIR', 0b0) #define all as output
#      self.write_chip('IODIR', 0b11111111111111111) #define all as input
      
      self.write_chip('OLAT',  0b0) #close all outputs
      self.write_chip('IPOL',  0b0) #reset logic to normal
#      print('chip {} clean'.format(self.name))
   
   def check_cond(self):  #repeated code in check()
#      global rdlog
#      if not(( self.read_chip('IODIR') == self.inputs_b ) and ( self.read_chip('IPOL') == self.oposit_logic )):
#         lgstr = ' {} chip {} pokazał {} a powinien {}    oraz {} a powinien {}'.format(time_str(), self.name,self.read_chip('IODIR'),self.inputs_b,self.read_chip('IPOL'),self.oposit_logic)
#         rdlog.error(lgstr)
      return ( self.read_chip('IODIR') == self.inputs_b ) and ( self.read_chip('IPOL') == self.oposit_logic )     #if MCP23017 config is OK do nothing
   
   
   def check(self):  #checking the healt of MCP23017
      global rdlog
      while not self.check_cond():      #if MCP23017 config is OK - do nothing
         lgstr = ' {} chip {} pokazuje błąd - restart'.format(time_str(), self.name)
         rdlog.error(lgstr)
         sleep(5)
         exit(99)    #exiting the red_diode and restart it from crontab schedule
#         if not self.check_cond():      #if MCP23017 config is OK - do nothing
#            VButt.butt('re_config').v_push()
#            lgstr = ' {} chip {} naprawion !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'.format(time_str(), self.name)
#            rdlog.error(lgstr)
   
#                                read from chip, to be used to read input pins
   def read_chip(self, ConRe):
      global rdlog
      try:
#         global i2c
#         print('read i2c %d  chip %s adres %s %s result %d %s time %f' % (self.bus, hex(self.bus_adrs), ConRe, hex(self.ConReg_dic[ConRe]),999, bin(999), perf_counter()))
#         r=i2c[self.bus].read_word_data( self.bus_adrs, self.ConReg_dic[ConRe])
#         print('read i2c %d  chip %s adres %s result %d %s time %f' % (self.bus, hex(self.bus_adrs), hex(self.ConReg_dic[ConRe]),r, bin(r), perf_counter()))
#         return r
         return i2c[self.bus].read_word_data( self.bus_adrs, self.ConReg_dic[ConRe])
      except:
         lgstr = ' {} read_chip ERROR i2c {}  chip {} adres {} time {}'.format(time_str(), self.bus, hex(self.bus_adrs), ConRe, perf_counter())
         rdlog.error(lgstr)
         return 0
   
#                             return pin binary value adres,argument 0..15
   def pin_adr(self, pin):
      global rdlog
      if pin in range(0,16): 
         return 2**pin         
      else:
         lgstr = ' {} error pin {} adres '.format(time_str(), pin)
         rdlog.error(lgstr)
         return 0
         
#                                   write to chip, 
   def write_chip(self, ConRe, val):
      global i2c, rdlog
      try:
#         print('write i2c %d  chip  %s adres %s vbin %s vhex %s' % (self.bus, hex(self.bus_adrs), hex(self.ConReg_dic[ConRe]), hex(val), bin(val)))  #test
         i2c[self.bus].write_word_data( self.bus_adrs, self.ConReg_dic[ConRe], val)
         return 1
      except:
         lgstr = ' {} write_chip ERROR {} {}'.format(time_str(), ConRe, val)
         rdlog.error(lgstr)
         return 0
      
#                       setting inputs pin: 0-15, input_dev_pointer - pointer to button
   def set_input(self,pin, input_dev_pointer):
      global rdlog
      try:
         pin_b = self.pin_adr(pin)
         self.write_chip('IODIR',  ( pin_b |  self.read_chip('IODIR') )) #define as input
#         self.write_chip('GPPU', ( pin_b |  self.read_chip('GPPU') ) ) #add pull ups for inputs
         self.write_chip('GPINTEN', ( pin_b |  self.read_chip('GPINTEN') ) ) #add to INTERUPS pins
         self.write_chip('INTCON', ( (~(pin_b) & 0xffff) &  self.read_chip('INTCON') ) ) #add to INTERUPS on-change (not DEFAULT)
         self.inputs.update({pin_b:input_dev_pointer})                      #update input list for referencing inputs
         self.inputs_b |= pin_b
      except:
         lgstr = ' {} set_input ERROR {}'.format(time_str(), pin)
         rdlog.error(lgstr)
         
#                       clear inputs pin
#                       if no argument provided all inputs will be cleared        
   def set_output(self,*pin):
      global rdlog
      try:
         if not len(pin):            #if no pin passed as parameters, all pins will be outputs
            pin=range(0,16)
         for p in pin:
            if p in range(0,15):
   #         print('set output controller', p)
               pin_b = self.pin_adr(p)
               self.write_chip('IODIR',  ((~(pin_b) & 0xffff) & self.read_chip('IODIR'))) 
               self.write_chip('GPPU',  ((~(pin_b) & 0xffff) & self.read_chip('GPPU'))) 
                       #Bitwise bit removal ((~0b101 & 0b11111111) & 0b10101110) > '0b10101010'
               self.norm_log(p) 
                        #forcing norm logic
               try:
                  del self.inputs[pin_b]  #removes from input list 
                  self.inputs_b = ((~(pin_b) & 0xffff) & self.inputs_b )
               except:
                  pass 
      except:
         lgstr = ' {} set_output ERROR {} {}'.format(time_str(), pin, self.name)
         rdlog.error(lgstr)
          
#                             togle output status for pins or for all
   def togle_output(self,*pin):
      if not len(pin):            #if no pin passed as parameters, 
         pin=range(0,16)
      for p in pin:
         if self.is_output(p):
            self.write_chip('OLAT', (self.read_chip('OLAT') ^ self.pin_adr(p))) #togle with bin XOR
   
#                    set up oposit logic for pin, usefull for contactrons or reverse logic inputs
   def op_log(self,pin):
      pin_b = self.pin_adr(pin)
      self.write_chip('IPOL',  (self.read_chip('IPOL') | pin_b))
      self.oposit_logic |= pin_b
                  #in/out logic are ConRegs 02 and 03. value 1 is oposit 0 is normal
                  #Bitwise OR bin(0b110101 | 0b001000) > '0b111101'
   
   
#                    set up normal logic for pin
   def norm_log(self,pin):
      pin_b = self.pin_adr(pin)
      self.write_chip('IPOL',  ((~(pin_b) & 0xffff) & self.read_chip('IPOL')))
      self.oposit_logic = ((~(pin_b) & 0xffff) & self.oposit_logic  )
                  #in/out logic are ConRegs 02 and 03. value 1 is oposit 0 is normal
                  #Bitwise bit removal ((~0b101 & 0b11111111) & 0b10101110) > '0b10101010'
   
#                             set outpin pin ON
   def set_output_on(self,*pin):
      if not len(pin):            #if no pin passed as parameters, 
         pin=range(0,16)
      for p in pin:
         self.write_chip('OLAT',  (self.read_chip('OLAT') | self.pin_adr(p))) #add open output by binary OR
   
#                             set outpin pin OFF
   def set_output_off(self,*pin):
      if not len(pin):            #if no pin passed as parameters, 
         pin=range(0,16)
      for p in pin:
         self.write_chip('OLAT', ((~(self.pin_adr(p)) & 0xffff) & self.read_chip('OLAT')))
                  #Bitwise bit removal ((~0b101 & 0b11111111) & 0b10101110) > '0b10101010'
   
#                    check if PIN binary is OUT, for single pin in argument returns True if pin is OUTPUT
   def is_output(self, pin):
      try:
         return  (self.read_chip('IODIR') & pin) == 0
      except:
         return str('is_output error', pin)
   
   
   def is_input(self, pin):
      global rdlog
      try:
         return  (self.read_chip('IODIR') & pin) == pin
      except:
         lgstr = " {} is_input error {}".format(time_str(), bin(pin))
         rdlog.error(lgstr)
         return  lgstr
   
   
#                    check if PIN binary is IN, returns True if pin is INPUT and is active
   def is_input_active(self, pin):
      global rdlog
      if self.is_input(pin):
         try:
            return (self.read_chip('GPIO') & pin) == pin
         except:
            lgstr = ' {} is_input_active error {}'.format(time_str(), str(pin))
            rdlog.error(lgstr)
            return  lgstr
   
   
                           # returning status of an Output. reverse logic handled in Relay classs
   def is_output_on(self,pin):
      global rdlog
      if self.is_output(pin):
         try:
            return ( self.read_chip('OLAT') & pin) == pin
         except:
            lgstr = ' {} is_output_on error {}'.format(time_str(), str(pin))
            rdlog.error(lgstr)
            return  lgstr




######################################################################################
#end of Class def
######################################################################################





