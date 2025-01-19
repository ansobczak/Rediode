#!/usr/bin/python3
# -*- coding: UTF-8 -*-

#global i2c
#print('config_pro', i2c)


import configparser
from red_diode_clases import I2C_ini, MCP23017, Relay, Butt, VButt, MovDetected, TempSensors, TempHumI2CSensors, ServoPWM, PWMout, Geo, Alarm, Red_diode_clases_log
from red_diode_procedures import seq_0, seq_1, seq_2, seq_3, seq_4, seq_5, seq_6 ,seq_7, seq_8, v_pres, seq_9, seq_10, seq_11, seq_12, seq_13, seq_14, seq_15,\
            arm_alarm, darm_alarm, alarm_function, time_str, procedures_set_log # set_alarm_times,
from ServoPi import PWM
from time import  perf_counter, sleep
import smbus
global longitude, latitude, global_sun_rise_delta, global_sun_set_delta, i2c, rd_log
i2c={}
longitude = 0
latitude = 0
global_sun_rise_delta = 0
global_sun_set_delta = 0


def open_config_file( CfFile):
   global rd_log
   try:
      cfg_str = configparser.ConfigParser(allow_no_value=True)
      cfg_str.read(CfFile)
      rd_log.info('config read OK')
      return CfFile, cfg_str
   except:
      rd_log.error('something wrong with open_config_file')

def read_config_mqtt( CfFile): #based on cfg file creates mqtt object
   cfg_file, confign_str=open_config_file(CfFile)
   username=confign_str['mqtt']['username']
   password=confign_str['mqtt']['password']
   broker_address = confign_str['mqtt']['broker_address']
   broker_port = confign_str['mqtt']['broker_port']
   broker_keepalive = confign_str['mqtt']['broker_keepalive']
   mqttUname = confign_str['mqtt']['mqttUname']
   topics = confign_str['mqtt']['topics'].split()
   hartbit = confign_str['mqtt']['hartbit']
   return username, password, broker_address, int(broker_port),  int(broker_keepalive), mqttUname, topics, int(hartbit)

def read_config_MCP23017(confign_str):       #based on cfg file creates MCP23017 objects representing installed chips
   global rd_log
   for ch in confign_str['Chips']['MCP23017'].split('\n'): 
      el=ch.split() 
      if str(el[0]) not in MCP23017.MCP23017_instance.keys():
         try:
            MCP23017(el[0], el[1], el[2])    #  chip-name | bus-number | adres-on-bus 
         except:
            rd_log.error('something wrong with config_MCP23017') 
            rd_log.error('MCP23017("%s", %s, %s )' % (str(el[0]), str(el[1]), str(el[2]))) 
      else:
         rd_log.error('MCP23017("%s", %s, %s ) - name exists' % (str(el[0]), str(el[1]), str(el[2])))


def read_config_ServoPWM(confign_str):    #based on cfg file creates ServoPWM object
   global rd_log
   try:
      for ch in confign_str['Chips']['ServoPWM'].split('\n'):   #reading servo information
         el=ch.split()
         if str(el[0]) not in ServoPWM.ServoPWM_instance.keys():
            try:
                        #  servo-name | bus-number | adres-on-bus |channel use | resolution
               ServoPWM( el[0], el[1], el[2], el[3], el[4]) 
               rd_log.info('ServoPWM( name: "%s", I2C bus: %s, bus# %s, channels: %s, resolution: %s )' % (str(el[0]), str(el[1]), str(el[2]) , str(el[3]), str(el[4])))
            except:
               rd_log.error('Error: ServoPWM( name: "%s", I2C bus: %s, bus# %s, channels: %s, resolution: %s ) \n\n' % (str(el[0]), str(el[1]), str(el[2]) , str(el[3]), str(el[4])))
#               sleep(3)
         else:
            rd_log.error('ServoPWM( name: "%s", I2C bus: %s, bus# %s, channels: %s, resolution: %s ) - name exists' % (str(el[0]), str(el[1]), str(el[2]), str(el[3]), str(el[4]))) 

   except:
      rd_log.error('No Servo power supply-relay  ')



