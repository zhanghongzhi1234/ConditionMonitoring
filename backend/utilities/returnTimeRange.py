
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

def processTimeRange(whichType,whichKind):
# Type refer to year, day, hour
# Kind refer to minute

	timeRange = []

	if whichType == 'next 10 years' and whichKind == 'minute':
		timeRange.append(525600*0)
		timeRange.append(525600*1)
		timeRange.append(525600*2)
		timeRange.append(525600*3)
		timeRange.append(525600*4)
		timeRange.append(525600*5)
		timeRange.append(525600*6)
		timeRange.append(525600*7)
		timeRange.append(525600*8)
		timeRange.append(525600*9)
		timeRange.append(525600*10)

	elif whichType == 'next 7 days' and whichKind == 'minute':
		timeRange.append(1440*0)
		timeRange.append(1440*1)
		timeRange.append(1440*2)
		timeRange.append(1440*3)
		timeRange.append(1440*4)
		timeRange.append(1440*5)
		timeRange.append(1440*6)
		timeRange.append(1440*7)

	elif whichType == 'next 24 hours' and whichKind == 'minute':
		timeRange.append(60*0)
		timeRange.append(60*1)
		timeRange.append(60*2)
		timeRange.append(60*3)
		timeRange.append(60*4)
		timeRange.append(60*5)
		timeRange.append(60*6)
		timeRange.append(60*7)
		timeRange.append(60*8)
		timeRange.append(60*9)
		timeRange.append(60*10)
		timeRange.append(60*11)
		timeRange.append(60*12)
		timeRange.append(60*13)
		timeRange.append(60*14)
		timeRange.append(60*15)
		timeRange.append(60*16)
		timeRange.append(60*17)
		timeRange.append(60*18)
		timeRange.append(60*19)
		timeRange.append(60*20)
		timeRange.append(60*21)
		timeRange.append(60*22)
		timeRange.append(60*23)
		timeRange.append(60*24)

	elif whichType == 'next 1 hour' and whichKind == 'minute':
		timeRange.append(0)
		timeRange.append(5)
		timeRange.append(10)
		timeRange.append(15)
		timeRange.append(20)
		timeRange.append(25)
		timeRange.append(30)
		timeRange.append(35)
		timeRange.append(40)
		timeRange.append(45)
		timeRange.append(50)
		timeRange.append(55)
		timeRange.append(60)
	
	return timeRange
	

