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

def processInterval(start_time,end_time):

	# The defaults are as follow:
	# Default for start_time is the start of epouch
	# Default for end_time is the current timestamp
	if start_time == None:
		start = datetime.datetime.strptime('1970-01-01 00:00:00','%Y-%m-%d %H:%M:%S')
		start_time = '1970-01-01 00:00:00'
	else:
		start = datetime.datetime.strptime(start_time,'%Y-%m-%d %H:%M:%S')

	if end_time == None:
		# SGT is UTC + 8
		end = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
	else:
		end = datetime.datetime.strptime(end_time,'%Y-%m-%d %H:%M:%S')		

	# Need to find the range, the time difference in milliseconds between start_time and end_time
	time_difference = end - start
	time_difference = int(time_difference.total_seconds() * 1000)
	
	# Given the time difference range, the time intervals for the line graph is decided
	# Default interval
	interval = 1
	
	if time_difference <= 86400000:
		# For less than a day (86400000 millisec), interval is 5 seconds
		interval = 1
	elif time_difference <= 604800000:
		# For less than a week, 7 days (604800000 millisec), interval is 1 minute
		interval = 12	
	elif time_difference <= 2592000000:
		# For less than a month,30 days (2592000000 millisec), interval is 5 minutes
		interval = 60
	elif time_difference <= 7776000000:
		# For less than 3 months, 90 days (7776000000), interval is 15 minutes
		interval = 180
	elif time_difference <= 15552000000:
		# For less than half a year, 180 days (15552000000 millisec), interval is 30 minutes
		interval = 360
	elif time_difference <= 31536000000:
		# For less than a year, 365 days (31536000000 millisec), interval is 1 hour
		interval = 720
	elif time_difference <= 94608000000:
		# For less than 3 years, 1095 days (94608000000 millisec), interval is 3 hours
		interval = 2160
	elif time_difference <= 157680000000:
		# For less than 5 years, 1825 days (157680000000 millisec), interval is 6 hours
		interval = 4320
	elif time_difference <= 315360000000:
		# For less than 10 years, 3650 days (315360000000 millisec), interval is 12 hours
		interval = 8640
	elif time_difference <= 946080000000:
		# For less than 30 years, 10950 days (157680000000 millisec), interval is 1 day
		interval = 17280

	return interval
	

