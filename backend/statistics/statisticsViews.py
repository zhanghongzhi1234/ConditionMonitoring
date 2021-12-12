
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

# Create your views here.

class StatisticsView(APIView):

	# Declare the static class variables
	global warningDefList
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
		station = self.request.query_params.get('station')
		category = self.request.query_params.get('category')
		#day = self.request.query_params.get('day')
		periodicity = self.request.query_params.get('periodicity')

		# default day to be 0
		day = 0

		# Patch due to changes in requirement, station_acronym used instead for 'station'
		# Need to retrieve the correct station_id, using the given station_acronym
		for li in stationList:
			if station == li[1]:
				station = li[0]
				break

		# If there is no input of periodicity from the frontend, take the default periodicity to be monthly
		if periodicity == None:
			periodicity = 'monthly'

		if periodicity == 'weekly':
			day = '7'
		elif periodicity == 'fortnight':
			day = '14'
		elif periodicity == 'monthly':
			day = '30'
		elif periodicity == 'bi-monthly':
			day = '60'
		elif periodicity == 'half-yearly':
			day = '180'
		elif periodicity == 'yearly':
			day = '360'
					
		# Title:List statistics information by category
		
		# Create and define the response list, where all the equipment dicts will be inserted into
		responseList = []
		
		# Create and define the equipment dicts
		transformerDict = {
					"category_name":"Transformer",
					"history":[],
					"trend_indicator":"",
					"trend_in_percent":"",
					"total":"",
					"model":[]
				}

		switchgearDict = {
					"category_name":"Switchgear",
					"history":[],
					"trend_indicator":"",
					"trend_in_percent":"",
					"total":""
				}

		doubleconverterDict = {
					"category_name":"DConverter",
					"history":[],
					"trend_indicator":"",
					"trend_in_percent":"",
					"total":""
				}

		rectifierDict = {
					"category_name":"Rectifier",
					"history":[],
					"trend_indicator":"",
					"trend_in_percent":"",
					"total":""
				}

		inverterDict = {
					"category_name":"Inverter",
					"history":[],
					"trend_indicator":"",
					"trend_in_percent":"",
					"total":""
				}
		# Create the history list
		trHistoryList = []
		swHistoryList = []
		dcHistoryList = []
		rcHistoryList = []
		ivHistoryList = []

		# This is for the transformer model list 
		# Create and define the dict for each transformer severity type- Critical,Urgent,Major,Minor
		trModelList = []
		trCriticalDict = {"label":"Critical","alarm_count":""}
		trUrgentDict = {"label":"Urgent","alarm_count":""}
		trMajorDict = {"label":"Major","alarm_count":""}
		trMinorDict = {"label":"Minor","alarm_count":""}

		# This is for the switchgear model list 
		# Create and define the dict for each switchgear severity type- Critical,Urgent,Major,Minor
		swModelList = []
		swCriticalDict = {"label":"Critical","alarm_count":""}
		swUrgentDict = {"label":"Urgent","alarm_count":""}
		swMajorDict = {"label":"Major","alarm_count":""}
		swMinorDict = {"label":"Minor","alarm_count":""}
		
		# This is for the doubleconverter model list 
		# Create and define the dict for each doubleconverter severity type- 'Critical,Urgent,Major,Minor
		dcModelList = []
		dcCriticalDict = {"label":"Critical","alarm_count":""}
		dcUrgentDict = {"label":"Urgent","alarm_count":""}
		dcMajorDict = {"label":"Major","alarm_count":""}
		dcMinorDict = {"label":"Minor","alarm_count":""}

		# This is for the doubleconverter model list 
		# Create and define the dict for each doubleconverter severity type- 'Critical,Urgent,Major,Minor
		rcModelList = []
		rcCriticalDict = {"label":"Critical","alarm_count":""}
		rcUrgentDict = {"label":"Urgent","alarm_count":""}
		rcMajorDict = {"label":"Major","alarm_count":""}
		rcMinorDict = {"label":"Minor","alarm_count":""}

		# This is for the inverter model list 
		# Create and define the dict for each inverter severity type- 'Critical,Urgent,Major,Minor
		ivModelList = []
		ivCriticalDict = {"label":"Critical","alarm_count":""}
		ivUrgentDict = {"label":"Urgent","alarm_count":""}
		ivMajorDict = {"label":"Major","alarm_count":""}
		ivMinorDict = {"label":"Minor","alarm_count":""}

		# Create the total warning count for each severity type 
		# (Transformer) - Critical,Urgent,Major,Minor
		trCritical = 0
		trUrgent = 0
		trMajor = 0
		trMinor = 0

		# (Switchgear) - Critical,Urgent,Major,Minor
		swCritical = 0
		swUrgent = 0
		swMajor = 0
		swMinor = 0

		# (Doubleconverter) - Critical,Urgent,Major,Minor
		dcCritical = 0
		dcUrgent = 0
		dcMajor = 0
		dcMinor = 0

		# (Doubleconverter) - Critical,Urgent,Major,Minor
		rcCritical = 0
		rcUrgent = 0
		rcMajor = 0
		rcMinor = 0

		# (Inverter) - Critical,Urgent,Major,Minor
		ivCritical = 0
		ivUrgent = 0
		ivMajor = 0
		ivMinor = 0

		# Create the total warning count for each equipment
		trTotal = 0
		swTotal = 0
		dcTotal = 0
		rcTotal = 0
		ivTotal = 0

		# tr variables
		previousTRDate = None
		firstTRIteration = 'TRUE'
		trValue = 0

		# sw variables
		previousSWDate = None
		firstSWIteration = 'TRUE'
		swValue = 0

		# dc variables
		previousDCDate = None
		firstDCIteration = 'TRUE'
		dcValue = 0

		# rc variables
		previousRCDate = None
		firstRCIteration = 'TRUE'
		rcValue = 0

		# iv variables
		previousIVDate = None
		firstIVIteration = 'TRUE'
		ivValue = 0

		# Declaration of the severity. Default NA- Not applicable
		severity = 'NA'

		resultList = []

		# if category is ALL and station is not specified
		if category == 'all' and station == 'all':

			queryStatement = "select TO_CHAR(record_time,'Dy'),EXTRACT(day from record_time),EXTRACT(year from record_time),EXTRACT(month from record_time),component,COUNT(*),station_id,system_id,subsystem_id,detail_code,warning_code from "+config.WARNING_LOGS+" where record_time between CURRENT_TIMESTAMP - INTERVAL '"+day+" day' and CURRENT_TIMESTAMP group by EXTRACT(year from record_time),EXTRACT(month from record_time),EXTRACT(day from record_time),TO_CHAR(record_time,'Dy'),component,station_id,system_id,subsystem_id,detail_code,warning_code order by EXTRACT(year from record_time),EXTRACT(month from record_time),EXTRACT(day from record_time),TO_CHAR(record_time,'Dy'),component,station_id,system_id,subsystem_id,detail_code,warning_code "
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

		# When category is ALL and station is specified
		elif category == 'all' and station != 'all':

			queryStatement = "select TO_CHAR(record_time,'Dy'),EXTRACT(day from record_time),EXTRACT(year from record_time),EXTRACT(month from record_time),component,COUNT(*),station_id,system_id,subsystem_id,detail_code,warning_code from "+config.WARNING_LOGS+" where record_time between CURRENT_TIMESTAMP - INTERVAL '"+day+" day' and CURRENT_TIMESTAMP and station_id = %s group by EXTRACT(year from record_time),EXTRACT(month from record_time),EXTRACT(day from record_time),TO_CHAR(record_time,'Dy'),component,station_id,system_id,subsystem_id,detail_code,warning_code order by EXTRACT(year from record_time),EXTRACT(month from record_time),EXTRACT(day from record_time),TO_CHAR(record_time,'Dy'),component,station_id,system_id,subsystem_id,detail_code,warning_code "
			parameter = [station]
			resultList = queryPostgre(queryStatement,parameter)

		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')	

		# Loop through the entire resultset, processing the data accordingly
		for thisRow in resultList:
			# Check which equipment
			if thisRow[4].find('transformer') != -1:
				# If equipment is transformer

				# Check the severity from warning_def
				for te in warningDefList:
					if te[0] == thisRow[10] :
						severity = te[2]
						break

				if firstTRIteration == 'TRUE':
					firstTRIteration = 'FALSE'
					# Set the first previousTRDate value
					previousTRDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						trCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						trUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						trMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						trMinor += thisRow[5]	

					# Add to the current value
					trValue += thisRow[5]

					# Add to the total count
					trTotal += thisRow[5]

				elif thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2])) != previousTRDate:

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						trCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						trUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						trMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						trMinor += thisRow[5]	

					# Create a new trDict
					trDict = {"date":"","alarm_count":""}
					if trValue == 0:
						trvvalue = None
					trDict['date'] = previousTRDate
					trDict['alarm_count'] = trValue
					trHistoryList.append(trDict)

					# set the new previousTRDate
					previousTRDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Add to the total count
					trTotal += thisRow[5]

					# set the current value for this new date
					trValue = thisRow[5]
				else:
					# set the new previousTRDate
					previousTRDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						trCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						trUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						trMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						trMinor += thisRow[5]	
		
					# Add to the current trValue
					trValue += thisRow[5]
					# Add to the total count
					trTotal += thisRow[5]

			# Else if for other equipments
			elif thisRow[4].find('switchgear') != -1:
				# If equipment is switchgear

				# Check the severity from warning_def
				for te in warningDefList:
					if te[0] == thisRow[10] :
						severity = te[2]
						break

				if firstSWIteration == 'TRUE':
					firstSWIteration = 'FALSE'
					# Set the first previousSWDate value
					previousSWDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						swCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						swUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						swMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						swMinor += thisRow[5]	

					# Add to the current value
					swValue += thisRow[5]
					# Add to the total count
					swTotal += thisRow[5]

				elif thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2])) != previousSWDate:

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						swCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						swUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						swMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						swMinor += thisRow[5]	

					# Create a new swDict
					swDict = {"date":"","alarm_count":""}
					if swValue == 0:
						swValue = None
					swDict['date'] = previousSWDate
					swDict['alarm_count'] = swValue
					swHistoryList.append(swDict)

					# set the new previousSWDate
					previousSWDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Add to the total count
					swTotal += thisRow[5]
					# set the current value for this new date
					swValue = thisRow[5]
				else:
					# set the new previousSWDate
					previousSWDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						swCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						swUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						swMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						swMinor += thisRow[5]	
		
					# Add to the current swValue
					swValue += thisRow[5]
					# Add to the total count
					swTotal += thisRow[5]

			elif thisRow[4].find('doubleconverter') != -1:
				# If equipment is doubleconverter

				# Check the severity from warning_def
				for te in warningDefList:
					if te[0] == thisRow[10] :
						severity = te[2]
						break

				if firstDCIteration == 'TRUE':
					firstDCIteration = 'FALSE'
					# Set the first previousDCDate value
					previousDCDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						dcCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						dcUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						dcMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						dcMinor += thisRow[5]		

					# Add to the current value
					dcValue += thisRow[5]
					# Add to the total count
					dcTotal += thisRow[5]

				elif thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2])) != previousDCDate:

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						dcCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						dcUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						dcMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						dcMinor += thisRow[5]	

					# Create a new dcDict
					dcDict = {"date":"","alarm_count":""}
					if dcValue == 0:
						dcValue = None
					dcDict['date'] = previousDCDate
					dcDict['alarm_count'] = dcValue
					dcHistoryList.append(dcDict)

					# set the new previousDCDate
					previousDCDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Add to the total count
					dcTotal += thisRow[5]
					# set the current value for this new date
					dcValue = thisRow[5]
				else:
					# set the new previousDCDate
					previousDCDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						dcCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						dcUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						dcMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						dcMinor += thisRow[5]	

					# Add to the current dcValue
					dcValue += thisRow[5]
					# Add to the total count
					dcTotal += thisRow[5]

			elif thisRow[4].find('rectifier') != -1:
				# If equipment is rectifier

				# Check the severity from warning_def
				for te in warningDefList:
					if te[0] == thisRow[10] :
						severity = te[2]
						break

				if firstRCIteration == 'TRUE':
					firstRCIteration = 'FALSE'
					# Set the first previousDCDate value
					previousRCDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						rcCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						rcUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						rcMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						rcMinor += thisRow[5]		

					# Add to the current value
					rcValue += thisRow[5]
					# Add to the total count
					rcTotal += thisRow[5]

				elif thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2])) != previousRCDate:

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						rcCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						rcUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						rcMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						rcMinor += thisRow[5]	

					# Create a new rcDict
					rcDict = {"date":"","alarm_count":""}
					if rcValue == 0:
						rcValue = None
					rcDict['date'] = previousRCDate
					rcDict['alarm_count'] = rcValue
					rcHistoryList.append(rcDict)

					# set the new previousRCDate
					previousRCDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Add to the total count
					rcTotal += thisRow[5]
					# set the current value for this new date
					rcValue = thisRow[5]
				else:
					# set the new previousRCDate
					previousRCDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						rcCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						rcUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						rcMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						rcMinor += thisRow[5]	

					# Add to the current dcValue
					rcValue += thisRow[5]
					# Add to the total count
					rcTotal += thisRow[5]
			elif thisRow[4].find('inverter') != -1:
				# If equipment is inverter

				# Check the severity from warning_def
				for te in warningDefList:
					if te[0] == thisRow[10] :
						severity = te[2]
						break

				if firstIVIteration == 'TRUE':
					firstIVIteration = 'FALSE'
					# Set the first previousIVDate value
					previousIVDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						ivCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						ivUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						ivMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						ivMinor += thisRow[5]		

					# Add to the current value
					ivValue += thisRow[5]
					# Add to the total count
					ivTotal += thisRow[5]

				elif thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2])) != previousIVDate:

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						ivCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						ivUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						ivMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						ivMinor += thisRow[5]	

					# Create a new ivDict
					ivDict = {"date":"","alarm_count":""}
					if ivValue == 0:
						ivValue = None
					ivDict['date'] = previousIVDate
					ivDict['alarm_count'] = ivValue
					ivHistoryList.append(ivDict)

					# set the new previousIVDate
					previousIVDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Add to the total count
					ivTotal += thisRow[5]
					# set the current value for this new date
					ivValue = thisRow[5]
				else:
					# set the new previousIVDate
					previousIVDate = thisRow[0]+', '+str(int(thisRow[1]))+' '+calendar.month_abbr[int(thisRow[3])]+' '+str(int(thisRow[2]))

					# Need to handle the severity type [Critical,Urgent,Major,Minor]
					# Add to the correct severity type
					if severity == config.SEVERITY_CRITICAL:
						# Severity is critical
						ivCritical += thisRow[5]
					elif severity == config.SEVERITY_URGENT:
						# Severity is urgent
						ivUrgent += thisRow[5]
					elif severity == config.SEVERITY_MAJOR:
						# Severity is major
						ivMajor += thisRow[5]	
					elif severity == config.SEVERITY_MINOR:
						# Severity is minor
						ivMinor += thisRow[5]	

					# Add to the current dcValue
					ivValue += thisRow[5]
					# Add to the total count
					ivTotal += thisRow[5]

		# After the last iteration
		# Create the last dict, for each equipment
		if previousTRDate != None:
			if trValue == 0:
				trvvalue = None
			trDict = {"date":"","alarm_count":""}
			trDict['date'] = previousTRDate
			trDict['alarm_count'] = trValue
			trHistoryList.append(trDict)

		if previousSWDate != None:
			if swValue == 0:
				swValue = None
			swDict = {"date":"","alarm_count":""}
			swDict['date'] = previousSWDate
			swDict['alarm_count'] = swValue
			swHistoryList.append(swDict)

		if previousDCDate != None:
			if dcValue == 0:
				dcValue = None
			dcDict = {"date":"","alarm_count":""}
			dcDict['date'] = previousDCDate
			dcDict['alarm_count'] = dcValue
			dcHistoryList.append(dcDict)

		if previousRCDate != None:
			if rcValue == 0:
				rcValue = None
			rcDict = {"date":"","alarm_count":""}
			rcDict['date'] = previousRCDate
			rcDict['alarm_count'] = rcValue
			rcHistoryList.append(rcDict)

		if previousIVDate != None:
			if ivValue == 0:
				ivValue = None
			ivDict = {"date":"","alarm_count":""}
			ivDict['date'] = previousIVDate
			ivDict['alarm_count'] = ivValue
			ivHistoryList.append(ivDict)

		# For transformer
		# Get the today and yesterday value from the transformer history list
		if len(trHistoryList) > 1:
			first = trHistoryList[-2]
			first = first['alarm_count']
			last = trHistoryList[-1]
			last = last['alarm_count']

			morethanzero = round(((last-first)/first) * 100,2)
			lessthanzero = round(((first-last)/first) * 100,2)

			# Calculate the trend indicator and percent
			
			if (last-first) == 0:
				transformerDict['trend_indicator'] = '='
				transformerDict['trend_in_percent'] = '0%'
			elif (last-first) > 0:
				transformerDict['trend_indicator'] = '+'
				transformerDict['trend_in_percent'] = ''+str(morethanzero)+'%'
			elif (last-first) < 0:
				transformerDict['trend_indicator'] = '-'
				transformerDict['trend_in_percent'] = ''+str(lessthanzero)+'%'
		else:
			# Since there is only today's data
			transformerDict['trend_indicator'] = '='
			transformerDict['trend_in_percent'] = '0%'

		# For switchgear
		# Get the today and yesterday value from the switchgear history list
		if len(swHistoryList) > 1:
			first = swHistoryList[-2]
			first = first['alarm_count']
			last = swHistoryList[-1]
			last = last['alarm_count']

			morethanzero = round(((last-first)/first) * 100,2)
			lessthanzero = round(((first-last)/first) * 100,2)

			# Calculate the trend indicator and percent
			
			if (last-first) == 0:
				switchgearDict['trend_indicator'] = '='
				switchgearDict['trend_in_percent'] = '0%'
			elif (last-first) > 0:
				switchgearDict['trend_indicator'] = '+'
				switchgearDict['trend_in_percent'] = ''+str(morethanzero)+'%'
			elif (last-first) < 0:
				switchgearDict['trend_indicator'] = '-'
				switchgearDict['trend_in_percent'] = ''+str(lessthanzero)+'%'
		else:
			# Since there is only today's data
			switchgearDict['trend_indicator'] = '='
			switchgearDict['trend_in_percent'] = '0%'

		# For doubleconverter
		# Get the today and yesterday value from the doubleconverter history list
		if len(dcHistoryList) > 1:
			first = dcHistoryList[-2]
			first = first['alarm_count']
			last = dcHistoryList[-1]
			last = last['alarm_count']

			morethanzero = round(((last-first)/first) * 100,2)
			lessthanzero = round(((first-last)/first) * 100,2)

			# Calculate the trend indicator and percent
			
			if (last-first) == 0:
				doubleconverterDict['trend_indicator'] = '='
				doubleconverterDict['trend_in_percent'] = '0%'
			elif (last-first) > 0:
				doubleconverterDict['trend_indicator'] = '+'
				doubleconverterDict['trend_in_percent'] = ''+str(morethanzero)+'%'
			elif (last-first) < 0:
				doubleconverterDict['trend_indicator'] = '-'
				doubleconverterDict['trend_in_percent'] = ''+str(lessthanzero)+'%'		
		else:
			# Since there is only today's data
			doubleconverterDict['trend_indicator'] = '='
			doubleconverterDict['trend_in_percent'] = '0%'

		# For rectifier
		# Get the today and yesterday value from the rectifier history list
		if len(rcHistoryList) > 1:
			first = rcHistoryList[-2]
			first = first['alarm_count']
			last = rcHistoryList[-1]
			last = last['alarm_count']

			morethanzero = round(((last-first)/first) * 100,2)
			lessthanzero = round(((first-last)/first) * 100,2)

			# Calculate the trend indicator and percent
			
			if (last-first) == 0:
				rectifierDict['trend_indicator'] = '='
				rectifierDict['trend_in_percent'] = '0%'
			elif (last-first) > 0:
				rectifierDict['trend_indicator'] = '+'
				rectifierDict['trend_in_percent'] = ''+str(morethanzero)+'%'
			elif (last-first) < 0:
				rectifierDict['trend_indicator'] = '-'
				rectifierDict['trend_in_percent'] = ''+str(lessthanzero)+'%'		
		else:
			# Since there is only today's data
			rectifierDict['trend_indicator'] = '='
			rectifierDict['trend_in_percent'] = '0%'

		# For inverter
		# Get the today and yesterday value from the inverter history list
		if len(ivHistoryList) > 1:
			first = ivHistoryList[-2]
			first = first['alarm_count']
			last = ivHistoryList[-1]
			last = last['alarm_count']

			morethanzero = round(((last-first)/first) * 100,2)
			lessthanzero = round(((first-last)/first) * 100,2)

			# Calculate the trend indicator and percent
			
			if (last-first) == 0:
				inverterDict['trend_indicator'] = '='
				inverterDict['trend_in_percent'] = '0%'
			elif (last-first) > 0:
				inverterDict['trend_indicator'] = '+'
				inverterDict['trend_in_percent'] = ''+str(morethanzero)+'%'
			elif (last-first) < 0:
				inverterDict['trend_indicator'] = '-'
				inverterDict['trend_in_percent'] = ''+str(lessthanzero)+'%'
		else:
			# Since there is only today's data
			inverterDict['trend_indicator'] = '='
			inverterDict['trend_in_percent'] = '0%'
		
		# Add the total count into the total count section of the individual dict
		transformerDict['total'] = trTotal
		switchgearDict['total'] = swTotal
		doubleconverterDict['total'] = dcTotal
		rectifierDict['total'] = rcTotal
		inverterDict['total'] = ivTotal

		# Add the transformer individual warning count for each transformer severity type Critical,Urgent,Major,Minor
		trCriticalDict['alarm_count'] = trCritical
		trUrgentDict['alarm_count'] = trUrgent
		trMajorDict['alarm_count'] = trMajor
		trMinorDict['alarm_count'] = trMinor
			
		# Add to the trModelList in order of Critical,Urgent,Major,Minor
		trModelList.append(trCriticalDict)
		trModelList.append(trUrgentDict)
		trModelList.append(trMajorDict)
		trModelList.append(trMinorDict)

		transformerDict['model'] = trModelList	

		# Add the switchgear individual warning count for each switchgear severity type Critical,Urgent,Major,Minor
		swCriticalDict['alarm_count'] = swCritical
		swUrgentDict['alarm_count'] = swUrgent
		swMajorDict['alarm_count'] = swMajor
		swMinorDict['alarm_count'] = swMinor
	
		# Add to the swModelList in order of '66','22','750'
		swModelList.append(swCriticalDict)
		swModelList.append(swUrgentDict)
		swModelList.append(swMajorDict)
		swModelList.append(swMinorDict)

		switchgearDict['model'] = swModelList	

		# Add the doubleconverter individual warning count for each doubleconverter severity type Critical,Urgent,Major,Minor
		dcCriticalDict['alarm_count'] = dcCritical
		dcUrgentDict['alarm_count'] = dcUrgent
		dcMajorDict['alarm_count'] = dcMajor
		dcMinorDict['alarm_count'] = dcMinor	

		# Add to the dcModelList in order of 'dconverter'
		dcModelList.append(dcCriticalDict)
		dcModelList.append(dcUrgentDict)
		dcModelList.append(dcMajorDict)
		dcModelList.append(dcMinorDict)

		doubleconverterDict['model'] = dcModelList		

		# Add the rectifier individual warning count for each rectifier severity type Critical,Urgent,Major,Minor
		rcCriticalDict['alarm_count'] = rcCritical
		rcUrgentDict['alarm_count'] = rcUrgent
		rcMajorDict['alarm_count'] = rcMajor
		rcMinorDict['alarm_count'] = rcMinor	

		# Add to the rcModelList in order of 'rectifier'
		rcModelList.append(rcCriticalDict)
		rcModelList.append(rcUrgentDict)
		rcModelList.append(rcMajorDict)
		rcModelList.append(rcMinorDict)

		rectifierDict['model'] = rcModelList	

		# Add the inverter individual warning count for each inverter severity type Critical,Urgent,Major,Minor
		ivCriticalDict['alarm_count'] = ivCritical
		ivUrgentDict['alarm_count'] = ivUrgent
		ivMajorDict['alarm_count'] = ivMajor
		ivMinorDict['alarm_count'] = ivMinor	

		# Add to the ivModelList in order of 'inverter'
		ivModelList.append(ivCriticalDict)
		ivModelList.append(ivUrgentDict)
		ivModelList.append(ivMajorDict)
		ivModelList.append(ivMinorDict)

		inverterDict['model'] = ivModelList	

		# Add the individual history list into the history section of the individual dict
		transformerDict['history'] = trHistoryList
		switchgearDict['history'] = swHistoryList
		doubleconverterDict['history'] = dcHistoryList
		rectifierDict['history'] = rcHistoryList
		inverterDict['history'] = ivHistoryList

		# Append the different dictionaries into the response list
		responseList.append(transformerDict)
		responseList.append(switchgearDict)
		responseList.append(doubleconverterDict)
		responseList.append(rectifierDict)
		responseList.append(inverterDict)

		resultJSON = processJSON(responseList)

		return processResponse(resultJSON,'OK')

