
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

class InverterTrendingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global ivRangeList

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

			queryStatement = "select min_operation_counts,max_operation_counts,min_max_power,max_max_power,min_operation_time,max_operation_time,min_panel_temp_1,max_panel_temp_1,min_panel_temp_2,max_panel_temp_2,equipment_type from "+config.INVERTER_RANGE+""
			parameter = []
			ivRangeList = queryPostgre(queryStatement,parameter)

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

		if (start_time != None or end_time != None) and whichType == 'operation-counts':

			interval = processInterval(start_time,end_time)

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}	
					
			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#for te in ivRangeList:
			#	if te[10] == equipment_type:
			#		responseDict['min_val'] = te[0]
			#		responseDict['max_val'] = te[1]
			#		break
			
			# Variable to record the highest and lowest value for operation counts
			# To be used for flexible range
			lowestCounter = 0
			highestCounter = 0

			numOfOpsData = None
			
			counterCount = 1

			timeList = []
			numberOfOperationsList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,operation_counts from "+config.INVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:
				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,operation_counts from "+config.INVERTER+" where station_id = %s and system_id = '%s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
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
							numOfOpsData = round(thisRow[2],2)
							numberOfOperationsList.append(numOfOpsData)
						elif thisRow[2] == None:
							numberOfOperationsList.append(None)
							numOfOpsData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest circuit breaker count
						#-------------------------------------------------------
						if counterCount == 1:
							lowestCounter = numOfOpsData
							highestCounter = numOfOpsData
							counterCount += 1
						else:
							if numOfOpsData > highestCounter:
								highestCounter = numOfOpsData
							elif numOfOpsData < lowestCounter:
								lowestCounter = numOfOpsData
						#--------------------------------------------------------
					else:
						count += 1
						
			numberOfOperationsDict = {"name":"number-of-operations","data":[]}

						# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			numberOfOperationsDict['data'] = numberOfOperationsList

			responseDict['data_series'].append(numberOfOperationsDict)
			
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

		elif (start_time != None or end_time != None) and whichType == 'max-power':

			interval = processInterval(start_time,end_time)

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}	

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#for te in ivRangeList:
			#	if te[10] == equipment_type:
			#		responseDict['min_val'] = te[2]
			#		responseDict['max_val'] = te[3]
			#		break
			
			# Variable to record the highest and lowest value for max power
			# To be used for flexible range
			lowestPower = 0
			highestPower = 0

			maxPowerData = None
			
			powerCount = 1

			timeList = []
			maxPowerList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,max_power from "+config.INVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,max_power from "+config.INVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
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
							maxPowerData = round(thisRow[2],2)
							maxPowerList.append(maxPowerData)
						elif thisRow[2] == None:
							maxPowerList.append(None)
							maxPowerData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest max power
						#-------------------------------------------------------
						if powerCount == 1:
							lowestPower = maxPowerData
							highestPower = maxPowerData
							powerCount += 1
						else:
							if maxPowerData > highestPower:
								highestPower = maxPowerData
							elif maxPowerData < lowestPower:
								lowestPower = maxPowerData
						#--------------------------------------------------------
					else:
						count += 1
					
			maxPowerDict = {"name":"panel-temperature 1","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList
			maxPowerDict['data'] = maxPowerList

			responseDict['data_series'].append(maxPowerDict)
			
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

		elif (start_time != None or end_time != None) and whichType == 'operation-time':

			interval = processInterval(start_time,end_time)

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}	

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#for te in ivRangeList:
			#	if te[10] == equipment_type:
			#		responseDict['min_val'] = te[4]
			#		responseDict['max_val'] = te[5]
			#		break

			# Variable to record the highest and lowest value for max power
			# To be used for flexible range
			lowestOptTime = 0
			highestOptTime = 0

			opsTimeData = None
			
			optTimeCount = 1

			timeList = []
			operationalTimeList =  []
			count = 1
			
			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,operation_time from "+config.INVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,operation_time from "+config.INVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
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
							opsTimeData = round(thisRow[2],2)
							operationalTimeList.append(opsTimeData)
						elif thisRow[2] == None:
							operationalTimeList.append(None)
							opsTimeData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest operation time
						#-------------------------------------------------------
						if optTimeCount == 1:
							lowestOptTime = opsTimeData
							highestOptTime = opsTimeData
							optTimeCount += 1
						else:
							if opsTimeData > highestOptTime:
								highestOptTime = opsTimeData
							elif opsTimeData < lowestOptTime:
								lowestOptTime = opsTimeData
						#--------------------------------------------------------
					else:
						count += 1
					
			operationalTimeDict = {"name":"operational time","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList
			operationalTimeDict['data'] = operationalTimeList

			responseDict['data_series'].append(operationalTimeDict)
			
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

		elif (start_time != None or end_time != None) and whichType == 'panel-temperature':

			interval = processInterval(start_time,end_time)

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}	

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#for te in ivRangeList:
			#	if te[10] == equipment_type:
			#		responseDict['min_val'] = te[6]
			#		responseDict['max_val'] = te[7]
			#		break
			
			# Variable to record the highest and lowest value for panel temperature
			# To be used for flexible range
			lowestTemp = 0
			highestTemp = 0

			panelTemp1Data = None
			panelTemp2Data = None
			
			tempCount = 1

			timeList = []
			panelTemperatureOneList =  []
			panelTemperatureTwoList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,panel_temp_1,panel_temp_2 from "+config.INVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,panel_temp_1,panel_temp_2 from "+config.INVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
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

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest temperature
						#-------------------------------------------------------
						if tempCount == 1:
							if panelTemp1Data > panelTemp2Data:
								lowestTemp = panelTemp2Data
								highestTemp = panelTemp1Data
							else:
								lowestTemp = panelTemp1Data
								highestTemp = panelTemp2Data
							tempCount += 1
						else:
							if panelTemp1Data > highestTemp or panelTemp2Data > highestTemp:
								if panelTemp1Data > panelTemp2Data:
									highestTemp = panelTemp1Data
								else:
									highestTemp = panelTemp2Data
							if panelTemp1Data < lowestTemp or panelTemp2Data < lowestTemp:
								if panelTemp1Data < panelTemp2Data:
									lowestTemp = panelTemp1Data
								else:
									lowestTemp = panelTemp2Data	
						#--------------------------------------------------------
					else:
						count += 1
					
			panelTemperatureOneDict = {"name":"panel-temperature 1","data":[]}
			panelTemperatureTwoDict = {"name":"panel-temperature 2","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			panelTemperatureOneDict['data'] = panelTemperatureOneList
			panelTemperatureTwoDict['data'] = panelTemperatureTwoList

			responseDict['data_series'].append(panelTemperatureOneDict)
			responseDict['data_series'].append(panelTemperatureTwoDict)

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















