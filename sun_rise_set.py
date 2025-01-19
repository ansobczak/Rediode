#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from time import mktime, localtime, gmtime
import math 

def sinrad(deg):
   return math.sin(deg * math.pi/180)

def cosrad(deg):
   return math.cos(deg * math.pi/180)

def calculatetimefromjuliandate(jd,td,zone):
   jd=jd+.5
   secs=int((jd-int(jd))*24*60*60+.5)
   mins=int(secs/60)
   hour=int(mins/60)-zone
   r_time=mktime((td[0], td[1], td[2],hour, mins % 60, secs % 60, td[6],td[7], -1))
   return r_time

def calcsunriseandsunset(dt, tz,longitude,latitude):
   a=math.floor((14-dt[1])/12)
   y = dt[0]+4800-a
   m = dt[1]+12*a -3
   julian_date=dt[2]+math.floor((153*m+2)/5)+365*y+math.floor(y/4)-math.floor(y/100)+math.floor(y/400)-32045
   nstar= (julian_date - 2451545.0 - 0.0009)-(longitude/360)
   n=round(nstar)
   jstar = 2451545.0+0.0009+(longitude/360) + n
   M=(357.5291+0.98560028*(jstar-2451545)) % 360
   c=(1.9148*sinrad(M))+(0.0200*sinrad(2*M))+(0.0003*sinrad(3*M))
   l=(M+102.9372+c+180) % 360
   jtransit = jstar + (0.0053 * sinrad(M)) - (0.0069 * sinrad(2 * l))
   delta=math.asin(sinrad(l) * sinrad(23.45))*180/math.pi
   H = math.acos((sinrad(-0.83)-sinrad(latitude)*sinrad(delta))/(cosrad(latitude)*cosrad(delta)))*180/math.pi
   jstarstar=2451545.0+0.0009+((H+longitude)/360)+n
   jset=jstarstar+(0.0053*sinrad(M))-(0.0069*sinrad(2*l))
   jrise=jtransit-(jset-jtransit)
   return (calculatetimefromjuliandate(jrise,dt,tz), calculatetimefromjuliandate(jset,dt,tz))

def sun_main(longitude=-21.46, latitude=52.25):
   #longitude West  #latitude North
   today=gmtime()
   tzc=gmtime().tm_hour-localtime().tm_hour
   r_sunrise,r_sunset = calcsunriseandsunset(today,tzc,longitude,latitude)
#   print ("sunrise and sunset local time: ", localtime(r_sunrise)[3:5], localtime(r_sunset)[3:5])
#   print ("sunrise and sunset UTC       : ", gmtime(r_sunrise)[3:5], gmtime(r_sunset)[3:5])
   return r_sunrise,r_sunset

def f_sun_rise_set(longitude, latitude, rise_corr=0, set_corr=0):        #correction is to start nigh and/or day sooner or later
   '''
   astro sunrise: positive correction make sunrise/sunset later, negative earlier  
   '''
   
   r_sunrise,r_sunset = sun_main(longitude, latitude)          #calculate sun rise and set
#   print(r_sunrise,r_sunset)
   lt = localtime()[3]*60+localtime()[4]                      #calculates local time in minutes since midnight 
   sr = localtime(r_sunrise)[3]*60+localtime(r_sunrise)[4] +  rise_corr   #counts minutes since midnight to sun rise
   ss = localtime(r_sunset)[3]*60+localtime(r_sunset)[4] + set_corr      #counts minutes since midnight to sun set
   sr = 0 if sr<0 else sr
   ss = 0 if ss<0 else ss
   if ss > lt > sr:
      day=True
      night=False
      sl_t = ss-lt                                                #calculate minutes to the sunset 
#      print('day_night run at {} day: {}  night: {} '.format(lt/60, day, night))
   elif lt <= sr:
      day=False
      night=True
      sl_t = sr-lt  
   elif lt >= ss:
      day=False
      night=True
      sl_t = 24*60 - lt + sr                                   #calculate minutes to the sunrise
#      print('day_night run at {} day: {}  night: {} '.format(lt/60, day, night))
   sl_t = sl_t if sl_t != 0 else 1
#   print('day_night run at {}:{} lon {} lat {} rc {} sc {} Day: {} Night {}, sleep {}, sun rise {}:{} sun set {}:{}'.format(localtime()[3],localtime()[4], longitude, latitude, rise_corr, set_corr, day, night,sl_t,localtime(r_sunrise)[3], localtime(r_sunrise)[4], localtime(r_sunset)[3],localtime(r_sunset)[4]))
   return day, night, sl_t, localtime(r_sunrise)[3:5], localtime(r_sunset)[3:5]  
         # bool, bool, minutes to sun rise or set , local time sun rise, local time sun set 


if __name__ == '__main__':
   longitude=-21.46
   latitude=52.25
   r_sunrise,r_sunset = sun_main(longitude, latitude)
   print("local time {}:{}".format(localtime()[3] , localtime()[4] ))
   print ("sunrise and sunset in seconds since epoch: {}  {}".format(r_sunrise, r_sunset))
   print ("sunrise {:02}:{:02} and sunset {:02}:{:02}  local time".format(localtime(r_sunrise)[3], localtime(r_sunrise)[4], \
                                                      localtime(r_sunset)[3],localtime(r_sunset)[3]))
   print ("sunrise {:02}:{:02} and sunset {:02}:{:02}  UTC time".format(gmtime(r_sunrise)[3], gmtime(r_sunrise)[4], \
                                                      gmtime(r_sunset)[3],gmtime(r_sunset)[3]))
