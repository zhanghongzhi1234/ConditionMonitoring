
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
#from backend.utilities.hiveQuery import queryHives
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

class TransformerTrendingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global trRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer,child_entity from "+config.EQUIPMENT_INFO+" order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_winding,max_winding,min_currentl1,max_currentl1,min_currentl2,max_currentl2,min_currentl3,max_currentl3,min_loading,max_loading,min_oil,max_oil,equipment_type from "+config.TRANSFORMER_RANGE+""
			parameter = []
			trRangeList = queryPostgre(queryStatement,parameter)

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

		# If periodicity is custom, then default it as 'daily'
		if periodicity == 'custom':
			periodicity = 'daily'

		staticRangeValue = trRangeList[0]

		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None
		child_entity = None
		child_loading_entity = None

		# find the equipment info given the asset_name
		for te in equipmentList:
			if te[0] == assetName:
				station_id = te[4]
				system_id = te[5]
				subsystem_id = te[6]
				detail_code = te[7]
				equipment_type = te[2]
				child_entity = te[9]
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
			

		if start_time != None or end_time != None:
			# If either start_time or end_time is not None, meaning this is custom.

			interval = processInterval(start_time,end_time)
					
			responseDict = {
					"yAxis":[],
					"xAxis":[],
					"data_series":[]
					}

			temperatureRangeDict = {
					"name":"Temperature (ºC)",
					"min_val":"",
					"max_val":""
					}

			loadingRangeDict = {
					"name":"Loading (MW)",	
					"min_val":"",
					"max_val":""				
					}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#for te in trRangeList:
			#	if te[12] == equipment_type:
			#		loadingRangeDict['min_val'] = te[8]
			#		loadingRangeDict['max_val'] = te[9]	
			#		if te[0] > te[10]:
			#			temperatureRangeDict['min_val'] = te[10]	
			#		else:
			#			temperatureRangeDict['min_val'] = te[0]
			#		if te[1] > te[11]:
			#			temperatureRangeDict['max_val'] = te[1]
			#		else:
			#			temperatureRangeDict['max_val'] = te[11]
			#		break	

			#responseDict['yAxis'].append(temperatureRangeDict)
			#responseDict['yAxis'].append(loadingRangeDict)

			oilDict = {
				     "name":"Oil",
				     "xAxisIndex":0,
				     "yAxisIndex":0,
				     "data":[]
				  }
			windingDict = {
				     "name":"Winding",
				     "xAxisIndex":0,
				     "yAxisIndex":0,
				     "data":[]
					}
			loadingDict = {
				     "name":"Loading",
				     "xAxisIndex":1,
				     "yAxisIndex":1,
				     "data":[]
					}

			temperatureTimeAxis = {
				     "name":"Temperature",
				     "data":[]
					}

			loadingTimeAxis = {
				     "name":"Loading",
				     "data":[]
					}	

			timeTemperatureList = []
			timeLoadingList = []
			oilList =  []
			windingList = []
			loadingList = []		

			# Variable to record the highest and lowest value for temperature and loading
			# To be used for flexible range
			lowestTemperature = 0
			highestTemperature = 0
			lowestLoading = 0
			highestLoading = 0

			oilData = None
			windingData = None
			loadingData = None

			tempCount = 1
			loadingCount = 1
			count = 1

			if end_time == None:		

				#queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, oil_temperature as oil, winding_temperature as winding from "+config.TRANSFORMER+" where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp('"+start_time+"','yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = '"+entityName+"' and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, oil_temperature as oil, winding_temperature as winding from "+config.TRANSFORMER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:	

				#queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, oil_temperature as oil, winding_temperature as winding from "+config.TRANSFORMER+" where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp('"+start_time+"','yyyy-MM-dd HH:mm:ss') and unix_timestamp('"+end_time+"','yyyy-MM-dd HH:mm:ss') and equipment_id = '"+entityName+"' and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, oil_temperature as oil, winding_temperature as winding from "+config.TRANSFORMER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,end_time,entityName]

			transformerList = queryHive(queryStatement,parameter)
			
			if transformerList != None:	
				if len(transformerList) > 0:
					transformerList = sorted(transformerList, key=itemgetter(0))

				# Need to loop
				for thisRow in transformerList:
					if count == interval:
						# Check the values for null
						# For datalog agent, any values that are out of range or invalid is return as null (please take note)
						# These null values will be plotted in the graph as well but will cause 'a line break' 
						if thisRow[2] != None:
							oilData = round(thisRow[2],2)	
							oilList.append(oilData)	
						elif thisRow[2] == None:
							oilList.append(None)	
							oilData = 0

						if thisRow[3] != None:
							windingData = round(thisRow[3],2)	
							windingList.append(windingData)
						elif thisRow[3] == None:
							windingList.append(None)
							windingData = 0

						# Add the timestamp into the time list
						timeTemperatureList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest temperature
						#-------------------------------------------------------
						if tempCount == 1:
							if oilData > windingData:
								lowestTemperature = windingData
								highestTemperature = oilData
							else:
								lowestTemperature = oilData
								highestTemperature = windingData
							tempCount += 1
						else:
							if oilData > highestTemperature or windingData > highestTemperature:
								if oilData > windingData:
									highestTemperature = oilData
								else:
									highestTemperature= windingData
							if oilData < lowestTemperature or windingData < lowestTemperature:
								if oilData < windingData:
									lowestTemperature = oilData
								else:
									lowestTemperature= windingData	
						#--------------------------------------------------------

					else:
						count += 1
					
			oilDict['data'] = oilList
			windingDict['data'] = windingList

			responseDict['data_series'].append(oilDict)
			responseDict['data_series'].append(windingDict)

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeTemperatureList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeTemperatureList = timeInfo['displaySeries']
			temperatureTimeAxis['data'] = timeTemperatureList
			
			child_info = child_entity.split(",")
			# loading is the first
			child_loading_entity = child_info[0]
			entity_info = child_loading_entity.split(".")
			station_id = entity_info[0]
			system_id = entity_info[1]
			subsystem_id = entity_info[2]
			detail_code = entity_info[3]

			entityName = ''+station_id+'.'+system_id+'.'+subsystem_id+'.'+detail_code+''

			#reset count
			count = 1

			if end_time == None:			

				#queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,active_power from "+config.TRANSFORMER_LOADING+" where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp('"+start_time+"','yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = '"+entityName+"' and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,active_power from "+config.TRANSFORMER_LOADING+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				#queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,active_power from "+config.TRANSFORMER_LOADING+" where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp('"+start_time+"','yyyy-MM-dd HH:mm:ss') and unix_timestamp('"+end_time+"','yyyy-MM-dd HH:mm:ss') and equipment_id = '"+entityName+"' and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,active_power from "+config.TRANSFORMER_LOADING+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,end_time,entityName]

			transformerLoadingList = queryHive(queryStatement,parameter)
			
			if transformerLoadingList != None:	
				if len(transformerLoadingList) > 0:
					transformerLoadingList = sorted(transformerLoadingList, key=itemgetter(0))

				for thisRow in transformerLoadingList:		
					if count == interval:
						# Check the values for null
						# For datalog agent, any values that are out of range or invalid is return as null (please take note)
						# These null values will be plotted in the graph as well but will cause 'a line break' 
						if thisRow[2] != None:
							loadingData = round(thisRow[2],2)
							loadingList.append(loadingData)	
						elif thisRow[2] == None:
							loadingList.append(None)
							loadingData = 0

						# Add the timestamp into the time list
						timeLoadingList.append(thisRow[1])	
						# Reset the count to 1
						count = 1

						# Patch to record the highest and lowest loading
						#-------------------------------------------------------
						if loadingCount == 1:
							lowestLoading = loadingData
							highestLoading = loadingData
							loadingCount += 1
						else:
							if loadingData > highestLoading:
								highestLoading = loadingData
							elif loadingData < lowestLoading:
								lowestLoading = loadingData
						#--------------------------------------------------------
					else:
						count += 1
						
			loadingDict['data'] = loadingList
			responseDict['data_series'].append(loadingDict)

			if len(timeLoadingList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeLoadingList = timeInfo['displaySeries']
			loadingTimeAxis['data'] = timeLoadingList

			responseDict['xAxis'].append(temperatureTimeAxis)
			responseDict['xAxis'].append(loadingTimeAxis)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			loadingRangeDict['min_val'] = round(lowestLoading - (highestLoading*0.3))
			loadingRangeDict['max_val'] = round(highestLoading + (highestLoading*0.3))
			temperatureRangeDict['min_val'] = round(lowestTemperature - (highestTemperature*0.3))
			temperatureRangeDict['max_val'] = round(highestTemperature + (highestTemperature*0.3))

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
				loadingRangeDict['max_val'] = round(highestLoading + (highestLoading*0.3)) + 1

			toNext = (math.floor(highestTemperature) + 0.5) / (1 + 0.3)

			if highestTemperature < toNext:
				# Add one to the highest value
				temperatureRangeDict['max_val'] = round(highestTemperature + (highestTemperature*0.3)) + 1
			#--------------------------------------------------------

			responseDict['yAxis'].append(temperatureRangeDict)
			responseDict['yAxis'].append(loadingRangeDict)

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')















