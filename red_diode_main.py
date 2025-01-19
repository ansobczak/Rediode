#!/usr/bin/python3
# -*- coding: UTF-8 -*-




from sys import argv
import smbus
import logging
from threading import Thread, Event, currentThread, Timer
from time import sleep, time, localtime, perf_counter
# from red_diode_clases import MCP23017, Relay, Butt, VButt, MovDetected, TempSensors, TempHumI2CSensors, ServoPWM, PWMout, Geo
from red_diode_clases import  TempSensors, TempHumI2CSensors, End_Run
from red_diode_MQTT_class import MQTT_client

#from red_diode_config_procedures import all_off, close_config_file, In_map, open_config_file, Out_map, read_config, \
#      read_config_inputs, read_config_MCP23017, read_config_mqtt, read_config_relays, \
#      read_config_ServoPWM, read_config_temp_hum_sensors, read_config_tempsensors, read_config_vbutt, read_dimming, \
#      read_i2c, read_time_after_move, re_read_config, r, tog, all_stop
from red_diode_config_procedures import read_config, read_config_mqtt, all_stop
#from red_diode_procedures import seq_0, seq_1, seq_2, seq_3, seq_4, seq_5, seq_6 ,seq_7, seq_8, v_pres, seq_9, seq_10, seq_11, seq_12, seq_13, seq_14, seq_15 
from red_diode_procedures import MCP23017_reading_thread, day_night, scheduler_eng, time_str #, Send_alarm

global longitude, latitude
global rd_log 


def log_start():
   f_path="/home/pi/Python/rd_log/"
   f_name=f_path+"red_diode_log"+time_str()+".log"
   logging.basicConfig(filename=f_name, encoding='utf-8', format='%(levelname)s:%(message)s', level=logging.DEBUG)
   msgstr='This message test debug logging', time_str()
   logging.info(msgstr)
#   logging.info('This message test info logging')
#   logging.warning('This message test warning logging')
#   logging.error('This message test error logging and diacriticals: ęóąśłżźćńĘÓĄŚŁŻŹĆŃ')
###############################################   lgstr = " {} ".format(time_str())
   return logging
   

def main():
   global i2c
   End_Run()         #initiating class
   rd_log = log_start()

#   rd_log.info("usage: python3 red_diode_main.py parg1 arg2")
#   rd_log.info("example to run for 24h: python3 red_diode_main.py $((1*60*24)) 0.05")
#   rd_log.info("first argument is how long RedDiode will run in minutes, use 0 (zero) for endless. ")
#   rd_log.info("second parameter is  <iterator time> (typical value 0.001-0.2) and optional. Use it if trouble reading I2C lines ")
                        #parsing CLI parameters
   how_long = 1        #how many minutes to run program
   slpt = 0.001         #iterator sleeping time or <iterator time>
   if len(argv) == 2:
      how_long=60*int(argv[1])
      lgstr = " {} RED_DIODE_START with one parameter: how_long:{}".format(time_str(),argv[1])
   elif len(argv) == 3:
      how_long=60*int(argv[1])
      slpt=float(argv[2])
      lgstr = " {} RED_DIODE_START with two parameters: how_long:{}, slpt:{}".format(time_str(),argv[1],argv[2])
   else:
      print('First argument is how_long in minutes or 0 for endless and obligatory, second argument is <iterator time> (typical value 0.001-0.2) and optional')
      print('If no arguments, will run for {:2} seconds with iterator time {:2} '.format(how_long, slpt))
      sleep(1)
   
   rd_log.info(lgstr)   
   
   CfFile = '/home/pi/Python/red_diode.cfg'   #configuration file location
   longitude, latitude, sun_rise_delta, sun_set_delta = read_config(rd_log, CfFile)   
   
   rd_log.info('how_long is {} or {:02.0f}h {:02.0f}min. \nSleep is {} seconds will work for {:02.0f}:{:02.0f} \nriseD {} setD {}'.format(how_long, how_long//3600, int((how_long/60)%60), slpt, int((how_long/60)//60), int((how_long/60)%60),sun_rise_delta, sun_set_delta))
   lgstr = " {} Setup ready".format(time_str())
   rd_log.info(lgstr)

   
   #starting mqtt main treat
   username, password, broker_address, broker_port,  broker_keepalive, MQTTUname, topic_name, hardbit = read_config_mqtt(CfFile)
   
   MQTT_client.mqtt_obj=MQTT_client(username, password, broker_address, broker_port,  broker_keepalive, MQTTUname, topic_name, hardbit)
   
   #sending MQTT message 
   MQTT_client.mqtt_obj.MQTT_publish("red/system", "START at " + time_str() , True)
                                                                                                      #true is for MQTT messge retain
   
   #starting MCP23017 management
   th_MCP1 = Thread (name="MCP1", target=MCP23017_reading_thread, args=(slpt, how_long,) )
   th_MCP1.setDaemon(True)
   th_MCP1.start() 
   
   th_Temp= Thread (name="TempPublish", target = TempSensors.publish_all_temp , args=(MQTT_client.mqtt_obj,))
   th_Temp.setDaemon(True)
   th_Temp.start()
   
   th_TempChart= Thread (name="TempChartPublish", target = TempSensors.publish_all_temp_chart , args=(MQTT_client.mqtt_obj,))
   th_TempChart.setDaemon(True)
   th_TempChart.start()
   
   th_TempHum= Thread(name="TempHumPublish", target = TempHumI2CSensors.publish_all_temp_hum, args=(MQTT_client.mqtt_obj,))
   th_TempHum.setDaemon(True)
   th_TempHum.start()
   
   th_DayNight = Thread (name="DayNight", target = day_night , args=(longitude, latitude, MQTT_client.mqtt_obj, sun_rise_delta, sun_set_delta,  ))
   th_DayNight.setDaemon(True)
   th_DayNight.start()
   
   th_Scheduler = Thread (name="Scheduler", target = scheduler_eng , args=(MQTT_client.mqtt_obj, rd_log,  ))
   th_Scheduler.setDaemon(True)
   th_Scheduler.start()
   
   lgstr = " {} threads started".format(time_str())
   rd_log.info(lgstr)   
   th_MCP1.join()
   
   lgstr = " {} threads ended".format(time_str())
   rd_log.info(lgstr) 
   rd_log.info('sending stop to all')
   all_stop()
   rd_log.info(' {} how_long was {} or {:4.0f}h {:3.0f}min.  Sleep was {}'.format(time_str(), how_long, how_long//3600, how_long//60, slpt))

   MQTT_client.mqtt_obj.MQTT_publish('red/system', "STOP at " + time_str() , True) 
                                                                                                                                          #true is for MQTT messge retain
   rd_log.info("RED_DIODE_END at" + time_str() )

      
if __name__ == "__main__":

   i2c={}
#   print("\n\nRED_DIODE_START at" + time_str() )
   main()
#   print("\n\nRED_DIODE_END at" + time_str() )