def read_config_relays(confign_str):      #based on cfg file creates outputs bia relays
   #setting RELAY OUTPUTS
   global rd_log
   for ch in confign_str['Relay']['Pins_relay'].split('\n'): 
      el=ch.split() 
      pwm, rev = False, False 
      for ell in el:
         if ell=='PWM': pwm=True
         if ell=='REV': rev=True
      try:
         if str(el[3]) not in Relay.Relay_instance.keys():
         #based on cfg file creates Relay objects representing output devices and they connection to physical relay
            Relay(el[0], el[1], el[2], el[3], pwm, rev)
            rd_log.info('Relay(chip: "%s", chip pin (0-15): %s, relay name: "%s", output name: "%s", PWM: %s, REV: %s)' % (str(el[0]), str(el[1]), str(el[2]), str(el[3]), pwm, rev))
         else:
         #or changing the Relay object attributes
            Relay.relay(el[3]).update(el[0], el[1], el[2], el[3], pwm, rev)
            rd_log.info('Relay(chip: "%s", chip pin (0-15): %s, relay name: "%s", output name: "%s", PWM: %s, REV: %s) - CHANGING !!!!!' % (str(el[0]), str(el[1]), str(el[2]), str(el[3]), pwm, rev))
      except:
         rd_log.info('ERROR Relay(chip: "%s", chip pin (0-15): %s, relay name: "%s", output name: "%s", PWM: %s, REV: %s)' % (str(el[0]), str(el[1]), str(el[2]), str(el[3]), pwm, rev))


def item_count(itm, element):    #checking if the element exist in itm and reads next value (numeric often)
                                 #if there is no value, return res1=False and n_val=None
   if itm.count(element) > 0:  #if element is in the item
      res1 = True
      n_val = (itm[itm.index(element)+1])  #read numeric value following element
   else:
      res1=False
      n_val=None
   return res1, n_val

def read_config_inputs(confign_str):      #based on cfg file creates INPUTS via MCP23017 GPIO - buttons, contactrons, motion detectors
   global global_sun_rise_delta, global_sun_set_delta
   global rd_log
   rd_log.info('\nButtons configuration read_config_inputs\n')  
   global_htime = confign_str['Global']['holdtime'] 
   sun_rise_delta, sun_set_delta = global_sun_rise_delta, global_sun_set_delta
   rd_log.info('read_config_inputs:   name, chip, pin, out_s, CON_s, MOV_s, NMO_s, htime, DLY_v, act, sun_rise_delta, sun_set_delta, function1, function2, time_mv, action1, action2')
   for d_line in confign_str['Buttons']['butt'].split('\n'): 
      d_item=d_line.split() #for parsing the button defining string
      tam = None # initial value for motion detection time after move detected
      name=d_item[0]   #button name
      chip=d_item[1]   #chip name button is connected to
      pin=d_item[2]    #pin on chip (0-15)
      action1=d_item[3]   #press button action 1
      action2=d_item[4]   #press button action 2
      out_s=[]       #outputs reacting to button actions
      for el in d_item[5].split(','): 
         if el in Relay.Relay_instance.keys(): out_s.append(el)   #make list of ouputs
         elif el in PWMout.PWMout_instance.keys(): out_s.append(el)   #make list of ouputs
         else: 
            rd_log.error(' read_config_inputs M25 "%s": there is no output %s' % (name, el))

      #vonu - value of no use
      CON_s, vonu = item_count(d_item, 'CON') #checking if Contactron
      MOV_s, tam = item_count(d_item, 'MOV') #checking if MOV motion detector, tam - time after move (to be active)
      NMO_s = False                          #to avoid error of not assignet value
      if not MOV_s:
         NMO_s, tam = item_count(d_item, 'NMO') #checking if NMO motion night detector      #         tam: timeaftermove = 0
      tam = int(tam) if isinstance(tam,str) else tam    #tam: timeaftermove 
      vonu, DLY_v = item_count(d_item, 'DLY')    #checking if delay action
      vonu, act = item_count(d_item, 'ACT')    #check if ACtion
      vonu, htime  = item_count(d_item, 'ht') #checking if there is hold time defined for the button
      htime = global_htime if htime == None else htime
      
      if d_item.count('SUN') > 0:            #check if SUN rise/set adjustment is set.
         sun_rise_delta, sun_set_delta = d_item[d_item.index('SUN')+1].split(',')[0], d_item[d_item.index('SUN')+1].split(',')[1]
      else:
         sun_rise_delta, sun_set_delta = global_sun_rise_delta, global_sun_set_delta
      
            #based on cfg file creates Butt objects representing inputs and in devices and they connection to MCP23017 chips
      if name not in Butt.Butt_instance.keys():
         Butt(name, chip, pin, out_s, CON_s, MOV_s, NMO_s, float(htime), DLY_v,  act, sun_rise_delta, sun_set_delta)
         if MOV_s or NMO_s:            #assigning function or actions to buttons - for motion detection
            Butt.Butt_instance[name].function1=apply_action('M1')   #function pointer
            Butt.Butt_instance[name].function2=apply_action('S0')   #do nothing function
            Butt.Butt_instance[name].mov_action1=action1          #action to be taken when motion is detected. function data string (on, off, togle, pass) or alarm trigers (ARM_ALARM to set on, DARM_ALARM to set off)
            Butt.Butt_instance[name].mov_action2=action2          #action to be taken when motion ends.        function data string (on, off, togle, pass) or alarm trigers (ARM_ALARM to set on, DARM_ALARM to set off)
            Butt.Butt_instance[name].alarm_function=alarm_function
