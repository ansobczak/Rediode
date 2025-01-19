#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
The below procedures defines actions and behaviors on pressed buttons

depending on the cycle/change version picking the way binary status is changed 
   seq_0 do nothing
   seq 1 100  010 001 000 cycle
   seq 2 100 010 110 001 101 011 111 000 cycle
   seq 3 000 100 110 111 000 cycle
   seq 4 all on/off - if at least one is on all will be off first, than next push will on all 
   seq 5 all off
   seq 6 all on
   seq 7 dim LED via PCA9685 Servo PWM
   seq_8: delay action, parameters as list: delay time in seconds, action, outputs
   seq_9: togle ouptups and set the motion detection on. typical short press 
   seq_10: set ouptups off and set the motion detection off, untill set on - typical use: long press )
   #togle ouptups and set the motion detection on. typical short press
   v_pres for virtual, for instancefor MQTT buttons
"""

from time import  perf_counter, sleep, time, localtime, gmtime
from threading import Thread, Event
from sun_rise_set import f_sun_rise_set #,sun_main
from red_diode_clases import  End_Run, MCP23017, Relay, Butt, VButt, PWMout, time_str, Alarm #,MovDetected, TempSensors, ServoPWM
from red_diode_MQTT_class import MQTT_client

#global alarmStartDelay, AlarmLong, alarmEnterDelay
#                 #global in red_diode_clases.py
#                 #global parameters for alarm
                 
#global seq_14_ev
#seq_14_ev=Event() #event controlling blinking



#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

global seq_12_delay #global var for sequence 12 delay, used for relays. the value shold be 0.5-1
global seq_12_standard_delay
global seq_12_komfort_delay

seq_12_delay = 1
seq_12_standard_delay = 1
seq_12_komfort_delay = 3

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

global rdlog     #global logging object

def procedures_set_log(log_):
   global rdlog
   rdlog=log_


#def time_str():      #return string with time in YYYY-MM-DD_HH-MM-SS format
#   return str("{}-{:02d}-{:02d}_{:02d}-{:02d}-{:02d}".format(\
#   localtime()[0],\
#   localtime()[1],\
#   localtime()[2],\
#   localtime()[3],\
#   localtime()[4],\
#   localtime()[5]))


def outstate(outputs): #checking which outputs are on and return Led_bit
   Led_bit=0                     #set 0 value for start
          #set binary lenght trim (this have to be 0b0111 for 3 elements, 0b01111 for 4 elemnts etc.)   
   n=0
   for output in outputs:
      try:
         if Relay.relay(output).state:
            Led_bit+=2**n           #constructing bit representation of light on or off
      except:
         try: 
            if PWMout.pwmout(output).last_value !=0:
               Led_bit+=2**n 
         except: pass
      n+=1
#   print("led bit result {} {}".format(Led_bit,outputs))
   return Led_bit

def out_on(out):        #set the output on
   try: Relay.relay(out).on()
   except:
      try: PWMout.pwmout(out).pwm_max()
      except: pass

def out_off(out):    #set the output off
   try: Relay.relay(out).off()
   except:
      try: PWMout.pwmout(out).pwm_min()
      except: pass

def out_togle(outputs, Led_bit):    #togle output
   n=0
   for output in outputs:
      if Led_bit & (2**n): 
         out_on(output)
      else:
         out_off(output)
      n+=1

def seq_0(num_par, action, outputs): #do nothing or even less
   pass

def seq_1(num_par, action, outputs):     #seq 1 100  010 001 000 cycle
   Led_bit = outstate(outputs) #checking which outputs are on and keep this in Led_bit
   Led_bit = ((Led_bit << 1 )  if Led_bit > 0 else 1)
   Led_bit = Led_bit & (2**len(outputs) -1)  #this make sequence 100  010 001 000 
#   print('test seq1 {} {:>16b}'.format(outputs, Led_bit))
   out_togle(outputs, Led_bit)


def seq_2(num_par, action, outputs):     #seq 2 100 010 110 001 101 011 111 000 cycle
   Led_bit = outstate(outputs) #checking which outputs are on and keep this in Led_bit
   Led_bit = (Led_bit+1 ) & (2**len(outputs) -1) 
   out_togle(outputs, Led_bit)


def seq_3(num_par, action, outputs):     #seq 3 000 100 110 111 000 cycle
#   print("seq 3 start",num_par, action, outputs)
   Led_bit = outstate(outputs) #checking which outputs are on and keep this in Led_bit
   Led_bit = (Led_bit<<1)+1 if ((Led_bit << 1) < (2**len(outputs))) else 0
   Led_bit = Led_bit & (2**len(outputs) -1) 
#   print("seq 3 midle", bin(Led_bit))
   out_togle(outputs, Led_bit)



def seq_4(num_par, action, outputs):     #seq 4 all on/off (togle)
#   print("seq 4")
   Led_bit = outstate(outputs) #checking which outputs are on and keep this in Led_bit
   Led_bit = (2**len(outputs) -1) if Led_bit == 0 else 0 
   out_togle(outputs, Led_bit)


def seq_5(num_par, action, outputs):     #seq 5 all off
   for output in outputs:
      out_off(output)
         
def seq_6(num_par, action, outputs):     #seq 6 all on
#   print("seq 6 output", outputs)
   for output in outputs:
      out_on(output)

def seq_7(num_par, action, outputs):  #seq 7 PWM control - diming LED
#   if len(outputs)>0:
#   print("sequence 7 outputs {}".format(outputs))
   for output in outputs:
      try: 
         PWMout.pwmout(output).dim()
      except: pass
      

def seq_8_th(delay, action, outputs):  #threading function for delay action seq_8, parameters: delay time in seconds, action (dimm, on, off, pass, togle), outputs
   Led_bit = outstate(outputs) #checking which outputs are on and keep this in Led_bit
   secnds=0
   cond=1
   slptime=0.2
   while (secnds < delay) and cond:       #runs until secnds is smaller that delay and cond is true
      sleep(slptime)
      secnds+=slptime
      cond = (Led_bit == outstate(outputs))     #cond is true if output status did not change
   if cond:    #executes action only if output state did not changed.
      action_executor( 0, action, outputs) #function execuitng the action

def seq_8(num_par, action, outputs):  #delay action, parameters as list: delay time in seconds, action (dimm, on, off, pass, togle, ), outputs
#dimm - , on, off, pass, togle, off_opt 
#   print('seq_8',num_par, action, outputs)
   num_par=float(num_par)
   th_seq_8 = Thread (name='seq_8', target=seq_8_th, args=(num_par, action, outputs, ) )
   th_seq_8.setDaemon(True)
   th_seq_8.start()
#   th_seq_8.join()      #experiment

def seq_9(num_par, action, outputs):  #on/off ouptups and set the motion detection on. typical short press 
   seq_4(num_par, action, outputs)   
   for out in outputs: 
      Butt.tog_motion_detection(out,1)

def seq_10(num_par, action, outputs): #set ouptups off and set the motion detection off, untill set on - typical use: long press )
   seq_5(num_par, action, outputs)
   for out in outputs: 
      Butt.tog_motion_detection(out,0)
   seq_5(num_par, action, outputs)


def seq_11(num_par, action, outputs):  #set outputs on for num_par seconds or turns all off
   seq_4(num_par, action, outputs)
   seq_8(num_par, 'off', outputs)


def seq_12(num_par, action, outputs):  #s12: seq_12: turn on for seq_12_delay - to use with roleta or alarm
#   global seq_12_delay
   for output in outputs:
      seq_6(0,"", [output])
      seq_8(num_par, 'off', [output])
      sleep(0.2)
#      print("seq 12 {} {} {}".format(num_par, 'off', [output]))
            
def seq_13(num_par, action, outputs):  #set outputs on for num_par seconds 
   seq_6(num_par, "", outputs)
   seq_8(num_par, 'off', outputs)

  

def seq_14_th(num_par, action, outputs):  #blinks outputs for num_par seconds, blink last for seq_12_delay (1 sec)
   global seq_12_delay 
   start_time = perf_counter()
#   print(num_par, action, outputs)
   while perf_counter()-start_time < num_par: 
#      print("seq 14 inside \r", perf_counter(),end=" ")
      seq_4(num_par, action, outputs)
      sleep(seq_12_delay)
      
def seq_14(num_par, action, outputs):  #blinks outputs for num_par seconds, blink last for seq_12_delay (1 sec)
   num_par=float(num_par)
   th_seq_14 = Thread (name='seq_14', target=seq_14_th, args=(num_par, action, outputs, ) )
   th_seq_14.setDaemon(True)
   th_seq_14.start()


def seq_15(num_par, action, outputs):  #tbd
   pass



def v_pres(param):   #setting the outputs for virtual button. Parameters are: an action ( on, off, togle, dimm ) + numeric value (delay time or dimm) + output list
   global rdlog
   lgstr=(' {} vpress par {}'.format(time_str(), param))
   rdlog.info(lgstr)
   if len(param)>0:
      action=param[0] #leading parameter is action
      nume_par=param[1]
#      outputs=param[1:][0] #outputs or outputs - optional led dimm value in % 0-100
      outputs=param[2:] #outputs or outputs - optional led dimm value in % 0-100
      action_executor(nume_par, action, outputs)    #function execuitng the action
   else: 
      lgstr=('{} vpress ERROR {}'.format(time_str(), param))
      rdlog.info(lgstr)
      
      
      
def action_executor(nume_par, action, outputs):        #executes actions for v_press and seq_8
   '''
   action can be:
   dimm
   roleta, delay
   pass, on, off, togle
   '''
   global rdlog
   global seq_12_standard_delay, seq_12_komfort_delay
   err1 = ' '   
   lgstr=(' {} action_executor nume_par: {}, action: {}, outputs: {}'.format(time_str(), nume_par, action, outputs))
   rdlog.info(lgstr)
   if action == 'dimm':
      for out in outputs[:]:
         try:
#            f={
#            'dimm':PWMout.pwmout(out).set_brightness
#            }[action]
#            f(int(outputs[-1]))
            PWMout.pwmout(out).set_brightness(int(nume_par))
         except: err1+="dim error "
   elif action == "roleta" or action == "roleta_komfort" or action == "delay":
      try:
         seq_f={
         'roleta': seq_12,
         'roleta_komfort': seq_12,
         'delay': seq_13
         }[action]
         if action == 'roleta_komfort': nume_par = seq_12_komfort_delay
         elif  action == 'roleta': nume_par = seq_12_standard_delay
         seq_f(nume_par,outputs[0],outputs)      
      except: err1+="roleta/delay error "
   elif action in ["ARM_ALARM_V", "DARM_ALARM_V"]:
      try:
         seq_f={
         'ARM_ALARM_V' :arm_alarm,
         'DARM_ALARM_V':darm_alarm
         }[action]
         seq_f(nume_par,outputs[0],outputs)
      except: err1+="ALARM err "
   else:
      for out in outputs:
         try:
            {
            'pass': Relay.relay(out).r_pass,
            'on': Relay.relay(out).on,
            'off': Relay.relay(out).off,
            'togle': Relay.relay(out).togle
            }[action]()
         except: err1+="Relay_err1 {}".format(out)
         try:
            {
            'pass':PWMout.pwmout(out).pwm_pass,
            'on': PWMout.pwmout(out).pwm_max,
            'off': PWMout.pwmout(out).pwm_min,
            'togle': PWMout.pwmout(out).pwm_tog
            }[action]()
         except: err1+="PWM_err1 {}".format(out)
         if not len(err1): 
            lgstr=' {} action_executor result {} '.format(time_str(),err1)
            rdlog.info(lgstr)



def arm_alarm(action, nume_par, outputs):      #arming alarm: 'ARM_ALARM' or 'ARM_ALARM_V': arm_alarm, set in def read_config_inputs in red_diode_config_procedures.py
   global rdlog
#   action, nume_par, outputs = in_par
   Alarm.arm_alarm_class_function(seq_4,seq_6,outputs)

   lgstr=' {} ALARM ARMING done {} {} {}'.format(time_str(), action, nume_par, outputs)
   rdlog.info(lgstr)
   #print(lgstr)
   MQTT_client.mqtt_obj.MQTT_publish('red/alarm', lgstr, True) 

   
   
def darm_alarm(action, nume_par, outputs):     #disarming alarm: 'DARM_ALARM' or 'DARM_ALARM_V': darm_alarm, set in def read_config_inputs in red_diode_config_procedures.py
   global rdlog
   Alarm.darm_alarm_class_function(seq_5,seq_13,outputs)

   lgstr=' {} ALARM DISARM done {} {} {}'.format(time_str(),action, nume_par, outputs)
   rdlog.info(lgstr)
   MQTT_client.mqtt_obj.MQTT_publish('red/alarm', lgstr, True)
   #print(lgstr)
   
def alarm_function(param):       #run when alarm is detected 
   global rdlog

#   lgstr=" {} alarm_function parameter: param {} AlarmLong {} alarm_outputs {}".format(time_str(), param, Alarm.alarm_Longivity, Alarm.alarm_outputs)
#   rdlog.info(lgstr)
#   #print(lgstr)

   if len(param)>0:
      action=param[0] #leading parameter is action

   MQTT_client.mqtt_obj.MQTT_publish('red/alarm','ALARM: INTRUDER DETECTED {} {}'.format(str(action), time_str()), True)

   Alarm.class_alarm_function(action)

   
###############################################   lgstr = " {} ".format(time_str())
   
   
                                 #checking if there is a day or nigh and changing setting when required
                                 #running as separate thread
#def day_night(longitude=-21.46, latitude=52.25, sun_rise_d=0, sun_set_d=0 ):
def day_night(longitude, latitude, mqtt_ob, sun_rise_d=0, sun_set_d=0 ):
   EarthRotating = 1
   asd = False    #already started day
   asn = False    #already started night
   while EarthRotating:
      day, night, sl_t, sunrise, sunset = f_sun_rise_set(longitude, latitude, sun_rise_d, sun_set_d )  
      #day, night - bool, sl_t - minutes to the sunrise or sunset
      if day and not night and not asd:
         for vbt in VButt.Butt_instance.values():
            if vbt.auto_night_off:
               vbt.v_push()
         asd=True 
         asn=False
      elif not day and night and not asn: 
         for vbt in VButt.Butt_instance.values():
            if vbt.auto_night_on:
               vbt.v_push()
         asd=False 
         asn=True
      else:
         pass
#         print("day_night info: day {} nigh {} asd {} asn {}".format(day, night, asd, asn))
      w=5                 #w is minutes to wait
      sl_t = sl_t*60 if sl_t < w else w*60
      if day:   mqtt_ob.MQTT_publish('red/sun','sunrise at {:02}:{:02} sunset at {:02}:{:02} sunset in {:02} hr {:02} min'.format(sunrise[0],sunrise[1], sunset[0],  sunset[1], sl_t//60, sl_t%60), True) 
      if night: mqtt_ob.MQTT_publish('red/sun','sunrise at {:02}:{:02} sunset at {:02}:{:02} sunrise in {:02} hr {:02} min'.format(sunrise[0],sunrise[1], sunset[0],  sunset[1], sl_t//60, sl_t%60), True) 
      sleep(sl_t)    #  line #      sleep(sl_t * 60  )


def matcher(schedule,lt):   #test if the cron-like elements match, schedule is cron parameter [* * 8 7 * * *], lt is local-time parameter
#   print("matcher par:", schedule,lt, type(schedule),type(lt) )
   if not isinstance(lt, (int)): return False # if not int then this is error
   if isinstance(schedule, (int)) and lt == schedule: return True # if element is integer and match, 2 = 2
   elif isinstance(schedule, (str)):      #if element is string
      if schedule.count("/"):             #if element have '/' (like */15) means every 15 minutes
         if lt%int(schedule.split('/')[-1]) :  return False    # so checking if */15 is ok for 0,15,30,45 minutess, becouse 30%15 is 0-false
         else: return True          #and becuse 30%15 is false we return here True :)
      elif schedule.count("*"): return False    #if there is ONLY '*' return False couse we want to do nothing
      else: return False                     #in any other case 
   else: return False
      

def sch_match(schedule, lt):  ##test if the cron-like line match, schedule is cron parameter [* * 8 7 * * *], lt is local-time parameter
   match = True
   for i in range(0,7):
      if schedule[i] == '*': 
         pass      #skip the * only
      else:
         r2= matcher(schedule[i],lt[i])
         match = match and r2
   return match

#   tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday


def scheduler_eng(mqtt_ob, rdlog): #run as separate thread, trigers scheduled actions at the predefined time
   EarthRotating = 1
   lt_struct=[]
   rdlog.info("sheduler threat is runing")
   while EarthRotating:
      lt_struct = list(localtime()[1:8])        #produce list from time tuple with tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday as we need those only
      last_iter = perf_counter()
      for vbt in VButt.Butt_instance.values():
         if vbt.schedule_b:
            if sch_match(vbt.schedule_s,lt_struct): 
               vbt.v_push()
               lgstr="Schedule {} run mon {:02} day {:02} time {:02}:{:02}".format(vbt.name,lt_struct[0],lt_struct[1],lt_struct[2],lt_struct[3])
               rdlog.info(lgstr)
#               print(lgstr)
               mqtt_ob.MQTT_publish('red/sch', lgstr, True) 
      while perf_counter()-last_iter < 60: 
         sleep(0.5)
         pass # slows down but not like sleep, slpt should be 0.002  up to 0.3 but be carefull
#      lt_struct=[]


def rolling(t, how_long):        #helper function for testing, keeping the app running for defined time in minutes or endlessly in loop if 0 provided as parameter
 
#   if not End_Run.WhatEndRun(): 
   if not End_Run.end_run:
      if how_long != 0:
         return True if ( ( perf_counter()-t ) < how_long ) else False
      else:
         return True
   else: 
#      print("global End_Run")
      return False         #ending rediode due to MQTT payload




##################################################################
#threads to manage buttons

##################################################################


                  #Bitwise bit removal ((~0b101 & 0b11111111) & 0b10101110) > '0b10101010'


def MCP23017_reading_thread(slpt=0.0001, how_long=60):      #MCP23017 chips thread that scans inputs
   
   t=perf_counter()           #previous time, to calculate time difference between events
#   slpt=0.0001              #0.01  - experiment with values if events are mising, typically values 0.01-0.04, depend on hardware
#   how_long=60          #ile sekund ma działać
      
      
   chips = MCP23017.MCP23017_instance
   
   for c in chips.values():                   #initiate input iterators
      for b in c.inputs.values():
         if b.is_mov or b.is_night_only_motion:            #check if motion or nighMotion
            b.butt_action_iterator = b.motion_action((0,0,0))  #initiate iterator
         elif b.is_con:                      #check if contactron
            b.butt_action_iterator = b.contactron_action((0,0,0))
         else:                               #else is normal push-button
            b.butt_action_iterator = b.butt_action((0,0,0))
         b.butt_action_iterator.send(None)
   
   last_read=perf_counter()


   while rolling(t, how_long):
      while perf_counter()-last_read < slpt:  # slows down but not like sleep, slpt should be 0.002  up to 0.3 but be carefull
         pass 
      for c in chips.values():      #for every chip
         c.check()      #check MCP23017 chip status and repair configuration if required.
         
#         INTF, GPIO, INTCAP = c.read_chip('INTF'), c.read_chip('GPIO'),c.read_chip('INTCAP')
         
         INTF, GPIO = c.read_chip('INTF'), c.read_chip('GPIO')
         
#         print ('  chip: {} INTFlag: {:>4x} GPIO: {:>4x} INTCAP: {:>4x}'.format(c, INTF, GPIO, INTCAP))
#         print ('  chip: {} INTFlag: {:08b} GPIO: {:>08b} '.format(c, INTF, GPIO))
#         if  ( INTF & c.inputs_b)  or  ( GPIO & c.inputs_b ) or ( INTCAP & c.inputs_b ):
         
         if  ( INTF & c.inputs_b)  or  ( GPIO & c.inputs_b ):  #if inputs are active or there was a change (interuption)
            for key in c.inputs.keys():
               if (key & GPIO) or (key & INTF):       #check which button was active
                  c.inputs[key].butt_action_iterator.send( (INTF,GPIO,perf_counter()) )  #engage iterator
      last_read=perf_counter()      #get the current time 
   
   
