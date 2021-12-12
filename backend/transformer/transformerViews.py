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

from backend.utilities.druidQuery import queryDruid
from backend.utilities.postgreQuery import queryPostgre
from backend.utilities.postgreUpdate import updatePostgre
#from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnJSON import processJSON
from backend.utilities.returnResponse import processResponse

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Create your views here.

class TransformerView(APIView):
	#print('Getting Transformers equipment info')

	def get (self, request, *args, **kwargs):
		# Title:List of transformers

		responseList = []
		twentytwoList = []

		queryStatement = "select equipment_category,equipment_type,acronym_asset_name,equipment_type_name from "+config.EQUIPMENT_INFO+" where equipment = 'transformer' order by acronym_asset_name"
		parameter = []
		resultList = queryPostgre(queryStatement,parameter)

		for thisRow in resultList:
			transformerDict = {"category":"","type":"","item_code":"","item_name":""}
			transformerDict['category'] = thisRow[0]
			transformerDict['type'] = thisRow[1]
			transformerDict['item_code'] = thisRow[2]
			transformerDict['item_name'] = thisRow[3]

			if thisRow[0] == config.TRANSFORMER_66KV:
				responseList.append(transformerDict)
			elif thisRow[0] == config.TRANSFORMER_22KV:
				twentytwoList.append(transformerDict)

		responseList.extend(twentytwoList)
		resultJSON = processJSON(responseList)

		return processResponse(resultJSON,'OK')

