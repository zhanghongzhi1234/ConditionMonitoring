
from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status
from rest_framework.views import APIView

from operator import itemgetter, attrgetter

import requests
import json
import datetime
import calendar

import time
import math

from backend.utilities.druidQuery import queryDruid
from backend.utilities.postgreQuery import queryPostgre
from backend.utilities.postgreUpdate import updatePostgre
from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnResponse import processResponse
from backend.utilities.returnInterval import processInterval
from backend.utilities.returnTimeSeries import processTimeSeries
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

class RectifierTrendingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global rcRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

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
		periodicity = self.request.query_params.get('periodicity')
		start_time = self.request.query_params.get('start_time')
		end_time = self.request.query_params.get('end_time')
		assetName = self.request.query_params.get('equipment_code')
		whichType = self.request.query_params.get('type')

		# If periodicity is custom, then default it as 'daily'
		if periodicity == 'custom':
			periodicity = 'daily'

		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None

		# find the equipment info given the asset_name
		for te in equipmentList:
			if te[0] == assetName:
				station_id = te[4]
				system_id = te[5]
				subsystem_id = te[6]
				detail_code = te[7]
				equipment_type = te[2]
				break

		entityName = ''+station_id+'.'+system_id+'.'+subsystem_id+'.'+detail_code+''
		
		if periodicity == 'daily':

			startHour = (datetime.datetime.utcnow() - datetime.timedelta(hours=24) + datetime.timedelta(hours=8))
			start_time = ""+str(startHour.year)+"-"+str(startHour.month)+"-"+str(startHour.day)+" "+str(startHour.hour)+":"+str(startHour.minute)+":"+str(startHour.second)+""
			endHour = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))			
			end_time = ""+str(endHour.year)+"-"+str(endHour.month)+"-"+str(endHour.day)+" "+str(endHour.hour)+":"+str(endHour.minute)+":"+str(endHour.second)+""	
		
		elif periodicity == 'weekly':

			startHour = (datetime.datetime.utcnow() - datetime.timedelta(days=7) + datetime.timedelta(hours=8))
			start_time = ""+str(startHour.year)+"-"+str(startHour.month)+"-"+str(startHour.day)+" "+str(startHour.hour)+":"+str(startHour.minute)+":"+str(startHour.second)+""
			endHour = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))			
			end_time = ""+str(endHour.year)+"-"+str(endHour.month)+"-"+str(endHour.day)+" "+str(endHour.hour)+":"+str(endHour.minute)+":"+str(endHour.second)+""

		elif periodicity == 'monthly':

			startHour = (datetime.datetime.utcnow() - datetime.timedelta(days=30) + datetime.timedelta(hours=8))
			start_time = ""+str(startHour.year)+"-"+str(startHour.month)+"-"+str(startHour.day)+" "+str(startHour.hour)+":"+str(startHour.minute)+":"+str(startHour.second)+""
			endHour = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))			
			end_time = ""+str(endHour.year)+"-"+str(endHour.month)+"-"+str(endHour.day)+" "+str(endHour.hour)+":"+str(endHour.minute)+":"+str(endHour.second)+""
			
		elif periodicity == 'yearly':

			startHour = (datetime.datetime.utcnow() - datetime.timedelta(days=365) + datetime.timedelta(hours=8))
			start_time = ""+str(startHour.year)+"-"+str(startHour.month)+"-"+str(startHour.day)+" "+str(startHour.hour)+":"+str(startHour.minute)+":"+str(startHour.second)+""
			endHour = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))			
			end_time = ""+str(endHour.year)+"-"+str(endHour.month)+"-"+str(endHour.day)+" "+str(endHour.hour)+":"+str(endHour.minute)+":"+str(endHour.second)+""


		if (start_time != None or end_time != None) and whichType == 'panel-temperature':

			interval = processInterval(start_time,end_time)

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#for te in rcRangeList:
			#	if te[8] == equipment_type:
			#		responseDict['min_val'] = te[0]
			#		responseDict['max_val'] = te[1]
			#		break

			# Variable to record the highest and lowest value for panel temperature
			# To be used for flexible range
			lowestTemp1 = 0
			highestTemp1 = 0
			lowestTemp2 = 0
			highestTemp2 = 0
			lowestTemp3 = 0
			highestTemp3 = 0
			lowestTemp4 = 0
			highestTemp4 = 0
			
			lowestTemp = 0
			highestTemp = 0
			tempCount = 1

			panelTemp1Data = None
			panelTemp2Data = None
			panelTemp3Data = None
			panelTemp4Data = None

			timeList = []
			panelTemperatureOneList =  []
			panelTemperatureTwoList =  []
			panelTemperatureThreeList =  []
			panelTemperatureFourList =  []

			count = 1
			
			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,panel_temperature_1,panel_temperature_2,panel_temperature_3,panel_temperature_4 from "+config.RECTIFIER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,panel_temperature_1,panel_temperature_2,panel_temperature_3,panel_temperature_4 from "+config.RECTIFIER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,end_time,entityName]

			resultList = queryHive(queryStatement,parameter)

			if resultList != None:	
				if len(resultList) > 0:
					resultList = sorted(resultList, key=itemgetter(0))

				for thisRow in resultList:
					if count == interval:
						# Check the values for null
						# For datalog agent, any values that are out of range or invalid is return as null (please take note)
						# These null values will be plotted in the graph as well but will cause 'a line break' 
						if thisRow[2] != None:
							panelTemp1Data = round(thisRow[2],2)
							panelTemperatureOneList.append(panelTemp1Data)
						elif thisRow[2] == None:
							panelTemperatureOneList.append(None)
							panelTemp1Data = 0

						if thisRow[3] != None:
							panelTemp2Data = round(thisRow[3],2)
							panelTemperatureTwoList.append(panelTemp2Data)
						elif thisRow[3] == None:
							panelTemperatureTwoList.append(None)
							panelTemp2Data = 0

						if thisRow[4] != None:
							panelTemp3Data = round(thisRow[4],2)
							panelTemperatureThreeList.append(panelTemp3Data)
						elif thisRow[4] == None:
							panelTemperatureThreeList.append(None)
							panelTemp3Data = 0

						if thisRow[5] != None:
							panelTemp4Data = round(thisRow[5],2)
							panelTemperatureFourList.append(panelTemp4Data)
						elif thisRow[5] == None:
							panelTemperatureFourList.append(None)
							panelTemp4Data = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest panel temperature
						#-------------------------------------------------------
						if tempCount == 1:
							lowestTemp1 = panelTemp1Data
							highestTemp1 = panelTemp1Data
							lowestTemp2 = panelTemp2Data
							highestTemp2 = panelTemp2Data
							lowestTemp3 = panelTemp3Data
							highestTemp3 = panelTemp3Data
							lowestTemp4 = panelTemp4Data
							highestTemp4 = panelTemp4Data

							tempCount += 1
						else:
							if panelTemp1Data > highestTemp1:
								highestTemp1 = panelTemp1Data
							elif panelTemp1Data < lowestTemp1:
								lowestTemp1 = panelTemp1Data
								
							if panelTemp2Data > highestTemp2:
								highestTemp2 = panelTemp2Data
							elif panelTemp2Data < lowestTemp2:
								lowestTemp2 = panelTemp2Data
								
							if panelTemp3Data > highestTemp3:
								highestTemp3 = panelTemp3Data
							elif panelTemp3Data < lowestTemp3:
								lowestTemp3 = panelTemp3Data
								
							if panelTemp4Data > highestTemp4:
								highestTemp4 = panelTemp4Data
							elif panelTemp4Data < lowestTemp4:
								lowestTemp4 = panelTemp4Data
							
						#--------------------------------------------------------
					else:
						count += 1

			panelTemperatureOneDict = {"name":"panel-temperature 1","data":[]}
			panelTemperatureTwoDict = {"name":"panel-temperature 2","data":[]}
			panelTemperatureThreeDict = {"name":"panel-temperature 3","data":[]}
			panelTemperatureFourDict = {"name":"panel-temperature 4","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			panelTemperatureOneDict['data'] = panelTemperatureOneList
			panelTemperatureTwoDict['data'] = panelTemperatureTwoList
			panelTemperatureThreeDict['data'] = panelTemperatureThreeList
			panelTemperatureFourDict['data'] = panelTemperatureFourList

			responseDict['data_series'].append(panelTemperatureOneDict)
			responseDict['data_series'].append(panelTemperatureTwoDict)
			responseDict['data_series'].append(panelTemperatureThreeDict)
			responseDict['data_series'].append(panelTemperatureFourDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			lowestTemp = lowestTemp1
			highestTemp = highestTemp1
			
			if lowestTemp2 < lowestTemp:
				lowestTemp = lowestTemp2
			if lowestTemp3 < lowestTemp:
				lowestTemp = lowestTemp3
			if lowestTemp4 < lowestTemp:
				lowestTemp = lowestTemp4
			
			if highestTemp2 > highestTemp:
				highestTemp = highestTemp2
			if highestTemp3 > highestTemp:
				highestTemp = highestTemp3
			if highestTemp4 > highestTemp:
				highestTemp = highestTemp4

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














