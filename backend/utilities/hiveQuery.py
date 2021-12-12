from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status

import requests
import json
import datetime
import calendar

from pyhive import hive
#import sasl

import importlib.util

# To be removed after test
#==============================================
#import puretransport
#==============================================

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# This is the standard non-parameterized query (used for testing purposes)
# Likely vulnerable to SQL injection
# Therefore, use the parameterized query below
def queryHiveTEST(dataSQL):
	resultset = None
	connection = None
	try:

		connection = hive.Connection(host = config.HIVE_HOST,
							port = config.HIVE_PORT,
							username = config.HIVE_USER,
							password = config.HIVE_PASSWORD,
							database = config.HIVE_DATABASE,
							auth = 'CUSTOM')

		cursor = connection.cursor()
		cursor.execute(dataSQL)
		
		resultset = cursor.fetchall()

	except Exception as e:
		print("Error while connecting to Hive")
		print(e)
	finally:
		# closing HiveServer2 connection
		if(connection):
			cursor.close()
			connection.close()

	return resultset

# Parameterized query to prevent SQL injection
def queryHive(dataSQL,parameterList):
	# parametersList is a python list of parameters
	# Need to convert to python tuple
	#parameter = tuple(i for i in parameterList)
	# or alternatively 
	parameter = tuple(parameterList)

	resultset = None
	connection = None
	try:

		connection = hive.Connection(host = config.HIVE_HOST,
							port = config.HIVE_PORT,
							username = config.HIVE_USER,
							password = config.HIVE_PASSWORD,
							database = config.HIVE_DATABASE,
							auth = 'CUSTOM')

		cursor = connection.cursor()
		cursor.execute(dataSQL,parameter)
		
		resultset = cursor.fetchall()

	except Exception as e:
		print("Error while connecting to Hive")
		print(e)
	finally:
		# closing HiveServer2 connection
		if(connection):
			cursor.close()
			connection.close()

	return resultset





	



