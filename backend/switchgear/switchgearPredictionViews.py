
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
import math

import time

from backend.utilities.druidQuery import queryDruid
from backend.utilities.postgreQuery import queryPostgre
from backend.utilities.returnResponse import processResponse
from backend.utilities.returnTimeSeries import processTimeSeries
from backend.utilities.returnTimeRange import processTimeRange
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class SwitchgearPredictionsView(APIView):

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
		assetName = self.request.query_params.get('equipment_code')
		category = self.request.query_params.get('category')
		whichType = self.request.query_params.get('type')
		interval = self.request.query_params.get('interval')
		year = self.request.query_params.get('year')

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
				
		queryStatement = "select service_count,rx,rz,shunt_temp,busbar_temp,cable_temp,control_temp,equipment_type from "+config.SWITCHGEAR_THRESHOLD+""
		parameter = []
		swThresholdList = queryPostgre(queryStatement,parameter)

		if whichType == 'cb-breaker':
			# Title: Predict circuit breaker time to servicing (#16)

			finalValue = None
			gradientValue = None
			offsetValue = None
			timeToExpire = None

			year = 0
			month = 0
			day = 0

			# Need to check the interval and year
			predictionDict = {"model_name":"Regression Model","equation":"y=mx+b","parameters":[],"trending_model":{},"status":"","description":""}

			# Handle the parameters
			max_count = {"name":"max count","value":""}
			expended_count = {"name":"expended count","value":""}

			for te in swThresholdList:
				if te[7] == equipment_type:
					max_count['value'] = te[0]
					finalValue = te[0]
					break

			queryStatement = "select counter,record_time from "+config.OPERATING_COUNT+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				expended_count['value'] = resultList[0][0]
				offsetValue = resultList[0][0]
			else:
				expended_count['value'] = 0
				offsetValue = 0				
		
			predictionDict['parameters'].append(max_count)
			predictionDict['parameters'].append(expended_count)

			dataSeries = []
			dataDict = {"name":"Operating Counts","data":[]}

			# Handle the trending_model
			trendingModel = {"min_val":"","max_val":"","time_series":[],"data_series":[]}

			# These are the default range values, subjected to change in the code below
			for te in swRangeList:
				if te[14] == equipment_type:
					trendingModel['min_val'] = te[0]
					trendingModel['max_val'] = te[1]
					break

			# Handle the time_series
			timeSeries = processTimeSeries('next 10 years','future')
			trendingModel['time_series'] = timeSeries

			timeRange = processTimeRange('next 10 years','minute')

			# Take the latest last 10 (there is 1 operating count a 10 year yearly predicted_val. 10 rows of predicted_val data)
			# Take note the value at time '0' is needed as well. This is the current value.
			queryStatement = "select record_time,predicted_value as counter from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"') and component like 'switchgear:count%%' order by interval_minutes ASC LIMIT 11"			
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			for thisDict in resultList:
				dataDict['data'].append(math.floor(thisDict[1]))

			dataSeries.append(dataDict)
			trendingModel['data_series'] = dataSeries

			queryStatement = "select max(predicted_value) as highestCount, min(predicted_value) as lowestCount from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"') and component like 'switchgear:count%%'"			
			parameter = [station_id,system_id,subsystem_id,detail_code]
			rangeList = queryPostgre(queryStatement,parameter)

			# SQL aggregate functions will return at least 1 row even if results are null.
			# Therefore, need to check for null values
			if len(rangeList) > 0 and rangeList[0][1] != None and rangeList[0][0] != None:
				trendingModel['min_val'] = int(math.floor(rangeList[0][1]))- int(math.floor(rangeList[0][0])*0.3)
				trendingModel['max_val'] = int(math.floor(rangeList[0][0]))+ int(math.floor(rangeList[0][0])*0.3)	

			predictionDict['trending_model'] = trendingModel

			# Handle the status and description
			predictionDict['status'] = 'healthy'

			queryStatement = "select warning_code,record_time from "+config.WARNING_LOGS+" where component like 'switchgear:count%%' and station_id = %s  and system_id = %s  and subsystem_id= %s  and detail_code = %s  and not (status = '1' and is_ack = '1') and prediction = TRUE order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				predictionDict['status'] = 'warning'

			# Retrieve the gradient value
			queryStatement = "select parameters,record_time from "+config.PREDICTION_MODEL_INFO+" where component like 'switchgear:count%%' and station_id = %s  and system_id = %s  and subsystem_id= %s  and detail_code = %s  order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				gradientFraction = resultList[0][0]
				elements=gradientFraction.split(",")
				gradientValue = float(elements[0])
				#jsonValue = json.loads(resultList[0][0])
				#gradientValue = float(jsonValue['gradient'])

				# Calculate the time to expire,timeToExpire (in minutes)
				timeToExpire = (finalValue - offsetValue)/gradientValue

				# Number of year(s)
				year = int(timeToExpire/525600)
				timeRemainder = timeToExpire%525600
				# Number of month(s)
				month = int(timeRemainder/43200)
				timeRemainder = timeRemainder%43200
				# Number of day(s)
				day = int(timeRemainder/1440)

				# if the year is in the negative but not 0, meaning to say all time should be 0
				if year < 0:
					year = 0
					month = 0
					day = 0

				predictionDict['description'] = "Remaining Useful Life(RUL): "+str(year)+" Year(s), "+str(month)+" Month(s), "+str(day)+" Day(s)"

			else:
				predictionDict['description'] = "Error: Insufficient data"

			resultJSON = processJSON(predictionDict)

			return processResponse(resultJSON,'OK')

		elif whichType == 'dc-feeder':
			# Title: Predict DC feeder cable insulation value in next 7days(#17)

			finalValue = 0
			gradientValue = None
			offsetValueRX = None
			offsetValueRZ = None
			timeToExpire = None

			year = 0
			month = 0
			day = 0

			predictionDict = {"model_name":"Regression Model","equation":"y=mx+b","parameters":[],"trending_model":{},"status":"","description":""}

			resistance_rx = {"name":"resistance 1","value":""}
			resistance_rz = {"name":"resistance 2","value":""}

			dataSeries = []
			resistancerxDict = {"name":"rx","data":[]}
			resistancerzDict = {"name":"rz","data":[]}

			# Handle the trending_model
			trendingModel = {"min_val":"","max_val":"","time_series":[],"data_series":[]}

			# These are the default range values, subjected to change in the code below
			for te in swRangeList:
				if te[14] == equipment_type:
					trendingModel['min_val'] = te[10]
					trendingModel['max_val'] = te[11]
					break

			# Handle the time_series
			timeSeries = processTimeSeries('next 7 days','future')

			trendingModel['time_series'] = timeSeries

			timeRange = processTimeRange('next 7 days','minute')

			# Handle the data_series
			# Take the latest last 14 (there are 2 resistances for each a 7 days predicted_val. 14 rows of predicted_val data)
			# Take note the value at time '0' is needed as well. This is the current value.
			queryStatement = "select record_time,component,predicted_value as predictedValue from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"') and (component like 'switchgear:rx%%' or component like 'switchgear:rz%%') order by interval_minutes ASC LIMIT 16"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			for thisDict in resultList:
				if thisDict[1] == 'switchgear:rx':
					resistancerxDict['data'].append(round(thisDict[2],2))
				elif thisDict[1] == 'switchgear:rz':
					resistancerzDict['data'].append(round(thisDict[2],2))

			dataSeries.append(resistancerxDict)
			dataSeries.append(resistancerzDict)

			trendingModel['data_series'] = dataSeries

			queryStatement = "select max(predicted_value) as highestResistance, min(predicted_value) as lowestResistance from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"') and (component like 'switchgear:rx%%' or component like 'switchgear:rz%%')"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			rangeList = queryPostgre(queryStatement,parameter)		

			# SQL aggregate functions will return at least 1 row even if results are null.
			# Therefore, need to check for null values
			if len(rangeList) > 0 and rangeList[0][1] != None and rangeList[0][0] != None:
				trendingModel['min_val'] = int(math.floor(rangeList[0][1]))- int(math.floor(rangeList[0][0])*0.3)
				trendingModel['max_val'] = int(math.floor(rangeList[0][0]))+ int(math.floor(rangeList[0][0])*0.3)	

			predictionDict['trending_model'] = trendingModel

			#Get the current value
			queryStatement = "select cable_insulation_resistance_measurement_rx,cable_insulation_resistance_measurement_rz from "+config.SWITCHGEAR_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				offsetValueRX = resultList[0][0]
				offsetValueRZ = resultList[0][1]

			# Handle the status and description
			predictionDict['status'] = 'healthy'

			queryStatement = "select warning_code,record_time from "+config.WARNING_LOGS+" where (component like 'switchgear:rx%%' or component like 'switchgear:rz%%') and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and not (status = '1' and is_ack = '1') and prediction = TRUE order by record_time DESC LIMIT 2"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				predictionDict['status'] = 'warning'

			# Retrieve the gradient value
			queryStatement = "select parameters,component,record_time from "+config.PREDICTION_MODEL_INFO+" where (component like 'switchgear:rx%%' or component like 'switchgear:rz%%') and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 2"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				for te in resultList:
					#jsonValue = json.loads(te[0])
					#gradientValue = jsonValue['gradient']
					gradientFraction = te[0]
					elements=gradientFraction.split(",")
					gradientValue = float(elements[0])
					
					if te[1] == 'switchgear:rx':
						#gradientFraction = te[0]
						#elements=gradientFraction.split(",")
						#gradientValue = float(elements[0])

						# Find the days remaining if finalValue is 0.1 for RX
						finalValue = 0.1

						if offsetValueRX != None:
							timeToExpire = (finalValue - offsetValueRX)/gradientValue
							day = int(timeToExpire/1440)
							resistance_rx['value'] = day
						else:
							resistance_rx['value'] = 'UNKNOWN'
					
					elif te[1] == 'switchgear:rz':
						#gradientFraction = te[0]
						#elements=gradientFraction.split(",")
						#gradientValue = float(elements[0])

						# Find the days remaining if finalValue is 0.01 for RZ
						finalValue = 0.01

						if offsetValueRZ != None:
							timeToExpire = (finalValue - offsetValueRZ)/gradientValue
							day = int(timeToExpire/1440)
							resistance_rz['value'] = day
						else:
							resistance_rz['value'] = 'UNKNOWN'

			else:
				resistance_rx['value'] = 'X'
				resistance_rz['value'] = 'X'

			predictionDict['parameters'].append(resistance_rx)
			predictionDict['parameters'].append(resistance_rz)

			resultJSON = processJSON(predictionDict)

			return processResponse(resultJSON,'OK')

		elif whichType == 'panel-temperature':
			# Title: Predict panel temperature over next 24 hours (#18)

			predictionDict = {"model_name":"Temperature Prediction Model","equation":"Θfuture top =[||Θfinal|| - Θpresent top ](1 - e-t/||T0||) + Θpresent top","parameters":[],"trending_model":{},"status":"","description":""}

			dataSeries = []
			shuntDict = {"name":"Shunt","data":[]}
			controlDict = {"name":"Control","data":[]}
			busbarDict = {"name":"Busbar","data":[]}
			cableDict = {"name":"Cable","data":[]}

			# Handle the parameters
			shunt_overload = {"name":"shunt overload","value":""}
			busbar_overload = {"name":"busbar overload","value":""}
			control_overload = {"name":"control overload","value":""}
			cable_overload = {"name":"cable overload","value":""}

			# Handle the trending_model
			trendingModel = {"min_val":"","max_val":"","time_series":[],"data_series":[]}

			# These are the default range values, subjected to change in the code below
			for te in swRangeList:
				if te[14] == equipment_type:
					trendingModel['min_val'] = te[2]
					trendingModel['max_val'] = te[3]
					break

			# Handle the time_series
			timeSeries = processTimeSeries('next 24 hours','future')

			trendingModel['time_series'] = timeSeries

			timeRange = processTimeRange('next 24 hours','minute')
			
			# Take the latest last 96 (there are 4 panel temperatures for each a 24 hours hourly predicted_val. 96 rows of predicted_val data)
			# Note that there are 4 current values, total of 100 values to be retrieved
			queryStatement = "select record_time,component,predicted_value as predictedValue from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"','"+str(timeRange[13])+"','"+str(timeRange[14])+"','"+str(timeRange[15])+"','"+str(timeRange[16])+"','"+str(timeRange[17])+"','"+str(timeRange[18])+"','"+str(timeRange[19])+"','"+str(timeRange[20])+"','"+str(timeRange[21])+"','"+str(timeRange[22])+"','"+str(timeRange[23])+"','"+str(timeRange[24])+"') and (component like '%%switchgear:shunt%%' or component like '%%switchgear:control%%' or component like '%%switchgear:busbar%%' or component like '%%switchgear:cable%%') order by interval_minutes ASC LIMIT 100"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				for thisDict in resultList:
					if thisDict[1] == 'switchgear:shunt':
						shuntDict['data'].append(round(thisDict[2],2))
					elif thisDict[1] == 'switchgear:control':
						controlDict['data'].append(round(thisDict[2],2))
					elif thisDict[1] == 'switchgear:busbar':
						busbarDict['data'].append(round(thisDict[2],2))
					elif thisDict[1] == 'switchgear:cable':
						cableDict['data'].append(round(thisDict[2],2))

			dataSeries.append(shuntDict)
			dataSeries.append(controlDict)
			dataSeries.append(busbarDict)
			dataSeries.append(cableDict)

			trendingModel['data_series'] = dataSeries

			#Find the highest and lowest temperature 
			queryStatement = "select max(predicted_value) as highestTemperature, min(predicted_value) as lowestTemperature from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"','"+str(timeRange[13])+"','"+str(timeRange[14])+"','"+str(timeRange[15])+"','"+str(timeRange[16])+"','"+str(timeRange[17])+"','"+str(timeRange[18])+"','"+str(timeRange[19])+"','"+str(timeRange[20])+"','"+str(timeRange[21])+"','"+str(timeRange[22])+"','"+str(timeRange[23])+"','"+str(timeRange[24])+"') and (component like '%%switchgear:shunt%%' or component like '%%switchgear:control%%' or component like '%%switchgear:busbar%%' or component like '%%switchgear:cable%%')"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			rangeList = queryPostgre(queryStatement,parameter)
			
			# SQL aggregate functions will return at least 1 row even if results are null.
			# Therefore, need to check for null values
			if len(rangeList) > 0 and rangeList[0][1] != None and rangeList[0][0] != None:
				trendingModel['min_val'] = int(math.floor(rangeList[0][1]))- int(math.floor(rangeList[0][0])*0.3)
				trendingModel['max_val'] = int(math.floor(rangeList[0][0]))+ int(math.floor(rangeList[0][0])*0.3)

			predictionDict['trending_model'] = trendingModel

			# Handle the status and description
			predictionDict['status'] = 'healthy'

			queryStatement = "select warning_code,record_time from "+config.WARNING_LOGS+" where (component like '%%switchgear:shunt%%' or component like '%%switchgear:control%%' or component like '%%switchgear:busbar%%' or component like '%%switchgear:cable%%') and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and not (status = '1' and is_ack = '1') and prediction = TRUE order by record_time DESC LIMIT 4"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				predictionDict['status'] = 'warning'
				
			queryStatement = "select panel_temperature_shunt,panel_temperature_busbar,panel_temperature_cable,panel_temperature_control,record_time from "+config.SWITCHGEAR_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)
			
			# Retrieve the latest present values for the panel temperatures (these will be the present values to be used in the model/formula later)
			if len(resultList) > 0:
				shuntValue = resultList[0][0]
				busbarValue = resultList[0][1]
				cableValue = resultList[0][2]
				controlValue = resultList[0][3]
			
			# Retrieve the threshold values for the panel temperatures (these will be the present values to be used in the model/formula later)
			shuntTH = 0
			busbarTH = 0
			cableTH = 0
			controlTH = 0
			
			for te in swThresholdList:
				if te[7] == equipment_type:
					shuntTH = te[3]
					busbarTH = te[4]
					cableTH = te[5]
					controlTH = te[6]
					break

			# Retrieve the parameters
			queryStatement = "select parameters,component,record_time from "+config.PREDICTION_MODEL_INFO+" where (component like '%%switchgear:shunt%%' or component like '%%switchgear:control%%' or component like '%%switchgear:busbar%%' or component like '%%switchgear:cable%%') and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 4"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)
			
			# Using Θfuture top =[||Θfinal|| - Θpresent top ](1 - e-t/||T0||) + Θpresent top
			# Future top is the threshold values
			# Need to find t
			# (1 - e-t/||T0||) = (Θfuture top - Θpresent top) / ([||Θfinal|| - Θpresent top ])
			#  1 - (Θfuture top - Θpresent top) / [||Θfinal|| - Θpresent top ]) =  e-t/||T0||
			# Need to take ln on both side to solve the equation,  find 1 - (Θfuture top - Θpresent top) / [||Θfinal|| - Θpresent top ])   --> lefthandside
			# ln(lefthandside) = -t/||T0||
			# ln(lefthandside)||T0|| = -t
			# Therefore, t = ln(lefthandside)||T0|| multiply by -1  [QED]
			lefthandside = 0
			result = 0
			
			if len(resultList) > 0:
				for te in resultList:		
					gradientFraction = te[0]
					elements=gradientFraction.split(",")
					thetaFinal = math.fabs(float(elements[0]))
					timeZero = math.fabs(float(elements[1]))
					
					#jsonValues = json.loads(te[0])
					# Taking the absolute values, T0 is in minutes
					#thetaFinal = math.fabs(float(jsonValues['theta_final']))
					#timeZero =  math.fabs(float(jsonValues['T0']))
					
					if te[1] == 'switchgear:shunt':
						# Find lefthandside
						lefthandside = 1 - ((shuntTH - shuntValue) / (thetaFinal - shuntValue ))				
						# ln the lefthandside
						lefthandside = math.log(lefthandside)		
						# multiply by ||T0||
						lefthandside =  lefthandside * timeZero	
						# Finally, multiply by -1
						result = lefthandside * -1
						result = result/60
						# Input t
						shunt_overload['value'] = round(result,2)
						
					elif te[1] == 'switchgear:busbar':
						lefthandside = 1 - ((busbarTH - busbarValue) / (thetaFinal - busbarValue ))
						lefthandside = math.log(lefthandside)
						lefthandside =  lefthandside * timeZero
						result = lefthandside * -1		
						result = result/60						
					
						busbar_overload['value'] = round(result,2)
						
					elif te[1] == 'switchgear:cable':
						lefthandside = 1 - ((cableTH - cableValue) / (thetaFinal - cableValue ))
						lefthandside = math.log(lefthandside)
						lefthandside =  lefthandside * timeZero
						result = lefthandside * -1
						result = result/60
						
						cable_overload['value'] = round(result,2)
						
					elif te[1] == 'switchgear:control':
						lefthandside = 1 - ((controlTH - controlValue) / (thetaFinal - controlValue ))
						lefthandside = math.log(lefthandside)
						lefthandside =  lefthandside * timeZero
						result = lefthandside * -1
						result = result/60
				
						control_overload['value'] = round(result,2)
			else:
				predictionDict['description'] = "Error: Insufficient data"
				
			predictionDict['parameters'].append(shunt_overload)
			predictionDict['parameters'].append(busbar_overload)
			predictionDict['parameters'].append(control_overload)
			predictionDict['parameters'].append(cable_overload)
			
			predictionDict['description'] = "Data computed"

			resultJSON = processJSON(predictionDict)

			return processResponse(resultJSON,'OK')
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')



