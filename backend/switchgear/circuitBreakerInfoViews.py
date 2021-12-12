
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

class CircuitBreakerInfoView(APIView):

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

			queryStatement = "select min_count,max_count,equipment_type from "+config.SWITCHGEAR_RANGE+""
			parameter = []
			swRangeList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def put (self, request, *args, **kwargs):
		assetName = self.request.query_params.get('equipment_code')
		is_pm_done = self.request.query_params.get('is_pm_done')
		is_service_done = self.request.query_params.get('is_service_done')
		whichType = self.request.query_params.get('type')
		new_val = self.request.query_params.get('new_val')
		remarks = self.request.query_params.get('remarks')
		operator_id = self.request.query_params.get('operator_id')
		signature  = self.request.query_params.get('signature')
		timestamp = self.request.query_params.get('timestamp')

		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None
		
		queryStatement = "select pm_count,service_count,trip_count,equipment_type from "+config.SWITCHGEAR_THRESHOLD+""
		parameter = []
		swThresholdList = queryPostgre(queryStatement,parameter)

		# find the equipment info given the asset_name
		for te in equipmentList:
			if te[1] == assetName:
				station_id = te[5]
				system_id = te[6]
				subsystem_id = te[7]
				detail_code = te[8]
				equipment_type = te[3]
				break

		for te in swThresholdList:
			if te[3] == equipment_type:
				pm_count = te[0]
				service_count = te[1]
				break

		##if whichType == 'pm-ack' and is_pm_done == 'true':
		if whichType == 'pm-ack':
			# Title: Acknowledge PM action (#12)
			# API call for PM(Preventive Maintenance)

			# First check whether the operator_id and password is correct
			queryStatement = "select operator_password from "+config.OPERATOR_ID_PASSWORD+" where operator_id = %s order by record_time DESC LIMIT 1"
			parameter = [operator_id]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				passwordInfo = resultList[0]
				operatorPassword = passwordInfo[0]
			else:
				operatorPassword = 'NO PASSWORD'				
			#remarks="a"		
			thisSignature=performEncodedHash(operatorPassword,""+assetName+"."+operator_id+"."+timestamp+"."+remarks+"")
			if thisSignature == signature:
				# Query for the latest record for this entity_name(this is the switchgear_code)		

				queryStatement = "select record_time, counter, counter_last_update,counter_last_remark,counter_update_by,all_time_counter, all_time_counter_last_update, all_time_counter_last_remark,all_time_counter_update_by, last_pm_at, is_pm_done, is_pm_ready, last_service_at, is_service_done, is_service_ready,iteration_no from "+config.OPERATING_COUNT+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
				parameter = [station_id,system_id,subsystem_id,detail_code]
				resultList = queryPostgre(queryStatement,parameter)

				if len(resultList) > 0:	
					#resultRow = resultList[0]
					#updatePostgre("update "+config.OPERATING_COUNT+" set is_pm_done = 'TRUE',is_pm_ready = 'FALSE',last_pm_at = CURRENT_TIMESTAMP,record_time = CURRENT_TIMESTAMP where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' ")
					updateStatement = "update "+config.OPERATING_COUNT+" set is_pm_done = 'TRUE',is_pm_ready = 'FALSE',last_pm_at = CURRENT_TIMESTAMP,record_time = CURRENT_TIMESTAMP where station_id = %s and system_id = %s and subsystem_id = %s and detail_code = %s "
					parameter = [station_id,system_id,subsystem_id,detail_code]
					updatePostgre(updateStatement,parameter)

					#updatePostgre("update "+config.WARNING_LOGS+" set mask = true where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' and component = 'switchgear:count' and status ='0' ")	
					updateStatement = "update "+config.WARNING_LOGS+" set mask = true, status = '1' where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component = 'switchgear:count' and status ='0' "
					parameter = [station_id,system_id,subsystem_id,detail_code]
					updatePostgre(updateStatement,parameter)

					return processResponse(None,'INSERTED')
				else:
					return processResponse(None,'NOT INSERTED')
			else:
				# If password is wrong, return an error status code 401:UNAUTHORIZED
				responseDict = {"error_code":"401","error_message":"Your ID and the password entered did not match our records. Please try again."}
				resultJSON = processJSON(responseDict)
				return processResponse(resultJSON,'UNAUTHORIZED')	 

		elif whichType == 'service-ack':
		##elif whichType == 'service-ack' and is_service_done == 'true':
			# Acknowledge servicing action (#13)
			# API call for service completion

			# First check whether the operator_id and password is correct
			queryStatement = "select operator_password from "+config.OPERATOR_ID_PASSWORD+" where operator_id = %s order by record_time DESC LIMIT 1"
			parameter = [operator_id]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				passwordInfo = resultList[0]
				operatorPassword = passwordInfo[0]
			else:
				operatorPassword = 'NO PASSWORD'

			thisSignature=performEncodedHash(operatorPassword,""+assetName+"."+operator_id+"."+timestamp+"."+remarks+"")

			if thisSignature == signature:

				# Query for the latest record for this entity_name(this is the switchgear_code)	

				queryStatement = "select record_time, counter, counter_last_update,counter_last_remark,counter_update_by,all_time_counter,all_time_counter_last_update,all_time_counter_last_remark,all_time_counter_update_by,last_pm_at, is_pm_done, is_pm_ready, last_service_at, is_service_done, is_service_ready,iteration_no from "+config.OPERATING_COUNT+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
				parameter = [station_id,system_id,subsystem_id,detail_code]
				resultList = queryPostgre(queryStatement,parameter)

				if len(resultList) > 0:	
					resultRow = resultList[0]
					# Patch: Number of iterations is redundant, so will be commented off for now
					#numberOfIterations = str(int(resultRow[15]) + 1)

					#updatePostgre("update "+config.OPERATING_COUNT+" set is_pm_done = 'FALSE',is_pm_ready = 'FALSE',is_service_done = 'FALSE',is_service_ready = 'FALSE',last_service_at = CURRENT_TIMESTAMP,record_time = CURRENT_TIMESTAMP, counter = 0, iteration_no = "+numberOfIterations+" where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' ")	
					updateStatement = "update "+config.OPERATING_COUNT+" set is_pm_done = 'FALSE',is_pm_ready = 'FALSE',is_service_ready = 'FALSE',last_service_at = CURRENT_TIMESTAMP,record_time = CURRENT_TIMESTAMP, counter = 0 where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s "
					parameter = [station_id,system_id,subsystem_id,detail_code]
					updatePostgre(updateStatement,parameter)

					#updatePostgre("update "+config.WARNING_LOGS+" set mask = true where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' and component = 'switchgear:count' and status ='0' ")	
					updateStatement = "update "+config.WARNING_LOGS+" set mask = true, status = '1' where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component = 'switchgear:count' and status ='0' "
					parameter = [station_id,system_id,subsystem_id,detail_code]
					updatePostgre(updateStatement,parameter)

					return processResponse(None,'INSERTED')

				else:
					return processResponse(None,'NOT INSERTED')
			else:
				# If password is wrong, return an error status code 401:UNAUTHORIZED
				responseDict = {"error_code":"401","error_message":"Your ID and the password entered did not match our records. Please try again."}
				resultJSON = processJSON(responseDict)
				return processResponse(resultJSON,'UNAUTHORIZED')			
		
		elif whichType == 'update-counter':
			# Title: Update circuit breaker counter value (#14)
			# If there is value for new_val and remarks, meaning update is needed for breaker count

			# First check whether the operator_id and password is correct
			queryStatement = "select operator_password from "+config.OPERATOR_ID_PASSWORD+" where operator_id = %s order by record_time DESC LIMIT 1"
			parameter = [operator_id]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				passwordInfo = resultList[0]
				operatorPassword = passwordInfo[0]
			else:
				operatorPassword = 'NO PASSWORD'		

			thisSignature=performEncodedHash(operatorPassword,""+assetName+"."+operator_id+"."+timestamp+"."+new_val+"."+remarks+"")

			if thisSignature == signature:
				# If password is correct, proceed to update the breaker count

				# Query for the latest record for this entity_name(this is the switchgear_code)

				queryStatement = "select record_time, counter, counter_last_update,counter_last_remark,counter_update_by,all_time_counter, all_time_counter_last_update,all_time_counter_last_remark,all_time_counter_update_by,last_pm_at, is_pm_done, is_pm_ready, last_service_at, is_service_done, is_service_ready,iteration_no from "+config.OPERATING_COUNT+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
				parameter = [station_id,system_id,subsystem_id,detail_code]
				resultList = queryPostgre(queryStatement,parameter)

				if len(resultList) > 0:		
					resultRow = resultList[0]	

					# However, for this new record, three conditions
					if float(new_val) < pm_count:
						# First condition: new value is less than PM count threshold, set is_pm_ready to false, set is_service_ready to false, set is_pm_done and is_service_done to false	
						#updatePostgre("update "+config.OPERATING_COUNT+" set is_pm_ready = 'FALSE',is_service_ready = 'FALSE',is_pm_done='FALSE',is_service_done='FALSE',record_time = CURRENT_TIMESTAMP,counter = '"+new_val+"', counter_last_remark = '"+remarks+"',counter_last_update = CURRENT_TIMESTAMP, counter_update_by = '"+operator_id+"' where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' ")	
						updateStatement = "update "+config.OPERATING_COUNT+" set is_pm_ready = 'FALSE',is_service_ready = 'FALSE',is_pm_done='FALSE',is_service_done='FALSE',record_time = CURRENT_TIMESTAMP,counter = %s, counter_last_remark = %s,counter_last_update = CURRENT_TIMESTAMP, counter_update_by = %s where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s "
						parameter = [new_val,remarks,operator_id,station_id,system_id,subsystem_id,detail_code]
						updatePostgre(updateStatement,parameter)

					elif float(new_val) >= pm_count and float(new_val) < service_count:
						# Second condition: new value is more or equal to PM count threshold but less than service count threshold, set is_pm_ready to true, set is_service_ready to false
						#updatePostgre("update "+config.OPERATING_COUNT+" set is_pm_ready = 'TRUE',is_service_ready = 'FALSE',record_time = CURRENT_TIMESTAMP,counter = '"+new_val+"', counter_last_remark = '"+remarks+"',counter_last_update = CURRENT_TIMESTAMP, counter_update_by = '"+operator_id+"' where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' ")
						updateStatement = "update "+config.OPERATING_COUNT+" set is_pm_ready = 'TRUE',is_service_ready = 'FALSE',record_time = CURRENT_TIMESTAMP,counter = %s, counter_last_remark = %s,counter_last_update = CURRENT_TIMESTAMP, counter_update_by = %s where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s "
						parameter = [new_val,remarks,operator_id,station_id,system_id,subsystem_id,detail_code]
						updatePostgre(updateStatement,parameter)

					elif float(new_val) >= service_count:
						# Third condition: new value is more or equal to service count threshold, set both is_pm_ready and is_service_ready to true
						#updatePostgre("update "+config.OPERATING_COUNT+" set is_pm_ready = 'TRUE',is_service_ready = 'TRUE',record_time = CURRENT_TIMESTAMP,counter = '"+new_val+"', counter_last_remark = '"+remarks+"',counter_last_update = CURRENT_TIMESTAMP, counter_update_by = '"+operator_id+"' where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' ")
						updateStatement = "update "+config.OPERATING_COUNT+" set is_pm_ready = 'TRUE',is_service_ready = 'TRUE', record_time = CURRENT_TIMESTAMP,counter = %s, counter_last_remark = %s,counter_last_update = CURRENT_TIMESTAMP, counter_update_by = %s where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s "
						parameter = [new_val,remarks,operator_id,station_id,system_id,subsystem_id,detail_code]
						updatePostgre(updateStatement,parameter)

					#updatePostgre("update "+config.WARNING_LOGS+" set mask = false where station_id = '"+station_id+"' and system_id = '"+system_id+"' and subsystem_id= '"+subsystem_id+"' and detail_code = '"+detail_code+"' and component = 'switchgear:count' and status ='0' ")
					updateStatement = "update "+config.WARNING_LOGS+" set mask = false where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component = 'switchgear:count' and status ='0' "
					parameter = [station_id,system_id,subsystem_id,detail_code]
					updatePostgre(updateStatement,parameter)

					return processResponse(None,'INSERTED')
				else:
					return processResponse(None,'NOT INSERTED')
			else:
				# If password is wrong, return an error status code 401:UNAUTHORIZED
				responseDict = {"error_code":"401","error_message":"Your ID and the password entered did not match our records. Please try again."}
				resultJSON = processJSON(responseDict)
				return processResponse(resultJSON,'UNAUTHORIZED')
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')

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

		# Title: Show operating counter information of individual switchgear (#8)
		dataset = {"switchgear_code":"","current_count":"","trip_count":"","min_count":"","max_count":"","pm_count":"","service_count":"","status":"","last_pm_at":"","last_service_at":"","is_service_done":"","is_pm_done":"","iteration_no":""}

		queryStatement = "select pm_count,service_count,trip_count,equipment_type from "+config.SWITCHGEAR_THRESHOLD+""
		parameter = []
		swThresholdList = queryPostgre(queryStatement,parameter)
		
		# Populate the data from the static table
		for te in swThresholdList:
			if te[3] == equipment_type:
				dataset['pm_count']=te[0]
				dataset['service_count']=te[1]
				break

		# Patch for flexible range
		#for te in swRangeList:
		#	if te[2] == equipment_type:
		#		dataset['min_count']=te[0]
		#		dataset['max_count']=te[1]
		#		break

		# There is no negative value for counter value so the min_count should start at 0
		dataset['min_count']= 0
		# The max_count should be more than the service_count
		dataset['max_count'] = round(int(dataset['service_count']) + (int(dataset['service_count'])*0.3))
		dataset['switchgear_code']=assetName

		queryStatement = "select record_time, counter, counter_last_update,counter_last_remark,all_time_counter, all_time_counter_last_update,all_time_counter_last_remark,trip,to_char(last_pm_at,'dd-Mon-yy HH24:mm:ss'), is_pm_done, is_pm_ready,to_char(last_service_at,'dd-Mon-yy HH24:mm:ss'), is_service_done, is_service_ready,iteration_no from "+config.OPERATING_COUNT+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		if len(resultList) > 0:		
			lastestOutput = resultList[0]

			currentCount = lastestOutput[1]

			# Populate the data from the latest value		
			dataset['last_pm_at']=lastestOutput[8]
			dataset['last_service_at']=lastestOutput[11]
			#dataset['is_service_done']=lastestOutput[12]
			#dataset['is_pm_done']=lastestOutput[9]

			if lastestOutput[12] == 0:
				dataset['is_service_done'] = 0
			elif lastestOutput[12] == 1:
				dataset['is_service_done'] = 1

			if lastestOutput[9] == 0:
				dataset['is_pm_done'] = 0
			elif lastestOutput[9] == 1:
				dataset['is_pm_done'] = 1
			
			dataset['trip_count']=lastestOutput[7]
			dataset['current_count'] = currentCount

			if currentCount < dataset['pm_count']:
				dataset['status'] = 'healthy'
				dataset['is_pm_ready']= 0
				dataset['is_service_ready']= 0
			elif currentCount >= dataset['pm_count'] and currentCount < dataset['service_count']:
				dataset['status'] = 'warning'
				dataset['is_pm_ready']= 1
				dataset['is_service_ready']= 0
			elif currentCount >= dataset['service_count']:
				dataset['status'] = 'warning'
				dataset['is_pm_ready']= 0
				dataset['is_service_ready']= 1

			# However, if is_pm_done is true and is_service_ready is false
			if dataset['is_pm_done'] == 1 and dataset['is_service_ready'] == 0:
				dataset['status'] = 'healthy'

		resultJSON = processJSON(dataset)

		return processResponse(resultJSON,'OK')


	def post (self, request, *args, **kwargs):
		# Use this to test try kafka insert
		"""
		now = datetime.datetime.utcnow()
		element = {"min_count":"1000","max_count":"200000","pm_count":"100000","service_count":"1000","trip_count":"100","ACK":"TRUE","timestamp":""}
		element['timestamp'] = ""+str(now.month)+"-"+str(now.day)+"-"+str(now.year)+" "+str(now.hour)+":"+str(now.minute)+":"+str(now.second)+" +00:00"
		messageList = []
		messageList.append(element)
		insertKafka(config.SOC_TEST,messageList)
		"""

		dt_obj = datetime.strptime('20-12-2016 09:38:42','%d-%m-%Y %H:%M:%S')
		print('ORIGINAL:')
		print(dt_obj)
		millisec = dt_obj.timestamp() * 1000
		print('In millisec:')
		print(millisec)
		print('Back to datetime:')
		print(datetime.datetime.fromtimestamp(millisec/1000.0))
		
		return processResponse(None,'INSERTED')		






