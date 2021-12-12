
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
from backend.utilities.returnResponse import processResponse
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Create your views here.

class StationView(APIView):

	# Declare the static class variables
	global stationList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here
			queryStatement = "select station_sequence,station_id,station_name,station_acronym from "+config.STATION_INFO+""
			parameter = []
			stationList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		# Title:List station information

		responseDict = {
				"dataset":[]
					}
		
		# Find the warning counts for each station
		queryStatement = "select station_id,count(*) from "+config.WARNING_LOGS+" where status = '0' group by station_id"
		parameter = []
		stationCountList = queryPostgre(queryStatement,parameter)			
		
		# Find the lastest updated time
		queryStatement = "select t.station_id,t.record_time,TO_CHAR(t.record_time,'dd-MM-yyyy HH:mm:ss') from "+config.WARNING_LOGS+" t inner join (select station_id,MAX(record_time) as MaxDate from "+config.WARNING_LOGS+" group by station_id) tm on t.station_id = tm.station_id and t.record_time = tm.MaxDate where status = '0'"
		parameter = []
		stationTimeInfo = queryPostgre(queryStatement,parameter)	
		
		# Find the most severe status 
		queryStatement = "select kd.station,MAX(kd.severity) from (select wl.station_id as station,(select df.severity from "+config.WARNING_DEF+" df where df.warning_code = wl.warning_code) as severity from "+config.WARNING_LOGS+" wl where wl.status = '0') as kd group by station"
		parameter = []
		stationSeverityInfo = queryPostgre(queryStatement,parameter)			
		
		for thisRow in stationList:
			stationDict ={"station_id":"","station_code":"","station_name":"","alarm_count":"","last_update":"","status":""}
			stationDict['station_id'] = thisRow[0]
			stationDict['station_code'] = thisRow[3]
			stationDict['station_name'] = thisRow[2]
			
			now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
			
			# These are the default values
			stationDict['alarm_count'] = 0
			stationDict['last_update'] = ""+str(now.day)+"-"+str(now.month)+"-"+str(now.year)+" "+str(now.hour)+":"+str(now.minute)+":"+str(now.second)+""
			stationDict['status'] = 0	
			
			# These are the updated values
			for te in stationCountList:
				if te[0] == thisRow[1]:
					stationDict['alarm_count'] = te[1]						
					break
					
			for te in stationSeverityInfo:
				if te[0] == thisRow[1]:
					stationDict['status'] = te[1]		
					break
					
			for te in stationTimeInfo:
				if te[0] == thisRow[1]:
					stationDict['last_update'] = te[2]		
					break

			responseDict['dataset'].append(stationDict)

		resultJSON = processJSON(responseDict)

		return processResponse(resultJSON,'OK')