#            rd_log.info('read_config_inputs 22 {} {} {}'.format(Butt.Butt_instance[name].function1, Butt.Butt_instance[name].function2, Butt.Butt_instance[name].alarm_function))
            Butt.butt(name).timeaftermove = tam
         else:            #assigning function or actions to buttons - for motion buttons or contactrons
            Butt.Butt_instance[name].function1=apply_action(action1)
            Butt.Butt_instance[name].function2=apply_action(action2)
#               print('button sequence {} {} {} {}'.format(Butt.Butt_instance[name].name, chip, Butt.Butt_instance[name].action1, Butt.Butt_instance[name].action2))
#            rd_log.info('read_config_inputs 32 {} {} '.format(Butt.Butt_instance[name].function1, Butt.Butt_instance[name].function2))
         rd_log.info('read_config_inputs 12 Butt {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}'.format(name, chip, pin, out_s, CON_s, MOV_s, NMO_s, htime, DLY_v, act, sun_rise_delta, sun_set_delta, Butt.Butt_instance[name].function1, Butt.Butt_instance[name].function2, tam, action1, action2 ))
      else:                #or changing the Butt objects representing inputs and in devices and they connection to MCP23017 chips
         Butt.butt(name).update(name, chip, pin, out_s, CON_s, MOV_s, NMO_s, float(htime), DLY_v, sun_rise_delta, sun_set_delta)
#            r_str+='Butt("%s", "%s", %s, %s, %s, %s, %s, %s, %s,  %s,  %s,  %s) - CHANGING !!!!!' % (name, chip, pin, out_s, CON_s, MOV_s, NMO_s, htime,  DLY_v, act, sun_rise_delta, sun_set_delta)
#            r_str+=', {}, {}'.format(Butt.Butt_instance[name].action1, Butt.Butt_instance[name].action2)
#      rd_log.info('name, chip, pin, out_s, CON_s, MOV_s, NMO_s, htime, DLY_v, act, sun_rise_delta, sun_set_delta, action1, action2, time_mv')
#      print('name, chip, pin, out_s, CON_s, MOV_s, NMO_s, htime, DLY_v, act, sun_rise_delta, sun_set_delta, action1, action2, time_mv')


def read_alarm_outputs(confign_str):  #reads outputs to be used when the alarm is on and detected intruder or seizure/attack/ fire.
   global rd_log
   rd_log.info('\n\nread_alarm_outputs\n\n')  
   str_alarm_outputs = confign_str['Buttons']['alarm_outputs'] 
   alarm_outputs=[]       #outputs reacting to button actions
   for el in str_alarm_outputs.split(','): 
      try:
         if el in Relay.Relay_instance.keys(): alarm_outputs.append(el)   #make list of ouputs
         elif el in PWMout.PWMout_instance.keys(): alarm_outputs.append(el)   #make list of ouputs
         else: 
            rd_log.error(' read_alarm_outputs "%s": there is no output %s' % (name, el))
      except: 
         rd_log.error('ERROR read_alarm_outputs "%s" ' % (str_alarm_outputs))
   return alarm_outputs




