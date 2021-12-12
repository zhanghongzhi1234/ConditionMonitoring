
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
from backend.utilities.returnTimeSeries import processTimeSeries
from backend.utilities.returnInterval import processInterval
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class SwitchgearTrendingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global swRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+""
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_count,max_count,min_shunt,max_shunt,min_busbar,max_busbar,min_cable,max_cable,min_control,max_control,min_rx,max_rx,min_rz,max_rz,equipment_type from "+config.SWITCHGEAR_RANGE+""
			parameter = []
			swRangeList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		periodicity = self.request.query_params.get('periodicity')
		whichType = self.request.query_params.get('type')
		start_time = self.request.query_params.get('start_time')
		end_time = self.request.query_params.get('end_time')
		assetName = self.request.query_params.get('equipment_code')

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
			if te[1] == assetName:
				station_id = te[5]
				system_id = te[6]
				subsystem_id = te[7]
				detail_code = te[8]
				equipment_type = te[3]
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
			

		if (start_time != None or end_time != None) and whichType == 'cb-breaker':
			# If either start_time or end_time is not None, meaning this is custom.

			interval = processInterval(start_time,end_time)

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}	


			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off					
			#for te in swRangeList:
			#	if te[14] == equipment_type:
			#		responseDict['min_val'] = te[0]
			#		responseDict['max_val'] = te[1]
			#		break
			
			# Variable to record the highest and lowest value for circuit breaker counter
			# To be used for flexible range
			lowestCounter = 0
			highestCounter = 0

			counterData = None
			
			counterCount = 1
			timeList = []
			counterList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, breaker_count from "+config.SWITCHGEAR_COUNTS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, breaker_count from "+config.SWITCHGEAR_COUNTS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,end_time,entityName]

			resultList = queryHive(queryStatement,parameter)

			if resultList != None:	
				if len(resultList) > 0:
					resultList = sorted(resultList, key=itemgetter(0))

				for thisRow in resultList:
					if count == interval:
						# Check that the values are not null 
						# , any values that are out of range is return as null (please take note)
						# Therefore, need to filter for null values
						# If null value is encountered, the previous value will be used for this timestamp
						if thisRow[2] != None:
							counterData = round(thisRow[2],2)
							counterList.append(counterData)
						elif thisRow[2] == None:
							counterList.append(None)

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest circuit breaker count
						#-------------------------------------------------------
						if counterCount == 1:
							lowestCounter = counterData
							highestCounter = counterData
							counterCount += 1
						else:
							if counterData > highestCounter:
								highestCounter = counterData
							elif counterData < lowestCounter:
								lowestCounter = counterData
						#--------------------------------------------------------
					else:
						count += 1

			counterDict = {
				     "name":"Operating Counts",
				     "data":[]
				  }

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			counterDict['data'] = counterList
			
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

			responseDict['data_series'].append(counterDict)

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
			#for te in swRangeList:
			#	if te[14] == equipment_type:
			#		responseDict['min_val'] = te[2]
			#		responseDict['max_val'] = te[3]
			#		break
					
			# Variable to record the highest and lowest value for panel temperature
			# To be used for flexible range
			lowestShunt = 0
			highestShunt = 0
			lowestBusbar = 0
			highestBusbar = 0
			lowestCable = 0
			highestCable = 0
			lowestControl = 0
			highestControl = 0
			
			lowestTemp = 0
			highestTemp = 0
			tempCount = 1

			shuntData = None
			controlData = None
			busbarData = None
			cableData = None

			timeList = []
			shuntList =  []
			controlList =  []
			busbarList =  []
			cableList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,panel_temperature_shunt as shunt,panel_temperature_busbar as busbar,panel_temperature_cable as cable, panel_temperature_control as control from "+config.SWITCHGEAR_TEMP_RES+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,panel_temperature_shunt as shunt,panel_temperature_busbar as busbar,panel_temperature_cable as cable, panel_temperature_control as control from "+config.SWITCHGEAR_TEMP_RES+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
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
							shuntData = round(thisRow[2],2)
							shuntList.append(shuntData)
						elif thisRow[2] == None:
							shuntList.append(None)
							shuntData = 0

						if thisRow[5] != None:
							controlData = round(thisRow[5],2)
							controlList.append(controlData)
						elif thisRow[5] == None:
							controlList.append(None)
							controlData = 0

						if thisRow[3] != None:
							busbarData = round(thisRow[3],2)
							busbarList.append(busbarData)
						elif thisRow[3] == None:
							busbarList.append(None)
							busbarData = 0

						if thisRow[4] != None:
							cableData = round(thisRow[4],2)
							cableList.append(cableData)
						elif thisRow[4] == None:
							cableList.append(None)
							cableData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest panel temperature
						#-------------------------------------------------------
						if tempCount == 1:
							lowestShunt = shuntData
							highestShunt = shuntData
							lowestBusbar = busbarData
							highestBusbar = busbarData
							lowestCable = cableData
							highestCable = cableData
							lowestControl = controlData
							highestControl = controlData
							tempCount += 1
						else:
							if shuntData > highestShunt:
								highestShunt = shuntData
							elif shuntData < lowestShunt:
								lowestShunt = shuntData
								
							if busbarData > highestBusbar:
								highestBusbar = busbarData
							elif busbarData < lowestBusbar:
								lowestBusbar = busbarData
								
							if cableData > highestCable:
								highestCable = cableData
							elif cableData < lowestCable:
								lowestCable = cableData

							if controlData > highestControl:
								highestControl = controlData
							elif controlData < lowestControl:
								lowestControl = controlData						
						#--------------------------------------------------------
					else:
						count += 1
						
			shuntDict = {"name":"Shunt","data":[]}
			controlDict = {"name":"Control","data":[]}
			busbarDict = {"name":"Busbar","data":[]}
			cableDict = {"name":"Cable","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			shuntDict['data'] = shuntList
			controlDict['data'] = controlList
			busbarDict['data'] = busbarList
			cableDict['data'] = cableList
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			lowestTemp = lowestShunt
			highestTemp = highestShunt
			
			if lowestBusbar < lowestTemp:
				lowestTemp = lowestBusbar
			if lowestCable < lowestTemp:
				lowestTemp = lowestCable
			if lowestControl < lowestTemp:
				lowestTemp = lowestControl
			
			if highestBusbar > highestTemp:
				highestTemp = highestBusbar
			if highestCable > highestTemp:
				highestTemp = highestCable
			if highestControl > highestTemp:
				highestTemp = highestControl
			
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

			responseDict['data_series'].append(shuntDict)
			responseDict['data_series'].append(controlDict)
			responseDict['data_series'].append(busbarDict)
			responseDict['data_series'].append(cableDict)

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')


		elif (start_time != None or end_time != None) and whichType == 'dc-feeder':

			interval = processInterval(start_time,end_time)

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}	
					

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#for te in swRangeList:
			#	if te[14] == equipment_type:
			#		responseDict['min_val'] = te[10]
			#		responseDict['max_val'] = te[11]
			#		break

			# Variable to record the highest and lowest value for resistance RX RZ
			# To be used for flexible range
			lowestResistance = 0
			highestResistance = 0
			
			resistanceCount = 1

			rxData = None
			rzData = None

			timeList = []
			rxList =  []
			rzList =  []

			count = 1
			
			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,cable_insulation_resistance_measurement_rz as rz,cable_insulation_resistance_measurement_rx as rx from "+config.SWITCHGEAR_TEMP_RES+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval,cable_insulation_resistance_measurement_rz as rz,cable_insulation_resistance_measurement_rx as rx from "+config.SWITCHGEAR_TEMP_RES+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"			
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
						if thisRow[3] != None:
							rxData = round(thisRow[3],2)
							rxList.append(rxData)
						elif thisRow[3] == None:
							rxList.append(None)
							rxData = 0

						if thisRow[2] != None:
							rzData = round(thisRow[2],2)
							rzList.append(rzData)
						elif thisRow[2] == None:
							rzList.append(None)
							rzData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest resistance
						#-------------------------------------------------------
						if resistanceCount == 1:
							if rzData > rxData:
								lowestResistance = rxData
								highestResistance = rzData
							else:
								lowestResistance = rzData
								highestResistance = rxData
							resistanceCount += 1
						else:
							if rzData > highestResistance or rxData > highestResistance:
								if rzData > rxData:
									highestResistance = rzData
								else:
									highestResistance= rxData
							if rzData < lowestResistance or rxData < lowestResistance:
								if rzData < rxData:
									lowestResistance = rzData
								else:
									lowestResistance= rxData	
						#--------------------------------------------------------
					else:
						count += 1
						
			rzDict = {"name":"Resistance RZ","data":[]}
			rxDict = {"name":"Resistance RX","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			rzDict['data'] = rzList
			rxDict['data'] = rxList

			responseDict['data_series'].append(rzDict)
			responseDict['data_series'].append(rxDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestResistance - (highestResistance*0.3))
			responseDict['max_val'] = round(highestResistance + (highestResistance*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestResistance) + 0.5) / (1 + 0.3)

			if highestResistance < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestResistance + (highestResistance*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')





