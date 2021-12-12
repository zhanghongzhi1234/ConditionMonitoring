
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

import time
import math

from backend.utilities.postgreQuery import queryPostgre
from backend.utilities.postgreUpdate import updatePostgre
#from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnResponse import processResponse
from backend.utilities.kafkaInsert import insertKafkaDictList
from backend.utilities.kafkaInsert import insertKafkaStringList
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

class MaximumPowerView(APIView):

	# Declare the static class variables
	global equipmentList
	global distinctStationList
	global maxPowerRangeList
	global stationList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here
			
			queryStatement = "select acronym_asset_name,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code from "+config.EQUIPMENT_INFO+" order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select distinct station_id from "+config.EQUIPMENT_INFO+" where equipment = 'inverter' order by station_id"
			parameter = []
			distinctStationList = queryPostgre(queryStatement,parameter)
			
			queryStatement = "select min_max_power,max_max_power equipment_type from "+config.INVERTER_RANGE+""
			parameter = []
			maxPowerRangeList = queryPostgre(queryStatement,parameter)

			queryStatement = "select distinct station_id,station_acronym from "+config.STATION_INFO+" order by station_id"
			parameter = []
			stationList = queryPostgre(queryStatement,parameter)
			
			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		groupby = self.request.query_params.get('group-by')
		
		queryStatement = "select max_power,equipment_type from "+config.INVERTER_THRESHOLD+""
		parameter = []
		maxPowerTHList = queryPostgre(queryStatement,parameter)

		maxPowerThreshold = maxPowerTHList[0]
		maxPowerRange = maxPowerRangeList[0]

		responseDict = {"category":"max-power",
				"station_series":[],
				"min_val":"",
				"max_val":"",
				"dataset":[]
				}

		# Patch to make the range more flexible. Patch to be found below
		# This section will be commented off	
		#responseDict['min_val']=maxPowerRange[0]
		#responseDict['max_val']=maxPowerRange[1]
		
		# Variable to record the highest and lowest value for operation count inv mode
		# To be used for flexible range
		lowestPower = 0
		highestPower = 0
		powerCount  = 1

		maxPowerDict = {"type":"maximum power","data_series":[],"mark_lines":""}

		th1Dict = {"id":"warning-1","name":"maximum power threshold","axis_val":""}

		th1Dict['axis_val'] = maxPowerThreshold[0]

		for te in distinctStationList:
			for li in stationList:
				if te[0] == li[0]:
					responseDict['station_series'].append(li[1])
					break

		queryStatement = "select station_id,system_id,subsystem_id,detail_code,max_power,record_time from "+config.INVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
		parameter = []
		resultList = queryPostgre(queryStatement,parameter)

		# Declaration of the asset_name. Default NA- Not applicable
		asset_name = 'NA'

		# Loop through the entire resultset, processing the data accordingly
		for thisRow in resultList:	
			powerData = thisRow[4]

			# Check the equipment type from equipment_info
			for te in equipmentList:
				if te[3] == thisRow[0] and te[4] == thisRow[1] and te[5] == thisRow[2] and te[6] == thisRow[3]:
					asset_name = te[0]
				
					insertDict = {"name":"","station":"","value":""}
					insertDict['name'] = asset_name
					for li in stationList:
						if thisRow[0] == li[0]:
							insertDict['station'] = li[1]
							break
					insertDict['value'] = powerData
					
					# Patch to record the highest and lowest value for flexible range
					#----------------------------------------------------------------
					if powerCount == 1:
						lowestPower = powerData
						highestPower = powerData
						powerCount += 1
					else:
						if powerData > highestPower:
							highestPower = powerData
						elif powerData < lowestPower:
							lowestPower = powerData
					#----------------------------------------------------------------	

					maxPowerDict['data_series'].append(insertDict)
					break

		marklines = {"data":[]}
		marklines['data'].append(th1Dict)
		maxPowerDict['mark_lines'] = marklines

		responseDict['dataset'].append(maxPowerDict)
		
		# Patch to be added here for flexible range
		#--------------------------------------------------------
		responseDict['min_val'] = round(lowestPower - (highestPower*0.3))
		responseDict['max_val'] = round(highestPower + (highestPower*0.3))

		# Do a double check here.
		# If both min_val and max_val are the same. Nothing will be plotted.
		# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
		# Since round() function >= 0.5 goes to the next number
		# Let highest value be A
		# A + (A * 0.3) >= math.floor(A) + 0.5
		# A (1 + 0.3) >= math.floor(A) + 0.5
		# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

		toNext = (math.floor(highestPower) + 0.5) / (1 + 0.3)

		if highestPower < toNext:
			# Add one to the highest value
			responseDict['max_val'] = round(highestPower + (highestPower*0.3)) + 1
		#--------------------------------------------------------

		resultJSON = processJSON(responseDict)

		return processResponse(resultJSON,'OK')
	
			
	