def apply_action(instr):         #instr - string with the name of the function   
                                 #returning the function pointer to be applied to the INPUT/button vbutton
   return {
               'S0':seq_0,
               'S1':seq_1,
               'S2':seq_2,
               'S3':seq_3,
               'S4':seq_4,
               'S5':seq_5,
               'S6':seq_6,
               'S7':seq_7,
               'S8':seq_8,
               'S9':seq_9,
               'S10':seq_10,
               'S11':seq_11,
               'S12':seq_12,
               'S13':seq_13,
               'S14':seq_14,
               'S15':seq_15,
               'ALL_OFF':all_off,
               'TOG':tog,
               'RE_READ_CONFIG':re_read_config,
               'M1':v_pres, #mov_detected
               'V1':v_pres, #for virtual buttons
               'V_PRES':v_pres, #for virtual buttons
               'ARM_ALARM_V': v_pres, #setting up alarm on via MQTT
               'DARM_ALARM_V': v_pres, #setting up alarm off via MQTT
               'ARM_ALARM': arm_alarm, #setting up alarm on via button
               'DARM_ALARM': darm_alarm, #setting up alarm off via button
               }[instr.upper()]

def intoint(obj):          #check if the object can be change into integer, return integer or original object
   try:
      re1, re2 =int(obj), True
   except:
      re2=False
   return int(obj) if re2 else obj


def read_config_vbutt(confign_str):     #based on cfg file creates vbutton object
         
   #setting vbutt (virtual button) action sequence
   # v_button:name, procedure ,(rest is optional) delay_time, delay_action, outputs
   #parameters for procedure v_press: 1st par: on, off , togle, delay 99, rolety. following parameters are outputs name's
   global rd_log
   try:
      for ch in confign_str['Buttons']['vbutt'].split('\n'):
         rd_log.info(' read_config_vbutt 1 ch '+ch)
         dlyt = 0
         sched_ = False
         cron=[]
         par=[]
         el=ch.split()
         l = len(el)
         if l > 2:      #if more than two parameters, prepares a list 
            if el[2] in ["on", "off","togle", "pass", "dimm", "roleta", "roleta_komfort", "ARM_ALARM_V", "DARM_ALARM_V"]:
               par.append(el[2])
               vonu, dimm_v = item_count(el, 'dimm') #read numeric value following 'dimm'
               par.append(dimm_v)   #append parameters list
            if el[2] in ["delay"]: 
               par.append(el[2])
               vonu, dlv = item_count(el, 'delay') #read numeric value following 'delay'
               par.append(dlv)   #append parameters list
            if el[0].startswith("schedule"):
               #schedule_wylacz_2  v_pres off CRON * * 0 15 * * *  L2_PokA_17,L2_Kuchnia_26,L1_Kuchnia_24,L2_Salon_9_3
               sched_ = True
               cron=[]
               n=el.index("CRON") #check position of CRON information
               for i in range(n+1,n+1+7): cron.append(intoint(el[i]))     #reading cron timings, changing into int what is possible to change
            par+=el[-1].split(',')        #add list of outputs/lights
         elif l == 2 : par=[] #if one or two parameters put the empy list
         else: 
            lgstr=' VButt config err (name: {}, sequence: {} , parameters: {}) parameters'.format((str(el[0]), str(el[1]), par))
            rd_log.error(lgstr)
   #      print("read config vbutt 02 - @ch: {} @dlyt: {} @sched: {} @cron: {} @par: {} @el: {} @l: {}".format(ch, dlyt, sched_, cron, par, el,l))
         if str(el[0]) not in VButt.Butt_instance.keys():
            lgstr=' VButt creating (name: {}, procedure: {} proc-ref {}, parameters: {})'.format(el[0], el[1], apply_action(el[1]), par)
            VButt(el[0], apply_action(el[1]), par)    #creates VButt
            if sched_:         #if this is scheduler
               VButt.butt(el[0]).schedule_b = sched_
               VButt.butt(el[0]).schedule_s = cron
            else: VButt.butt(el[0]).schedule_b = False
            lgstr+='sched: {}, cron: {}'.format(sched_, cron)
            rd_log.info(lgstr)
         else:
            #if VButt exist this code update action and parameters
            lgstr = ' VButt(name: {}, sequence: {}, parameters: {}) - CHANGING !!!!!'.format(str(el[0]), str(el[1]),par)
            rd_log.info(lgstr)
            VButt.butt(el[0]).update(el[0], apply_action(el[1]), par)  
            if sched_:         #if this is scheduler
               VButt.butt(el[0]).schedule_b=sched_
               VButt.butt(el[0]).schedule_s = cron
            else: VButt.butt(el[0]).schedule_b = False
   except:
      lgstr=' Config_Pocedures VButt(name: "%s", sequence: %s , parameters: %s)' % (str(el[0]), str(el[1]),par)
      rd_log.error(lgstr)

