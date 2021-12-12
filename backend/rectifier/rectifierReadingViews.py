
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
class RectifierReadingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global warningDefList
	global rcRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+"  where equipment = 'rectifier' order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select warning_code,warning_message,class from "+config.WARNING_DEF+""
			parameter = []
			warningDefList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_panel_temp_1,max_panel_temp_1,min_panel_temp_2,max_panel_temp_2,min_panel_temp_3,max_panel_temp_3,min_panel_temp_4,max_panel_temp_4,equipment_type from "+config.RECTIFIER_RANGE+""
			parameter = []
			rcRangeList = queryPostgre(queryStatement,parameter)

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

		panelTemperatureOneMax = None
		panelTemperatureTwoMax = None
		panelTemperatureThreeMax = None
		panelTemperatureFourMax = None

		panelTemperatureOneMin = None
		panelTemperatureTwoMin = None
		panelTemperatureThreeMin = None
		panelTemperatureFourMin = None
		
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
		for te in rcRangeList:
			if te[8] == equipment_type:
				panelTemperatureOneMax = te[1]
				panelTemperatureTwoMax = te[3]
				panelTemperatureThreeMax = te[5]
				panelTemperatureFourMax = te[7]

				panelTemperatureOneMin = te[0]
				panelTemperatureTwoMin = te[2]
				panelTemperatureThreeMin = te[4]
				panelTemperatureFourMin = te[6]
				break

		responseDict = {
				"current_reading":[],
				}

		panelTemperatureOne = {"id":"panel-temp1","name":"Panel Temperature 1","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		panelTemperatureTwo = {"id":"panel-temp2","name":"Panel Temperature 2","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		panelTemperatureThree = {"id":"panel-temp3","name":"Panel Temperature 3","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		panelTemperatureFour = {"id":"panel-temp4","name":"Panel Temperature 4","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		
		# First treat everything as healthy
		panelTemperatureOne['status'] = 'Healthy'
		panelTemperatureOne['description'] = 'Healthy'
		panelTemperatureTwo['status'] = 'Healthy'
		panelTemperatureTwo['description'] = 'Healthy'
		panelTemperatureThree['status'] = 'Healthy'
		panelTemperatureThree['description'] = 'Healthy'
		panelTemperatureFour['status'] = 'Healthy'
		panelTemperatureFour['description'] = 'Healthy'

		queryStatement = "select panel_temp_1,panel_temp_2,panel_temp_3,panel_temp_4 from "+config.RECTIFIER_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
		parameter = [equipment_type]
		rcThresholdList = queryPostgre(queryStatement,parameter)

		queryStatement = "select panel_temp_1,panel_temp_2,panel_temp_3,panel_temp_4,record_time from "+config.RECTIFIER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)
		
		if len(resultList) > 0:
			thisRow = resultList[0]
			panelTemperatureOne['current_val'] = thisRow[0]
			panelTemperatureTwo['current_val'] = thisRow[1]
			panelTemperatureThree['current_val'] = thisRow[2]
			panelTemperatureFour['current_val'] = thisRow[3]

			# Double check for null values status
			# Double check for out of range values
			if thisRow[0] == None:			
				panelTemperatureOne['status'] = 'Unknown'
				panelTemperatureOne['description'] = 'Unknown'
				panelTemperatureOne['current_val'] = 'NO VALUE'
			elif thisRow[0] > int(panelTemperatureOneMax) and thisRow[0] < int(panelTemperatureOneMin):
				panelTemperatureOne['status'] = 'outrange'
				panelTemperatureOne['description'] = 'out of range'
				panelTemperatureOne['current_val'] = 'out of range'

			if thisRow[1] == None:
				panelTemperatureTwo['status'] = 'Unknown'
				panelTemperatureTwo['description'] = 'Unknown'
				panelTemperatureTwo['current_val'] = 'NO VALUE'
			elif thisRow[1] > int(panelTemperatureTwoMax) and thisRow[1] < int(panelTemperatureTwoMin):
				panelTemperatureTwo['status'] = 'outrange'
				panelTemperatureTwo['description'] = 'out of range'
				panelTemperatureTwo['current_val'] = 'out of range'

			if thisRow[2] == None:
				panelTemperatureThree['status'] = 'Unknown'
				panelTemperatureThree['description'] = 'Unknown'
				panelTemperatureThree['current_val'] = 'NO VALUE'
			elif thisRow[2] > int(panelTemperatureThreeMax) and thisRow[2] < int(panelTemperatureThreeMin):
				panelTemperatureThree['status'] = 'outrange'
				panelTemperatureThree['description'] = 'out of range'
				panelTemperatureThree['current_val'] = 'out of range'

			if thisRow[3] == None:
				panelTemperatureFour['status'] = 'Unknown'
				panelTemperatureFour['description'] = 'Unknown'
				panelTemperatureFour['current_val'] = 'NO VALUE'
			elif thisRow[3] > int(panelTemperatureFourMax) and thisRow[3] < int(panelTemperatureFourMin):
				panelTemperatureFour['status'] = 'outrange'
				panelTemperatureFour['description'] = 'out of range'
				panelTemperatureFour['current_val'] = 'out of range'
		else:
			panelTemperatureOne['current_val'] = 'NO VALUE'
			panelTemperatureTwo['current_val'] = 'NO VALUE'
			panelTemperatureThree['current_val'] = 'NO VALUE'
			panelTemperatureFour['current_val'] = 'NO VALUE'

			panelTemperatureOne['status'] = 'Unknown'
			panelTemperatureOne['description'] = 'Unknown'
			panelTemperatureTwo['status'] = 'Unknown'
			panelTemperatureTwo['description'] = 'Unknown'
			panelTemperatureThree['status'] = 'Unknown'
			panelTemperatureThree['description'] = 'Unknown'
			panelTemperatureFour['status'] = 'Unknown'
			panelTemperatureFour['description'] = 'Unknown'

		# Populate the static values from postgre
		for te in rcRangeList:
			if te[8] == equipment_type:
				panelTemperatureOne['min_val'] = te[0]
				panelTemperatureOne['max_val'] = te[1]
				panelTemperatureTwo['min_val'] = te[2]
				panelTemperatureTwo['max_val'] = te[3]
				panelTemperatureThree['min_val'] = te[4]
				panelTemperatureThree['max_val'] = te[5]
				panelTemperatureFour['min_val'] = te[6]
				panelTemperatureFour['max_val'] = te[7]
				break
				
		for te in rcThresholdList:
			panelTemperatureOne['threshold_val1'] = te[0]
			panelTemperatureTwo['threshold_val1'] = te[1]
			panelTemperatureThree['threshold_val1'] = te[2]
			panelTemperatureFour['threshold_val1'] = te[3]
			break

		queryStatement = "select warning_code,component,record_time from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and status = '0' and component like 'rectifier:%%' order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		for thisRow in resultList:
			if thisRow[1] == 'rectifier:paneltemp1':
				if thisRow[0] != 'NA':
					panelTemperatureOne['status'] = 'Warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							panelTemperatureOne['description'] = te[1]
							break

			elif thisRow[1] == 'rectifier:paneltemp2':
				if thisRow[0] != 'NA':
					panelTemperatureTwo['status'] = 'Warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							panelTemperatureTwo['description'] = te[1]
							break

			elif thisRow[1] == 'rectifier:paneltemp3':
				if thisRow[0] != 'NA':
					panelTemperatureThree['status'] = 'Warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							panelTemperatureThree['description'] = te[1]
							break

			elif thisRow[1] == 'rectifier:paneltemp4':
				if thisRow[0] != 'NA':
					panelTemperatureFour['status'] = 'Warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							panelTemperatureFour['description'] = te[1]
							break

		responseDict['current_reading'].append(panelTemperatureOne)
		responseDict['current_reading'].append(panelTemperatureTwo)
		responseDict['current_reading'].append(panelTemperatureThree)
		responseDict['current_reading'].append(panelTemperatureFour)

		resultJSON = processJSON(responseDict)

		return processResponse(resultJSON,'OK')

