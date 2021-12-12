
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
from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnResponse import processResponse
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Create your views here.
class TransformerReadingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global warningDefList
	global trRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+"  where equipment = 'transformer' order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select warning_code,warning_message,class,severity from "+config.WARNING_DEF+""
			parameter = []
			warningDefList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_winding,max_winding,min_currentl1,max_currentl1,min_currentl2,max_currentl2,min_currentl3,max_currentl3,min_loading,max_loading,min_oil,max_oil,equipment_type,min_ambient,max_ambient from "+config.TRANSFORMER_RANGE+""
			parameter = []
			trRangeList = queryPostgre(queryStatement,parameter)

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

		windingMax = None
		oilMax = None
		loadingMax = None 

		windingMin = None
		oilMin = None
		loadingMin = None 
		
		# find the equipment info given the asset_name
		for te in equipmentList:
			if te[0] == assetName:
				station_id = te[4]
				system_id = te[5]
				subsystem_id = te[6]
				detail_code = te[7]
				equipment_type = te[2]
				break

		# find the maximum allowable value for this equipment type
		for te in trRangeList:
			if te[12] == equipment_type:
				windingMax = te[1]
				oilMax = te[11]
				loadingMax = te[9]
				break

		responseDict = {
				"temperature_model":{},
				"current_model":{},
				"transformer_status":"",
				"battery_status":"Work in progress"
				}
		temperatureModel = {"current_reading":[]}
		currentModel = {"current_reading":[]}

		temperatureList = []
		currentList = []

		windingDict = {"id":"winding","name":"Winding","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":"","threshold_val2":""}
		oilDict = {"id":"oil","name":"Oil","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		ambientDict = {"id":"ambient","name":"Ambient","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		loadingDict = {"id":"total-loading","name":"Total Loading","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}

		L1Dict = {"id":"l1","name":"L1","min_val":"","max_val":"","current_val":"","threshold_val1":""}
		L2Dict = {"id":"l2","name":"L2","min_val":"","max_val":"","current_val":"","threshold_val1":""}
		L3Dict = {"id":"l3","name":"L3","min_val":"","max_val":"","current_val":"","threshold_val1":""}

		# First treat everything as healthy
		windingDict['status'] = 'Healthy'
		windingDict['description'] = 'Healthy'
		oilDict['status'] = 'Healthy'
		oilDict['description'] = 'Healthy'
		loadingDict['status'] = 'Healthy'
		loadingDict['description'] = 'Healthy'
		ambientDict['status'] = 'Healthy'
		ambientDict['description'] = 'Healthy'
		
		# Query the transformer's thresholds based on its equipment_type
		queryStatement = "select windings1,windings2,currentl1,currentl2,currentl3,total_loading,oils1,oils2,ambient from "+config.TRANSFORMER_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
		parameter = [equipment_type]
		trThresholdList = queryPostgre(queryStatement,parameter)

		queryStatement = "select winding_temperature,oil_temperature,active_power,l1_current,l2_current,l3_current,record_time from "+config.TRANSFORMER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)
		
		if len(resultList) > 0:
			thisRow = resultList[0]
			windingDict['current_val'] = thisRow[0]
			oilDict['current_val'] = thisRow[1]
			loadingDict['current_val'] = thisRow[2]
			L1Dict['current_val'] = thisRow[3]
			L2Dict['current_val'] = thisRow[4]
			L3Dict['current_val'] = thisRow[5]

			# Double check for null values
			# Double check for out of range values
			if thisRow[0] == None:
				windingDict['status'] = 'Unknown'
				windingDict['description'] = 'Unknown'
				windingDict['current_val'] = 'NO VALUE'
			elif thisRow[0] > int(windingMax) and thisRow[0] < int(windingMin):
				windingDict['status'] = 'outrange'
				windingDict['description'] = 'out of range'
				windingDict['current_val'] = 'out of range'

			if thisRow[1] == None:
				oilDict['status'] = 'Unknown'
				oilDict['description'] = 'Unknown'
				oilDict['current_val'] = 'NO VALUE'
			elif thisRow[1] > int(oilMax) and thisRow[1] < int(oilMin):
				oilDict['status'] = 'outrange'
				oilDict['description'] = 'out of range'
				oilDict['current_val'] = 'out of range'

			if thisRow[2] == None:
				loadingDict['status'] = 'Unknown'
				loadingDict['description'] = 'Unknown'
				loadingDict['current_val'] = 'NO VALUE'
			elif thisRow[2] > int(loadingMax) and thisRow[2] < int(loadingMin):
				loadingDict['status'] = 'outrange'
				loadingDict['description'] = 'out of range'
				loadingDict['current_val'] = 'out of range'
		else:
			windingDict['current_val'] = 'NO VALUE'
			oilDict['current_val'] = 'NO VALUE'
			loadingDict['current_val'] = 'NO VALUE'
			L1Dict['current_val'] = 'NO VALUE'
			L2Dict['current_val'] = 'NO VALUE'
			L3Dict['current_val'] = 'NO VALUE'
			# This means that the status is unknown since no data present
			windingDict['status'] = 'Unknown'
			windingDict['description'] = 'Unknown'
			oilDict['status'] = 'Unknown'
			oilDict['description'] = 'Unknown'
			loadingDict['status'] = 'Unknown'
			loadingDict['description'] = 'Unknown'

		# Populate the static values from postgre
		for te in trRangeList:
			if te[12] == equipment_type:
				windingDict['min_val'] = te[0]
				windingDict['max_val'] = te[1]
				oilDict['min_val'] = te[10]
				oilDict['max_val'] = te[11]
				loadingDict['min_val'] = te[8]
				loadingDict['max_val'] = te[9]
				L1Dict['min_val'] = te[2]
				L1Dict['max_val'] = te[3]
				L2Dict['min_val'] = te[4]
				L2Dict['max_val'] = te[5]
				L3Dict['min_val'] = te[6]
				L3Dict['max_val'] = te[7]
				ambientDict['min_val'] = te[13]
				ambientDict['max_val'] = te[14]
				break

		for te in trThresholdList:
			windingDict['threshold_val1'] = te[0]
			windingDict['threshold_val2'] = te[1]
			oilDict['threshold_val1'] = te[6]
			oilDict['threshold_val2'] = te[7]
			loadingDict['threshold_val1'] = te[5]
			L1Dict['threshold_val1'] = te[2]
			L2Dict['threshold_val1'] = te[3]
			L3Dict['threshold_val1'] = te[4]
			ambientDict['threshold_val1'] = 0
			ambientDict['current_val'] = te[8]

		ambientDict['min_val'] = '0'
		ambientDict['max_val'] = '100'
				
		criticalFlag = 'FALSE'

		queryStatement = "select warning_code,component,record_time from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and status = '0' and component like 'transformer:%%' order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		for thisRow in resultList:
			if thisRow[1] == 'transformer:winding':
				if thisRow[0] != 'NA':
					windingDict['status'] = 'warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							windingDict['description'] = te[1]
							if te[3] == 4:
								criticalFlag = 'TRUE'
							break

			elif thisRow[1] == 'transformer:oil':
				if thisRow[0] != 'NA':
					oilDict['status'] = 'warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							oilDict['description'] = te[1]
							if te[3] == 4:
								criticalFlag = 'TRUE'
							break

			elif thisRow[1] == 'transformer:activepower':
				if thisRow[0] != 'NA':
					loadingDict['status'] = 'warning'
					for te in warningDefList:
						if te[0] == thisRow[0]:
							loadingDict['description'] = te[1]
							if te[3] == 4:
								criticalFlag = 'TRUE'
							break

		if len(resultList) > 0:	
			responseDict['transformer_status'] = 'warning'
		else:
			responseDict['transformer_status'] = 'healthy'
			
		if criticalFlag == 'TRUE':
			responseDict['transformer_status'] = 'critical'

		temperatureList.append(windingDict)
		temperatureList.append(oilDict)
		temperatureList.append(ambientDict)

		currentList.append(L1Dict)
		currentList.append(L2Dict)
		currentList.append(L3Dict)
		currentList.append(loadingDict)

		temperatureModel['current_reading'] = temperatureList
		currentModel['current_reading'] = currentList

		responseDict['temperature_model'] = temperatureModel
		responseDict['current_model'] = currentModel

		resultJSON = processJSON(responseDict)

		return processResponse(resultJSON,'OK')