def read_dimming(confign_str):     #based on cfg file defines PWM behaviours
   #read dimming information
   global rd_log
   try:
      try:
         for ch in confign_str['Chips']['dimming'].split('\n'):
            el=ch.split()
            c_range, m_range = item_count(el,'RNG' )
            m_range = intoint(m_range) if c_range else ServoPWM.ServoPWM_instance[el[1]].ServoResol 
                                 #checking if max pwm range is limited for this channel, if not pass the max for the servo
            c_step, step = item_count(el, 'STEP' )
            step = intoint(step) if c_step else 40
                                 #checking if number of steps provided, if not pass 40
            if el[0] not in PWMout.PWMout_instance.keys():
               PWMout(el[0], el[1], el[2], el[3], m_range, step) #outputs connected to PWM Servo: human readable name, chip name, channel number, power supplu name, max pwm range, steps)
               lgstr = 'PWMout(name: {}, chip: {}, chanel: {}, powerSuply: {},  max range: {}, steps {})'.format(el[0], el[1], el[2], el[3], m_range, step)
               rd_log.info(lgstr)
            else:
               lgstr = ' PWMout(name: {}, chip: {}, chanel: {}, powerSuply: {}, max range: {}, steps {})  - CHANGING !!!!!'.format(el[0], el[1], el[2], el[3],m_range, step)
               rd_log.info(lgstr)
               PWMout.pwmout(el[0]).update(el[0], el[1], el[2],0,1, m_range, step)
         PWMout.servo_powersupply_setup()          #classmethod building the dictionary of power supplies
      except:
         lgstr = ' ERR PWMout(name: {}, chip: {}, chanel: {}, last value: {}, last direction: {}, max range: {}, steps {})'.format(el[0], el[1], el[2],0,1,m_range,steps)
         rd_log.error(lgstr)
         
   except:
      rd_log.error('No PWMout')
      

def read_config_tempsensors(confign_str): 
   #read temp sensors configuragion 
   global rd_log
   try:
      temp_path=confign_str['Sensors']['temp_path']
      temp_file=confign_str['Sensors']['temp_file']
   except:
      rd_log.error('something wrong read_config_tempsensors 1 ') 
      #wstawia gołe termometry uj wie po co
   try:
      for ch in confign_str['Sensors']['termo'].split('\n'):
         el=ch.split() #        sensor code      | name | read frequency in sec
         lgstr = str('TempSensors("%s", "%s", %s)' % (el[1], temp_path+el[0]+'/'+temp_file, el[2]) )
         rd_log.error(lgstr)
         TempSensors(el[1], temp_path+el[0]+'/'+temp_file,  el[2])
   except:
      rd_log.error('something wrong read_config_tempsensors 2 ') 
#      sleep(3)
   
def read_config_temp_hum_sensors(confign_str): 
   #read temp_hum sensors configuragion 
   global rd_log
   try:
      for ch in confign_str['Sensors']['terhum'].split('\n'):
         el=ch.split() #     sensor human redable name | i2c bus | i2c address | read frequency in sec
         rd_log.info(str('TempHumI2CSensors("%s", %s, %s, %s)' % (el[0], el[1], el[2],el[3] )))
#         exec(str('TempHumI2CSensors("%s", %s, %s, %s)' % (el[0], el[1], el[2],,el[3] )))
         TempHumI2CSensors(el[0], el[1], el[2],el[3] )
   except:
      rd_log.error('something wrong read_config_temp_hum_sensors') 
      
      
def read_i2c(confign_str):        #read i2c buses at start and pass the argument to Classess file
   global i2c, rd_log
#   print('read_config 1', i2c)
   for ch in confign_str['i2cbus']['buses'].split('\n'):
      ch_n=int(ch)
      if ch_n not in i2c.keys(): 
         i2c.update({ch_n:smbus.SMBus(ch_n)})
#   print('read_i2c:', i2c)
   lgstr = str('read_i2c: OK')
   rd_log.info(lgstr)
   Red_diode_clases_log(rd_log)   #need this here for Red_diode_setup to run properly	
   I2C_ini(i2c)


