
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
from backend.utilities.hashMessage import performEncodedHash
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

class InverterOperationInfoView(APIView):

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

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+""
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_operation_time,max_operation_time,equipment_type from "+config.INVERTER_RANGE+""
			parameter = []
			ivRangeList = queryPostgre(queryStatement,parameter)

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
			if te[1] == assetName:
				station_id = te[5]
				system_id = te[6]
				subsystem_id = te[7]
				detail_code = te[8]
				equipment_type = te[3]
				break

		#dataset = {"id":"operational-time","equipment_code":"","current_val":"","min_val":"","max_val":"","pm_threshold":"","status":"","last_pm_at":"","is_pm_ready":"","is_pm_done":""}
		#dataset = {"id":"operational-time","equipment_code":"","current_val":"","min_val":"","max_val":"","pm_threshold":"","status":""}
		dataset = {"id":"operational-time","equipment_code":"","current_val":"","min_val":"","max_val":"","pm_threshold":"","status":"","last_pm_at":"","is_pm_ready":"","is_pm_done":"","service_threshold":"","last_service_at":"","is_service_ready":"","is_service_done":""}  		

		queryStatement = "select operation_time,equipment_type from "+config.INVERTER_THRESHOLD+""
		parameter = []
		ivThresholdList = queryPostgre(queryStatement,parameter)

		# Populate the data from the static table
		for te in ivThresholdList:
			if te[1] == equipment_type:
				dataset['pm_threshold']=te[0]
				break

		for te in ivRangeList:
			if te[2] == equipment_type:
				dataset['min_val']=te[0]
				dataset['max_val']=te[1]
				break

		dataset['equipment_code']=assetName

		#queryStatement = "select record_time,operational_time,to_char(last_pm_at,'MM-dd-YYYY HH24:MI:SS'),is_pm_ready,is_pm_done from "+config.OPERATIONAL_TIME+" where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' order by record_time DESC LIMIT 1"
		queryStatement = "select record_time,operation_time from "+config.INVERTER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		if len(resultList) > 0:		
			lastestOutput = resultList[0]

			# Populate the data from the latest value
			dataset['current_val']=lastestOutput[1]		
			#dataset['last_pm_at']=lastestOutput[2]
			#dataset['is_pm_ready']=lastestOutput[3]
			#dataset['is_pm_done']=lastestOutput[4]


			if lastestOutput[1] < dataset['pm_threshold']:
				dataset['status'] = 'healthy'
			elif lastestOutput[1] >= dataset['pm_threshold']:
				dataset['status'] = 'warning'


		resultList = []
		resultList.append(dataset)
		resultJSON = processJSON(resultList)

		return processResponse(resultJSON,'OK')







