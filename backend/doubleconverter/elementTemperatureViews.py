
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

class ElementTemperatureView(APIView):

	# Declare the static class variables
	global equipmentList
	global distinctStationList
	global tempStatsRangeList
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
			
			queryStatement =  "select min_panel_temp_1_rec1,max_panel_temp_1_rec1,min_panel_temp_1_rec2,max_panel_temp_1_rec2, min_panel_temp_1_inv, max_panel_temp_1_inv, min_module_temp_thy1, max_module_temp_thy1,min_module_temp_thy2, max_module_temp_thy2, min_module_temp_igbt1, max_module_temp_igbt1,min_panel_temp_2_rec1,max_panel_temp_2_rec1,min_panel_temp_2_rec2,max_panel_temp_2_rec2, min_panel_temp_2_inv, max_panel_temp_2_inv from "+config.DOUBLECONVERTER_RANGE+""
			parameter = []
			tempStatsRangeList = queryPostgre(queryStatement,parameter)

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
		
		queryStatement =  "select panel_temp_1_rec1,panel_temp_1_rec2,panel_temp_1_inv,module_temp_thy1,module_temp_thy2,module_temp_igbt1,panel_temp_2_rec1,panel_temp_2_rec2,panel_temp_2_inv from "+config.DOUBLECONVERTER_THRESHOLD+""
		parameter = []
		tempStatsTHList = queryPostgre(queryStatement,parameter)

		tempStatsThreshold = tempStatsTHList[0]
		tempStatsRange = tempStatsRangeList[0]

		if whichtype == 'rec1-top':

			# By panel temperature TOP (Rec 1 mode)

			responseDict = {"category":"Double Converter: Panel temperature TOP (Rec 1 mode)",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[0]
			#responseDict['max_val']=tempStatsRange[1]
			
			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTempRec1TopDict = {"type":"rec1-top","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Panel temperature TOP (Rec 1 mode) threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[0]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temperature_1_rec1,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						panelTempRec1TopDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTempRec1TopDict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTempRec1TopDict)
			
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

		elif whichtype == 'rec2-top':
			# By panel temperature TOP (Rec 2 mode)

			responseDict = {"category":"Double Converter: Panel temperature TOP (Rec 2 mode)",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[2]
			#responseDict['max_val']=tempStatsRange[3]

			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTempRec2TopDict = {"type":"rec2-top","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Panel temperature TOP (Rec 2 mode) threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[1]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temperature_1_rec2,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						panelTempRec2TopDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTempRec2TopDict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTempRec2TopDict)
			
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

		elif whichtype == 'inv-top':
			# By panel temperature TOP (Inv mode)

			responseDict = {"category":"Double Converter: Panel temperature TOP (Inv mode)",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}
					
			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[4]
			#responseDict['max_val']=tempStatsRange[5]

			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1			

			panelTempInvTopDict = {"type":"inv-top","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Panel temperature TOP (Inv mode) threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[2]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temperature_1_inv,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						panelTempInvTopDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTempInvTopDict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTempInvTopDict)
			
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

		elif whichtype == 'rec1-bottom':
			# By panel temperature BOTTOM (Rec 1 mode)

			responseDict = {"category":"Double Converter: Panel temperature BOTTOM (Rec 1 mode)",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[12]
			#responseDict['max_val']=tempStatsRange[13]
			
			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTempRec1BottomDict = {"type":"rec1-bottom","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Panel temperature BOTTOM (Rec 1 mode) threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[6]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temperature_2_rec1,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						panelTempRec1BottomDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTempRec1BottomDict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTempRec1BottomDict)
			
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

		elif whichtype == 'rec2-bottom':
			# By panel temperature BOTTOM (Rec 2 mode)

			responseDict = {"category":"Double Converter: Panel temperature BOTTOM (Rec 2 mode)",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[14]
			#responseDict['max_val']=tempStatsRange[15]
			
			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTempRec2BottomDict = {"type":"rec2-bottom","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Panel temperature BOTTOM (Rec 2 mode) threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[7]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temperature_2_rec2,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						panelTempRec2BottomDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTempRec2BottomDict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTempRec2BottomDict)
			
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

		elif whichtype == 'inv-bottom':
			# By panel temperature BOTTOM (Inv mode)

			responseDict = {"category":"Double Converter: Panel temperature BOTTOM (Inv mode)",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[16]
			#responseDict['max_val']=tempStatsRange[17]
			
			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			panelTempInvBottomDict = {"type":"inv-bottom","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Panel temperature BOTTOM (Inv mode) threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[8]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,panel_temperature_2_inv,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						panelTempInvBottomDict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			panelTempInvBottomDict['mark_lines'] = marklines

			responseDict['dataset'].append(panelTempInvBottomDict)
			
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

		elif whichtype == 'mod-thy1':
			# By module temperature thy1

			responseDict = {"category":"Double Converter: Module temperature thy1",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[6]
			#responseDict['max_val']=tempStatsRange[7]
			
			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			moduleTempThy1Dict = {"type":"mod-thy1","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Module temperature thy1 threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[3]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,module_temperature_thy1,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						moduleTempThy1Dict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			moduleTempThy1Dict['mark_lines'] = marklines

			responseDict['dataset'].append(moduleTempThy1Dict)
			
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

		elif whichtype == 'mod-thy2':
			# By module temperature thy2

			responseDict = {"category":"Double Converter: Module temperature thy2",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[8]
			#responseDict['max_val']=tempStatsRange[9]
			
			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			moduleTempThy2Dict = {"type":"mod-thy2","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Module temperature thy2 threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[4]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,module_temperature_thy2,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						moduleTempThy2Dict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			moduleTempThy2Dict['mark_lines'] = marklines

			responseDict['dataset'].append(moduleTempThy2Dict)
			
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

		elif whichtype == 'mod-igbt1':
			# By module temperature igbt1

			responseDict = {"category":"Double Converter: Module temperature igbt1",
					"station_series":[],
					"min_val":"",
					"max_val":"",
					"dataset":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#responseDict['min_val']=tempStatsRange[10]
			#responseDict['max_val']=tempStatsRange[11]
			
			# Variable to record the highest and lowest value for panel temperature 1
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0
			tempCount  = 1

			moduleTempIgbt1Dict = {"type":"mod-igbt1","data_series":[],"mark_lines":""}

			th1Dict = {"id":"threshold-1","name":"Module temperature igbt1 threshold","axis_val":""}

			th1Dict['axis_val'] = tempStatsThreshold[5]

			for te in distinctStationList:
				for li in stationList:
					if te[0] == li[0]:
						responseDict['station_series'].append(li[1])
						break

			queryStatement = "select station_id,system_id,subsystem_id,detail_code,module_temperature_igbt1,record_time from "+config.DOUBLECONVERTER_DATA+" order by station_id,system_id,subsystem_id,detail_code,record_time ASC"
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

						moduleTempIgbt1Dict['data_series'].append(insertDict)
						break

			marklines = {"data":[]}
			marklines['data'].append(th1Dict)
			moduleTempIgbt1Dict['mark_lines'] = marklines

			responseDict['dataset'].append(moduleTempIgbt1Dict)
			
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

	
