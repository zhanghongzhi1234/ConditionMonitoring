
from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status

import requests
import json
import datetime
import calendar

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

def toDayOfWeek(num):
	dow = None
	if num == 0:
		dow = 'Mon'
	elif num == 1:
		dow = 'Tue'	
	elif num == 2:
		dow = 'Wed'
	elif num == 3:
		dow = 'Thu'
	elif num == 4:
		dow = 'Fri'
	elif num == 5:
		dow = 'Sat'
	elif num == 6:
		dow = 'Sun'

	return dow

def toMonthOfYear(num):
	moy = None
	if num == 1:
		moy = 'Jan'
	elif num == 2:
		moy = 'Feb'	
	elif num == 3:
		moy = 'Mar'
	elif num == 4:
		moy = 'Apr'
	elif num == 5:
		moy = 'May'
	elif num == 6:
		moy = 'Jun'
	elif num == 7:
		moy = 'Jul'	
	elif num == 8:
		moy = 'Aug'
	elif num == 9:
		moy = 'Sep'
	elif num == 10:
		moy = 'Oct'
	elif num == 11:
		moy = 'Nov'
	elif num == 12:
		moy = 'Dec'	

	return moy

def processTimeSeries(periodicity,trendingType):
# periodicity for historical trending can be either daily,weekly,monthly,yearly
# trendingType is either historical or future
# periodicity for future trending can be either next 24 hours, next 7 days, next 10 years

	timeSeries = []
	displaySeries = []

	timeInfo = {
		"timeSeries":[],
		"displaySeries":[]
		}
	
	# Handle the historical data 
	if periodicity == 'daily' and trendingType == 'historical':

		# Find data for the past 24 hours, +08:00 hours for SGT
		hour1 = (datetime.datetime.now() - datetime.timedelta(hours=24) + datetime.timedelta(hours=8))
		hour2 = (datetime.datetime.now() - datetime.timedelta(hours=23) + datetime.timedelta(hours=8))
		hour3 = (datetime.datetime.now() - datetime.timedelta(hours=22) + datetime.timedelta(hours=8))
		hour4 = (datetime.datetime.now() - datetime.timedelta(hours=21) + datetime.timedelta(hours=8))
		hour5 = (datetime.datetime.now() - datetime.timedelta(hours=20) + datetime.timedelta(hours=8))
		hour6 = (datetime.datetime.now() - datetime.timedelta(hours=19) + datetime.timedelta(hours=8))
		hour7 = (datetime.datetime.now() - datetime.timedelta(hours=18) + datetime.timedelta(hours=8))
		hour8 = (datetime.datetime.now() - datetime.timedelta(hours=17) + datetime.timedelta(hours=8))
		hour9 = (datetime.datetime.now() - datetime.timedelta(hours=16) + datetime.timedelta(hours=8))
		hour10 = (datetime.datetime.now() - datetime.timedelta(hours=15) + datetime.timedelta(hours=8))
		hour11 = (datetime.datetime.now() - datetime.timedelta(hours=14) + datetime.timedelta(hours=8))
		hour12 = (datetime.datetime.now() - datetime.timedelta(hours=13) + datetime.timedelta(hours=8))
		hour13 = (datetime.datetime.now() - datetime.timedelta(hours=12) + datetime.timedelta(hours=8))
		hour14 = (datetime.datetime.now() - datetime.timedelta(hours=11) + datetime.timedelta(hours=8))
		hour15 = (datetime.datetime.now() - datetime.timedelta(hours=10) + datetime.timedelta(hours=8))
		hour16 = (datetime.datetime.now() - datetime.timedelta(hours=9) + datetime.timedelta(hours=8))
		hour17 = (datetime.datetime.now() - datetime.timedelta(hours=8) + datetime.timedelta(hours=8))
		hour18 = (datetime.datetime.now() - datetime.timedelta(hours=7) + datetime.timedelta(hours=8))
		hour19 = (datetime.datetime.now() - datetime.timedelta(hours=6) + datetime.timedelta(hours=8))
		hour20 = (datetime.datetime.now() - datetime.timedelta(hours=5) + datetime.timedelta(hours=8))
		hour21 = (datetime.datetime.now() - datetime.timedelta(hours=4) + datetime.timedelta(hours=8))
		hour22 = (datetime.datetime.now() - datetime.timedelta(hours=3) + datetime.timedelta(hours=8))
		hour23 = (datetime.datetime.now() - datetime.timedelta(hours=2) + datetime.timedelta(hours=8))
		hour24 = (datetime.datetime.now() - datetime.timedelta(hours=1) + datetime.timedelta(hours=8))

		timeSeries.append(""+str(hour1.hour)+", "+str(hour1.day)+"-"+str(hour1.month)+"-"+str(hour1.year)+"")
		timeSeries.append(""+str(hour2.hour)+", "+str(hour2.day)+"-"+str(hour2.month)+"-"+str(hour2.year)+"")
		timeSeries.append(""+str(hour3.hour)+", "+str(hour3.day)+"-"+str(hour3.month)+"-"+str(hour3.year)+"")
		timeSeries.append(""+str(hour4.hour)+", "+str(hour4.day)+"-"+str(hour4.month)+"-"+str(hour4.year)+"")
		timeSeries.append(""+str(hour5.hour)+", "+str(hour5.day)+"-"+str(hour5.month)+"-"+str(hour5.year)+"")
		timeSeries.append(""+str(hour6.hour)+", "+str(hour6.day)+"-"+str(hour6.month)+"-"+str(hour6.year)+"")
		timeSeries.append(""+str(hour7.hour)+", "+str(hour7.day)+"-"+str(hour7.month)+"-"+str(hour7.year)+"")
		timeSeries.append(""+str(hour8.hour)+", "+str(hour8.day)+"-"+str(hour8.month)+"-"+str(hour8.year)+"")
		timeSeries.append(""+str(hour9.hour)+", "+str(hour9.day)+"-"+str(hour9.month)+"-"+str(hour9.year)+"")
		timeSeries.append(""+str(hour10.hour)+", "+str(hour10.day)+"-"+str(hour10.month)+"-"+str(hour10.year)+"")
		timeSeries.append(""+str(hour11.hour)+", "+str(hour11.day)+"-"+str(hour11.month)+"-"+str(hour11.year)+"")
		timeSeries.append(""+str(hour12.hour)+", "+str(hour12.day)+"-"+str(hour12.month)+"-"+str(hour12.year)+"")
		timeSeries.append(""+str(hour13.hour)+", "+str(hour13.day)+"-"+str(hour13.month)+"-"+str(hour13.year)+"")
		timeSeries.append(""+str(hour14.hour)+", "+str(hour14.day)+"-"+str(hour14.month)+"-"+str(hour14.year)+"")
		timeSeries.append(""+str(hour15.hour)+", "+str(hour15.day)+"-"+str(hour15.month)+"-"+str(hour15.year)+"")
		timeSeries.append(""+str(hour16.hour)+", "+str(hour16.day)+"-"+str(hour16.month)+"-"+str(hour16.year)+"")
		timeSeries.append(""+str(hour17.hour)+", "+str(hour17.day)+"-"+str(hour17.month)+"-"+str(hour17.year)+"")
		timeSeries.append(""+str(hour18.hour)+", "+str(hour18.day)+"-"+str(hour18.month)+"-"+str(hour18.year)+"")
		timeSeries.append(""+str(hour19.hour)+", "+str(hour19.day)+"-"+str(hour19.month)+"-"+str(hour19.year)+"")
		timeSeries.append(""+str(hour20.hour)+", "+str(hour20.day)+"-"+str(hour20.month)+"-"+str(hour20.year)+"")
		timeSeries.append(""+str(hour21.hour)+", "+str(hour21.day)+"-"+str(hour21.month)+"-"+str(hour21.year)+"")
		timeSeries.append(""+str(hour22.hour)+", "+str(hour22.day)+"-"+str(hour22.month)+"-"+str(hour22.year)+"")
		timeSeries.append(""+str(hour23.hour)+", "+str(hour23.day)+"-"+str(hour23.month)+"-"+str(hour23.year)+"")
		timeSeries.append(""+str(hour24.hour)+", "+str(hour24.day)+"-"+str(hour24.month)+"-"+str(hour24.year)+"")

		displaySeries.append(""+str(hour1.hour)+":00 "+str(hour1.day)+"/"+str(hour1.month)+"")
		displaySeries.append(""+str(hour2.hour)+":00 "+str(hour2.day)+"/"+str(hour2.month)+"")
		displaySeries.append(""+str(hour3.hour)+":00 "+str(hour3.day)+"/"+str(hour3.month)+"")
		displaySeries.append(""+str(hour4.hour)+":00 "+str(hour4.day)+"/"+str(hour4.month)+"")
		displaySeries.append(""+str(hour5.hour)+":00 "+str(hour5.day)+"/"+str(hour5.month)+"")
		displaySeries.append(""+str(hour6.hour)+":00 "+str(hour6.day)+"/"+str(hour6.month)+"")
		displaySeries.append(""+str(hour7.hour)+":00 "+str(hour7.day)+"/"+str(hour7.month)+"")
		displaySeries.append(""+str(hour8.hour)+":00 "+str(hour8.day)+"/"+str(hour8.month)+"")
		displaySeries.append(""+str(hour9.hour)+":00 "+str(hour9.day)+"/"+str(hour9.month)+"")
		displaySeries.append(""+str(hour10.hour)+":00 "+str(hour10.day)+"/"+str(hour10.month)+"")
		displaySeries.append(""+str(hour11.hour)+":00 "+str(hour11.day)+"/"+str(hour11.month)+"")
		displaySeries.append(""+str(hour12.hour)+":00 "+str(hour12.day)+"/"+str(hour12.month)+"")
		displaySeries.append(""+str(hour13.hour)+":00 "+str(hour13.day)+"/"+str(hour13.month)+"")
		displaySeries.append(""+str(hour14.hour)+":00 "+str(hour14.day)+"/"+str(hour14.month)+"")
		displaySeries.append(""+str(hour15.hour)+":00 "+str(hour15.day)+"/"+str(hour15.month)+"")
		displaySeries.append(""+str(hour16.hour)+":00 "+str(hour16.day)+"/"+str(hour16.month)+"")
		displaySeries.append(""+str(hour17.hour)+":00 "+str(hour17.day)+"/"+str(hour17.month)+"")
		displaySeries.append(""+str(hour18.hour)+":00 "+str(hour18.day)+"/"+str(hour18.month)+"")
		displaySeries.append(""+str(hour19.hour)+":00 "+str(hour19.day)+"/"+str(hour19.month)+"")
		displaySeries.append(""+str(hour20.hour)+":00 "+str(hour20.day)+"/"+str(hour20.month)+"")
		displaySeries.append(""+str(hour21.hour)+":00 "+str(hour21.day)+"/"+str(hour21.month)+"")
		displaySeries.append(""+str(hour22.hour)+":00 "+str(hour22.day)+"/"+str(hour22.month)+"")
		displaySeries.append(""+str(hour23.hour)+":00 "+str(hour23.day)+"/"+str(hour23.month)+"")
		displaySeries.append(""+str(hour24.hour)+":00 "+str(hour24.day)+"/"+str(hour24.month)+"")

		timeInfo['timeSeries'] = timeSeries
		timeInfo['displaySeries'] = displaySeries

		return timeInfo

	elif periodicity == 'weekly' and trendingType == 'historical':

		# Find data for the past 7 days, +08:00 hours for SGT
		day1 = (datetime.datetime.now() - datetime.timedelta(days=7) + datetime.timedelta(hours=8)).date()
		day2 = (datetime.datetime.now() - datetime.timedelta(days=6) + datetime.timedelta(hours=8)).date()
		day3 = (datetime.datetime.now() - datetime.timedelta(days=5) + datetime.timedelta(hours=8)).date()
		day4 = (datetime.datetime.now() - datetime.timedelta(days=4) + datetime.timedelta(hours=8)).date()
		day5 = (datetime.datetime.now() - datetime.timedelta(days=3) + datetime.timedelta(hours=8)).date()
		day6 = (datetime.datetime.now() - datetime.timedelta(days=2) + datetime.timedelta(hours=8)).date()
		day7 = (datetime.datetime.now() - datetime.timedelta(days=1) + datetime.timedelta(hours=8)).date()

		timeSeries.append(""+toDayOfWeek(day1.weekday())+", "+str(day1.day)+"-"+str(day1.month)+"-"+str(day1.year)+"")
		timeSeries.append(""+toDayOfWeek(day2.weekday())+", "+str(day2.day)+"-"+str(day2.month)+"-"+str(day2.year)+"")
		timeSeries.append(""+toDayOfWeek(day3.weekday())+", "+str(day3.day)+"-"+str(day3.month)+"-"+str(day3.year)+"")
		timeSeries.append(""+toDayOfWeek(day4.weekday())+", "+str(day4.day)+"-"+str(day4.month)+"-"+str(day4.year)+"")
		timeSeries.append(""+toDayOfWeek(day5.weekday())+", "+str(day5.day)+"-"+str(day5.month)+"-"+str(day5.year)+"")
		timeSeries.append(""+toDayOfWeek(day6.weekday())+", "+str(day6.day)+"-"+str(day6.month)+"-"+str(day6.year)+"")
		timeSeries.append(""+toDayOfWeek(day7.weekday())+", "+str(day7.day)+"-"+str(day7.month)+"-"+str(day7.year)+"")

		displaySeries.append(""+toDayOfWeek(day1.weekday())+","+str(day1.day)+"/"+str(day1.month)+"")
		displaySeries.append(""+toDayOfWeek(day2.weekday())+","+str(day2.day)+"/"+str(day2.month)+"")
		displaySeries.append(""+toDayOfWeek(day3.weekday())+","+str(day3.day)+"/"+str(day3.month)+"")
		displaySeries.append(""+toDayOfWeek(day4.weekday())+","+str(day4.day)+"/"+str(day4.month)+"")
		displaySeries.append(""+toDayOfWeek(day5.weekday())+","+str(day5.day)+"/"+str(day5.month)+"")
		displaySeries.append(""+toDayOfWeek(day6.weekday())+","+str(day6.day)+"/"+str(day6.month)+"")
		displaySeries.append(""+toDayOfWeek(day7.weekday())+","+str(day7.day)+"/"+str(day7.month)+"")

		timeInfo['timeSeries'] = timeSeries
		timeInfo['displaySeries'] = displaySeries

		return timeInfo

	elif periodicity == 'monthly' and trendingType == 'historical':

		# Find data for the past 30 days, +08:00 hours for SGT
		day1 = (datetime.datetime.now() - datetime.timedelta(days=30) + datetime.timedelta(hours=8)).date()
		day2 = (datetime.datetime.now() - datetime.timedelta(days=29) + datetime.timedelta(hours=8)).date()
		day3 = (datetime.datetime.now() - datetime.timedelta(days=28) + datetime.timedelta(hours=8)).date()
		day4 = (datetime.datetime.now() - datetime.timedelta(days=27) + datetime.timedelta(hours=8)).date()
		day5 = (datetime.datetime.now() - datetime.timedelta(days=26) + datetime.timedelta(hours=8)).date()
		day6 = (datetime.datetime.now() - datetime.timedelta(days=25) + datetime.timedelta(hours=8)).date()
		day7 = (datetime.datetime.now() - datetime.timedelta(days=24) + datetime.timedelta(hours=8)).date()
		day8 = (datetime.datetime.now() - datetime.timedelta(days=23) + datetime.timedelta(hours=8)).date()
		day9 = (datetime.datetime.now() - datetime.timedelta(days=22) + datetime.timedelta(hours=8)).date()
		day10 = (datetime.datetime.now() - datetime.timedelta(days=21) + datetime.timedelta(hours=8)).date()
		day11 = (datetime.datetime.now() - datetime.timedelta(days=20) + datetime.timedelta(hours=8)).date()
		day12 = (datetime.datetime.now() - datetime.timedelta(days=19) + datetime.timedelta(hours=8)).date()
		day13 = (datetime.datetime.now() - datetime.timedelta(days=18) + datetime.timedelta(hours=8)).date()
		day14 = (datetime.datetime.now() - datetime.timedelta(days=17) + datetime.timedelta(hours=8)).date()
		day15 = (datetime.datetime.now() - datetime.timedelta(days=16) + datetime.timedelta(hours=8)).date()
		day16 = (datetime.datetime.now() - datetime.timedelta(days=15) + datetime.timedelta(hours=8)).date()
		day17 = (datetime.datetime.now() - datetime.timedelta(days=14) + datetime.timedelta(hours=8)).date()
		day18 = (datetime.datetime.now() - datetime.timedelta(days=13) + datetime.timedelta(hours=8)).date()
		day19 = (datetime.datetime.now() - datetime.timedelta(days=12) + datetime.timedelta(hours=8)).date()
		day20 = (datetime.datetime.now() - datetime.timedelta(days=11) + datetime.timedelta(hours=8)).date()
		day21 = (datetime.datetime.now() - datetime.timedelta(days=10) + datetime.timedelta(hours=8)).date()
		day22 = (datetime.datetime.now() - datetime.timedelta(days=9) + datetime.timedelta(hours=8)).date()
		day23 = (datetime.datetime.now() - datetime.timedelta(days=8) + datetime.timedelta(hours=8)).date()
		day24 = (datetime.datetime.now() - datetime.timedelta(days=7) + datetime.timedelta(hours=8)).date()
		day25 = (datetime.datetime.now() - datetime.timedelta(days=6) + datetime.timedelta(hours=8)).date()
		day26 = (datetime.datetime.now() - datetime.timedelta(days=5) + datetime.timedelta(hours=8)).date()
		day27 = (datetime.datetime.now() - datetime.timedelta(days=4) + datetime.timedelta(hours=8)).date()
		day28 = (datetime.datetime.now() - datetime.timedelta(days=3) + datetime.timedelta(hours=8)).date()
		day29 = (datetime.datetime.now() - datetime.timedelta(days=2) + datetime.timedelta(hours=8)).date()
		day30 = (datetime.datetime.now() - datetime.timedelta(days=1) + datetime.timedelta(hours=8)).date()

		timeSeries.append(""+str(day1.day)+"-"+str(day1.month)+"-"+str(day1.year)+"")
		timeSeries.append(""+str(day2.day)+"-"+str(day2.month)+"-"+str(day2.year)+"")
		timeSeries.append(""+str(day3.day)+"-"+str(day3.month)+"-"+str(day3.year)+"")
		timeSeries.append(""+str(day4.day)+"-"+str(day4.month)+"-"+str(day4.year)+"")
		timeSeries.append(""+str(day5.day)+"-"+str(day5.month)+"-"+str(day5.year)+"")
		timeSeries.append(""+str(day6.day)+"-"+str(day6.month)+"-"+str(day6.year)+"")
		timeSeries.append(""+str(day7.day)+"-"+str(day7.month)+"-"+str(day7.year)+"")
		timeSeries.append(""+str(day8.day)+"-"+str(day8.month)+"-"+str(day8.year)+"")
		timeSeries.append(""+str(day9.day)+"-"+str(day9.month)+"-"+str(day9.year)+"")
		timeSeries.append(""+str(day10.day)+"-"+str(day10.month)+"-"+str(day10.year)+"")
		timeSeries.append(""+str(day11.day)+"-"+str(day11.month)+"-"+str(day11.year)+"")
		timeSeries.append(""+str(day12.day)+"-"+str(day12.month)+"-"+str(day12.year)+"")
		timeSeries.append(""+str(day13.day)+"-"+str(day13.month)+"-"+str(day13.year)+"")
		timeSeries.append(""+str(day14.day)+"-"+str(day14.month)+"-"+str(day14.year)+"")
		timeSeries.append(""+str(day15.day)+"-"+str(day15.month)+"-"+str(day15.year)+"")
		timeSeries.append(""+str(day16.day)+"-"+str(day16.month)+"-"+str(day16.year)+"")
		timeSeries.append(""+str(day17.day)+"-"+str(day17.month)+"-"+str(day17.year)+"")
		timeSeries.append(""+str(day18.day)+"-"+str(day18.month)+"-"+str(day18.year)+"")
		timeSeries.append(""+str(day19.day)+"-"+str(day19.month)+"-"+str(day19.year)+"")
		timeSeries.append(""+str(day20.day)+"-"+str(day20.month)+"-"+str(day20.year)+"")
		timeSeries.append(""+str(day21.day)+"-"+str(day21.month)+"-"+str(day21.year)+"")
		timeSeries.append(""+str(day22.day)+"-"+str(day22.month)+"-"+str(day22.year)+"")
		timeSeries.append(""+str(day23.day)+"-"+str(day23.month)+"-"+str(day23.year)+"")
		timeSeries.append(""+str(day24.day)+"-"+str(day24.month)+"-"+str(day24.year)+"")
		timeSeries.append(""+str(day25.day)+"-"+str(day25.month)+"-"+str(day25.year)+"")
		timeSeries.append(""+str(day26.day)+"-"+str(day26.month)+"-"+str(day26.year)+"")
		timeSeries.append(""+str(day27.day)+"-"+str(day27.month)+"-"+str(day27.year)+"")
		timeSeries.append(""+str(day28.day)+"-"+str(day28.month)+"-"+str(day28.year)+"")
		timeSeries.append(""+str(day29.day)+"-"+str(day29.month)+"-"+str(day29.year)+"")
		timeSeries.append(""+str(day30.day)+"-"+str(day30.month)+"-"+str(day30.year)+"")

		displaySeries.append(""+str(day1.day)+"/"+str(day1.month)+"")
		displaySeries.append(""+str(day2.day)+"/"+str(day2.month)+"")
		displaySeries.append(""+str(day3.day)+"/"+str(day3.month)+"")
		displaySeries.append(""+str(day4.day)+"/"+str(day4.month)+"")
		displaySeries.append(""+str(day5.day)+"/"+str(day5.month)+"")
		displaySeries.append(""+str(day6.day)+"/"+str(day6.month)+"")
		displaySeries.append(""+str(day7.day)+"/"+str(day7.month)+"")
		displaySeries.append(""+str(day8.day)+"/"+str(day8.month)+"")
		displaySeries.append(""+str(day9.day)+"/"+str(day9.month)+"")
		displaySeries.append(""+str(day10.day)+"/"+str(day10.month)+"")
		displaySeries.append(""+str(day11.day)+"/"+str(day11.month)+"")
		displaySeries.append(""+str(day12.day)+"/"+str(day12.month)+"")
		displaySeries.append(""+str(day13.day)+"/"+str(day13.month)+"")
		displaySeries.append(""+str(day14.day)+"/"+str(day14.month)+"")
		displaySeries.append(""+str(day15.day)+"/"+str(day15.month)+"")
		displaySeries.append(""+str(day16.day)+"/"+str(day16.month)+"")
		displaySeries.append(""+str(day17.day)+"/"+str(day17.month)+"")
		displaySeries.append(""+str(day18.day)+"/"+str(day18.month)+"")
		displaySeries.append(""+str(day19.day)+"/"+str(day19.month)+"")
		displaySeries.append(""+str(day20.day)+"/"+str(day20.month)+"")
		displaySeries.append(""+str(day21.day)+"/"+str(day21.month)+"")
		displaySeries.append(""+str(day22.day)+"/"+str(day22.month)+"")
		displaySeries.append(""+str(day23.day)+"/"+str(day23.month)+"")
		displaySeries.append(""+str(day24.day)+"/"+str(day24.month)+"")
		displaySeries.append(""+str(day25.day)+"/"+str(day25.month)+"")
		displaySeries.append(""+str(day26.day)+"/"+str(day26.month)+"")
		displaySeries.append(""+str(day27.day)+"/"+str(day27.month)+"")
		displaySeries.append(""+str(day28.day)+"/"+str(day28.month)+"")
		displaySeries.append(""+str(day29.day)+"/"+str(day29.month)+"")
		displaySeries.append(""+str(day30.day)+"/"+str(day30.month)+"")

		timeInfo['timeSeries'] = timeSeries
		timeInfo['displaySeries'] = displaySeries

		return timeInfo


	elif periodicity == 'yearly' and trendingType == 'historical':

		now = datetime.datetime.now()
		month = now.month
		year = now.year
		
		# Loop 12 times for the past 12 months
		for x in range(12):
			# Decrement month
			timeSeries.append(""+toMonthOfYear(month)+","+str(year)+"")
			displaySeries.append(""+toMonthOfYear(month)+" "+str(year)+"")
			month -= 1
			if month == 0:
				year -= 1
				month = 12

		timeSeries.reverse()
		displaySeries.reverse()

		timeInfo['timeSeries'] = timeSeries
		timeInfo['displaySeries'] = displaySeries

		return timeInfo


	# Handle the future data 
	if periodicity == 'next 24 hours' and trendingType == 'future':

		hour0 = (datetime.datetime.now() + datetime.timedelta(hours=0) + datetime.timedelta(hours=8))
		hour1 = (datetime.datetime.now() + datetime.timedelta(hours=1) + datetime.timedelta(hours=8))
		hour2 = (datetime.datetime.now() + datetime.timedelta(hours=2) + datetime.timedelta(hours=8))
		hour3 = (datetime.datetime.now() + datetime.timedelta(hours=3) + datetime.timedelta(hours=8))
		hour4 = (datetime.datetime.now() + datetime.timedelta(hours=4) + datetime.timedelta(hours=8))
		hour5 = (datetime.datetime.now() + datetime.timedelta(hours=5) + datetime.timedelta(hours=8))
		hour6 = (datetime.datetime.now() + datetime.timedelta(hours=6) + datetime.timedelta(hours=8))
		hour7 = (datetime.datetime.now() + datetime.timedelta(hours=7) + datetime.timedelta(hours=8))
		hour8 = (datetime.datetime.now() + datetime.timedelta(hours=8) + datetime.timedelta(hours=8))
		hour9 = (datetime.datetime.now() + datetime.timedelta(hours=9) + datetime.timedelta(hours=8))
		hour10 = (datetime.datetime.now() + datetime.timedelta(hours=10) + datetime.timedelta(hours=8))
		hour11 = (datetime.datetime.now() + datetime.timedelta(hours=11) + datetime.timedelta(hours=8))
		hour12 = (datetime.datetime.now() + datetime.timedelta(hours=12) + datetime.timedelta(hours=8))
		hour13 = (datetime.datetime.now() + datetime.timedelta(hours=13) + datetime.timedelta(hours=8))
		hour14 = (datetime.datetime.now() + datetime.timedelta(hours=14) + datetime.timedelta(hours=8))
		hour15 = (datetime.datetime.now() + datetime.timedelta(hours=15) + datetime.timedelta(hours=8))
		hour16 = (datetime.datetime.now() + datetime.timedelta(hours=16) + datetime.timedelta(hours=8))
		hour17 = (datetime.datetime.now() + datetime.timedelta(hours=17) + datetime.timedelta(hours=8))
		hour18 = (datetime.datetime.now() + datetime.timedelta(hours=18) + datetime.timedelta(hours=8))
		hour19 = (datetime.datetime.now() + datetime.timedelta(hours=19) + datetime.timedelta(hours=8))
		hour20 = (datetime.datetime.now() + datetime.timedelta(hours=20) + datetime.timedelta(hours=8))
		hour21 = (datetime.datetime.now() + datetime.timedelta(hours=21) + datetime.timedelta(hours=8))
		hour22 = (datetime.datetime.now() + datetime.timedelta(hours=22) + datetime.timedelta(hours=8))
		hour23 = (datetime.datetime.now() + datetime.timedelta(hours=23) + datetime.timedelta(hours=8))
		hour24 = (datetime.datetime.now() + datetime.timedelta(hours=24) + datetime.timedelta(hours=8))

		timeSeries.append(""+str(hour0.hour)+":00:00, "+str(hour0.day)+"-"+str(hour0.month)+"-"+str(hour0.year)+"")
		timeSeries.append(""+str(hour1.hour)+":00:00, "+str(hour1.day)+"-"+str(hour1.month)+"-"+str(hour1.year)+"")
		timeSeries.append(""+str(hour2.hour)+":00:00, "+str(hour2.day)+"-"+str(hour2.month)+"-"+str(hour2.year)+"")
		timeSeries.append(""+str(hour3.hour)+":00:00, "+str(hour3.day)+"-"+str(hour3.month)+"-"+str(hour3.year)+"")
		timeSeries.append(""+str(hour4.hour)+":00:00, "+str(hour4.day)+"-"+str(hour4.month)+"-"+str(hour4.year)+"")
		timeSeries.append(""+str(hour5.hour)+":00:00, "+str(hour5.day)+"-"+str(hour5.month)+"-"+str(hour5.year)+"")
		timeSeries.append(""+str(hour6.hour)+":00:00, "+str(hour6.day)+"-"+str(hour6.month)+"-"+str(hour6.year)+"")
		timeSeries.append(""+str(hour7.hour)+":00:00, "+str(hour7.day)+"-"+str(hour7.month)+"-"+str(hour7.year)+"")
		timeSeries.append(""+str(hour8.hour)+":00:00, "+str(hour8.day)+"-"+str(hour8.month)+"-"+str(hour8.year)+"")
		timeSeries.append(""+str(hour9.hour)+":00:00, "+str(hour9.day)+"-"+str(hour9.month)+"-"+str(hour9.year)+"")
		timeSeries.append(""+str(hour10.hour)+":00:00, "+str(hour10.day)+"-"+str(hour10.month)+"-"+str(hour10.year)+"")
		timeSeries.append(""+str(hour11.hour)+":00:00, "+str(hour11.day)+"-"+str(hour11.month)+"-"+str(hour11.year)+"")
		timeSeries.append(""+str(hour12.hour)+":00:00, "+str(hour12.day)+"-"+str(hour12.month)+"-"+str(hour12.year)+"")
		timeSeries.append(""+str(hour13.hour)+":00:00, "+str(hour13.day)+"-"+str(hour13.month)+"-"+str(hour13.year)+"")
		timeSeries.append(""+str(hour14.hour)+":00:00, "+str(hour14.day)+"-"+str(hour14.month)+"-"+str(hour14.year)+"")
		timeSeries.append(""+str(hour15.hour)+":00:00, "+str(hour15.day)+"-"+str(hour15.month)+"-"+str(hour15.year)+"")
		timeSeries.append(""+str(hour16.hour)+":00:00, "+str(hour16.day)+"-"+str(hour16.month)+"-"+str(hour16.year)+"")
		timeSeries.append(""+str(hour17.hour)+":00:00, "+str(hour17.day)+"-"+str(hour17.month)+"-"+str(hour17.year)+"")
		timeSeries.append(""+str(hour18.hour)+":00:00, "+str(hour18.day)+"-"+str(hour18.month)+"-"+str(hour18.year)+"")
		timeSeries.append(""+str(hour19.hour)+":00:00, "+str(hour19.day)+"-"+str(hour19.month)+"-"+str(hour19.year)+"")
		timeSeries.append(""+str(hour20.hour)+":00:00, "+str(hour20.day)+"-"+str(hour20.month)+"-"+str(hour20.year)+"")
		timeSeries.append(""+str(hour21.hour)+":00:00, "+str(hour21.day)+"-"+str(hour21.month)+"-"+str(hour21.year)+"")
		timeSeries.append(""+str(hour22.hour)+":00:00, "+str(hour22.day)+"-"+str(hour22.month)+"-"+str(hour22.year)+"")
		timeSeries.append(""+str(hour23.hour)+":00:00, "+str(hour23.day)+"-"+str(hour23.month)+"-"+str(hour23.year)+"")
		timeSeries.append(""+str(hour24.hour)+":00:00, "+str(hour24.day)+"-"+str(hour24.month)+"-"+str(hour24.year)+"")

		return timeSeries

	elif periodicity == 'next 7 days' and trendingType == 'future':

		day0 = (datetime.datetime.now() + datetime.timedelta(days=0) + datetime.timedelta(hours=8)).date()
		day1 = (datetime.datetime.now() + datetime.timedelta(days=1) + datetime.timedelta(hours=8)).date()
		day2 = (datetime.datetime.now() + datetime.timedelta(days=2) + datetime.timedelta(hours=8)).date()
		day3 = (datetime.datetime.now() + datetime.timedelta(days=3) + datetime.timedelta(hours=8)).date()
		day4 = (datetime.datetime.now() + datetime.timedelta(days=4) + datetime.timedelta(hours=8)).date()
		day5 = (datetime.datetime.now() + datetime.timedelta(days=5) + datetime.timedelta(hours=8)).date()
		day6 = (datetime.datetime.now() + datetime.timedelta(days=6) + datetime.timedelta(hours=8)).date()
		day7 = (datetime.datetime.now() + datetime.timedelta(days=7) + datetime.timedelta(hours=8)).date()

		timeSeries.append(""+toDayOfWeek(day0.weekday())+", "+str(day0.day)+"-"+str(day0.month)+"-"+str(day0.year)+"")
		timeSeries.append(""+toDayOfWeek(day1.weekday())+", "+str(day1.day)+"-"+str(day1.month)+"-"+str(day1.year)+"")
		timeSeries.append(""+toDayOfWeek(day2.weekday())+", "+str(day2.day)+"-"+str(day2.month)+"-"+str(day2.year)+"")
		timeSeries.append(""+toDayOfWeek(day3.weekday())+", "+str(day3.day)+"-"+str(day3.month)+"-"+str(day3.year)+"")
		timeSeries.append(""+toDayOfWeek(day4.weekday())+", "+str(day4.day)+"-"+str(day4.month)+"-"+str(day4.year)+"")
		timeSeries.append(""+toDayOfWeek(day5.weekday())+", "+str(day5.day)+"-"+str(day5.month)+"-"+str(day5.year)+"")
		timeSeries.append(""+toDayOfWeek(day6.weekday())+", "+str(day6.day)+"-"+str(day6.month)+"-"+str(day6.year)+"")
		timeSeries.append(""+toDayOfWeek(day7.weekday())+", "+str(day7.day)+"-"+str(day7.month)+"-"+str(day7.year)+"")

		return timeSeries

	elif periodicity == 'next 10 years' and trendingType == 'future':
	
		now = datetime.datetime.now()
		year = now.year

		timeSeries = []
		
		# Add the current year
		timeSeries.append(''+str(year)+'')
		
		for x in range(10):
			year += 1
			timeSeries.append(''+str(year)+'')

		return timeSeries





		
	

	


