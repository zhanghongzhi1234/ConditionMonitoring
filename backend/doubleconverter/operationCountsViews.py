
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

class OperationCountsView(APIView):

	# Declare the static class variables
	global equipmentList
	global distinctStationList
	global opsCountsRangeList
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
			
			queryStatement = "select distinct station_id from "+config.EQUIPMENT_INFO+" where equipment = 'dconverter' order by station_id"
			parameter = []
			distinctStationList = queryPostgre(queryStatement,parameter)
			
			queryStatement = "select min_num_operations_rec, max_num_operations_rec, min_num_operations_inv, max_num_operations_inv from "+config.DOUBLECONVERTER_RANGE+""
			parameter = []
			opsCountsRangeList = queryPostgre(queryStatement,parameter)

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
		whichtype = self.request.query_params.get('type')
		
		queryStatement = "select num_operations_rec,num_operations_inv from "+config.DOUBLECONVERTER_THRESHOLD+""
		parameter = []
		opsCountsTHList = queryPostgre(queryStatement,parameter)

		opsCountsThreshold = opsCountsTHList[0]
		opsCountsRange = opsCountsRangeList[0]

		if whichtype == 'rec-mode':
			# By number of operations (Rec mode)

			responseDict = {"category":"Double Converter: Number of operations (Rec mode)",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}
					
			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=opsCountsRange[0]
			#responseDict['max_val']=opsCountsRange[1]
			
			# Variable to record the highest and lowest value for operation count rec mode
			# To be used for flexible range
			lowestCounter = 0
			highestCounter = 0
			opsCount  = 1

			numOpsRecDict = {"type":"rec-mode","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"number of operations (Rec mode) threshold","axis_val":""}

			th1Dict['axis_val'] = opsCountsThreshold[0]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,number_of_operations_rec_mode,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				opsCountData = thisRow[4]

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
						insertDict['value'] = opsCountData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if opsCount == 1:
							lowestCounter = opsCountData
							highestCounter = opsCountData
							opsCount += 1
						else:
							if opsCountData > highestCounter:
								highestCounter = opsCountData
							elif opsCountData < lowestCounter:
								lowestCounter = opsCountData
						#----------------------------------------------------------------	

						numOpsRecDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			numOpsRecDict['mark_lines'] = marklines

			responseDict['dataset'].append(numOpsRecDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestCounter - (highestCounter*0.3))
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

		elif whichtype == 'inv-mode':
			# By number of operations (Inv mode)

			responseDict = {"category":"Double Converter: Number of operations (Inv mode)",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=opsCountsRange[2]
			#responseDict['max_val']=opsCountsRange[3]
			
			# Variable to record the highest and lowest value for operation count inv mode
			# To be used for flexible range
			lowestCounter = 0
			highestCounter = 0
			opsCount  = 1

			numOpsInvDict = {"type":"inv-mode","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"number of operations (Rec mode) threshold","axis_val":""}

			th1Dict['axis_val'] = opsCountsThreshold[1]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,number_of_operations_inv_mode,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				opsCountData = thisRow[4]
				
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
						insertDict['value'] = opsCountData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if opsCount == 1:
							lowestCounter = opsCountData
							highestCounter = opsCountData
							opsCount += 1
						else:
							if opsCountData > highestCounter:
								highestCounter = opsCountData
							elif opsCountData < lowestCounter:
								lowestCounter = opsCountData
						#----------------------------------------------------------------	

						numOpsInvDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			numOpsInvDict['mark_lines'] = marklines

			responseDict['dataset'].append(numOpsInvDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestCounter - (highestCounter*0.3))
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
		


