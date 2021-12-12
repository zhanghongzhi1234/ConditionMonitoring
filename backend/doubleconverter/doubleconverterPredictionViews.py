
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


class DoubleconverterPredictionsView(APIView):

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

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+""
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)
			
			queryStatement = "select min_module_temp_thy1,max_module_temp_thy1,min_module_temp_thy2,max_module_temp_thy2,min_module_temp_igbt1,max_module_temp_igbt1,min_num_operations_rec,max_num_operations_rec,min_num_operations_inv,max_num_operations_inv,min_operational_time_fans,max_operational_time_fans,equipment_type from "+config.DOUBLECONVERTER_RANGE+""
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
		assetName = self.request.query_params.get('equipment_code')
		whichType = self.request.query_params.get('type')

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
				
		queryStatement = "select module_temp_thy1,module_temp_thy2,module_temp_igbt1,num_operations_rec,num_operations_inv,operational_time_fans,min_operational_current_fans,max_operational_current_fans from "+config.DOUBLECONVERTER_THRESHOLD+""
		parameter = []
		dcThresholdList = queryPostgre(queryStatement,parameter)
		
		dcThreshold = dcThresholdList[0]

		if whichType == 'thy-temperature':
		
			predictionDict = {"model_name":"Temperature Prediction Model","equation":"Θfuture top =[||Θfinal|| - Θpresent top ](1 - e-t/||T0||) + Θpresent top","parameters":[],"trending_model":{}}

			dataSeries = []
			thy1Dict = {"name":"Thy1","data":[]}
			thy2Dict = {"name":"Thy2","data":[]}
			
			# Handle the trending_model
			trendingModel = {"min_val":"","max_val":"","time_series":[],"data_series":[],"mark_lines":{}}

			# These are the default range values, subjected to change in the code below
			for te in dcRangeList:
				if te[12] == equipment_type:
					trendingModel['min_val'] = te[0]
					trendingModel['max_val'] = te[1]
					break

			# Handle the time_series
			trendingModel['time_series'] = ["00:00","00:05","00:10","00:15","00:20","00:25","00:30","00:35","00:40","00:45","00:50","00:55","01:00"]

			timeRange = processTimeRange('next 1 hour','minute')
			
			# Handle the data_series	
			queryStatement = "select record_time,component,predicted_value as predictedValue,interval_minutes from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"') and (component like '%%doubleconverter:moduletempthy1%%' or component like '%%doubleconverter:moduletempthy2%%' ) order by interval_minutes ASC LIMIT 26"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)
			
			thy1Value = 0
			thy1Time = 0
			thy2Value = 0
			thy2Time = 0
			
			thy1Flag = 'false'
			thy2Flag = 'false'

			if len(resultList) > 0:
				for thisDict in resultList:
					if thisDict[1] == 'doubleconverter:moduletempthy1':
						thy1Dict['data'].append(round(thisDict[2],2))
						if thy1Flag == 'false':
							thy1Value = thisDict[2]
							thy1Time = thisDict[3]
						if thisDict[2] >= dcThreshold[0]:
							thy1Flag = 'true'
						
					elif thisDict[1] == 'doubleconverter:moduletempthy2':
						thy2Dict['data'].append(round(thisDict[2],2))
						if thy2Flag == 'false':
							thy2Value = thisDict[2]
							thy2Time = thisDict[3]
						if thisDict[2] >= dcThreshold[1]:
							thy2Flag = 'true'

			dataSeries.append(thy1Dict)
			dataSeries.append(thy2Dict)

			trendingModel['data_series'] = dataSeries

			# Handle the mark_lines
			marklines = {"data":[]}
			thy1Threshold = {"id":"threshold-1","name":"Thy1 Threshold","axis_val":""}
			thy2Threshold = {"id":"threshold-2","name":"Thy2 Threshold","axis_val":""}
			
			thy1Threshold['axis_val'] = dcThreshold[0]
			thy2Threshold['axis_val'] = dcThreshold[1] 
			
			marklines['data'].append(thy1Threshold)
			marklines['data'].append(thy2Threshold)
			
			trendingModel['mark_lines'] = marklines			

			queryStatement = "select max(predicted_value) as highestValue, min(predicted_value) as lowestValue from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"') and (component like '%%doubleconverter:moduletempthy1%%' or component like '%%doubleconverter:moduletempthy2%%' )"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			rangeList = queryPostgre(queryStatement,parameter)

			# SQL aggregate functions will return at least 1 row even if results are null.
			# Therefore, need to check for null values
			if len(rangeList) > 0 and rangeList[0][1] != None and rangeList[0][0] != None:
				trendingModel['min_val'] = int(math.floor(rangeList[0][1]))- int(math.floor(rangeList[0][0])*0.3)
				trendingModel['max_val'] = int(math.floor(rangeList[0][0]))+ int(math.floor(rangeList[0][0])*0.3)				
			
			predictionDict['trending_model'] = trendingModel
			
			# Handle the parameters
			thy1_parameter = {"id":"thy1","name":"Thy1","predicted_value":"","predicted_time":"","status":""}
			thy2_parameter = {"id":"thy2","name":"Thy2","predicted_value":"","predicted_time":"","status":""}
			
			if thy1Flag == 'true':
				thy1_parameter['status'] = 'warning'
			else:
				thy1_parameter['status'] = 'healthy'	
					
			if thy2Flag == 'true':
				thy2_parameter['status'] = 'warning'			
			else:
				thy2_parameter['status'] = 'healthy'		

			thy1_parameter['predicted_value'] = round(thy1Value,2)
			thy1_parameter['predicted_time'] = thy1Time
			thy2_parameter['predicted_value'] = round(thy2Value,2)
			thy2_parameter['predicted_time'] = thy2Time

			predictionDict['parameters'].append(thy1_parameter)
			predictionDict['parameters'].append(thy2_parameter)

			resultJSON = processJSON(predictionDict)

			return processResponse(resultJSON,'OK')
			
		elif whichType == 'igbt-temperature':
		
			predictionDict = {"model_name":"Temperature Prediction Model","equation":"Θfuture top =[||Θfinal|| - Θpresent top ](1 - e-t/||T0||) + Θpresent top","parameters":[],"trending_model":{}}

			dataSeries = []
			igbt1Dict = {"name":"IGBT1","data":[]}
			
			# Handle the trending_model
			trendingModel = {"min_val":"","max_val":"","time_series":[],"data_series":[],"mark_lines":{}}

			# These are the default range values, subjected to change in the code below
			for te in dcRangeList:
				if te[12] == equipment_type:
					trendingModel['min_val'] = te[4]
					trendingModel['max_val'] = te[5]
					break

			# Handle the time_series
			trendingModel['time_series'] = ["00:00","00:05","00:10","00:15","00:20","00:25","00:30","00:35","00:40","00:45","00:50","00:55","01:00"]

			timeRange = processTimeRange('next 1 hour','minute')
			
			# Handle the data_series		
			queryStatement = "select record_time,component,predicted_value as predictedValue,interval_minutes from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"') and component like '%%doubleconverter:moduletempigbt1%%' order by interval_minutes ASC LIMIT 13"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)
			
			igbt1Value = 0
			igbt1Time = 0
			
			igbt1Flag = 'false'

			if len(resultList) > 0:
				for thisDict in resultList:
					if thisDict[1] == 'doubleconverter:moduletempigbt1':
						igbt1Dict['data'].append(round(thisDict[2],2))
						if igbt1Flag == 'false':
							igbt1Value = thisDict[2]
							igbt1Time = thisDict[3]
						if thisDict[2] >= dcThreshold[2]:
							igbt1Flag = 'true'

			dataSeries.append(igbt1Dict)

			trendingModel['data_series'] = dataSeries

			# Handle the mark_lines
			marklines = {"data":[]}
			igbt1Threshold = {"id":"threshold-1","name":"igbt1 Threshold","axis_val":""}
			
			igbt1Threshold['axis_val'] = dcThreshold[2]
			
			marklines['data'].append(igbt1Threshold)
			
			trendingModel['mark_lines'] = marklines		

			queryStatement = "select max(predicted_value) as highestValue, min(predicted_value) as lowestValue from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"') and component like '%%doubleconverter:moduletempigbt1%%'"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			rangeList = queryPostgre(queryStatement,parameter)	

			# SQL aggregate functions will return at least 1 row even if results are null.
			# Therefore, need to check for null values
			if len(rangeList) > 0 and rangeList[0][1] != None and rangeList[0][0] != None:
				trendingModel['min_val'] = int(math.floor(rangeList[0][1]))- int(math.floor(rangeList[0][0])*0.3)
				trendingModel['max_val'] = int(math.floor(rangeList[0][0]))+ int(math.floor(rangeList[0][0])*0.3)				
			
			predictionDict['trending_model'] = trendingModel
			
			# Handle the parameters
			igbt1_parameter = {"id":"igbt1","name":"igbt1","predicted_value":"","predicted_time":"","status":""}
			
			if igbt1Flag == 'true':
				igbt1_parameter['status'] = 'warning'
			else:
				igbt1_parameter['status'] = 'healthy'	
						

			igbt1_parameter['predicted_value'] = round(igbt1Value,2)
			igbt1_parameter['predicted_time'] = igbt1Time

			predictionDict['parameters'].append(igbt1_parameter)

			resultJSON = processJSON(predictionDict)

			return processResponse(resultJSON,'OK')
			
		elif whichType == 'operation-count':

			predictionDict = {"model_name":"Linear Regression Model","equation":"y = mx + c","parameters":[],"trending_model":{}}

			# Handle the trending_model
			trendingModel = {"yAxis":[],"xAxis":[],"data_series":[]}
			
			dataSeries = []

			recTotalDict = {"name":"Rec(Total)","xAxisIndex":0,"yAxisIndex":0,"data":[]}
			invTotalDict = {"name":"Inv(Total)","xAxisIndex":0,"yAxisIndex":0,"data":[]}
			
			timeAxis = {"name":"Predict Time","data":["00:00","00:05","00:10","00:15","00:20","00:25","00:30","00:35","00:40","00:45","00:50","00:55","01:00"]}
			
			trendingModel['xAxis'].append(timeAxis)
			
			countsTotal = {"name":"Counts (Total)","min_val":"","max_val":""}
			
			# These are the default range values, subjected to change in the code below
			for te in dcRangeList:
				if te[12] == equipment_type:
					countsTotal['min_val'] = te[6]
					countsTotal['max_val'] = te[7]
					break				
			
			timeRange = processTimeRange('next 1 hour','minute')
			
			# Handle the data_series		
			queryStatement = "select record_time,component,predicted_value as predictedValue,interval_minutes from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"') and (component like '%%doubleconverter:operationrec%%' or component like '%%doubleconverter:operationinv%%') order by interval_minutes ASC LIMIT 26"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)
					
			if len(resultList) > 0:
				for thisDict in resultList:
					if thisDict[1] == 'doubleconverter:operationrec':
						recTotalDict['data'].append(math.floor(thisDict[2]))
						
					elif thisDict[1] == 'doubleconverter:operationinv':
						invTotalDict['data'].append(math.floor(thisDict[2]))

			dataSeries.append(recTotalDict)
			dataSeries.append(invTotalDict)

			trendingModel['data_series'] = dataSeries

			queryStatement = "select max(predicted_value) as highestValue, min(predicted_value) as lowestValue from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"') and (component like '%%doubleconverter:operationrec%%' or component like '%%doubleconverter:operationinv%%')"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			rangeList = queryPostgre(queryStatement,parameter)

			# SQL aggregate functions will return at least 1 row even if results are null.
			# Therefore, need to check for null values
			if len(rangeList) > 0 and rangeList[0][1] != None and rangeList[0][0] != None:
				countsTotal['min_val'] = int(math.floor(rangeList[0][1]))- int(math.floor(rangeList[0][0])*0.3)
				countsTotal['max_val'] = int(math.floor(rangeList[0][0]))+ int(math.floor(rangeList[0][0])*0.3)
				
			trendingModel['yAxis'].append(countsTotal)
			predictionDict['trending_model'] = trendingModel
			
			# Handle the parameters
			opRec_parameter = {"id":"rec-total-count","name":"Rec Total Counts","predicted_value":"","predicted_time":"","status":""}
			opInv_parameter = {"id":"inv-total-count","name":"Inv Total Counts","predicted_value":"","predicted_time":"","status":""}

			offsetValueREC = 0
			offsetValueINV = 0
			hourREC = 0
			hourINV = 0
			finalValueREC = dcThreshold[3]
			finalValueINV = dcThreshold[4]
			opRec_parameter['predicted_value'] = dcThreshold[3]	
			opInv_parameter['predicted_value'] = dcThreshold[4]

			#Get the current value
			queryStatement = "select number_of_operations_rec_mode, number_of_operations_inv_mode from "+config.DOUBLECONVERTER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				offsetValueREC = resultList[0][0]
				offsetValueINV = resultList[0][1]

			# Retrieve the gradient value
			queryStatement = "select parameters,component,record_time from "+config.PREDICTION_MODEL_INFO+" where (component like 'doubleconverter:operationrec%%' or component like 'doubleconverter:operationinv%%') and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 2"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				for te in resultList:
					gradientFraction = te[0]
					elements=gradientFraction.split(",")
					gradientValue = float(elements[0])

					if te[1] == 'doubleconverter:operationrec':
						# Calculate the time to expire,timeToExpire (in minutes)
						timeToExpire = (finalValueREC - offsetValueREC)/gradientValue
						hourREC = round(int(timeToExpire/60))

						opRec_parameter['predicted_time'] = hourREC

					elif te[1] == 'doubleconverter:operationinv':
						# Calculate the time to expire,timeToExpire (in minutes)
						timeToExpire = (finalValueINV - offsetValueINV)/gradientValue
						hourINV = round(int(timeToExpire/60))

						opInv_parameter['predicted_time'] = hourINV

			if hourREC < 10:
				opRec_parameter['status'] = 'warning'
			else:
				opRec_parameter['status'] = 'healthy'	

			if hourINV < 10:
				opInv_parameter['status'] = 'warning'
			else:
				opInv_parameter['status'] = 'healthy'

			predictionDict['parameters'].append(opRec_parameter)
			predictionDict['parameters'].append(opInv_parameter)

			resultJSON = processJSON(predictionDict)

			return processResponse(resultJSON,'OK')

		elif whichType == 'cooling-fan':

			predictionDict = {"model_name":"Linear Regression Model","equation":"y = mx + c","parameters":[],"trending_model":{}}

			# Handle the trending_model
			trendingModel = {"yAxis":[],"xAxis":[],"data_series":[]}
			
			timeAxis = {"name":"Predict Time","data":["00:00","00:05","00:10","00:15","00:20","00:25","00:30","00:35","00:40","00:45","00:50","00:55","01:00"]}
			
			trendingModel['xAxis'].append(timeAxis)
			
			expendedHours = {"name":"Expended Hours","min_val":"","max_val":""}
			#currentA = {"name":"Current (A)","min_val":"","max_val":""}
			
			# These are the default range values, subjected to change in the code below
			for te in dcRangeList:
				if te[12] == equipment_type:
					expendedHours['min_val'] = te[10]
					expendedHours['max_val'] = te[11]
					#currentA['min_val'] = te[12]
					#currentA['max_val'] = te[13]
					break
					
			#trendingModel['yAxis'].append(currentA)
			
			dataSeries = []
			# Expended is actually operating time
			expendedHourDict = {"name":"Expended Hours","xAxisIndex":0,"yAxisIndex":0,"data":[]}
			#currentDict = {"name":"Current","xAxisIndex":1,"yAxisIndex":0,"data":[]}
			
			# Handle the data_series
			timeRange = processTimeRange('next 1 hour','minute')
			
			queryStatement = "select record_time,component,predicted_value as predictedValue,interval_minutes from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"') and (component like '%%doubleconverter:operationaltimecoolingfans%%' or component like '%%doubleconverter:operationalcurrentcoolingfans%%') order by interval_minutes ASC LIMIT 26"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)	

			opTimeValue = 0
			opTimeTime = 0
			#opCurrentValue = 0
			#opCurrentTime = 0
			
			opTimeFlag = 'false'
			#opCurrentFlag = 'false'			
			
			if len(resultList) > 0:
				for thisDict in resultList:
					if thisDict[1] == 'doubleconverter:operationaltimecoolingfans':
						expendedHourDict['data'].append(round(thisDict[2],2))
						if opTimeFlag == 'false':
							opTimeValue = thisDict[2]
							opTimeTime = thisDict[3]
						if thisDict[2] >= dcThreshold[5]:
							opTimeFlag = 'true'
						
					#elif thisDict[1] == 'doubleconverter:operationalcurrentcoolingfans':
					#	currentDict['data'].append(thisDict[2])
					#	if opCurrentFlag == 'false':
					#		opCurrentValue = thisDict[2]
					#		opCurrentTime = thisDict[3]
					#	if thisDict[2] >= dcThreshold[6]:
					#		opCurrentFlag = 'true'

			dataSeries.append(expendedHourDict)
			#dataSeries.append(currentDict)

			trendingModel['data_series'] = dataSeries

			queryStatement = "select max(predicted_value) as highestValue, min(predicted_value) as lowestValue from "+config.PREDICTION_MODEL+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and interval_minutes in ('"+str(timeRange[0])+"','"+str(timeRange[1])+"','"+str(timeRange[2])+"','"+str(timeRange[3])+"','"+str(timeRange[4])+"','"+str(timeRange[5])+"','"+str(timeRange[6])+"','"+str(timeRange[7])+"','"+str(timeRange[8])+"','"+str(timeRange[9])+"','"+str(timeRange[10])+"','"+str(timeRange[11])+"','"+str(timeRange[12])+"') and (component like '%%doubleconverter:operationaltimecoolingfans%%' or component like '%%doubleconverter:operationalcurrentcoolingfans%%')"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			rangeList = queryPostgre(queryStatement,parameter)	

			# SQL aggregate functions will return at least 1 row even if results are null.
			# Therefore, need to check for null values
			if len(rangeList) > 0 and rangeList[0][1] != None and rangeList[0][0] != None:
				expendedHours['min_val'] = int(math.floor(rangeList[0][1]))- int(math.floor(rangeList[0][0])*0.3)
				expendedHours['max_val'] = int(math.floor(rangeList[0][0]))+ int(math.floor(rangeList[0][0])*0.3)

			trendingModel['yAxis'].append(expendedHours)	
			predictionDict['trending_model'] = trendingModel
			
			# Handle the parameters
			opTime_parameter = {"id":"expended-hour","name":"Expended Hours","predicted_value":"","predicted_time":"","status":""}
			
			if opTimeFlag == 'true':
				opTime_parameter['status'] = 'warning'
			else:
				opTime_parameter['status'] = 'healthy'	
						

			opTime_parameter['predicted_value'] = round(opTimeValue,2)
			opTime_parameter['predicted_time'] = opTimeTime

			predictionDict['parameters'].append(opTime_parameter)

			resultJSON = processJSON(predictionDict)

			return processResponse(resultJSON,'OK')
		
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')



