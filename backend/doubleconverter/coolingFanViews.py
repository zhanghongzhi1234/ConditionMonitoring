
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

class CoolingFanView(APIView):

	# Declare the static class variables
	global equipmentList
	global distinctStationList
	global coolingFanRangeList
	global stationList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here
			queryStatement = "select acronym_asset_name,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code from "+config.EQUIPMENT_INFO+""		
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select distinct station_id from "+config.EQUIPMENT_INFO+" where equipment = 'dconverter' order by station_id"		
			parameter = []	
			distinctStationList = queryPostgre(queryStatement,parameter)	

			queryStatement = "select min_operational_time_fans,max_operational_time_fans, min_operational_current_fans,max_operational_current_fans,equipment_type from "+config.DOUBLECONVERTER_RANGE+""
			parameter = []
			coolingFanRangeList  = queryPostgre(queryStatement,parameter)

			queryStatement = "select distinct station_id,station_acronym from "+config.STATION_INFO+" order by station_id"
			parameter = []
			stationList = queryPostgre(queryStatement,parameter)
			
			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: Druid service connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		groupby = self.request.query_params.get('group-by')
		whichtype = self.request.query_params.get('type')
		
		queryStatement = "select operational_time_fans,min_operational_current_fans,max_operational_current_fans,equipment_type from "+config.DOUBLECONVERTER_THRESHOLD+""
		parameter = []
		coolingFanTHList = queryPostgre(queryStatement,parameter)

		coolingFanThreshold = coolingFanTHList[0]
		coolingFanRange = coolingFanRangeList[0]

		if whichtype == 'operation-time':
			# By operational time cooling fans 

			responseDict = {"category":"Double Converter: Operational time cooling fans ",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=coolingFanRange[0]
			#responseDict['max_val']=coolingFanRange[1]
				
			# Variable to record the highest and lowest value for cooling fan
			# To be used for flexible range
			lowestOptTime = 0
			highestOptTime = 0
			optTimeCount  = 1
			
			servicelineDict = {"id":"service-line","name":"Servicing required","axis_val":""}

			#opsTimeFansDict = {"type":"operation","data_series":[],"mark_lines":""}
			healthyDict = {"type":"healthy","data_series":[],"mark_lines":""}
			serviceReqDict = {"type":"service-required","data_series":[],"mark_lines":""}

			servicelineDict['axis_val'] = coolingFanThreshold[0]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,operational_time_of_cooling_fans,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = None

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:				
				fanData = thisRow[4]

				# Check the asset_name from equipment_info
				for te in equipmentList:
					if te[3] == thisRow[0] and te[4] == thisRow[1] and te[5] == thisRow[2] and te[6] == thisRow[3]:
						asset_name = te[0]

						insertDict = {"name":"","station":"","value":""}
						insertDict['name'] = asset_name
						#insertDict['station'] = thisRow[0]
						for li in stationList:
							if thisRow[0] == li[0]:
								insertDict['station']=li[1]
								break
						insertDict['value'] = fanData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if fanData != None:
							if optTimeCount == 1:
								lowestOptTime = fanData
								highestOptTime = fanData
								optTimeCount += 1
							else:
								if fanData > highestOptTime:
									highestOptTime = fanData
								elif fanData < lowestOptTime:
									lowestOptTime = fanData
						#----------------------------------------------------------------

						#opsTimeFansDict['data_series'].append(insertDict)
						if fanData >= servicelineDict['axis_val']:
							serviceReqDict['data_series'].append(insertDict)
						else:
							healthyDict['data_series'].append(insertDict)
						break

			marklinesHealthy = {"data":[]}
			marklinesService = {"data":[]}
			
			marklinesService['data'].append(servicelineDict)

			serviceReqDict['mark_lines'] = marklinesService
			healthyDict['mark_lines'] = marklinesHealthy

			responseDict['dataset'].append(serviceReqDict)
			responseDict['dataset'].append(healthyDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestOptTime - (highestOptTime*0.3))
			responseDict['max_val'] = round(highestOptTime + (highestOptTime*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestOptTime) + 0.5) / (1 + 0.3)

			if highestOptTime < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestOptTime + (highestOptTime*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		elif whichtype == 'operation-current':
			# By operational current cooling fans

			responseDict = {"category":"Double Converter: Operational current cooling fans",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off		
			#responseDict['min_val']=coolingFanRange[2]
			#responseDict['max_val']=coolingFanRange[3]
			
			# Variable to record the highest and lowest value for cooling fan
			# To be used for flexible range
			lowestOptCurrent = 0
			highestOptCurrent = 0
			optCurrentCount  = 1

			opsCurrentFansDict = {"type":"operation-current","data_series":[],"mark_lines":""}

			lowerTHDict = {"id":"lower-line","name":"Lower acceptable current","axis_val":""}
			upperTHDict = {"id":"upper-line","name":"upper acceptable current","axis_val":""}

			lowerTHDict['axis_val'] = coolingFanThreshold[1]
			upperTHDict['axis_val'] = coolingFanThreshold[2]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,operational_current_of_cooling_fans,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:	
				fanData = thisRow[4]

				# Check the equipment type from equipment_info
				for te in equipmentList:
					if te[3] == thisRow[0] and te[4] == thisRow[1] and te[5] == thisRow[2] and te[6] == thisRow[3]:
						asset_name = te[0]

						insertDict = {"name":"","station":"","value":""}
						insertDict['name'] = asset_name
						#insertDict['station'] = thisRow[0]
						for li in stationList:
							if thisRow[0] == li[0]:
								insertDict['station']=li[1]
								break
						insertDict['value'] = fanData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if fanData != None:
							if optCurrentCount == 1:
								lowestOptCurrent = fanData
								highestOptCurrent = fanData
								optCurrentCount += 1
							else:
								if fanData > highestOptCurrent:
									highestOptCurrent = fanData
								elif fanData < lowestOptCurrent:
									lowestOptCurrent = fanData
						#----------------------------------------------------------------

						opsCurrentFansDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			
			marklines['data'].append(lowerTHDict)
			marklines['data'].append(upperTHDict)
			
			opsCurrentFansDict['mark_lines'] = marklines

			responseDict['dataset'].append(opsCurrentFansDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestOptCurrent - (highestOptCurrent*0.3))
			responseDict['max_val'] = round(highestOptCurrent + (highestOptCurrent*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestOptCurrent) + 0.5) / (1 + 0.3)

			if highestOptCurrent < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestOptCurrent + (highestOptCurrent*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')
			
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')