def close_config_file(file):
   global rd_log
   try:
      file.close()
   except:
      rd_log.info('closing file {}'.format(file))
      sleep(1)

               #reading config file and setting up chips and (tbd)
#def read_config(rd_log, CfFile = '/home/pi/Python/red_diode.cfg'):
def read_config(rd_log_p, CfFile):
   global longitude, latitude, global_sun_rise_delta, global_sun_set_delta, rd_log
   rd_log=rd_log_p
#   Red_diode_clases_log(rd_log_p)
   Red_diode_clases_log(rd_log)            #sending parameters to rred_diode_clases
   procedures_set_log(rd_log)          #sending parameters to red_diode_procedures
   cfg_file, confign_str=open_config_file(CfFile)
   longitude = float(confign_str['Global']['longitude'])
   latitude = float(confign_str['Global']['latitude'])
   Geo(longitude,latitude)
   global_sun_rise_delta = int(confign_str['Global']['sun_rise_delta'])
   global_sun_set_delta = int(confign_str['Global']['sun_set_delta'])
   read_i2c(confign_str)
#   read_config_mqtt(confign_str)  #this is done is red_diode_main
   read_config_MCP23017(confign_str)   
   
   read_config_ServoPWM(confign_str)      # cmpwm   
   read_dimming(confign_str)
   
   read_config_relays(confign_str)
   
   read_config_inputs(confign_str)

   read_config_vbutt(confign_str)

   Alarm( int(confign_str['Global']['alarmStartDelay']), \
          int(confign_str['Global']['alarmLongivity']), \
          int(confign_str['Global']['alarmEnterDelay']), \
          seq_5, seq_6)                                     #initiating alarm class with timings and function pointer
   Alarm.alarm_outputs = read_alarm_outputs(confign_str)
   

   read_config_tempsensors(confign_str)
   read_config_temp_hum_sensors(confign_str)
#   read_time_after_move(confign_str)
   close_config_file(cfg_file)
   return longitude, latitude, global_sun_rise_delta, global_sun_set_delta
   
 

def re_read_config(CfFile):
   pass       #left for compatibility
#   cfg_file, confign_str=open_config_file( CfFile)
#   #read_config_MCP23017(confign_str)
#   MCP23017.clean_all()   #clean the MCP23017 chips configuration
#   #   read_config_mqtt(confign_str)  #this is done is red_diode_main
#   read_config_ServoPWM(confign_str) #cmpwm   
#   read_config_relays(confign_str)
#   read_config_inputs(confign_str)
#   #   read_config_inputs_actions(confign_str)
#   read_config_vbutt(confign_str)
#   #   read_config_tempsensors(confign_str)
#   #   read_time_after_move(confign_str)
#   close_config_file(cfg_file)





'''
###################################################################


Below are some helper functions to build and check configuration


###################################################################
'''



def config_set_log(rd_log_p):     #when using Red_diode_setup use this funtion to set up logger
   global rd_log
   rd_log = rd_log_p

def Out_map():     #help mapping chip pins to relay channels and physical outputs/receivers
   print('\n\n')
   conf_str=''
   for key in MCP23017.MCP23017_instance.keys():
      c=MCP23017.MCP23017_instance[key]
      for i in range(0,16):
#         if c.is_output(i):
         c.set_output_off(i)
         c.set_output_on(i)
#         print('\033[Achip %s pin %d enter relay number and name:' % (c.name, i),end="")
         print('chip %s pin %d enter relay number and name:' % (c.name, i),end="")
         con=input(' ')
         if con not in ('','0'): 
            print("\033[Achip %s pin %d relay %s                             \n" % (c.name,i,con))
            conf_str+=str(c.name)+' '+str(i)+' r_n_'+str(c.name)+'_'+str(con)+' '+str(con)+' \n'
         else: 
            print('\033[Achip %s pin %d relay not recorded:                                        ' % (c.name, i))
         c.set_output_off(i)
   print('\n\n')
   print("add the below to 'red_diode.cfg' file under 'Pins_relay=' section. You can edit the 'relay_name' to smth more decriptive ")
   print("add optional sections: | optional: PWM - dimming Mark (PWM) |  optional REV (reverse logic for fail-safe operation) \n")
   print("chip_name | GPIO_pin | relay_name | output_name |")
   print("Pins_relay= ")
   print(conf_str)


