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

class AuthenticationView(APIView):
	
	def post (self, request, *args, **kwargs):
		operator_id = self.request.query_params.get('operator_id')
		timestamp = self.request.query_params.get('timestamp')
		random_seed = self.request.query_params.get('random_seed')
		signature = self.request.query_params.get('signature')

		if operator_id == None or timestamp == None or random_seed == None or signature == None:
			return processResponse(None,'INVALID PARAMETER')

		# First check whether the operator_id and password is correct
		queryStatement = "select operator_password from "+config.OPERATOR_ID_PASSWORD+" where operator_id = %s order by record_time DESC LIMIT 1"
		parameter = [operator_id]
		resultList = queryPostgre(queryStatement,parameter)

		if len(resultList) > 0:
			passwordInfo = resultList[0]
			operatorPassword = passwordInfo[0]
		else:
			operatorPassword = 'NO PASSWORD'

		thisSignature=performEncodedHash(operatorPassword,""+operator_id+"."+timestamp+"."+random_seed+"")
		if thisSignature == signature:
			responseDict = {"status_code":"200","message":"User authenticated"}
			resultJSON = processJSON(responseDict)
			return processResponse(resultJSON,'OK')

		else:
			# If password is wrong, return an error status code 401:UNAUTHORIZED
			responseDict = {"error_code":"401","error_message":"Your ID and the password entered did not match our records. Please try again."}
			resultJSON = processJSON(responseDict)
			return processResponse(resultJSON,'UNAUTHORIZED')
		
		return processResponse(None,'INSERTED')		




