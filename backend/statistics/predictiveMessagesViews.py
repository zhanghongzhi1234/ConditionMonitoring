
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

class PredictiveMessagesView(APIView):

	# Declare the static class variables
	global warningDefList
	global equipmentList
	global stationList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select warning_code,warning_message,severity,recommended_action from "+config.WARNING_DEF+""
			parameter = []
			warningDefList = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select distinct station_id,station_acronym from "+config.STATION_INFO+" order by station_id"
			parameter = []
			stationList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		category = self.request.query_params.get('category')
		station = self.request.query_params.get('station')
		hour = self.request.query_params.get('hour')
		limit = self.request.query_params.get('limit')
		whichType = self.request.query_params.get('type')

		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None

		# Patch due to changes in requirement, station_acronym used instead for 'station'
		# Need to retrieve the correct station_id, using the given station_acronym
		for li in stationList:
			if station == li[1]:
				station = li[0]
				break

		if limit == None:
			# Use default for limit
			limit = str(1000)

		assetName = self.request.query_params.get('equipment_code')
		if assetName != None:
			# find the equipment info given the asset_name
			for te in equipmentList:
				if te[1] == assetName:
					station_id = te[5]
					system_id = te[6]
					subsystem_id = te[7]
					detail_code = te[8]
					break

		if category == 'all' and station == 'all':
			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break			

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]

				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1
					
				# message_key here is for acknowledgement purposes later
				#warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')

		elif category == 'all' and station != 'all':
			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where station_id = %s and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [station,limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''


				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')

		elif category == 'transformer' and assetName != None:
			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like 'transformer%%' and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [station_id,system_id,subsystem_id,detail_code,limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)	

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')

		elif category == 'transformer':
			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like 'transformer%%' and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')

		elif category == 'switchgear' and assetName != None:

			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like '%%switchgear%%' and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [station_id,system_id,subsystem_id,detail_code,limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]

				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''	
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')	

		elif category == 'switchgear' and whichType != None:
			# Show list of detected and predicted faults warning_message (#10)
			responseList = []

			if whichType.find(',') != -1:
				typeInfo = whichType.split(",")
				type1 = typeInfo[0]
				type2 = typeInfo[1]
				
				if type1 == '750vdc':
					type1=type1[0:3]
				else:			
					type1=type1[0:2]

				if type2 == '750vdc':
					type2=type2[0:3]
				else: 
					type2=type2[0:2]
		
				responseList = []

				queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where (subsystem_id = %s or subsystem_id = %s) and component like 'switchgear%%' and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
				parameter = [type1,type2,limit]
				resultList = queryPostgre(queryStatement,parameter)

			else:
				whichType=whichType[0:2]

				queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like '%%switchgear%%' and subsystem_id = %s and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC limit %s"
				parameter = [whichType,limit]
				resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]

				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')	

		elif category == 'switchgear':
			# Title: List predicted and detected warnings (#6)
			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like 'switchgear%%' and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				# This is for predictive warning_message
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]

				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''	
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''				

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')	

		elif category == 'double-converter' and assetName != None:

			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like '%%doubleconverter%%' and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [station_id,system_id,subsystem_id,detail_code,limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''	
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')	

		elif category == 'double-converter':
			
			responseList = []
	
			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like 'doubleconverter%%' and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				# This is for predictive warning_message
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''	
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''				

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')	

		elif category == 'rectifier' and assetName != None:

			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like '%%rectifier%%' and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [station_id,system_id,subsystem_id,detail_code,limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''	
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')
			
		elif category == 'rectifier':
			
			responseList = []
	
			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like 'rectifier%%' and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				# This is for predictive warning_message
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''		
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''			

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')	

		elif category == 'inverter' and assetName != None:

			responseList = []

			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like '%%inverter%%' and station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [station_id,system_id,subsystem_id,detail_code,limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''	
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')	

		elif category == 'inverter':
			
			responseList = []
	
			queryStatement = "select TO_CHAR(record_time,'dd-Mon-yy HH24:MI:SS'),TO_CHAR(record_time,'yyyyMMddHHmmss'),component,CONCAT(station_id,'/',system_id,'/',subsystem_id,'/',detail_code),station_id,system_id,subsystem_id,detail_code,warning_code,status,is_ack,mask,notes from "+config.WARNING_LOGS+" where component like 'inverter%%' and not (status = '1' and is_ack = '1') and not (mask = true and is_ack='1') order by record_time DESC LIMIT %s"
			parameter = [limit]
			resultList = queryPostgre(queryStatement,parameter)

			# Loop through the entire resultset, processing the data accordingly
			for thisRow in resultList:
				# This is for predictive warning_message
				warningDict = {"message_key":"","created_at":"","station_code":"","equipment_code":"","equipment_type":"","equipment_category":"","severity":"","status":"","is_ack":"","description":"","recommended_action":"","notes":""}
				warningDict['created_at'] = thisRow[0]
				warningDict['notes'] = thisRow[12]

				for te in stationList:
					if te[0] == thisRow[4]:
						warningDict['station_code'] = te[1]
						break

				for te in equipmentList:
					if te[5] == thisRow[4] and te[6] == thisRow[5] and te[7] == thisRow[6] and te[8] == thisRow[7]:
						warningDict['equipment_code'] = te[1]
						warningDict['equipment_type'] = te[2]
						warningDict['equipment_category'] = te[0]
						break

				if thisRow[11] == 1:
					warningDict['status'] = 1
				else:
					warningDict['status'] = thisRow[9]
					
				if thisRow[10] == '0':
					warningDict['is_ack'] = 0
				elif thisRow[10] == '1':
					warningDict['is_ack'] = 1

				# message_key here is for acknowledgement purposes later
				# warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[1])+''		
				warningDict['message_key'] = str(thisRow[2])+'|'+str(thisRow[3])+'|'+str(thisRow[8])+'|'+str(thisRow[9])+''			

				# Loop the warning_def static list
				warningDict['description'] = 'UNKNOWN CODE'
				for te in warningDefList:
					if te[0] == thisRow[8]:
						warningDict['description'] = te[1]
						warningDict['recommended_action'] = te[3]
						warningDict['severity'] = te[2]
						break

				responseList.append(warningDict)

			resultJSON = processJSON(responseList)

			return processResponse(resultJSON,'OK')	
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')

	def put (self, request, *args, **kwargs):
		messageKey = self.request.query_params.get('message_key')
		remarks = self.request.query_params.get('remarks')
		notes = self.request.query_params.get('notes')
		acknowledge = self.request.query_params.get('acknowledge')
		editNotes = self.request.query_params.get('editNotes')
		operator_id = self.request.query_params.get('operator_id')
		signature  = self.request.query_params.get('signature')
		timestamp = self.request.query_params.get('timestamp')
		
		#if timestamp ==None:
			# Temp fix for mispelled timestamp
			#timestamp = self.request.query_params.get('timestmap')

		if acknowledge == 'true':
			# Title: Acknowledge a warning_message with a given message_key (#7,#11)
			
			# Delimit messageKey to get the 3 values: componentType,equipment_id,creation_time
			delimitedValues = messageKey.split("|")
			componentType = delimitedValues[0]	
			equipment_id = delimitedValues[1]
			#creation_time = delimitedValues[2]
			warning_code = delimitedValues[2]
			status = delimitedValues[3]

			# Delimit equipment_id further to get the 4 values: 
			delimitedValues = equipment_id.split("/")
			station_id = delimitedValues[0]
			system_id = delimitedValues[1]
			subsystem_id = delimitedValues[2]
			detail_code = delimitedValues[3]

			# Now have all the relevant identifiers: creationTime,componentType,station_id,system_id,subsystem_id,detail_code

			# First check whether the operator_id and password is correct

			queryStatement = "select operator_password from "+config.OPERATOR_ID_PASSWORD+" where operator_id = %s order by record_time DESC LIMIT 1"
			parameter = [operator_id]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				passwordInfo = resultList[0]
				operatorPassword = passwordInfo[0]
			else:
				operatorPassword = 'NO PASSWORD'

			thisSignature=performEncodedHash(operatorPassword,""+messageKey+"."+operator_id+"."+timestamp+"."+remarks+"")

			if thisSignature == signature:
				# If password is correct, after signature hash comparison

				# Do a query to check whether the warning_message is acknowledged status, check by latest entry
				# queryStatement = "select record_time,station_id,system_id,subsystem_id,detail_code,component,warning_code,is_ack from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component = %s and TO_CHAR(record_time,'yyyyMMddHHmmss') = %s and is_ack = '0' order by record_time DESC LIMIT 1"
				# parameter = [station_id,system_id,subsystem_id,detail_code,componentType,creation_time]

				queryStatement = "select record_time,station_id,system_id,subsystem_id,detail_code,component,warning_code,is_ack from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component = %s and warning_code = %s and is_ack = '0' order by record_time DESC LIMIT 1"
				parameter = [station_id,system_id,subsystem_id,detail_code,componentType,warning_code]
				resultList = queryPostgre(queryStatement,parameter)

				if len(resultList) > 0:
					# Query result should only have one element, one row  
					resultRow = resultList[0]

					#updatePostgre("update "+config.WARNING_LOGS+" set is_ack = '1', operator_id = '"+operator_id+"', ack_time = CURRENT_TIMESTAMP, remarks = '"+remarks+"' where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' and component = '"+componentType+"' and TO_CHAR(record_time,'yyyyMMddHHmmss') = '"+creation_time+"'")	
					#updateStatement = "update "+config.WARNING_LOGS+" set is_ack = '1', operator_id = %s, ack_time = CURRENT_TIMESTAMP, remarks = %s where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component = %s and TO_CHAR(record_time,'yyyyMMddHHmmss') = %s"
					#parameter = [operator_id,remarks,station_id,system_id,subsystem_id,detail_code,componentType,creation_time]

					updateStatement = "update "+config.WARNING_LOGS+" set is_ack = '1', operator_id = %s, ack_time = CURRENT_TIMESTAMP, remarks = %s where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component = %s and warning_code = %s"
					parameter = [operator_id,remarks,station_id,system_id,subsystem_id,detail_code,componentType,warning_code]
					updatePostgre(updateStatement,parameter)

					return processResponse(None,'INSERTED')
				else:
					return processResponse(None,'NOT INSERTED')

			else:
				responseDict = {"error_code":"401","error_message":"Your ID and the password entered did not match our records. Please try again."}
				resultJSON = processJSON(responseDict)
				return processResponse(resultJSON,'UNAUTHORIZED')

		elif editNotes == 'true':

			# Delimit messageKey to get the 3 values: componentType,equipment_id,creation_time
			delimitedValues = messageKey.split("|")
			componentType = delimitedValues[0]	
			equipment_id = delimitedValues[1]
			#creation_time = delimitedValues[2]
			warning_code = delimitedValues[2]
			status = delimitedValues[3]

			# Delimit equipment_id further to get the 4 values: 
			delimitedValues = equipment_id.split("/")
			station_id = delimitedValues[0]
			system_id = delimitedValues[1]
			subsystem_id = delimitedValues[2]
			detail_code = delimitedValues[3]

			# Now have all the relevant identifiers: creationTime,componentType,station_id,system_id,subsystem_id,detail_code

			# First check whether the operator_id and password is correct

			queryStatement = "select operator_password from "+config.OPERATOR_ID_PASSWORD+" where operator_id = %s order by record_time DESC LIMIT 1"
			parameter = [operator_id]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				passwordInfo = resultList[0]
				operatorPassword = passwordInfo[0]
			else:
				operatorPassword = 'NO PASSWORD'

			thisSignature=performEncodedHash(operatorPassword,""+messageKey+"."+operator_id+"."+timestamp+"."+notes+"")

			if thisSignature == signature:

				updateStatement = "update "+config.WARNING_LOGS+" set notes = %s, operator_id = %s where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component = %s and warning_code = %s and status = %s"
				parameter = [notes,operator_id,station_id,system_id,subsystem_id,detail_code,componentType,warning_code,status]
				updatePostgre(updateStatement,parameter)

				return processResponse(None,'INSERTED')

			else:
				return processResponse(None,'NOT INSERTED')

		else:
			return processResponse(None,'NOT FOUND')


