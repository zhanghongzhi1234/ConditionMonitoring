
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
from backend.utilities.postgreUpdate import updatePostgre
#from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnResponse import processResponse
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

class TransformerDuvalTriangleView(APIView):

	# Declare the static class variables
	global equipmentList
	global warningDefList
	global dtmRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer,child_entity from "+config.EQUIPMENT_INFO+" order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select warning_code,warning_message,class from "+config.WARNING_DEF+" where class = 'dtm' and equipment = 'transformer' "
			parameter = []
			warningDefList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_c2h2,max_c2h2,min_c2h4,max_c2h4,min_ch4,max_ch4,equipment_type from "+config.TRANSFORMER_RANGE+""
			parameter = []
			dtmRangeList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		thistype = self.request.query_params.get('type')
		assetName = self.request.query_params.get('equipment_code')

		entity_name = None
		entity_info = None
		child_entity = None

		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None

		# find the system_id given the asset_name
		for te in equipmentList:
			if te[1] == assetName:
				child_entity = te[10]
				equipment_type = te[3]
				#child_info = child_entity.split(",")
				# Gas measurement is the second 
				#entity_name = child_info[1]
				#entity_info = entity_name.split(".")
				station_id = te[5]
				system_id = te[6]
				subsystem_id = te[7]
				detail_code = te[8]
				break

		if thistype == 'indicator':
			# Title: Show transformer individual duval triangle indicator

			responseDict = {
					"indicator":[]
					}	

			for thisRow in warningDefList:	
				thisInfo = {"name":"","description":""}
				thisInfo['name'] = thisRow[0]
				thisInfo['description'] = thisRow[1]
				responseDict['indicator'].append(thisInfo)		

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')				
			
		elif thistype == 'info':
			# Duval Triangle Method(DTM) requires three gases: Acetylene(C2H2), Ethylene(C2H4), Methane(CH4)
			# Datasource Name: dissolved_gas_analysis_gas_measurement

			# Title: Show transformer duval triangle composition information

			responseDict = {
					"series":[],
					"output":{}
					}
			queryStatement = "select gas_c2h2,gas_c2h4,gas_ch4,equipment_type from "+config.TRANSFORMER_THRESHOLD+""
			parameter = []
			dtmThresholdList = queryPostgre(queryStatement,parameter)
			
			queryStatement = "select acetylene_concentration,ethylene_concentration,methane_concentration, record_time from "+config.TRANSFORMER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and NOT (acetylene_concentration IS NULL or ethylene_concentration IS NULL or methane_concentration IS NULL) order by record_time DESC LIMIT 1 "
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				# There is only 1 row for this resultset due to LIMIT 1
				thisRow = resultList[0]
				
				# Create the series list for all gas concentrations
				seriesList = []

				# For each gas concentration dict
				C2H2 = {"name":"C2H2","warning_val":"","max_val":"","min_val":"","current_val":""}
				C2H4 = {"name":"C2H4","warning_val":"","max_val":"","min_val":"","current_val":""}
				CH4 = {"name":"CH4","warning_val":"","max_val":"","min_val":"","current_val":""}

				C2H2['current_val'] = float(thisRow[0])
				C2H4['current_val'] = float(thisRow[1])
				CH4['current_val'] = float(thisRow[2])

				for te in dtmRangeList:
					if te[6] == equipment_type:
						C2H2['min_val'] =  te[0]
						C2H4['min_val'] = te[2]
						CH4['min_val'] = te[4]
						C2H2['max_val'] = te[1]
						C2H4['max_val'] = te[3]
						CH4['max_val'] = te[5]
						break

				for te in dtmThresholdList:
					if te[3] == equipment_type:
						C2H2['warning_val'] = te[0]
						C2H4['warning_val'] = te[1]
						CH4['warning_val'] = te[2]	
						break
				
				seriesList.append(C2H2)
				seriesList.append(C2H4)
				seriesList.append(CH4)

				responseDict['series'] = seriesList

			queryStatement = "select record_time,warning_code,EXTRACT(day from record_time),EXTRACT(month from record_time),EXTRACT(year from record_time),EXTRACT(hour from record_time),EXTRACT(minute from record_time),EXTRACT(second from record_time) from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component like 'transformer:dtm' order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)
			
			if len(resultList) > 0:
				latestOutput = resultList[0]

				resultDict = {"result":"","result_type":"","description":""}

				# find the message given the warning code
				for te in warningDefList:
					if te[0] == latestOutput[1] and te[2] == 'dtm':
						message = te[1]
						break

				resultDict['result'] = message
				resultDict['result_type'] = 'healthy'
				if latestOutput[1] !=  'NA':
					resultDict['result_type'] = 'warning'

				TimeEnd = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
				TimeStart = datetime.datetime(int(latestOutput[4]),int(latestOutput[3]),int(latestOutput[2]),int(latestOutput[5]),int(latestOutput[6]),int(latestOutput[7]))
				TimeDiff = TimeEnd - TimeStart
				TimeDiff = TimeDiff.total_seconds() / 60
				TimeDiff = abs(math.ceil(TimeDiff))

				resultDict['description'] = '< '+str(TimeDiff)+' minutes ago'
				
				responseDict['output'] = resultDict
				#responseDict['output'] = {"result":"Abnormal: Arcing in oil","result_type":"warning","description":"< 5 minutes ago"}

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')	

		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')