def In_map():     #help mapping chip pins to buttons and inputs
   from red_diode_clases import MCP23017, Relay, Butt, VButt, MovDetected, TempSensors
   from math import log
   import subprocess
   
   print('push the button or close the contactron and type name')
   print('to finish the task, press any button and type END ')
   conf_str_1=''
   conf_str_2=''
   con=''
   while con!='END':
      for key in MCP23017.MCP23017_instance.keys():
         sleep(0.02)
         c=MCP23017.MCP23017_instance[key]
         read=c.read_chip('GPIO')
         if read != 0:
            print('\n\n                        chip {} pin {} pinadr {}, enter name'.format(c, round(log(read,2)),read ) ,end=" ")
            con=input(' >> ')
            if con not in ('','0','END'): 
               print('\033[Achip {} pin {} pinadr {}, name {}                     '.format(c, round(log(read,2)),read, con ))
               conf_str_1+=str(con)+' '+str(c.name)+' '+str(round(log(read,2)))+' '+' \n'
#               conf_str_2+=str(con)+' \n'
               print('push the button or close the contactron and type name (type END to finish)\r', end=' ')
   print('\n\n')
   print('#######################################################################################################')
   print('\n\n')
   print("add the below to 'red_diode.cfg' file under 'butt= ' section and add related outputs human readable names")
   print('\nbutt= ')
   print(conf_str_1)
   print('\n\n')
#   print("add the below to 'red_diode.cfg' file under 'sequence= ' section and add sequence")
#   print('\nsequence= ')
#   print(conf_str_2)


def In_map_d(how_long=30):     #reads inputs and prints chip and pin, runs for 30 seconds if no parameter passed
   from red_diode_clases import MCP23017, Relay, Butt, VButt, MovDetected, TempSensors
   from math import log
   import subprocess
   t=perf_counter()
   print('push the button or close the contactron')
   print('I will run for {} seconds '.format(how_long))
#   conf_str_1=''
#   conf_str_2=''
   while ( ( perf_counter()-t ) < how_long ):
      for key in MCP23017.MCP23017_instance.keys():
         sleep(0.02)
         c=MCP23017.MCP23017_instance[key]
         read=c.read_chip('GPIO')
         if read != 0:
            print('\n\n chip {} pin {} pinadr {}, enter name'.format(c, round(log(read,2)),read ))
#            con=input(' >> ')
#            if con not in ('','0','END'): 
#               print('\033[Achip {} pin {} pinadr {}, name {}                     '.format(c, round(log(read,2)),read, con ))
#               conf_str_1+=str(con)+' '+str(c.name)+' '+str(round(log(read,2)))+' '+' \n'
#               conf_str_2+=str(con)+' \n'
#               print('push the button or close the contactron and type name (type END to finish)\r', end=' ')



def tog(): # function changing outputs on/off - convenient for checking the configuration
   for key in Relay.Relay_instance.keys():
      Relay.Relay_instance[key].togle()
   for v in PWMout.PWMout_instance.values():
      v.pwm_tog()


def r():    #function displaying inputs status - convenient for checking the configuration
   for key in MCP23017.MCP23017_instance.keys():
      c=MCP23017.MCP23017_instance[key]
      print('MCP23017: ',c)
      print('IODIR {} IPOL {}  GPIO {}'.format(bin(c.read_chip('IODIR')), bin(c.read_chip('IPOL')), bin(c.read_chip('GPIO'))))
      print(end='\n')

def all_off(delay_time=1, delay_action='', outputs=[]): # function setting all outputs off - convenient for checking the configuration
               # use as vbutt function
#   print("all off", delay_time, delay_action, outputs)
   PWMout.all_dark()    #switching off all outputs
   Relay.all_off()


def all_stop():   #switching off all outputs, stop led, switching off power supply and servo
   try: Butt.stop_motion_detection()  #stops detecting motions
   except: pass
   sleep(2)
   try: all_off(1,'a',[])                     #set up all outputs off
   except: pass
   sleep(2)
   try: ServoPWM.servo_stop_pwm()     #stopping the led servo
   except: pass
   sleep(2)
   MCP23017.clean_all()          #cleaning the MCP23017 chips to deafault state. 
#   sleep(0.2)
   
   
   
   
   
