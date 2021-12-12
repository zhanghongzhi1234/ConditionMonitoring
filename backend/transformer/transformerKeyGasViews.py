
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

class TransformerKeyGasView(APIView):

	# Declare the static class variables
	global equipmentList
	global warningDefList

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

			queryStatement = "select warning_code,warning_message,class from "+config.WARNING_DEF+" where class = 'kgm' and equipment = 'transformer' "
			parameter = []
			warningDefList = queryPostgre(queryStatement,parameter)
	
			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		thistype = self.request.query_params.get('type')
		assetName = self.request.query_params.get('equipment_code')

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
				child_info = child_entity.split(",")
				# Gas measurement is the second 
				#entity_name = child_info[1]
				#entity_info = entity_name.split(".")
				station_id = te[5]
				system_id = te[6]
				subsystem_id = te[7]
				detail_code = te[8]
				break

		if thistype == 'indicator':
			# Title: Show transformer individual key gas indicator

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
			# Dissolved Gas Analysis(DGA) requires these gases: Hydrogen(H2),Carbon Monoxide(CO),Carbon Dioxide(CO2), Acetylene(C2H2), Ethylene(C2H4), Methane(CH4), Ethane(C2H6)
			# Datasource Name: dissolved_gas_analysis_gas_measurement

			# Title: Show transformer individual key gas information

			message = None

			responseDict = {
					"series":[],
					"output":{}
					}	
					
			queryStatement = "select gas_c2h2,gas_c2h4,gas_ch4,gas_h2,gas_co,gas_c2h6,equipment_type from "+config.TRANSFORMER_THRESHOLD+""
			parameter = []
			kgmThresholdList = queryPostgre(queryStatement,parameter)

			queryStatement = "select hydrogen_concentration,carbon_monoxide_concentration,acetylene_concentration,ethylene_concentration,methane_concentration,ethane_concentration,record_time from "+config.TRANSFORMER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and NOT (hydrogen_concentration IS NULL or carbon_monoxide_concentration IS NULL or acetylene_concentration IS NULL or ethylene_concentration IS NULL or methane_concentration IS NULL or ethane_concentration IS NULL) order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				# There is only 1 row for this resultset due to LIMIT 1
				thisRow = resultList[0]
				
				# Create the series list for all gas concentrations
				seriesList = []

				# For each gas concentration dict
				H2 = {"name":"H2","ratio_val":"","threshold_val":"","current_val":""}
				CO = {"name":"CO","ratio_val":"","threshold_val":"","current_val":""}
				C2H2 = {"name":"C2H2","ratio_val":"","threshold_val":"","current_val":""}
				C2H4 = {"name":"C2H4","ratio_val":"","threshold_val":"","current_val":""}
				CH4 = {"name":"CH4","ratio_val":"","threshold_val":"","current_val":""}
				C2H6 = {"name":"C2H6","ratio_val":"","threshold_val":"","current_val":""}

				total_composition = float(thisRow[0]) + float(thisRow[1]) +  float(thisRow[2]) + float(thisRow[3]) + float(thisRow[4]) + float(thisRow[5])
				
				H2['current_val'] = float(thisRow[0])
				CO['current_val'] = float(thisRow[1])
				C2H2['current_val'] = float(thisRow[2])
				C2H4['current_val'] = float(thisRow[3])
				CH4['current_val'] = float(thisRow[4])
				C2H6['current_val'] = float(thisRow[5])

				H2['ratio_val'] = round((float(thisRow[0])/total_composition) * 100 ,2)
				CO['ratio_val'] = round((float(thisRow[1])/total_composition) * 100,2)
				C2H2['ratio_val'] = round((float(thisRow[2])/total_composition) * 100,2)
				C2H4['ratio_val'] = round((float(thisRow[3])/total_composition) * 100,2)
				CH4['ratio_val'] = round((float(thisRow[4])/total_composition) * 100,2)
				C2H6['ratio_val'] = round((float(thisRow[5])/total_composition) * 100,2)

				for te in kgmThresholdList:
					if te[6] == equipment_type:
						H2['threshold_val'] = te[3]
						CO['threshold_val'] = te[4]
						C2H2['threshold_val'] = te[0]
						C2H4['threshold_val'] = te[1]
						CH4['threshold_val'] = te[2]
						C2H6['threshold_val'] = te[5]
						break
			
				seriesList.append(H2)
				seriesList.append(CO)
				seriesList.append(C2H2)
				seriesList.append(C2H4)
				seriesList.append(CH4)
				seriesList.append(C2H6)

				responseDict['series'] = seriesList

			queryStatement = "select record_time,warning_code,EXTRACT(day from record_time),EXTRACT(month from record_time),EXTRACT(year from record_time),EXTRACT(hour from record_time),EXTRACT(minute from record_time),EXTRACT(second from record_time) from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component like 'transformer:kgm'  order by record_time DESC LIMIT 1"
			parameter = [station_id,system_id,subsystem_id,detail_code]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				latestOutput = resultList[0]

				resultDict = {"result":"","result_type":"","description":""}

				# find the message given the warning code
				for te in warningDefList:
					if te[0] == latestOutput[1] and te[2] == 'kgm':
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


