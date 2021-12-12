
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


class DoubleconverterTrendingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global dcRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here
			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" where equipment = 'dconverter' order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_num_operations_rec, max_num_operations_rec, min_num_operations_inv, max_num_operations_inv, min_operating_time_rec, max_operating_time_rec,min_operating_time_inv, max_operating_time_inv,min_max_power_rec,max_max_power_rec,min_max_power_inv,max_max_power_inv, min_operational_time_fans,max_operational_time_fans, min_operational_current_fans,max_operational_current_fans,min_panel_temp_1_rec1,max_panel_temp_1_rec1,min_panel_temp_1_rec2,max_panel_temp_1_rec2, min_panel_temp_1_inv, max_panel_temp_1_inv, min_module_temp_thy1, max_module_temp_thy1,min_module_temp_thy2, max_module_temp_thy2, min_module_temp_igbt1, max_module_temp_igbt1,min_panel_temp_2_rec1,max_panel_temp_2_rec1,min_panel_temp_2_rec2,max_panel_temp_2_rec2, min_panel_temp_2_inv, max_panel_temp_2_inv,equipment_type from "+config.DOUBLECONVERTER_RANGE+""
			parameter = []
			dcRangeList = queryPostgre(queryStatement,parameter)
			
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

		staticRangeValue = dcRangeList[0]

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
			

		if (start_time != None or end_time != None) and whichType == 'operation-counts':
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
			#for te in dcRangeList:
			#	if te[34] == equipment_type:
			#		responseDict['min_val'] = te[0]
			#		responseDict['max_val'] = te[1]
			#		break

			# Variable to record the highest and lowest value for operation counts
			# To be used for flexible range
			lowestCounter = 0
			highestCounter = 0

			recData = None
			invData = None
			
			counterCount = 1

			timeList = []
			recList =  []
			invList =  []

			count = 1
			
			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, number_of_operations_rec_mode,number_of_operations_inv_mode from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, number_of_operations_rec_mode,number_of_operations_inv_mode from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"	
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
							recData = round(thisRow[2],2)
							recList.append(recData)
						elif thisRow[2] == None:
							recList.append(None)
							recData = 0

						if thisRow[3] != None:
							invData = round(thisRow[3],2)
							invList.append(invData)
						elif thisRow[3] == None:
							invList.append(None)
							invData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest temperature
						#-------------------------------------------------------
						if counterCount == 1:
							if recData > invData:
								lowestCounter = invData
								highestCounter = recData
							else:
								lowestCounter = recData
								highestCounter = invData
							counterCount += 1
						else:
							if recData > highestCounter or invData > highestCounter:
								if recData > invData:
									highestCounter = recData
								else:
									highestCounter = invData
							if recData < lowestCounter or invData < lowestCounter:
								if recData < invData:
									lowestCounter = recData
								else:
									lowestCounter = invData	
						#--------------------------------------------------------
					else:
						count += 1

			recDict = {"name":"Number of operations (Rec Mode)","data":[]}
			invDict = {"name":"Number of operations (Inv Mode)","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			recDict['data'] = recList
			invDict['data'] = invList

			responseDict['data_series'].append(recDict)
			responseDict['data_series'].append(invDict)
			
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
			#for te in dcRangeList:
			#	if te[34] == equipment_type:
			#		responseDict['min_val'] = te[10]
			#		responseDict['max_val'] = te[11]
			#		break
			
			# Variable to record the highest and lowest value for max power
			# To be used for flexible range
			lowestPower = 0
			highestPower = 0

			recData = None
			invData = None
			
			powerCount = 1

			timeList = []
			recList =  []
			invList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, maximum_power_rec_mode,maximum_power_inv_mode from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, maximum_power_rec_mode,maximum_power_inv_mode from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
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
							recData = round(thisRow[2],2)
							recList.append(recData)
						elif thisRow[2] == None:
							recList.append(None)
							recData = 0

						if thisRow[3] != None:
							invData = round(thisRow[3],2)
							invList.append(invData)
						elif thisRow[3] == None:
							invList.append(None)
							invData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest temperature
						#-------------------------------------------------------
						if powerCount == 1:
							if recData > invData:
								lowestPower = invData
								highestPower = recData
							else:
								lowestPower = recData
								highestPower = invData
							powerCount += 1
						else:
							if recData > highestPower or invData > highestPower:
								if recData > invData:
									highestPower = recData
								else:
									highestPower= invData
							if recData < lowestPower or invData < lowestPower:
								if recData < invData:
									lowestPower = recData
								else:
									lowestPower= invData
						#--------------------------------------------------------
					else:
						count += 1

			recDict = {"name":"Maximum power (Rec Mode)","data":[]}
			invDict = {"name":"Maximum power (Inv Mode)","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			recDict['data'] = recList
			invDict['data'] = invList

			responseDict['data_series'].append(recDict)
			responseDict['data_series'].append(invDict)
			
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

		elif (start_time != None or end_time != None) and whichType == 'module-temperature':

			interval = processInterval(start_time,end_time)

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}	

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#for te in dcRangeList:
			#	if te[34] == equipment_type:
			#		responseDict['min_val'] = te[22]
			#		responseDict['max_val'] = te[23]
			#		break
			
			# Variable to record the highest and lowest value for panel temperature
			# To be used for flexible range
			lowestThy1 = 0
			highestThy1 = 0
			lowestThy2 = 0
			highestThy2 = 0
			lowestIgbt1 = 0
			highestIgbt1 = 0

			thy1Data = None
			thy2Data = None
			igbt1Data = None
			
			lowestTemp = 0
			highestTemp = 0
			tempCount = 1

			timeList = []
			thy1List =  []
			thy2List =  []
			igbt1List =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, module_temperature_thy1,module_temperature_thy2,module_temperature_igbt1 from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"	
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, module_temperature_thy1,module_temperature_thy2,module_temperature_igbt1 from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"			
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
							thy1Data = round(thisRow[2],2)
							thy1List.append(thy1Data)
						elif thisRow[2] == None:
							thy1List.append(None)
							thy1Data = 0

						if thisRow[3] != None:
							thy2Data = round(thisRow[3],2)
							thy2List.append(thy2Data)
						elif thisRow[3] == None:
							thy2List.append(None)
							thy2Data = 0

						if thisRow[4] != None:
							igbt1Data = round(thisRow[4],2)
							igbt1List.append(igbt1Data)
						elif thisRow[4] == None:
							igbt1List.append(None)
							igbt1Data = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest panel temperature
						#-------------------------------------------------------
						if tempCount == 1:
							lowestThy1 = thy1Data
							highestThy1 = thy1Data
							lowestThy2 = thy2Data
							highestThy2 = thy2Data
							lowestIgbt1 = igbt1Data
							highestIgbt1 = igbt1Data
							tempCount += 1
						else:
							if thy1Data > highestThy1:
								highestThy1 = thy1Data
							elif thy1Data < lowestThy1:
								lowestThy1 = thy1Data
								
							if thy2Data > highestThy2:
								highestThy2 = thy2Data
							elif thy2Data < lowestThy2:
								lowestThy2 = thy2Data
								
							if igbt1Data > highestIgbt1:
								highestIgbt1 = igbt1Data
							elif igbt1Data < lowestIgbt1:
								lowestIgbt1 = igbt1Data
							
						#--------------------------------------------------------
					else:
						count += 1

			thy1Dict = {"name":"Module temperature thy1","data":[]}
			thy2Dict = {"name":"Module temperature thy1","data":[]}
			igbt1Dict = {"name":"Module temperature igbt1","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			thy1Dict['data'] = thy1List
			thy2Dict['data'] = thy2List
			igbt1Dict['data'] = igbt1List

			responseDict['data_series'].append(thy1Dict)
			responseDict['data_series'].append(thy2Dict)
			responseDict['data_series'].append(igbt1Dict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			lowestTemp = lowestThy1
			highestTemp = highestThy1
			
			if lowestThy2 < lowestTemp:
				lowestTemp = lowestThy2
			if lowestIgbt1 < lowestTemp:
				lowestTemp = lowestIgbt1
			
			if highestThy2 > highestTemp:
				highestTemp = highestThy2
			if highestIgbt1 > highestTemp:
				highestTemp = highestIgbt1

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
			#for te in dcRangeList:
			#	if te[34] == equipment_type:
			#		responseDict['min_val'] = te[16]
			#		responseDict['max_val'] = te[17]
			#		break
			
			# Variable to record the highest and lowest value for panel temperature
			# To be used for flexible range
			lowestTemp1Rec1 = 0
			highestTemp1Rec1 = 0
			lowestTemp1Rec2 = 0
			highestTemp1Rec2 = 0
			lowestTemp1Inv = 0
			highestTemp1Inv = 0
			lowestTemp2Rec1 = 0
			highestTemp2Rec1 = 0
			lowestTemp2Rec2 = 0
			highestTemp2Rec2 = 0
			lowestTemp2Inv = 0
			highestTemp2Inv = 0

			temp1rec1Data = None
			temp1rec2Data = None
			temp1invData = None
			temp2rec1Data = None
			temp2rec2Data = None
			temp2invData = None
			
			lowestTemp = 0
			highestTemp = 0
			tempCount = 1

			timeList = []
			temp1rec1List =  []
			temp1rec2List =  []
			temp1invList =  []
			temp2rec1List =  []
			temp2rec2List =  []
			temp2invList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, panel_temperature_1_rec1,panel_temperature_1_rec2,panel_temperature_1_inv,panel_temperature_2_rec1,panel_temperature_2_rec2,panel_temperature_2_inv from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"	
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, panel_temperature_1_rec1,panel_temperature_1_rec2,panel_temperature_1_inv,panel_temperature_2_rec1,panel_temperature_2_rec2,panel_temperature_2_inv from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"			
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
							temp1rec1Data = round(thisRow[2],2)
							temp1rec1List.append(temp1rec1Data)
						elif thisRow[2] == None:
							temp1rec1List.append(None)
							temp1rec1Data = 0

						if thisRow[3] != None:
							temp1rec2Data = round(thisRow[3],2)
							temp1rec2List.append(temp1rec2Data)
						elif thisRow[3] == None:
							temp1rec2List.append(None)
							temp1rec2Data = 0

						if thisRow[4] != None:
							temp1invData = round(thisRow[4],2)
							temp1invList.append(temp1invData)
						elif thisRow[4] == None:
							temp1invList.append(None)
							temp1invData = 0

						if thisRow[5] != None:
							temp2rec1Data = round(thisRow[5],2)
							temp2rec1List.append(temp2rec1Data)
						elif thisRow[5] == None:
							temp2rec1List.append(None)
							temp2rec1Data = 0

						if thisRow[6] != None:
							temp2rec2Data = round(thisRow[6],2)
							temp2rec2List.append(temp2rec2Data)
						elif thisRow[6] == None:
							temp2rec2List.append(None)
							temp2rec2Data = 0

						if thisRow[7] != None:
							temp2invData = round(thisRow[7],2)
							temp2invList.append(temp2invData)	
						elif thisRow[7] == None:
							temp2invList.append(None)
							temp2invData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest panel temperature
						#-------------------------------------------------------
						if tempCount == 1:
							lowestTemp1Rec1 = temp1rec1Data
							highestTemp1Rec1 = temp1rec1Data
							lowestTemp1Rec2 = temp1rec2Data
							highestTemp1Rec2 = temp1rec2Data
							lowestTemp1Inv = temp1invData
							highestTemp1Inv = temp1invData
							lowestTemp2Rec1 = temp2rec1Data
							highestTemp2Rec1 = temp2rec1Data
							lowestTemp2Rec2 = temp2rec2Data
							highestTemp2Rec2 = temp2rec2Data
							lowestTemp2Inv = temp2invData
							highestTemp2Inv = temp2invData
							tempCount += 1
						else:
							if temp1rec1Data > highestTemp1Rec1:
								highestTemp1Rec1 = temp1rec1Data
							elif temp1rec1Data < lowestTemp1Rec1:
								lowestTemp1Rec1 = temp1rec1Data
								
							if temp1rec2Data > highestTemp1Rec2:
								highestTemp1Rec2 = temp1rec2Data
							elif temp1rec2Data < lowestTemp1Rec2:
								lowestTemp1Rec2 = temp1rec2Data
								
							if temp1invData > highestTemp1Inv:
								highestTemp1Inv = temp1invData
							elif temp1invData < lowestTemp1Inv:
								lowestTemp1Inv = temp1invData

							if temp2rec1Data > highestTemp2Rec1:
								highestTemp2Rec1 = temp2rec1Data
							elif temp2rec1Data < lowestTemp2Rec1:
								lowestTemp2Rec1 = temp2rec1Data		

							if temp2rec2Data > highestTemp2Rec2:
								highestTemp2Rec2 = temp2rec2Data
							elif temp2rec2Data < lowestTemp2Rec2:
								lowestTemp2Rec2 = temp2rec2Data	

							if temp2invData > highestTemp2Inv:
								highestTemp2Inv = temp2invData
							elif temp2invData < lowestTemp2Inv:
								lowestTemp2Inv = temp2invData						
						#--------------------------------------------------------
					else:
						count += 1

			temp1rec1Dict = {"name":"Panel temperature TOP rec 1","data":[]}
			temp1rec2Dict = {"name":"Panel temperature TOP rec 2","data":[]}
			temp1invDict = {"name":"Panel temperature TOP inv","data":[]}
			temp2rec1Dict = {"name":"Panel temperature BOTTOM rec 1","data":[]}
			temp2rec2Dict = {"name":"Panel temperature BOTTOM rec 2","data":[]}
			temp2invDict = {"name":"Panel temperature BOTTOM inv","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			temp1rec1Dict['data'] = temp1rec1List
			temp1rec2Dict['data'] = temp1rec2List
			temp1invDict['data'] = temp1invList
			temp2rec1Dict['data'] = temp2rec1List
			temp2rec2Dict['data'] = temp2rec2List
			temp2invDict['data'] = temp2invList

			responseDict['data_series'].append(temp1rec1Dict)
			responseDict['data_series'].append(temp1rec2Dict)
			responseDict['data_series'].append(temp1invDict)
			responseDict['data_series'].append(temp2rec1Dict)
			responseDict['data_series'].append(temp2rec2Dict)
			responseDict['data_series'].append(temp2invDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			lowestTemp = lowestTemp1Rec1
			highestTemp = highestTemp1Rec1
			
			if lowestTemp1Rec2 < lowestTemp:
				lowestTemp = lowestTemp1Rec2
			if lowestTemp1Inv < lowestTemp:
				lowestTemp = lowestTemp1Inv
			if lowestTemp2Rec1 < lowestTemp:
				lowestTemp = lowestTemp2Rec1
			if lowestTemp2Rec2 < lowestTemp:
				lowestTemp = lowestTemp2Rec2
			if lowestTemp2Inv < lowestTemp:
				lowestTemp = lowestTemp2Inv
			
			if highestTemp1Rec2 > highestTemp:
				highestTemp = highestTemp1Rec2
			if highestTemp1Inv > highestTemp:
				highestTemp = highestTemp1Inv
			if highestTemp2Rec1 > highestTemp:
				highestTemp = highestTemp2Rec1
			if highestTemp2Rec2 > highestTemp:
				highestTemp = highestTemp2Rec2
			if highestTemp2Inv > highestTemp:
				highestTemp = highestTemp2Inv

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
			#for te in dcRangeList:
			#	if te[34] == equipment_type:
			#		responseDict['min_val'] = te[6]
			#		responseDict['max_val'] = te[7]
			#		break
			
			# Variable to record the highest and lowest value for operation time rec and inv mode
			# To be used for flexible range
			lowestOpsTime = 0
			highestOpsTime = 0

			recData = None
			invData = None

			opsTimeCount = 1

			timeList = []
			recList =  []
			invList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, operating_time_rec_mode,operating_time_inv_mode from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, operating_time_rec_mode,operating_time_inv_mode from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
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
							recData = round(thisRow[2],2)
							recList.append(recData)
						elif thisRow[2] == None:
							recList.append(None)
							recData = 0

						if thisRow[3] != None:
							invData = round(thisRow[3],2)
							invList.append(invData)
						elif thisRow[3] == None:
							invList.append(None)
							invData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest temperature
						#-------------------------------------------------------
						if opsTimeCount == 1:
							if recData > invData:
								lowestOpsTime = invData
								highestOpsTime = recData
							else:
								lowestOpsTime = recData
								highestOpsTime = invData
							opsTimeCount += 1
						else:
							if recData > highestOpsTime or invData > highestOpsTime:
								if recData > invData:
									highestOpsTime = recData
								else:
									highestOpsTime= invData
							if recData < lowestOpsTime or invData < lowestOpsTime:
								if recData < invData:
									lowestOpsTime = recData
								else:
									lowestOpsTime= invData	
						#--------------------------------------------------------
					else:
						count += 1

			recDict = {"name":"Operating time (Rec Mode)","data":[]}
			invDict = {"name":"Operating time (Inv Mode)","data":[]}

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList

			recDict['data'] = recList
			invDict['data'] = invList

			responseDict['data_series'].append(recDict)
			responseDict['data_series'].append(invDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			responseDict['min_val'] = round(lowestOpsTime - (highestOpsTime*0.3))
			responseDict['max_val'] = round(highestOpsTime + (highestOpsTime*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestOpsTime) + 0.5) / (1 + 0.3)

			if highestOpsTime < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestOpsTime + (highestOpsTime*0.3)) + 1
			#--------------------------------------------------------

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		elif (start_time != None or end_time != None) and whichType == 'cooling-fan':

			interval = processInterval(start_time,end_time)

			responseDict = {
					"yAxis":[],
					"xAxis":[],
					"data_series":[]
					}

			fanTimeSeries = {"name":"Time","data":[]}
			fanCurrentSeries = {"name":"Current","data":[]}

			coolingFanTime = {"name":"Time (Hours)","min_val":"","max_val":""}
			coolingFanCurrent = {"name":"Current (A)","min_val":"","max_val":""}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off	
			#for te in dcRangeList:
			#	if te[34] == equipment_type:
			#		coolingFanTime['min_val'] = te[12]
			#		coolingFanTime['max_val'] = te[13]
			#		coolingFanCurrent['min_val'] = te[14]
			#		coolingFanCurrent['max_val'] = te[15]
			#		break

			#responseDict['yAxis'].append(coolingFanTime)
			#responseDict['yAxis'].append(coolingFanCurrent)

			# Variable to record the highest and lowest value for cooling fan operation time and current
			# To be used for flexible range
			lowestOptTime = 0
			highestOptTime = 0
			lowestOptCurrent = 0
			highestOptCurrent = 0

			optimeData = None
			opcurrentData = None

			coolingFanCount = 1

			timeList = []
			optimeList =  []
			opcurrentList =  []

			count = 1

			if end_time == None:			

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, operational_time_of_cooling_fans,operational_current_of_cooling_fans from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"		
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:	

				queryStatement = "select record_time,DATE_FORMAT(record_time,'dd-MMM-yy HH:mm:ss') as time_interval, operational_time_of_cooling_fans,operational_current_of_cooling_fans from "+config.DOUBLE_CONVERTER+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and unix_timestamp(record_time,'MM-dd-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id = %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)" 		
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
							optimeData = round(thisRow[2],2)
							optimeList.append(optimeData)
						elif thisRow[2] == None:
							optimeList.append(None)
							optimeData = 0

						if thisRow[3] != None:
							opcurrentData = round(thisRow[3],2)
							opcurrentList.append(opcurrentData)
						elif thisRow[3] == None:
							opcurrentList.append(None)
							opcurrentData = 0

						# Add the timestamp into the time list
						timeList.append(thisRow[1])	
						# Reset the count back to 1
						count = 1

						# Patch to record the highest and lowest operation time and current
						#-------------------------------------------------------
						if coolingFanCount == 1:
							lowestOptTime = optimeData
							highestOptTime = optimeData
							lowestOptCurrent = opcurrentData
							highestOptCurrent = opcurrentData

							coolingFanCount += 1
						else:
							if optimeData > highestOptTime:
								highestOptTime = optimeData
							elif optimeData < lowestOptTime:
								lowestOptTime = optimeData
							if opcurrentData > highestOptCurrent:
								highestOptCurrent = opcurrentData
							elif opcurrentData < lowestOptCurrent:
								lowestOptCurrent = opcurrentData
						#--------------------------------------------------------
					else:
						count += 1
	
			optimeDict = {"name":"Operational time of cooling fans","xAxisIndex":0,"yAxisIndex":0,"data":[]}
			opcurrentDict = {"name":"Operational current of cooling fans","xAxisIndex":1,"yAxisIndex":1,"data":[]}

			optimeDict['data'] = optimeList
			opcurrentDict['data'] = opcurrentList

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			fanTimeSeries['data'] = timeList
			fanCurrentSeries['data'] = timeList

			responseDict['xAxis'].append(fanTimeSeries)
			responseDict['xAxis'].append(fanCurrentSeries)

			responseDict['data_series'].append(optimeDict)
			responseDict['data_series'].append(opcurrentDict)
			
			# Patch to be added here for flexible range
			#--------------------------------------------------------
			coolingFanTime['min_val'] = round(lowestOptTime - (highestOptTime*0.3))
			coolingFanTime['max_val'] = round(highestOptTime + (highestOptTime*0.3))
			coolingFanCurrent['min_val'] = round(lowestOptCurrent - (highestOptCurrent*0.3))
			coolingFanCurrent['max_val'] = round(highestOptCurrent + (highestOptCurrent*0.3))
			
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
				coolingFanTime['max_val'] = round(highestOptTime + (highestOptTime*0.3)) + 1

			toNext = (math.floor(highestOptCurrent) + 0.5) / (1 + 0.3)

			if highestOptCurrent < toNext:
				# Add one to the highest value
				coolingFanCurrent['max_val'] = round(highestOptCurrent + (highestOptCurrent*0.3)) + 1
			#--------------------------------------------------------

			responseDict['yAxis'].append(coolingFanTime)
			responseDict['yAxis'].append(coolingFanCurrent)

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')

		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')







		

