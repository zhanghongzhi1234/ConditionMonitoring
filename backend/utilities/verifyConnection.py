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

def checkConnection():
	connection = None
	try:

		connection = psycopg2.connect(user = config.POSTGRE_USER,
							password = config.POSTGRE_PASSWORD,
							host = config.POSTGRE_HOST,
							port = config.POSTGRE_PORT,
							database = config.POSTGRE_DATABASE)
#	except (Exception, psycopg2.Error) as error:
#		return 'Error while connecting to PostgreSQL'
	except:
		return 'Errors encountered!'
	else:
		return 200
	finally:
		# closing database connection
		if(connection):
			connection.close()


	
