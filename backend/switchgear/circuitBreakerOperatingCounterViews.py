
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

from backend.utilities.druidQuery import queryDruid
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

class CircuitBreakerOperatingCounterView(APIView):

	# Declare the static class variables
	global distinctStationList
	global equipmentList
	global swRangeList
	global stationList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here
			
			queryStatement = "select distinct station_id from "+config.EQUIPMENT_INFO+" where equipment = 'switchgear' order by station_id ASC"
			parameter = []
			distinctStationList = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+""
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_count,max_count,min_shunt,max_shunt,min_busbar,max_busbar,min_cable,max_cable,min_control,max_control,min_rx,max_rx,min_rz,max_rz,equipment_type from "+config.SWITCHGEAR_RANGE+""
			parameter = []
			swRangeList = queryPostgre(queryStatement,parameter)

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
		whichType = self.request.query_params.get('type')

		queryStatement = "select pm_count,service_count,trip_count,equipment_type from "+config.SWITCHGEAR_THRESHOLD+""
		parameter = []
		swThresholdList = queryPostgre(queryStatement,parameter)

		if whichType == '66kv':
			# Title: Show operating count by type and group by station  (#3)

			responseDict = {"category":"switchgear-66kv",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			servicelineDict = {"id":"threshold-2","name":"Service Required","axis_val":""}
			pmlineDict = {"id":"threshold-1","name":"PM Required","axis_val":""}

			# Populate the data from the static table
			for te in swThresholdList:
				if te[3] == config.SWITCHGEAR_66KV:
					servicelineDict['axis_val'] = te[1]
					pmlineDict['axis_val'] = te[0]
					break

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#for te in swRangeList:
			#	if te[14] == config.SWITCHGEAR_66KV:
			#		responseDict['min_val'] = te[0]
			#		responseDict['max_val'] = te[1]
			#		break
			
			# Variable to record the highest and lowest value for circuit breaker operating counter
			# To be used for flexible range
			lowestCounter = 0
			highestCounter = 0
			breakerCount  = 1

			healthyDict = {"type":"healthy","data_series":[],"mark_lines":""}
			pmReqDict = {"type":"pm-required","data_series":[],"mark_lines":""}
			serviceReqDict = {"type":"service-required","data_series":[],"mark_lines":""}

			for te in distinctStationList:
				for li in stationList:
					if li[0] == te[0]:
						responseDict['station_series'].append(li[1])
						break		

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,counter,is_pm_done,is_pm_ready,is_service_done,is_service_ready,record_time from "+config.OPERATING_COUNT+" order by station_id ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				opsCountData = thisRow[4]

				# Check the equipment type from equipment_info
				for te in equipmentList:
					if te[5] == thisRow[0] and te[6] == thisRow[1] and te[7] == thisRow[2] and te[8] == thisRow[3] and te[3] == config.SWITCHGEAR_66KV:
						asset_name = te[1]

						insertDict = {"name":"","station":"","value":""}
						insertDict['name'] = asset_name
						for li in stationList:
							if thisRow[0] == li[0]:
								insertDict['station'] = li[1]
								break
						insertDict['value'] = opsCountData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if breakerCount == 1:
							lowestCounter = opsCountData
							highestCounter = opsCountData
							breakerCount += 1
						else:
							if opsCountData > highestCounter:
								highestCounter = opsCountData
							elif opsCountData < lowestCounter:
								lowestCounter = opsCountData
						#----------------------------------------------------------------						

						# if opsCountData >= pmlineDict['axis_val'] and opsCountData < servicelineDict['axis_val'] and thisRow[5] == 0 and thisRow[6] == 1:
						# elif opsCountData >= servicelineDict['axis_val'] and thisRow[7] == 0 and thisRow[8] == 1:		
						# if count is more than PM count but less than service count, and PM is not done
						if opsCountData >= pmlineDict['axis_val'] and opsCountData < servicelineDict['axis_val'] and thisRow[5] == 0:			
							pmReqDict['data_series'].append(insertDict)
						# else if count is more than service count and service is not done
						elif opsCountData >= servicelineDict['axis_val'] and thisRow[7] == 0:
							serviceReqDict['data_series'].append(insertDict)
						else:
							healthyDict['data_series'].append(insertDict)
						break

			marklinesHealthy = {"data":[]}
			marklinesPM = {"data":[]}
			marklinesService = {"data":[]}

			marklinesService['data'].append(servicelineDict)
			marklinesPM['data'].append(pmlineDict)

			pmReqDict['mark_lines'] = marklinesPM
			serviceReqDict['mark_lines'] = marklinesService
			healthyDict['mark_lines'] = marklinesHealthy

			responseDict['dataset'].append(pmReqDict)
			responseDict['dataset'].append(serviceReqDict)
			responseDict['dataset'].append(healthyDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			#responseDict['min_val'] = round(lowestCounter - (highestCounter*0.3))
			# operating count cannot be negative..
			responseDict['min_val'] = 0
			responseDict['max_val'] = round(highestCounter + (highestCounter*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestCounter) + 0.5) / (1 + 0.3)

			if highestCounter < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestCounter + (highestCounter*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		elif whichType == '22kv':
			# Title: Show operating count by type and group by station  (#4)

			responseDict = {"category":"switchgear-22kv",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			servicelineDict = {"id":"threshold-2","name":"Service Required","axis_val":""}
			pmlineDict = {"id":"threshold-1","name":"PM Required","axis_val":""}

			# Populate the data from the static table
			for te in swThresholdList:
				if te[3] == config.SWITCHGEAR_22KV:
					servicelineDict['axis_val'] = te[1]
					pmlineDict['axis_val'] = te[0]
					break

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#for te in swRangeList:
			#	if te[14] == config.SWITCHGEAR_22KV:
			#		responseDict['min_val'] = te[0]
			#		responseDict['max_val'] = te[1]
			#		break

			# Variable to record the highest and lowest value for circuit breaker operating counter
			# To be used for flexible range
			lowestCounter = 0
			highestCounter = 0
			breakerCount  = 1
			
			healthyDict = {"type":"healthy","data_series":[],"mark_lines":""}
			pmReqDict = {"type":"pm-required","data_series":[],"mark_lines":""}
			serviceReqDict = {"type":"service-required","data_series":[],"mark_lines":""}

			for te in distinctStationList:
				for li in stationList:
					if li[0] == te[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,counter,is_pm_done,is_pm_ready,is_service_done,is_service_ready,record_time from "+config.OPERATING_COUNT+" order by station_id ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				opsCountData = thisRow[4]

				# Check the equipment type from equipment_info
				for te in equipmentList:
					if te[5] == thisRow[0] and te[6] == thisRow[1] and te[7] == thisRow[2] and te[8] == thisRow[3] and te[3] == config.SWITCHGEAR_22KV:
						asset_name = te[1]
						
						insertDict = {"name":"","station":"","value":""}
						insertDict['name'] = asset_name
						for li in stationList:
							if thisRow[0] == li[0]:
								insertDict['station'] = li[1]
								break
						insertDict['value'] = opsCountData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if breakerCount == 1:
							lowestCounter = opsCountData
							highestCounter = opsCountData
							breakerCount += 1
						else:
							if opsCountData > highestCounter:
								highestCounter = opsCountData
							elif opsCountData < lowestCounter:
								lowestCounter = opsCountData
						#----------------------------------------------------------------

						# if opsCountData >= pmlineDict['axis_val'] and opsCountData < servicelineDict['axis_val'] and thisRow[5] == 0 and thisRow[6] == 1:
						# elif opsCountData >= servicelineDict['axis_val'] and thisRow[7] == 0 and thisRow[8] == 1:
						# if count is more than PM count but less than service count, and PM is not done
						if opsCountData >= pmlineDict['axis_val'] and opsCountData < servicelineDict['axis_val'] and thisRow[5] == 0:					
							pmReqDict['data_series'].append(insertDict)
						# else if count is more than service count and service is not done
						elif opsCountData >= servicelineDict['axis_val'] and thisRow[7] == 0:
							serviceReqDict['data_series'].append(insertDict)
						else:
							healthyDict['data_series'].append(insertDict)
						break

			marklinesHealthy = {"data":[]}
			marklinesPM = {"data":[]}
			marklinesService = {"data":[]}

			marklinesService['data'].append(servicelineDict)
			marklinesPM['data'].append(pmlineDict)

			pmReqDict['mark_lines'] = marklinesPM
			serviceReqDict['mark_lines'] = marklinesService
			healthyDict['mark_lines'] = marklinesHealthy

			responseDict['dataset'].append(pmReqDict)
			responseDict['dataset'].append(serviceReqDict)
			responseDict['dataset'].append(healthyDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			#responseDict['min_val'] = round(lowestCounter - (highestCounter*0.3))
			# operating count cannot be negative..
			responseDict['min_val'] = 0
			responseDict['max_val'] = round(highestCounter + (highestCounter*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestCounter) + 0.5) / (1 + 0.3)

			if highestCounter < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestCounter + (highestCounter*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		elif whichType == '750vdc':
			# Title: Show operating count by type and group by station  (#5)

			responseDict = {"category":"switchgear-750kv",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			servicelineDict = {"id":"threshold-2","name":"Service Required","axis_val":""}
			pmlineDict = {"id":"threshold-1","name":"PM Required","axis_val":""}

			# Populate the data from the static table
			for te in swThresholdList:
				if te[3] == config.SWITCHGEAR_750VDC:
					servicelineDict['axis_val'] = te[1]
					pmlineDict['axis_val'] = te[0]
					break

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#for te in swRangeList:
			#	if te[14] == config.SWITCHGEAR_750VDC:
			#		responseDict['min_val'] = te[0]
			#		responseDict['max_val'] = te[1]
			#		break

			# Variable to record the highest and lowest value for circuit breaker operating counter
			# To be used for flexible range
			lowestCounter = 0
			highestCounter = 0
			breakerCount  = 1
			
			healthyDict = {"type":"healthy","data_series":[],"mark_lines":""}
			pmReqDict = {"type":"pm-required","data_series":[],"mark_lines":""}
			serviceReqDict = {"type":"service-required","data_series":[],"mark_lines":""}

			for te in distinctStationList:
				for li in stationList:
					if li[0] == te[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,counter,is_pm_done,is_pm_ready,is_service_done,is_service_ready,record_time from "+config.OPERATING_COUNT+" order by station_id ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				opsCountData = thisRow[4]
				
				# Check the equipment type from equipment_info
				for te in equipmentList:
					if te[5] == thisRow[0] and te[6] == thisRow[1] and te[7] == thisRow[2] and te[8] == thisRow[3] and te[3] == config.SWITCHGEAR_750VDC:
						asset_name = te[1]

						insertDict = {"name":"","station":"","value":""}
						insertDict['name'] = asset_name
						for li in stationList:
							if thisRow[0] == li[0]:
								insertDict['station'] = li[1]
								break
						insertDict['value'] = opsCountData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if breakerCount == 1:
							lowestCounter = opsCountData
							highestCounter = opsCountData
							breakerCount += 1
						else:
							if opsCountData > highestCounter:
								highestCounter = opsCountData
							elif opsCountData < lowestCounter:
								lowestCounter = opsCountData
						#----------------------------------------------------------------

						# if opsCountData >= pmlineDict['axis_val'] and opsCountData < servicelineDict['axis_val'] and thisRow[5] == 0 and thisRow[6] == 1:
						# elif opsCountData >= servicelineDict['axis_val'] and thisRow[7] == 0 and thisRow[8] == 1:
						# if count is more than PM count but less than service count, and PM is not done
						if opsCountData >= pmlineDict['axis_val'] and opsCountData < servicelineDict['axis_val'] and thisRow[5] == 0:					
							pmReqDict['data_series'].append(insertDict)
						# else if count is more than service count and service is not done
						elif opsCountData >= servicelineDict['axis_val'] and thisRow[7] == 0:
							serviceReqDict['data_series'].append(insertDict)
						else:
							healthyDict['data_series'].append(insertDict)
						break

			marklinesHealthy = {"data":[]}
			marklinesPM = {"data":[]}
			marklinesService = {"data":[]}

			marklinesService['data'].append(servicelineDict)
			marklinesPM['data'].append(pmlineDict)

			pmReqDict['mark_lines'] = marklinesPM
			serviceReqDict['mark_lines'] = marklinesService
			healthyDict['mark_lines'] = marklinesHealthy

			responseDict['dataset'].append(pmReqDict)
			responseDict['dataset'].append(serviceReqDict)
			responseDict['dataset'].append(healthyDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			#responseDict['min_val'] = round(lowestCounter - (highestCounter*0.3))
			# operating count cannot be negative..
			responseDict['min_val'] = 0
			responseDict['max_val'] = round(highestCounter + (highestCounter*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestCounter) + 0.5) / (1 + 0.3)

			if highestCounter < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestCounter + (highestCounter*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)	

			return processResponse(resultJSON,'OK')
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')
			



	







