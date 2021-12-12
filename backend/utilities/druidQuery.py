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

def queryDruid(dataSQL):
	#print('Querying Druid...')

	url = config.urlDruid
	headers = config.contentTypeJson
	resultset = None

	try:
		resultset = requests.post(url,data=json.dumps(dataSQL),headers=headers)
		
	except Exception as ex:

		print('Exception in querying from Druid: ')
		print(str(ex))

	return resultset





	



