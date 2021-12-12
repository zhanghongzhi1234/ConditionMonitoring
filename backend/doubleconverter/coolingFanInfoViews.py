
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

from backend.utilities.druidQuery import queryDruid
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

class CoolingFanInfoView(APIView):

	# Declare the static class variables
	global equipmentList
	global distinctStationList
	global coolingFanRangeList
	
	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here
			queryStatement = "select acronym_asset_name,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code from "+config.EQUIPMENT_INFO+""	
			parameter = []	
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select distinct station_id from "+config.EQUIPMENT_INFO+" where equipment = 'dconverter' order by station_id"			
			parameter = []
			distinctStationList = queryPostgre(queryStatement,parameter)	

			queryStatement = "select min_operational_time_fans,max_operational_time_fans,min_operational_current_fans,max_operational_current_fans,equipment_type from "+config.DOUBLECONVERTER_RANGE+""
			parameter = []
			coolingFanRangeList  = queryPostgre(queryStatement,parameter)
			
			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		assetName = self.request.query_params.get('equipment_code')
		
		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None

		# find the equipment info given the asset_name
		for te in equipmentList:
			if te[0] == assetName:
				station_id = te[3]
				system_id = te[4]
				subsystem_id = te[5]
				detail_code = te[6]
				equipment_type = te[1]
				break
				
		queryStatement = "select operational_time_fans,min_operational_current_fans,max_operational_current_fans,equipment_type from "+config.DOUBLECONVERTER_THRESHOLD+""
		parameter = []
		coolingFanTHList = queryPostgre(queryStatement,parameter)

		responseList = []

		responseDict = {"id":"cooling-fan1","equipment_code":"","operation_time":{},"operation_current":{}}
		operationTimeDict = {"current_val":"","min_val":"","max_val":"","pm_threshold":"","service_threshold":"","status":"","last_pm_at":"","last_service_at":"","is_service_ready":"","is_service_done":"","is_pm_ready":"","is_pm_done":""}
		operationCurrent = {"current_val":"","lower_limit":"","upper_limit":"","min_val":"","max_val":"","status":""}

		responseDict['equipment_code'] = assetName

		for te in coolingFanRangeList:
			if te[4] == equipment_type:
				operationTimeDict['min_val'] = te[0]
				operationTimeDict['max_val'] = te[1]
				operationCurrent['min_val'] = te[2]
				operationCurrent['max_val'] = te[3]
				break

		for te in coolingFanTHList:
			if te[3] == equipment_type:
				operationTimeDict['pm_threshold'] = te[0]
				operationCurrent['lower_limit'] = te[1]
				operationCurrent['upper_limit'] = te[2]
				break

		operationTimeDict['service_threshold'] = 0

		queryStatement = "select record_time,operational_time_of_cooling_fans,operational_current_of_cooling_fans from "+config.DOUBLECONVERTER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		if len(resultList) > 0:	
			thisRow = resultList[0]
			operationTimeDict['current_val'] = thisRow[1]
			operationCurrent['current_val'] = thisRow[2]

		queryStatement = "select record_time,component,TO_CHAR(last_pm_at,'yyyy-MM-dd HH:mm:ss'),TO_CHAR(last_service_at,'yyyy-MM-dd HH:mm:ss'),is_pm_done,is_service_done,is_pm_ready,is_service_ready from "+config.DOUBLECONVERTER_OPERATIONAL_TIME+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component like 'doubleconverter:operationaltimecoolingfans' order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		for thisRow in resultList:
			if thisRow[1] == 'doubleconverter:operationaltimecoolingfans':
				operationTimeDict['last_pm_at'] = ""
				operationTimeDict['last_service_at'] = thisRow[3]	
				operationTimeDict['is_pm_done'] = ""
				#operationTimeDict['is_service_done'] = thisRow[5]
				operationTimeDict['is_pm_ready'] = ""
				#operationTimeDict['is_service_ready'] = thisRow[7]

				if thisRow[5] == '0':
					operationTimeDict['is_service_done'] = 0
				elif thisRow[5] == '1':
					operationTimeDict['is_service_done'] = 1

				if thisRow[7] == '0':
					operationTimeDict['is_service_ready'] = 0
				elif thisRow[7] == '1':
					operationTimeDict['is_service_ready'] = 1		

		operationTimeDict['status'] = 'healthy'
		operationCurrent['status'] = 'healthy'

		queryStatement = "select record_time,component,warning_code from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and (component like 'doubleconverter:operationaltimecoolingfans' or component like 'doubleconverter:operationalcurrentcoolingfans') and status = '0' order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		for thisRow in resultList:
			if thisRow[1] == 'doubleconverter:operationaltimecoolingfans':
				if thisRow[2] != 'NA':
					operationTimeDict['status'] = 'Warning'
					operationCurrent['status'] = 'Warning'
					
			if thisRow[1] == 'doubleconverter:operationalcurrentcoolingfans':
				if thisRow[2] != 'NA':
					operationCurrent['status'] = 'Warning'


		responseDict['operation_time'] = operationTimeDict
		responseDict['operation_current'] = operationCurrent
		responseList.append(responseDict)

		resultJSON = processJSON(responseList)

		return processResponse(resultJSON,'OK')	





