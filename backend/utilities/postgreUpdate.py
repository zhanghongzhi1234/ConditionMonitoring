from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status

import requests
import json
import datetime
import calendar

import psycopg2

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# This is the standard non-parameterized update query (used for testing purposes)
# Likely vulnerable to SQL injection
# Therefore, use the parameterized query below
def updatePostgreTEST(dataSQL):
	resultset = None
	connection = None
	try:

		connection = psycopg2.connect(user = config.POSTGRE_USER,
							password = config.POSTGRE_PASSWORD,
							host = config.POSTGRE_HOST,
							port = config.POSTGRE_PORT,
							database = config.POSTGRE_DATABASE)

		cursor = connection.cursor()
		cursor.execute(dataSQL)
		
		connection.commit()

	except (Exception, psycopg2.Error) as error:
		print("Error while connecting to PostgreSQL",error)
		return 'FAIL'
	finally:
		# closing database connection
		if(connection):
			cursor.close()
			connection.close()
			#print("PostgreSQL connection is closed")


	return 'SUCCESS'

# Parameterized update query to prevent SQL injection
def updatePostgre(dataSQL,parameterList):
	# parametersList is a python list of parameters
	# Need to convert to python tuple
	#parameter = tuple(i for i in parameterList)
	# or alternatively 
	parameter = tuple(parameterList)

	resultset = None
	connection = None
	try:

		connection = psycopg2.connect(user = config.POSTGRE_USER,
							password = config.POSTGRE_PASSWORD,
							host = config.POSTGRE_HOST,
							port = config.POSTGRE_PORT,
							database = config.POSTGRE_DATABASE)

		cursor = connection.cursor()
		cursor.execute(dataSQL,parameter)
		
		connection.commit()

	except (Exception, psycopg2.Error) as error:
		print("Error while connecting to PostgreSQL",error)
		return 'FAIL'
	finally:
		# closing database connection
		if(connection):
			cursor.close()
			connection.close()
			#print("PostgreSQL connection is closed")


	return 'SUCCESS'





	



