
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
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Create your views here.
class TransformerLoadingView(APIView):

	# Declare the static class variables
	global equipmentList
	global distinctStationList
	global loadingRangeList
	global stationList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here
	
			queryStatement = "select acronym_asset_name,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,child_entity from "+config.EQUIPMENT_INFO+" order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)
			
			queryStatement = "select distinct station_id from "+config.EQUIPMENT_INFO+" where equipment = 'transformer' order by station_id"
			parameter = []
			distinctStationList = queryPostgre(queryStatement,parameter)
			
			queryStatement = "select max(min_loading),max(max_loading) from "+config.TRANSFORMER_RANGE+""
			parameter = []
			loadingRangeList = queryPostgre(queryStatement,parameter)

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

		loadingRange = loadingRangeList[0]
		
		queryStatement = "select total_loading,equipment_type from "+config.TRANSFORMER_THRESHOLD+""
		parameter = []
		loadingTHList = queryPostgre(queryStatement,parameter)

		if whichtype == 'all':
			# Title: List transformers loading status by type and group by station

			responseDict = {"category":"Transformer",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=loadingRange[0]
			#responseDict['max_val']=loadingRange[1]
			
			# Variable to record the highest and lowest value for loading
			# To be used for flexible range
			lowestLoading = 0
			highestLoading = 0
			loadingCount  = 1

			mtDict = {"type":"MT","data_series":[],"mark_lines":""}
			stOneDict = {"type":"ST_1MVA","data_series":[],"mark_lines":""}
			stTwoSixDict = {"type":"ST_26MVA","data_series":[],"mark_lines":""}
			itDict = {"type":"IT","data_series":[],"mark_lines":""}
			rtDict = {"type":"RT","data_series":[],"mark_lines":""}
			dctDict = {"type":"DCT","data_series":[],"mark_lines":""}

			mtTHDict = {"id":"threshold-1","name":"MT Loading threshold","axis_val":""}
			stOneTHDict = {"id":"threshold-1","name":"ST_1MVA Loading threshold","axis_val":""}
			stTwoSixTHDict = {"id":"threshold-1","name":"ST_26MVA Loading threshold","axis_val":""}
			itTHDict = {"id":"threshold-1","name":"IT Loading threshold","axis_val":""}
			rtTHDict = {"id":"threshold-1","name":"RT Loading threshold","axis_val":""}
			dctTHDict = {"id":"threshold-1","name":"DCT Loading threshold","axis_val":""}

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,active_power from "+config.TRANSFORMER_DATA+" order by station_id,system_id,subsystem_id,detail_code ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the equipment_type. Default NA- Not applicable
			equipment_type = 'NA'
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				loadingData = thisRow[4]
				
				# Check the equipment type from equipment_info
				for te in equipmentList:
					if te[3] == thisRow[0] and te[4] == thisRow[1] and te[5] == thisRow[2] and te[6] == thisRow[3]:
						equipment_type = te[1]
						asset_name = te[0]
				
						insertDict = {"name":"","station":"","value":""}
						insertDict['name'] = asset_name
						for li in stationList:
							if thisRow[0] == li[0]:
								insertDict['station'] = li[1]
								break
						insertDict['value'] = loadingData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if loadingData != None:
							if loadingCount == 1:
								lowestLoading = loadingData
								highestLoading = loadingData
								loadingCount += 1
							else:
								if loadingData> highestLoading:
									highestLoading = loadingData
								elif loadingData < lowestLoading:
									lowestLoading = loadingData
						#----------------------------------------------------------------

						if equipment_type == config.INTAKE_TRANSFORMER:
							# Type is Intake transformer
							mtDict['data_series'].append(insertDict)
						elif equipment_type == config.SERVICE_TRANSFORMER_1MVA:
							# Type is Service transformer 1MVA
							stOneDict['data_series'].append(insertDict)
						elif equipment_type == config.SERVICE_TRANSFORMER_26MVA:
							# Type is Service transformer 26MVA
							stTwoSixDict['data_series'].append(insertDict)
						elif equipment_type == config.INVERTER_TRANSFORMER:
							# Type is Inverter transformer
							itDict['data_series'].append(insertDict)
						elif equipment_type == config.RECTIFIER_TRANSFORMER:
							# Type is Rectifier transformer
							rtDict['data_series'].append(insertDict)
						elif equipment_type == config.DOUBLE_CONVERTER_TRANSFORMER:
							# Type is Double Converter transformer
							dctDict['data_series'].append(insertDict)
						break

			for te in loadingTHList:
				if te[1] == config.INTAKE_TRANSFORMER:
					mtTHDict['axis_val'] = te[0]
				elif te[1] == config.SERVICE_TRANSFORMER_1MVA:
					stOneTHDict['axis_val'] = te[0]
				elif te[1] == config.SERVICE_TRANSFORMER_26MVA:
					stTwoSixTHDict['axis_val'] = te[0]
				elif te[1] == config.RECTIFIER_TRANSFORMER:
					itTHDict['axis_val'] = te[0]
				elif te[1] == config.DOUBLE_CONVERTER_TRANSFORMER:
					rtTHDict['axis_val'] = te[0]
				elif te[1] == config.INVERTER_TRANSFORMER:
					dctTHDict['axis_val'] = te[0]

			mtMarklines = {"data":[]}
			mtMarklines['data'].append(mtTHDict)
			stOneMarklines = {"data":[]}
			stOneMarklines['data'].append(stOneTHDict)
			stTwoSixMarklines = {"data":[]}
			stTwoSixMarklines['data'].append(stTwoSixTHDict)
			itMarklines = {"data":[]}
			itMarklines['data'].append(itTHDict)
			rtMarklines = {"data":[]}
			rtMarklines['data'].append(rtTHDict)
			dctMarklines = {"data":[]}
			dctMarklines['data'].append(dctTHDict)

			mtDict['mark_lines'] = mtMarklines
			stOneDict['mark_lines'] = stOneMarklines
			stTwoSixDict['mark_lines'] = stTwoSixMarklines
			itDict['mark_lines'] = itMarklines
			rtDict['mark_lines'] = rtMarklines
			dctDict['mark_lines'] = dctMarklines

			responseDict['dataset'].append(mtDict)
			responseDict['dataset'].append(stOneDict)
			responseDict['dataset'].append(stTwoSixDict)
			responseDict['dataset'].append(itDict)
			responseDict['dataset'].append(rtDict)
			responseDict['dataset'].append(dctDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestLoading - (highestLoading*0.3))
			responseDict['max_val'] = round(highestLoading + (highestLoading*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestLoading) + 0.5) / (1 + 0.3)

			if highestLoading < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestLoading + (highestLoading*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')



