
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

class PanelTemperatureView(APIView):

	# Declare the static class variables
	global equipmentList
	global distinctStationList
	global panelTempRangeList
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

			queryStatement = "select distinct station_id from "+config.EQUIPMENT_INFO+" where equipment = 'rectifier' order by station_id"
			parameter = []
			distinctStationList = queryPostgre(queryStatement,parameter)
			
			queryStatement = "select min_panel_temp_1,max_panel_temp_1,min_panel_temp_2,max_panel_temp_2,min_panel_temp_3,max_panel_temp_3,min_panel_temp_4,max_panel_temp_4,equipment_type from "+config.RECTIFIER_RANGE+""
			parameter = []
			panelTempRangeList = queryPostgre(queryStatement,parameter)

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
		
		queryStatement = "select panel_temp_1,panel_temp_2,panel_temp_3,panel_temp_4,equipment_type from "+config.RECTIFIER_THRESHOLD+""
		parameter = []
		panelTempTHList = queryPostgre(queryStatement,parameter)

		panelTempThreshold = panelTempTHList[0]
		panelTempRange = panelTempRangeList[0]

		if whichtype == 'panel-temp1':

			responseDict = {"category":"panel-temp1",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#responseDict['min_val']=panelTempRange[0]
			#responseDict['max_val']=panelTempRange[1]
			
			# Variable to record the highest and lowest value for panel temp
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTemp1Dict = {"type":"panel-temp1","data_series":[],"mark_lines":""}

			th1Dict = {"id":"warning-1","name":" Panel temperature 1 threshold","axis_val":""}

			th1Dict['axis_val'] = panelTempThreshold[0]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temp_1,record_time from "+config.RECTIFIER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				temperatureData = thisRow[4]

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
						insertDict['value'] = temperatureData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if tempCount == 1:
							lowestTemp = temperatureData
							highestTemp = temperatureData
							tempCount += 1
						else:
							if temperatureData > highestTemp:
								highestTemp = temperatureData
							elif temperatureData < lowestTemp:
								lowestTemp = temperatureData
						#----------------------------------------------------------------	

						panelTemp1Dict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTemp1Dict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTemp1Dict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestTemp - (highestTemp*0.3))
			responseDict['max_val'] = round(highestTemp + (highestTemp*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestTemp) + 0.5) / (1 + 0.3)

			if highestTemp < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestTemp + (highestTemp*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		elif whichtype == 'panel-temp2':

			responseDict = {"category":"panel-temp2",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#responseDict['min_val']=panelTempRange[2]
			#responseDict['max_val']=panelTempRange[3]
			
			# Variable to record the highest and lowest value for panel temp
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTemp2Dict = {"type":"panel-temp2","data_series":[],"mark_lines":""}

			th1Dict = {"id":"warning-1","name":" Panel temperature 2 threshold","axis_val":""}

			th1Dict['axis_val'] = panelTempThreshold[1]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temp_2,record_time from "+config.RECTIFIER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				temperatureData = thisRow[4]

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
						insertDict['value'] = temperatureData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if tempCount == 1:
							lowestTemp = temperatureData
							highestTemp = temperatureData
							tempCount += 1
						else:
							if temperatureData > highestTemp:
								highestTemp = temperatureData
							elif temperatureData < lowestTemp:
								lowestTemp = temperatureData
						#----------------------------------------------------------------	

						panelTemp2Dict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTemp2Dict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTemp2Dict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestTemp - (highestTemp*0.3))
			responseDict['max_val'] = round(highestTemp + (highestTemp*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestTemp) + 0.5) / (1 + 0.3)

			if highestTemp < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestTemp + (highestTemp*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		elif whichtype == 'panel-temp3':

			responseDict = {"category":"panel-temp3",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#responseDict['min_val']=panelTempRange[4]
			#responseDict['max_val']=panelTempRange[5]
			
			# Variable to record the highest and lowest value for panel temp
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTemp3Dict = {"type":"panel-temp3","data_series":[],"mark_lines":""}

			th1Dict = {"id":"warning-1","name":" Panel temperature 3 threshold","axis_val":""}

			th1Dict['axis_val'] = panelTempThreshold[1]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temp_3,record_time from "+config.RECTIFIER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				temperatureData = thisRow[4]

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
						insertDict['value'] = temperatureData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if tempCount == 1:
							lowestTemp = temperatureData
							highestTemp = temperatureData
							tempCount += 1
						else:
							if temperatureData > highestTemp:
								highestTemp = temperatureData
							elif temperatureData < lowestTemp:
								lowestTemp = temperatureData
						#----------------------------------------------------------------	

						panelTemp3Dict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTemp3Dict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTemp3Dict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestTemp - (highestTemp*0.3))
			responseDict['max_val'] = round(highestTemp + (highestTemp*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestTemp) + 0.5) / (1 + 0.3)

			if highestTemp < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestTemp + (highestTemp*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		elif whichtype == 'panel-temp4':
			
			responseDict = {"category":"panel-temp4",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#responseDict['min_val']=panelTempRange[6]
			#responseDict['max_val']=panelTempRange[7]
			
			# Variable to record the highest and lowest value for panel temp
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTemp4Dict = {"type":"panel-temp4","data_series":[],"mark_lines":""}

			th1Dict = {"id":"warning-1","name":" Panel temperature 4 threshold","axis_val":""}

			th1Dict['axis_val'] = panelTempThreshold[1]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temp_4,record_time from "+config.RECTIFIER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			# Declaration of the asset_name. Default NA- Not applicable
			asset_name = 'NA'

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				temperatureData = thisRow[4]
				
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
						insertDict['value'] = temperatureData
						
						# Patch to record the highest and lowest value for flexible range
						#----------------------------------------------------------------
						if tempCount == 1:
							lowestTemp = temperatureData
							highestTemp = temperatureData
							tempCount += 1
						else:
							if temperatureData > highestTemp:
								highestTemp = temperatureData
							elif temperatureData < lowestTemp:
								lowestTemp = temperatureData
						#----------------------------------------------------------------	

						panelTemp4Dict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTemp4Dict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTemp4Dict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestTemp - (highestTemp*0.3))
			responseDict['max_val'] = round(highestTemp + (highestTemp*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestTemp) + 0.5) / (1 + 0.3)

			if highestTemp < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestTemp + (highestTemp*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')		
			
	




