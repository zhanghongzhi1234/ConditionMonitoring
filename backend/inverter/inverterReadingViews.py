
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

import random
import time

from backend.utilities.druidQuery import queryDruid
from backend.utilities.postgreQuery import queryPostgre
from backend.utilities.postgreUpdate import updatePostgre
#from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnResponse import processResponse
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Create your views here.
class InverterReadingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global warningDefList
	global ivRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+"  where equipment = 'inverter' order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select warning_code,warning_message,class from "+config.WARNING_DEF+""
			parameter = []
			warningDefList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_operation_counts,max_operation_counts,min_max_power,max_max_power,min_panel_temp_1,max_panel_temp_1,min_panel_temp_2,max_panel_temp_2,equipment_type from "+config.INVERTER_RANGE+""
			parameter = []
			ivRangeList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		# Title: Show transformer individual readings

		assetName = self.request.query_params.get('equipment_code')

		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None

		operationCountsMax = None
		maxPowerMax = None
		panelTemperatureOneMax = None
		panelTemperatureTwoMax = None

		operationCountsMin = None
		maxPowerMin = None
		panelTemperatureOneMin = None
		panelTemperatureTwoMin = None
		
		# find the equipment info given the asset_name
		for te in equipmentList:
			if te[0] == assetName:
				station_id = te[4]
				system_id = te[5]
				subsystem_id = te[6]
				detail_code = te[7]
				equipment_type = te[2]
				break

		# find the maximum and minimum allowable value for this equipment type
		for te in ivRangeList:
			if te[8] == equipment_type:
				operationCountsMax = te[1]
				maxPowerMax = te[3]
				panelTemperatureOneMax = te[5]
				panelTemperatureTwoMax = te[7]

				operationCountsMin = te[0]
				maxPowerMin = te[2]
				panelTemperatureOneMin = te[4]
				panelTemperatureTwoMin = te[6]
				break

		responseDict = {
				"current_reading":[],
				}

		operationCounts = {"id":"operation-counts","name":"Operation Counts","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		maxPower = {"id":"max-power","name":"Maximum Power","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		panelTemperatureOne = {"id":"panel-temp1","name":"Panel 1","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		panelTemperatureTwo = {"id":"panel-temp2","name":"Panel 2","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		
		# First treat everything as healthy
		operationCounts['status'] = 'Healthy'
		operationCounts['description'] = 'Healthy'
		maxPower['status'] = 'Healthy'
		maxPower['description'] = 'Healthy'
		panelTemperatureOne['status'] = 'Healthy'
		panelTemperatureOne['description'] = 'Healthy'
		panelTemperatureTwo['status'] = 'Healthy'
		panelTemperatureTwo['description'] = 'Healthy'

		queryStatement = "select operation_counts,max_power,panel_temp_1,panel_temp_2 from "+config.INVERTER_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
		parameter = [equipment_type]
		ivThresholdList = queryPostgre(queryStatement,parameter)

		queryStatement = "select operation_counts,max_power,panel_temp_1,panel_temp_2,record_time from "+config.INVERTER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)
		
		if len(resultList) > 0:
			thisRow = resultList[0]
			operationCounts['current_val'] = thisRow[0]
			maxPower['current_val'] = thisRow[1]
			panelTemperatureOne['current_val'] = thisRow[2]
			panelTemperatureTwo['current_val'] = thisRow[3]

			# Double check for null values status
			# Double check for out of range values
			if thisRow[0] == None:
				operationCounts['status'] = 'Unknown'
				operationCounts['description'] = 'Unknown'
				operationCounts['current_val'] = 'NO VALUE'
			elif thisRow[0] > int(operationCountsMax) and thisRow[0] < int(operationCountsMin):
				operationCounts['status'] = 'outrange'
				operationCounts['description'] = 'out of range'
				operationCounts['current_val'] = 'out of range'

			if thisRow[1] == None:
				maxPower['status'] = 'Unknown'
				maxPower['description'] = 'Unknown'
				maxPower['current_val'] = 'NO VALUE'
			elif thisRow[1] > int(maxPowerMax) and thisRow[1] < int(maxPowerMin):
				maxPower['status'] = 'outrange'
				maxPower['description'] = 'out of range'
				maxPower['current_val'] = 'out of range'

			if thisRow[2] == None:
				panelTemperatureOne['status'] = 'Unknown'
				panelTemperatureOne['description'] = 'Unknown'
				panelTemperatureOne['current_val'] = 'NO VALUE'
			elif thisRow[2] > int(panelTemperatureOneMax) and thisRow[2] < int(panelTemperatureOneMin):
				panelTemperatureOne['status'] = 'outrange'
				panelTemperatureOne['description'] = 'out of range'
				panelTemperatureOne['current_val'] = 'out of range'

			if thisRow[3] == None:
				panelTemperatureTwo['status'] = 'Unknown'
				panelTemperatureTwo['description'] = 'Unknown'
				panelTemperatureTwo['current_val'] = 'NO VALUE'
			elif thisRow[3] > int(panelTemperatureTwoMax) and thisRow[3] < int(panelTemperatureTwoMin):
				panelTemperatureTwo['status'] = 'outrange'
				panelTemperatureTwo['description'] = 'out of range'
				panelTemperatureTwo['current_val'] = 'out of range'
		else:
			operationCounts['current_val'] = 'NO VALUE'
			maxPower['current_val'] = 'NO VALUE'
			panelTemperatureOne['current_val'] = 'NO VALUE'
			panelTemperatureTwo['current_val'] = 'NO VALUE'

			operationCounts['status'] = 'Unknown'
			operationCounts['description'] = 'Unknown'
			maxPower['status'] = 'Unknown'
			maxPower['description'] = 'Unknown'
			panelTemperatureOne['status'] = 'Unknown'
			panelTemperatureOne['description'] = 'Unknown'
			panelTemperatureTwo['status'] = 'Unknown'
			panelTemperatureTwo['description'] = 'Unknown'

		# Populate the static values from postgre
		for te in ivRangeList:
			if te[8] == equipment_type:
				operationCounts['min_val'] = te[0]
				operationCounts['max_val'] = te[1]
				maxPower['min_val'] = te[2]
				maxPower['max_val'] = te[3]
				panelTemperatureOne['min_val'] = te[4]
				panelTemperatureOne['max_val'] = te[5]
				panelTemperatureTwo['min_val'] = te[6]
				panelTemperatureTwo['max_val'] = te[7]
				break
				
		for te in ivThresholdList:
			operationCounts['threshold_val1'] = te[0]
			maxPower['threshold_val1'] = te[1]
			panelTemperatureOne['threshold_val1'] = te[2]
			panelTemperatureTwo['threshold_val1'] = te[3]
			break

		queryStatement = "select warning_code,component,record_time from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and status = '0' and component like 'inverter:%%' order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		for thisRow in resultList:
			if thisRow[1] == 'inverter:operationcounts':
				if thisRow[0] != 'NA':
					operationCounts['status'] = 'Warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							operationCounts['description'] = te[1]
							break

			elif thisRow[1] == 'inverter:maxpower':
				if thisRow[0] != 'NA':
					maxPower['status'] = 'Warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							maxPower['description'] = te[1]
							break

			elif thisRow[1] == 'inverter:paneltemp1':
				if thisRow[0] != 'NA':
					panelTemperatureOne['status'] = 'Warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							panelTemperatureOne['description'] = te[1]
							break

			elif thisRow[1] == 'inverter:paneltemp2':
				if thisRow[0] != 'NA':
					panelTemperatureTwo['status'] = 'Warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							panelTemperatureTwo['description'] = te[1]
							break

		responseDict['current_reading'].append(operationCounts)
		responseDict['current_reading'].append(maxPower)
		responseDict['current_reading'].append(panelTemperatureOne)
		responseDict['current_reading'].append(panelTemperatureTwo)

		resultJSON = processJSON(responseDict)

		return processResponse(resultJSON,'OK')

