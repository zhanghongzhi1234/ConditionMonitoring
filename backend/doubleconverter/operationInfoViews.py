
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

class OperationInfoView(APIView):

	# Declare the static class variables
	global equipmentList
	global opsTimeRangeList

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
			
			queryStatement = "select min_operating_time_rec,max_operating_time_rec,min_operating_time_inv,max_operating_time_inv,equipment_type from "+config.DOUBLECONVERTER_RANGE+""
			parameter = []
			opsTimeRangeList = queryPostgre(queryStatement,parameter)
			
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

		responseList = []

		operationTimeRec = {"id":"operational-time-rec-mode","equipment_code":"","current_val":"","min_val":"","max_val":"","pm_threshold":"","service_threshold":"","status":"","last_pm_at":"","last_service_at":"","is_service_ready":"","is_service_done":"","is_pm_ready":"","is_pm_done":""}
		operationTimeInv = {"id":"operational-time-inv-mode","equipment_code":"","current_val":"","min_val":"","max_val":"","pm_threshold":"","service_threshold":"","status":"","last_pm_at":"","last_service_at":"","is_service_ready":"","is_service_done":"","is_pm_ready":"","is_pm_done":""}

		operationTimeRec['equipment_code'] = assetName
		operationTimeInv['equipment_code'] = assetName
		
		queryStatement = "select operating_time_rec,operating_time_inv,equipment_type from "+config.DOUBLECONVERTER_THRESHOLD+""
		parameter = []
		opsTimeTHList = queryPostgre(queryStatement,parameter)

		for te in opsTimeRangeList:
			if te[4] == equipment_type:
				operationTimeRec['min_val'] = te[0]
				operationTimeRec['max_val'] = te[1]
				operationTimeInv['min_val'] = te[2]
				operationTimeInv['max_val'] = te[3]
				break

		for te in opsTimeTHList:
			if te[2] == equipment_type:
				operationTimeRec['pm_threshold'] = te[0]
				operationTimeInv['pm_threshold'] = te[1]
				break

		operationTimeRec['service_threshold'] = 0
		operationTimeInv['service_threshold'] = 0

		queryStatement = "select record_time,operating_time_rec_mode,operating_time_inv_mode from "+config.DOUBLECONVERTER_DATA+" where station_id = %s and system_id =  %s and subsystem_id=  %s and detail_code =  %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		if len(resultList) > 0:	
			thisRow = resultList[0]
			operationTimeRec['current_val'] = thisRow[1]
			operationTimeInv['current_val'] = thisRow[2]

		queryStatement = "select record_time,component,TO_CHAR(last_pm_at,'yyyy-MM-dd HH:mm:ss'),TO_CHAR(last_service_at,'yyyy-MM-dd HH:mm:ss'),is_pm_done,is_service_done,is_pm_ready,is_service_ready from "+config.DOUBLECONVERTER_OPERATIONAL_TIME+" where station_id =  %s and system_id =  %s and subsystem_id=  %s and detail_code =  %s and (component like 'doubleconverter:operatingtimerec' or component like 'doubleconverter:operatingtimeinv') order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		for thisRow in resultList:
			if thisRow[1] == 'doubleconverter:operatingtimerec':
				operationTimeRec['last_pm_at'] = thisRow[2]
				operationTimeRec['last_service_at'] = ""	
				#operationTimeRec['is_pm_done'] = thisRow[4]
				operationTimeRec['is_service_done'] = ""
				#operationTimeRec['is_pm_ready'] = thisRow[6]
				operationTimeRec['is_service_ready'] = ""		

				if thisRow[4] == '0':
					operationTimeRec['is_pm_done'] = 0
				elif thisRow[4] == '1':
					operationTimeRec['is_pm_done'] = 1

				if thisRow[6] == '0':
					operationTimeRec['is_pm_ready'] = 0
				elif thisRow[6] == '1':
					operationTimeRec['is_pm_ready'] = 1

			elif thisRow[1] == 'doubleconverter:operatingtimeinv':
				operationTimeInv['last_pm_at'] = thisRow[2]
				operationTimeInv['last_service_at'] = ""	
				#operationTimeInv['is_pm_done'] = thisRow[4]
				operationTimeInv['is_service_done'] = ""
				#operationTimeInv['is_pm_ready'] = thisRow[6]
				operationTimeInv['is_service_ready'] = ""

				if thisRow[4] == '0':
					operationTimeInv['is_pm_done'] = 0
				elif thisRow[4] == '1':
					operationTimeInv['is_pm_done'] = 1

				if thisRow[6] == '0':
					operationTimeInv['is_pm_ready'] = 0
				elif thisRow[6] == '1':
					operationTimeInv['is_pm_ready'] = 1

		operationTimeRec['status'] = 'healthy'
		operationTimeInv['status'] = 'healthy'

		queryStatement = "select record_time,component,warning_code from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and (component like 'doubleconverter:operatingtimerec' or component like 'doubleconverter:operatingtimeinv') and status = '0' order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		for thisRow in resultList:
			if thisRow[1] == 'doubleconverter:operatingtimerec':
				if thisRow[2] != 'NA':
					operationTimeRec['status'] = 'Warning'

			elif thisRow[1] == 'doubleconverter:operatingtimeinv':
				if thisRow[2] != 'NA':
					operationTimeInv['status'] = 'Warning'

		responseList.append(operationTimeRec)
		responseList.append(operationTimeInv)

		resultJSON = processJSON(responseList)

		return processResponse(resultJSON,'OK')









