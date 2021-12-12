from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status
from rest_framework.views import APIView

import requests
import json
import datetime
import calendar

from backend.utilities.druidQuery import queryDruid
from backend.utilities.postgreQuery import queryPostgre
from backend.utilities.postgreUpdate import updatePostgre
#from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnJSON import processJSON
from backend.utilities.returnResponse import processResponse
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Create your views here.

class ConfigurationView(APIView):
	# Declare the static class variables
	global equipmentList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200
	
		if connection_status == 200 and (connection_status != 'No route to host' or connection_status != 'Errors encountered!'):	
			# Add all the static datasources here

			queryStatement = "select DISTINCT equipment,equipment_type,equipment_type_name from "+config.EQUIPMENT_INFO+""
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):

		responseList=[]
		
		transformerConfigDict = {
						"category":"transformer",
						"type":"threshold",
						"id":"transformer-configs",
						"name":"Transformer",
						"item_list":[]
					}
		switchgearConfigDict = {
						"category":"switchgear",
						"type":"threshold",
						"id":"switchgear-configs",
						"name":"Switchgear",
						"item_list":[]
					}
		doubleconverterConfigDict = {
						"category":"dconverter",
						"type":"threshold",
						"id":"doubleconverter-configs",
						"name":"Doubleconverter",
						"item_list":[]
					}
		rectifierConfigDict = {
						"category":"rectifier",
						"type":"threshold",
						"id":"rectifier-configs",
						"name":"Rectifier",
						"item_list":[]
					}
		inverterConfigDict = {
						"category":"inverter",
						"type":"threshold",
						"id":"inverter-configs",
						"name":"Inverter",
						"item_list":[]
					}

		bmuConfigDict = {
						"category":"batterymonitoringunit",
						"type":"threshold",
						"id":"bmu-configs",
						"name":"Battery monitoring unit",
						"item_list":[]
					}

		for thisRow in equipmentList:
			if thisRow[0] == 'transformer':
				transformerConfigDict['item_list'].append({"item_code":thisRow[1],"item_name":thisRow[2]})

			elif thisRow[0] == 'switchgear':
				switchgearConfigDict['item_list'].append({"item_code":thisRow[1],"item_name":thisRow[2]})

			elif thisRow[0] == 'dconverter':
				doubleconverterConfigDict['item_list'].append({"item_code":thisRow[1],"item_name":thisRow[2]})

			elif thisRow[0] == 'rectifier':
				rectifierConfigDict['item_list'].append({"item_code":thisRow[1],"item_name":thisRow[2]})

			elif thisRow[0] == 'inverter':
				inverterConfigDict['item_list'].append({"item_code":thisRow[1],"item_name":thisRow[2]})

			elif thisRow[0] == 'BMU':
				bmuConfigDict['item_list'].append({"item_code":thisRow[1],"item_name":thisRow[2]})

		responseList.append(transformerConfigDict)
		responseList.append(switchgearConfigDict)
		responseList.append(doubleconverterConfigDict)
		responseList.append(rectifierConfigDict)
		responseList.append(inverterConfigDict)
		responseList.append(bmuConfigDict)

		resultJSON = processJSON(responseList)

		return processResponse(resultJSON,'OK')
