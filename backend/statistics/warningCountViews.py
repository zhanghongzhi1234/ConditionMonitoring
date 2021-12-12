
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

class WarningCountView(APIView):

	# Declare the static class variables
	#global equipmentList
	global equipmentTransformerList
	global equipmentSwitchgearList
	global equipmentDoubleConverterList
	global equipmentRectifierList
	global equipmentInverterList
	global warningDefList
	global stationList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200
	
		if connection_status == 200 and (connection_status != 'No route to host' or connection_status != 'Errors encountered!'):	
			# Add all the static datasources here

			queryStatement = "select warning_code,warning_message,severity,recommended_action from "+config.WARNING_DEF+""
			parameter = []
			warningDefList = queryPostgre(queryStatement,parameter)

			#queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+""
			#parameter = []
			#equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" where equipment = 'transformer'"
			parameter = []
			equipmentTransformerList = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" where equipment = 'switchgear'"
			parameter = []
			equipmentSwitchgearList = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" where equipment = 'dconverter'"
			parameter = []
			equipmentDoubleConverterList = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" where equipment = 'rectifier'"
			parameter = []
			equipmentRectifierList = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" where equipment = 'inverter'"
			parameter = []
			equipmentInverterList = queryPostgre(queryStatement,parameter)

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
		severity = self.request.query_params.get('severity')
		groupby = self.request.query_params.get('group-by')
		month = self.request.query_params.get('month')
		whichtype = self.request.query_params.get('type')
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
		if periodicity == None or periodicity == '':
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

		if station == None:
			station = 'all'

		bystation = 'FALSE'

		# Check to see if by station or cateogry
		if station != None and category == None:
			bystation = 'TRUE'

		if bystation == 'TRUE':
			if station == 'all':
		
				responseList = []

				queryStatement = "select station_id,COUNT(*) from "+config.WARNING_LOGS+" where record_time between CURRENT_TIMESTAMP - INTERVAL '"+day+" day' and CURRENT_TIMESTAMP group by station_id order by station_id"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				for thisRow in stationList:
					stationDict = {"station_code":"","alarm_count":""}
					stationDict['station_code'] = thisRow[1]
					stationDict['alarm_count'] = 0
					for te in resultList:
						if te[0] == thisRow[0]:
							stationDict['alarm_count'] = te[1]
							break
					responseList.append(stationDict)

				resultJSON = processJSON(responseList)

				return processResponse(resultJSON,'OK')
			else:
				# Title: List alarm-count by station

				responseList = []

				queryStatement = "select station_id,COUNT(*) from "+config.WARNING_LOGS+" where record_time between CURRENT_TIMESTAMP - INTERVAL '"+day+" day' and CURRENT_TIMESTAMP  group by station_id  order by station_id"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				for thisRow in stationList:
					stationDict = {"station_code":"","alarm_count":""}
					stationDict['station_code'] = thisRow[1]
					stationDict['alarm_count'] = 0
					for te in resultList:
						if te[0] == thisRow[0]:
							stationDict['alarm_count'] = te[1]
							break
					responseList.append(stationDict)

				resultJSON = processJSON(responseList)

				return processResponse(resultJSON,'OK')		
			
		# Else if category is ALL and station is not specified
		elif category == 'all' and station == 'all':
			# Title:List alarm counts by category		
			transformerDict = { "category_name":"Transformer","alarm_count":""}
			switchgearDict = {"category_name":"Switchgear","alarm_count":""}
			dcConverterDict = {"category_name":"DConverter","alarm_count":""}
			rectifierDict = {"category_name":"Rectifier","alarm_count":""}
			inverterDict = {"category_name":"Inverter","alarm_count":""}

			responseDict = {
					"dataset":[]
					}
			returnList =[]

			trTotal = 0
			swTotal = 0
			dcTotal = 0
			rtTotal = 0
			itTotal = 0
			
			queryStatement = "select COUNT(*),component from "+config.WARNING_LOGS+" where status = '0' group by component order by component"
			parameter = []
			resultList = queryPostgre(queryStatement,parameter)

			for thisRow in resultList:
				if thisRow[1].find('transformer') != -1:
					trTotal += thisRow[0]
					
				elif thisRow[1].find('switchgear') != -1:
					swTotal += thisRow[0]
					
				elif thisRow[1].find('doubleconverter') != -1:
					dcTotal += thisRow[0]
					
				elif thisRow[1].find('rectifier') != -1:
					rtTotal += thisRow[0]
					
				elif thisRow[1].find('inverter') != -1:
					itTotal += thisRow[0]
					

			transformerDict['alarm_count'] = trTotal
			switchgearDict['alarm_count'] = swTotal
			dcConverterDict['alarm_count'] = dcTotal
			rectifierDict['alarm_count'] = rtTotal
			inverterDict['alarm_count'] = itTotal

			returnList.append(transformerDict)
			returnList.append(switchgearDict)
			returnList.append(dcConverterDict)
			returnList.append(rectifierDict)
			returnList.append(inverterDict)

			responseDict['dataset'] = returnList

			resultJSON = processJSON(responseDict)
			
			return processResponse(resultJSON,'OK')
		# Else if category is ALL and station is specified
		elif category == 'all' and station != 'all':
			# Title:List alarm counts by category		
			transformerDict = {"category_name":"Transformer","alarm_count":""}
			switchgearDict = {"category_name":"Switchgear","alarm_count":""}
			dcConverterDict = {"category_name":"DConverter","alarm_count":""}
			rectifierDict = {"category_name":"Rectifier","alarm_count":""}
			inverterDict = {"category_name":"Inverter","alarm_count":""}

			responseDict = {
					"dataset":[]
					}
			returnList =[]

			trTotal = 0
			swTotal = 0
			dcTotal = 0
			rtTotal = 0
			itTotal = 0
			
			queryStatement = "select COUNT(*),component from "+config.WARNING_LOGS+" where status = '0' and station_id = %s group by component order by component "
			parameter = [station]
			resultList = queryPostgre(queryStatement,parameter)

			for thisRow in resultList:
				if thisRow[1].find('transformer') != -1:
					trTotal += thisRow[0]
					
				elif thisRow[1].find('switchgear') != -1:
					swTotal += thisRow[0]
					
				elif thisRow[1].find('doubleconverter') != -1:
					dcTotal += thisRow[0]
					
				elif thisRow[1].find('rectifier') != -1:
					rtTotal += thisRow[0]
					
				elif thisRow[1].find('inverter') != -1:
					itTotal += thisRow[0]

			transformerDict['alarm_count'] = trTotal
			switchgearDict['alarm_count'] = swTotal
			dcConverterDict['alarm_count'] = dcTotal
			rectifierDict['alarm_count'] = rtTotal
			inverterDict['alarm_count'] = itTotal

			returnList.append(transformerDict)
			returnList.append(switchgearDict)
			returnList.append(dcConverterDict)
			returnList.append(rectifierDict)
			returnList.append(inverterDict)

			responseDict['dataset'] = returnList

			resultJSON = processJSON(responseDict)
			
			return processResponse(resultJSON,'OK')
		
		# Else if category is transformer
		elif category == 'transformer':							
			# If category is transformer and time period is within 30 days for all type
			if whichtype == 'all':			
				# Title: List transformers' alarm-count by type and group by station	

				responseDict = {
						"dataset":[]
						}
				datasetDict = {	
						"category":"transformer",
						"type_series":['MT','ST','IT','RT','DCT'],  
						"data_series":[]		
						}

				# Create the data_series list

				dataSeries = []

				queryStatement = "select station_id,system_id,subsystem_id,detail_code,COUNT(*) from "+config.WARNING_LOGS+" where not (status = '1' and is_ack = '1') and component like 'transformer%%' group by station_id,system_id,subsystem_id,detail_code order by station_id,system_id,subsystem_id,detail_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				mtTemp = 0
				stTemp = 0
				itTemp = 0
				rtTemp = 0
				dctTemp = 0

				# The previous location
				previousLocation = ' '
				firstIteration = 'TRUE'

				# Declaration of the equipment_type. Default NA - Not applicable
				equipment_type = 'NA'

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# find the equipment_type for this asset using the station_id,system_id,subsystem_id,detail_code combo
					for te in equipmentTransformerList:
						if te[5] == thisRow[0] and te[6] == thisRow[1] and te[7] == thisRow[2] and te[8] == thisRow[3]:
							equipment_type = te[3]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousLocation = thisRow[0]

						if equipment_type == config.INTAKE_TRANSFORMER:
							# Type is Intake transformer
							mtTemp += thisRow[4]
						elif (equipment_type == config.SERVICE_TRANSFORMER_1MVA or equipment_type == config.SERVICE_TRANSFORMER_26MVA):
							# Type is Service transformer
							stTemp += thisRow[4]
						elif equipment_type == config.INVERTER_TRANSFORMER:
							# Type is Inverter transformer
							itTemp += thisRow[4]
						elif equipment_type == config.RECTIFIER_TRANSFORMER:
							# Type is Rectifier transformer
							rtTemp += thisRow[4]
						elif equipment_type == config.DOUBLE_CONVERTER_TRANSFORMER:
							# Type is Double converter transformer
							dctTemp += thisRow[4]

					# If the location for the previous element is not the same
					elif thisRow[0] != previousLocation:
						# Create the stationDict
						stationDict = {"station_name":"","alarm_count":[]}
						for te in stationList:
							if te[0] == previousLocation:
								stationDict['station_name'] = te[1]
								break
						
						"""
						if mtTemp == 0:
							mtTemp = None;
						if stTemp == 0:
							stTemp = None;
						if itTemp == 0:
							itTemp = None;
						if rtTemp == 0:
							rtTemp = None;
						if dctTemp == 0:
							dctTemp = None;
						"""

						# Append the values to the value_list in order of 'MT','ST','IT','RT','DCT'
						# If there are no values for that particular type, it would be defaulted to 0
						stationDict['alarm_count'].append(mtTemp)
						stationDict['alarm_count'].append(stTemp)
						stationDict['alarm_count'].append(itTemp)
						stationDict['alarm_count'].append(rtTemp)
						stationDict['alarm_count'].append(dctTemp)
			
						# Append the dict
						dataSeries.append(stationDict)

						# Clear the type temp
						mtTemp = 0
						stTemp = 0
						itTemp = 0
						rtTemp = 0
						dctTemp = 0	

						previousLocation = thisRow[0]

						if equipment_type == config.INTAKE_TRANSFORMER:
							# Type is Intake transformer
							mtTemp += thisRow[4]
						elif (equipment_type == config.SERVICE_TRANSFORMER_1MVA or equipment_type == config.SERVICE_TRANSFORMER_26MVA):
							# Type is Service transformer
							stTemp += thisRow[4]
						elif equipment_type == config.INVERTER_TRANSFORMER:
							# Type is Inverter transformer
							itTemp += thisRow[4]
						elif equipment_type == config.RECTIFIER_TRANSFORMER:
							# Type is Rectifier transformer
							rtTemp += thisRow[4]
						elif equipment_type == config.DOUBLE_CONVERTER_TRANSFORMER:
							# Type is Double converter transformer
							dctTemp += thisRow[4]

					else:
						previousLocation = thisRow[0]

						if equipment_type == config.INTAKE_TRANSFORMER:
							# Type is Intake transformer
							mtTemp += thisRow[4]
						elif (equipment_type == config.SERVICE_TRANSFORMER_1MVA or equipment_type == config.SERVICE_TRANSFORMER_26MVA):
							# Type is Service transformer
							stTemp += thisRow[4]
						elif equipment_type == config.INVERTER_TRANSFORMER:
							# Type is Inverter transformer
							itTemp += thisRow[4]
						elif equipment_type == config.RECTIFIER_TRANSFORMER:
							# Type is Rectifier transformer
							rtTemp += thisRow[4]
						elif equipment_type == config.DOUBLE_CONVERTER_TRANSFORMER:
							# Type is Double converter transformer
							dctTemp += thisRow[4]

				# After the last iteration
				# Create the last stationDict
				if len(resultList) > 0:
					stationDict = {"station_name":"","alarm_count":[]}
					for te in stationList:
						if te[0] == previousLocation:
							stationDict['station_name'] = te[1]
							break

					"""
					if mtTemp == 0:
						mtTemp = None;
					if stTemp == 0:
						stTemp = None;
					if itTemp == 0:
						itTemp = None;
					if rtTemp == 0:
						rtTemp = None;
					if dctTemp == 0:
						dctTemp = None;
					"""

					stationDict['alarm_count'].append(mtTemp)
					stationDict['alarm_count'].append(stTemp)
					stationDict['alarm_count'].append(itTemp)
					stationDict['alarm_count'].append(rtTemp)
					stationDict['alarm_count'].append(dctTemp)
		
					# Append the dict
					dataSeries.append(stationDict)

				# Final check to populate stations without any warning counts
				# Loop through all the entries in the equipmentTransformerList
				# Check for missing station(s)
				isStationFound = 'False'

				for te in equipmentTransformerList:
					for li in dataSeries:
						if li['station_name'] == te[5]:
							isStationFound = 'True'
							break

					if isStationFound == 'False':
						stationDict = {"station_name":"","alarm_count":[]}
						stationDict['station_name'] = te[5]
						stationDict['alarm_count'].append(0)
						stationDict['alarm_count'].append(0)
						stationDict['alarm_count'].append(0)
						stationDict['alarm_count'].append(0)
						stationDict['alarm_count'].append(0)

						# Append the dict
						dataSeries.append(stationDict)

					isStationFound = 'False'	
										
				datasetDict['data_series'] = dataSeries
				responseDict['dataset'].append(datasetDict)

				resultJSON = processJSON(responseDict)

				return processResponse(resultJSON,'OK')

			# Else if category is transformer and time period is within the last 3 months
			elif month == '3' and severity == 'all':
				# Title: List all alarm counts by severity and group by month
				now = datetime.datetime.now()
				month = now.month
				thisyear = now.year
				lastyear = now.year-1
							
				monthsCal = {
					"1":['Nov-'+str(lastyear)+'','Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+''],
					"2":['Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+''],
					"3":['Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+''],
					"4":['Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+''],
					"5":['Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+'','May-'+str(thisyear)+''],
					"6":['Apr-'+str(thisyear)+'','May-'+str(thisyear)+'','Jun-'+str(thisyear)+''],
					"7":['May-'+str(thisyear)+'','Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+''],
					"8":['Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+''],
					"9":['Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+''],
					"10":['Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+''],
					"11":['Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+''],
					"12":['Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+'','Dec-'+str(thisyear)+'']
					}

				lastThree = monthsCal[''+str(month)+'']

				responseDict = {
						"dataset":{}
						}
				datasetDict = {	
						"category":"transformer",
						"type_series":['Critical','Urgent','Major','Minor'],
						"data_series":[]		
						}

				# Create the data_series list
				dataSeries = []

				queryStatement = "select EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code,COUNT(*) from "+config.WARNING_LOGS+" where TO_CHAR(record_time,'Mon-YYYY') in ('"+lastThree[0]+"','"+lastThree[1]+"','"+lastThree[2]+"') and component like 'transformer%%' group by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code order by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code DESC"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the severity values
				criticalTemp = 0
				urgentTemp = 0
				majorTemp = 0
				minorTemp = 0

				# The previous location
				previousMonth = ' '
				firstIteration = 'TRUE'

				# Declaration of severity. Default 0
				thisSeverity = 0

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# Check to see which severity, derive from the warning code
					for te in warningDefList:
						if te[0] == thisRow[2]:
							thisSeverity = te[2]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# Severity is Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# Severity is Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# Severity is Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# Severity is Minor
							minorTemp += thisRow[3]

					# If the month for the previous element is not the same
					elif calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0])) != previousMonth:

						# Create the monthDict
						monthDict = {"month_name":"","value_list":[]}
						monthDict['month_name'] = previousMonth

						"""
						if criticalTemp == 0:
							criticalTemp = None;
						if urgentTemp == 0:
							urgentTemp = None;
						if majorTemp == 0:
							majorTemp = None;
						if minorTemp == 0:
							minorTemp = None;
						"""

						# Append the values to the value_list in order of Critical,Urgent,Major,Minor
						monthDict['value_list'].append(criticalTemp)
						monthDict['value_list'].append(urgentTemp)
						monthDict['value_list'].append(majorTemp)
						monthDict['value_list'].append(minorTemp)
		
						# Append the dict
						dataSeries.append(monthDict)

						# Clear the severity temp
						criticalTemp = 0
						urgentTemp = 0
						majorTemp = 0
						minorTemp = 0

						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# Severity is Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# Severity is Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# Severity is Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# Severity is Minor
							minorTemp += thisRow[3]			
					else:
						#previousMonth = str(thisRow[1])+','+str(thisRow[0])
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# Severity is Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# Severity is Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# Severity is Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# Severity is Minor
							minorTemp += thisRow[3]

				# After the last iteration
				# Create the last monthDict
				if len(resultList) > 0:
					monthDict = {"month_name":"","value_list":[]}

					"""
					if criticalTemp == 0:
						criticalTemp = None;
					if urgentTemp == 0:
						urgentTemp = None;
					if majorTemp == 0:
						majorTemp = None;
					if minorTemp == 0:
						minorTemp = None;
					"""

					monthDict['month_name'] = previousMonth
					monthDict['value_list'].append(criticalTemp)
					monthDict['value_list'].append(urgentTemp)
					monthDict['value_list'].append(majorTemp)
					monthDict['value_list'].append(minorTemp)

					# Append the dict
					dataSeries.append(monthDict)
				
				datasetDict['data_series'] = dataSeries
				responseDict['dataset'] = datasetDict

				resultJSON = processJSON(responseDict)
		
				return processResponse(resultJSON,'OK')
			else:
				resultJSON = {}
				return processResponse(resultJSON,'NOT FOUND')

		# Else if category is switchgear
		elif category == 'switchgear':
			#Title: Warning count by station based on switchgear type (#2)
			if whichtype == 'all':	

				responseDict = {
						"dataset":[]
						}
				datasetDict = {	
						"category":"switchgear",
						"type_series":['66KV','22KV','750VDC'],  
						"data_series":[]		
						}
				# Create the data_series list
				dataSeries = []

				queryStatement = "select station_id,system_id,subsystem_id,detail_code,COUNT(*) from "+config.WARNING_LOGS+" where not (status = '1' and is_ack = '1') and component like 'switchgear%%' group by station_id,system_id,subsystem_id,detail_code order by station_id,system_id,subsystem_id,detail_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				sixsixTemp = 0
				twotwoTemp = 0
				sevenfivezeroTemp = 0

				# The previous location
				previousLocation = ' '
				firstIteration = 'TRUE'

				# Declaration of the equipment_type. Default NA - Not applicable
				equipment_type = 'NA'

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# find the equipment_type for this asset using the station_id,system_id,subsystem_id,detail_code combo
					for te in equipmentSwitchgearList:
						if te[5] == thisRow[0] and te[6] == thisRow[1] and te[7] == thisRow[2] and te[8] == thisRow[3]:
							equipment_type = te[3]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousLocation = thisRow[0]

						if equipment_type == config.SWITCHGEAR_66KV:
							# Type is 66kv switchgear
							sixsixTemp += thisRow[4]
						elif equipment_type == config.SWITCHGEAR_22KV:
							# Type is 22kv switchgear
							twotwoTemp += thisRow[4]
						elif equipment_type == config.SWITCHGEAR_750VDC:
							# Type is 750vdc switchgear
							sevenfivezeroTemp += thisRow[4]

					# If the location for the previous element is not the same
					elif thisRow[0] != previousLocation:
						# Create the stationDict
						stationDict = {"station_name":"","alarm_count":[]}
						for te in stationList:
							if te[0] == previousLocation:
								stationDict['station_name'] = te[1]
								break
						
						"""
						if sixsixTemp == 0:
							sixsixTemp = None;
						if twotwoTemp == 0:
							twotwoTemp = None;
						if sevenfivezeroTemp == 0:
							sevenfivezeroTemp = None;
						"""

						stationDict['alarm_count'].append(sixsixTemp)
						stationDict['alarm_count'].append(twotwoTemp)
						stationDict['alarm_count'].append(sevenfivezeroTemp)
			
						# Append the dict
						dataSeries.append(stationDict)

						# Clear the type temp
						sixsixTemp = 0
						twotwoTemp = 0
						sevenfivezeroTemp = 0

						previousLocation = thisRow[0]

						if equipment_type == config.SWITCHGEAR_66KV:
							# Type is 66kv switchgear
							sixsixTemp += thisRow[4]
						elif equipment_type == config.SWITCHGEAR_22KV:
							# Type is 22kv switchgear
							twotwoTemp += thisRow[4]
						elif equipment_type == config.SWITCHGEAR_750VDC:
							# Type is 750vdc switchgear
							sevenfivezeroTemp += thisRow[4]

					else:
						previousLocation = thisRow[0]

						if equipment_type == config.SWITCHGEAR_66KV:
							# Type is 66kv switchgear
							sixsixTemp += thisRow[4]
						elif equipment_type == config.SWITCHGEAR_22KV:
							# Type is 22kv switchgear
							twotwoTemp += thisRow[4]
						elif equipment_type == config.SWITCHGEAR_750VDC:
							# Type is 750vdc switchgear
							sevenfivezeroTemp += thisRow[4]

				# After the last iteration
				# Create the last stationDict
				if len(resultList) > 0:
					stationDict = {"station_name":"","alarm_count":[]}
					for te in stationList:
						if te[0] == previousLocation:
							stationDict['station_name'] = te[1]
							break

					"""
					if sixsixTemp == 0:
						sixsixTemp = None;
					if twotwoTemp == 0:
						twotwoTemp = None;
					if sevenfivezeroTemp == 0:
						sevenfivezeroTemp = None;
					"""

					stationDict['alarm_count'].append(sixsixTemp)
					stationDict['alarm_count'].append(twotwoTemp)
					stationDict['alarm_count'].append(sevenfivezeroTemp)
		
					# Append the dict
					dataSeries.append(stationDict)

				# Final check to populate stations without any warning counts
				# Loop through all the entries in the equipmentSwitchgearList
				# Check for missing station(s)
				isStationFound = 'False'

				for te in equipmentSwitchgearList:
					for li in dataSeries:
						if li['station_name'] == te[5]:
							isStationFound = 'True'
							break

					if isStationFound == 'False':
						stationDict = {"station_name":"","alarm_count":[]}
						stationDict['station_name'] = te[5]
						stationDict['alarm_count'].append(0)
						stationDict['alarm_count'].append(0)
						stationDict['alarm_count'].append(0)

						# Append the dict
						dataSeries.append(stationDict)

					isStationFound = 'False'	

				datasetDict['data_series'] = dataSeries
				responseDict['dataset'].append(datasetDict)

				resultJSON = processJSON(responseDict)

				return processResponse(resultJSON,'OK')

			elif severity == 'all':

				now = datetime.datetime.now()
				month = now.month
				thisyear = now.year
				lastyear = now.year-1
							
				monthsCal = {
					"1":['Nov-'+str(lastyear)+'','Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+''],
					"2":['Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+''],
					"3":['Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+''],
					"4":['Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+''],
					"5":['Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+'','May-'+str(thisyear)+''],
					"6":['Apr-'+str(thisyear)+'','May-'+str(thisyear)+'','Jun-'+str(thisyear)+''],
					"7":['May-'+str(thisyear)+'','Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+''],
					"8":['Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+''],
					"9":['Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+''],
					"10":['Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+''],
					"11":['Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+''],
					"12":['Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+'','Dec-'+str(thisyear)+'']
					}

				lastThree = monthsCal[''+str(month)+'']

				responseDict = {
						"dataset":{}
						}
				datasetDict = {	
						"category":"switchgear",
						"type_series":['Critical','Urgent','Major','Minor'],
						"data_series":[],
						"mark_lines":{}
						}

				# Data-series

				dataSeries = []

				queryStatement = "select EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code,COUNT(*) from "+config.WARNING_LOGS+" where TO_CHAR(record_time,'Mon-YYYY') in ('"+lastThree[0]+"','"+lastThree[1]+"','"+lastThree[2]+"') and component like 'switchgear%%' group by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code order by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				criticalTemp = 0
				urgentTemp = 0
				majorTemp = 0
				minorTemp = 0

				# The previous month
				previousMonth = ' '
				firstIteration = 'TRUE'

				# Declaration of thisSeverity. 
				thisSeverity = 0

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# Check to see which severity, derive from the warning code
					for te in warningDefList:
						if te[0] == thisRow[2]:
							thisSeverity = te[2]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]

					# If the month for the previous element is not the same
					elif calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0])) != previousMonth:
						# Create the monthDict
						monthDict = {"month_name":"","value_list":[]}
						monthDict['month_name'] = previousMonth

						"""
						if criticalTemp == 0:
							criticalTemp = None;
						if urgentTemp == 0:
							urgentTemp = None;
						if majorTemp == 0:
							majorTemp = None;
						if minorTemp == 0:
							minorTemp = None;
						"""

						monthDict['value_list'].append(criticalTemp)
						monthDict['value_list'].append(urgentTemp)
						monthDict['value_list'].append(majorTemp)
						monthDict['value_list'].append(minorTemp)
			
						# Append the dict
						dataSeries.append(monthDict)

						# Clear the type temp
						criticalTemp = 0
						urgentTemp = 0
						majorTemp = 0
						minorTemp = 0

						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]

					else:
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]
				# After the last iteration
				# Create the last monthDict
				if len(resultList) > 0:
					monthDict = {"month_name":"","value_list":[]}
					monthDict['month_name'] = previousMonth

					"""
					if criticalTemp == 0:
						criticalTemp = None;
					if urgentTemp == 0:
						urgentTemp = None;
					if majorTemp == 0:
						majorTemp = None;
					if minorTemp == 0:
						minorTemp = None;
					"""

					monthDict['value_list'].append(criticalTemp)
					monthDict['value_list'].append(urgentTemp)
					monthDict['value_list'].append(majorTemp)
					monthDict['value_list'].append(minorTemp)

					# Append the dict
					dataSeries.append(monthDict)
				
				datasetDict['data_series'] = dataSeries
				responseDict['dataset'] = datasetDict

				resultJSON = processJSON(responseDict)
		
				return processResponse(resultJSON,'OK')
			else:
				resultJSON = {}
				return processResponse(resultJSON,'NOT FOUND')

		# Else if category is doubleconverter
		elif category == 'double-converter':

			if whichtype == 'all':	

				# Create the data_series list
				responseList = []

				queryStatement = "select station_id,system_id,subsystem_id,detail_code,COUNT(*) from "+config.WARNING_LOGS+" where not (status = '1' and is_ack = '1') and component like 'doubleconverter%%' group by station_id,system_id,subsystem_id,detail_code order by station_id,system_id,subsystem_id,detail_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				dconverterTemp = 0

				# The previous location
				previousLocation = ' '
				firstIteration = 'TRUE'

				# Declaration of the equipment_type. Default NA - Not applicable
				equipment_type = 'NA'

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# find the equipment_type for this asset using the station_id,system_id,subsystem_id,detail_code combo
					for te in equipmentDoubleConverterList:
						if te[5] == thisRow[0] and te[6] == thisRow[1] and te[7] == thisRow[2] and te[8] == thisRow[3]:
							equipment_type = te[3]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousLocation = thisRow[0]

						if equipment_type == config.DOUBLECONVERTER_DCONVERTER:
							# There is only one type for double converter
							dconverterTemp += thisRow[4]

					# If the location for the previous element is not the same
					elif thisRow[0] != previousLocation:
						# Create the stationDict
						stationDict = {"station_code":"","alarm_count":""}
						for te in stationList:
							if te[0] == previousLocation:
								stationDict['station_code'] = te[1]
								break
						#stationDict['station_code'] = previousLocation

						"""
						if dconverterTemp == 0:
							dconverterTemp = None;
						"""

						stationDict['alarm_count'] = dconverterTemp
			
						# Append the dict
						responseList.append(stationDict)

						# Clear the type temp
						dconverterTemp = 0

						previousLocation = thisRow[0]

						if equipment_type == config.DOUBLECONVERTER_DCONVERTER:
							# There is only one type for double converter
							dconverterTemp += thisRow[4]

					else:
						previousLocation = thisRow[0]

						if equipment_type == config.DOUBLECONVERTER_DCONVERTER:
							# There is only one type for double converter
							dconverterTemp += thisRow[4]

				# After the last iteration
				# Create the last stationDict
				if len(resultList) > 0:
					stationDict = {"station_code":"","alarm_count":""}
					for te in stationList:
						if te[0] == previousLocation:
							stationDict['station_code'] = te[1]
							break
					#stationDict['station_code'] = previousLocation

					"""
					if dconverterTemp == 0:
						dconverterTemp = None;
					"""

					stationDict['alarm_count'] = dconverterTemp
		
					# Append the dict
					responseList.append(stationDict)		

				# Final check to populate stations without any warning counts
				# Loop through all the entries in the equipmentDoubleConverterList
				# Check for missing station(s)
				isStationFound = 'False'

				for te in equipmentDoubleConverterList:
					for li in responseList:
						if li['station_code'] == te[5]:
							isStationFound = 'True'
							break

					if isStationFound == 'False':
						stationDict = {"station_code":"","alarm_count":""}
						stationDict['station_code'] = te[5]
						stationDict['alarm_count'] = 0

						# Append the dict
						responseList.append(stationDict)

					isStationFound = 'False'											

				resultJSON = processJSON(responseList)

				return processResponse(resultJSON,'OK')

			elif severity == 'all':

				now = datetime.datetime.now()
				month = now.month
				thisyear = now.year
				lastyear = now.year-1
							
				monthsCal = {
					"1":['Nov-'+str(lastyear)+'','Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+''],
					"2":['Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+''],
					"3":['Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+''],
					"4":['Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+''],
					"5":['Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+'','May-'+str(thisyear)+''],
					"6":['Apr-'+str(thisyear)+'','May-'+str(thisyear)+'','Jun-'+str(thisyear)+''],
					"7":['May-'+str(thisyear)+'','Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+''],
					"8":['Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+''],
					"9":['Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+''],
					"10":['Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+''],
					"11":['Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+''],
					"12":['Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+'','Dec-'+str(thisyear)+'']
					}
					
				lastThree = monthsCal[''+str(month)+'']

				responseDict = {
						"dataset":{}
						}
				datasetDict = {"category":"doubleconverter","type_series":['Critical','Urgent','Major','Minor'],"data_series":[],"mark_lines":{}}

				# Data-series

				dataSeries = []

				queryStatement = "select EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code,COUNT(*) from "+config.WARNING_LOGS+" where TO_CHAR(record_time,'Mon-YYYY') in ('"+lastThree[0]+"','"+lastThree[1]+"','"+lastThree[2]+"') and component like 'doubleconverter%%' group by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code order by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				criticalTemp = 0
				urgentTemp = 0
				majorTemp = 0
				minorTemp = 0

				# The previous month
				previousMonth = ' '
				firstIteration = 'TRUE'

				# Declaration of thisSeverity. 
				thisSeverity = 0

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# Check to see which severity, derive from the warning code
					for te in warningDefList:
						if te[0] == thisRow[2]:
							thisSeverity = te[2]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))  

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]

					# If the month for the previous element is not the same
					elif calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0])) != previousMonth:
						# Create the monthDict
						monthDict = {"month_name":"","value_list":[]}
						monthDict['month_name'] = previousMonth

						"""
						if criticalTemp == 0:
							criticalTemp = None;
						if urgentTemp == 0:
							urgentTemp = None;
						if majorTemp == 0:
							majorTemp = None;
						if minorTemp == 0:
							minorTemp = None;
						"""

						monthDict['value_list'].append(criticalTemp)
						monthDict['value_list'].append(urgentTemp)
						monthDict['value_list'].append(majorTemp)
						monthDict['value_list'].append(minorTemp)
			
						# Append the dict
						dataSeries.append(monthDict)

						# Clear the type temp
						criticalTemp = 0
						urgentTemp = 0
						majorTemp = 0
						minorTemp = 0

						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]

					else:
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]
				# After the last iteration
				# Create the last monthDict
				if len(resultList) > 0:
					monthDict = {"month_name":"","value_list":[]}
					monthDict['month_name'] = previousMonth

					"""
					if criticalTemp == 0:
						criticalTemp = None;
					if urgentTemp == 0:
						urgentTemp = None;
					if majorTemp == 0:
						majorTemp = None;
					if minorTemp == 0:
						minorTemp = None;
					"""

					monthDict['value_list'].append(criticalTemp)
					monthDict['value_list'].append(urgentTemp)
					monthDict['value_list'].append(majorTemp)
					monthDict['value_list'].append(minorTemp)
		
					# Append the dict
					dataSeries.append(monthDict)
				
				datasetDict['data_series'] = dataSeries
				responseDict['dataset'] = datasetDict

				resultJSON = processJSON(responseDict)
		
				return processResponse(resultJSON,'OK')
			else:
				resultJSON = {}
				return processResponse(resultJSON,'NOT FOUND')


		elif category == 'rectifier':

			if whichtype == 'all':	

				# Create the data_series list
				responseList = []

				queryStatement = "select station_id,system_id,subsystem_id,detail_code,COUNT(*) from "+config.WARNING_LOGS+" where not (status = '1' and is_ack = '1') and component like 'rectifier%%' group by station_id,system_id,subsystem_id,detail_code order by station_id,system_id,subsystem_id,detail_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				rectifierTemp = 0

				# The previous location
				previousLocation = ' '
				firstIteration = 'TRUE'

				# Declaration of the equipment_type. Default NA - Not applicable
				equipment_type = 'NA'

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# find the equipment_type for this asset using the station_id,system_id,subsystem_id,detail_code combo
					for te in equipmentRectifierList:
						if te[5] == thisRow[0] and te[6] == thisRow[1] and te[7] == thisRow[2] and te[8] == thisRow[3]:
							equipment_type = te[3]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousLocation = thisRow[0]

						if equipment_type == config.RECTIFIER_RECTIFIER:
							# There is only one type for rectifier
							rectifierTemp += thisRow[4]

					# If the location for the previous element is not the same
					elif thisRow[0] != previousLocation:
						# Create the stationDict
						stationDict = {"station_code":"","alarm_count":""}
						for te in stationList:
							if te[0] == previousLocation:
								stationDict['station_code'] = te[1]
								break
						#stationDict['station_code'] = previousLocation

						"""
						if rectifierTemp == 0:
							rectifierTemp = None;
						"""

						stationDict['alarm_count'] = rectifierTemp
			
						# Append the dict
						responseList.append(stationDict)

						# Clear the type temp
						rectifierTemp = 0

						previousLocation = thisRow[0]

						if equipment_type == config.RECTIFIER_RECTIFIER:
							# There is only one type for rectifier
							rectifierTemp += thisRow[4]

					else:
						previousLocation = thisRow[0]

						if equipment_type == config.RECTIFIER_RECTIFIER:
							# There is only one type for rectifier
							rectifierTemp += thisRow[4]

				# After the last iteration
				# Create the last stationDict
				if len(resultList) > 0:
					stationDict = {"station_code":"","alarm_count":""}
					for te in stationList:
						if te[0] == previousLocation:
							stationDict['station_code'] = te[1]
							break
					#stationDict['station_code'] = previousLocation

					"""
					if rectifierTemp == 0:
						rectifierTemp = None;
					"""

					stationDict['alarm_count'] = rectifierTemp
		
					# Append the dict
					responseList.append(stationDict)

				# Final check to populate stations without any warning counts
				# Loop through all the entries in the equipmentRectifierList
				# Check for missing station(s)
				isStationFound = 'False'

				for te in equipmentRectifierList:
					for li in responseList:
						if li['station_code'] == te[5]:
							isStationFound = 'True'
							break

					if isStationFound == 'False':
						stationDict = {"station_code":"","alarm_count":""}
						stationDict['station_code'] = te[5]
						stationDict['alarm_count'] = 0

						# Append the dict
						responseList.append(stationDict)

					isStationFound = 'False'
										
				resultJSON = processJSON(responseList)

				return processResponse(resultJSON,'OK')

			elif severity == 'all':

				now = datetime.datetime.now()
				month = now.month
				thisyear = now.year
				lastyear = now.year-1
							
				monthsCal = {
					"1":['Nov-'+str(lastyear)+'','Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+''],
					"2":['Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+''],
					"3":['Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+''],
					"4":['Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+''],
					"5":['Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+'','May-'+str(thisyear)+''],
					"6":['Apr-'+str(thisyear)+'','May-'+str(thisyear)+'','Jun-'+str(thisyear)+''],
					"7":['May-'+str(thisyear)+'','Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+''],
					"8":['Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+''],
					"9":['Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+''],
					"10":['Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+''],
					"11":['Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+''],
					"12":['Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+'','Dec-'+str(thisyear)+'']
					}

				lastThree = monthsCal[''+str(month)+'']

				responseDict = {
						"dataset":{}
						}
				datasetDict = {"category":"rectifier","type_series":['Critical','Urgent','Major','Minor'],"data_series":[],"mark_lines":{}}

				# Data-series

				dataSeries = []

				queryStatement = "select EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code,COUNT(*) from "+config.WARNING_LOGS+" where TO_CHAR(record_time,'Mon-YYYY') in ('"+lastThree[0]+"','"+lastThree[1]+"','"+lastThree[2]+"') and component like 'rectifier%%' group by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code order by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				criticalTemp = 0
				urgentTemp = 0
				majorTemp = 0
				minorTemp = 0

				# The previous month
				previousMonth = ' '
				firstIteration = 'TRUE'

				# Declaration of thisSeverity. 
				thisSeverity = 0

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# Check to see which severity, derive from the warning code
					for te in warningDefList:
						if te[0] == thisRow[2]:
							thisSeverity = te[2]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))  

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]

					# If the month for the previous element is not the same
					elif calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0])) != previousMonth:
						# Create the monthDict
						monthDict = {"month_name":"","value_list":[]}
						monthDict['month_name'] = previousMonth

						"""
						if criticalTemp == 0:
							criticalTemp = None;
						if urgentTemp == 0:
							urgentTemp = None;
						if majorTemp == 0:
							majorTemp = None;
						if minorTemp == 0:
							minorTemp = None;
						"""

						monthDict['value_list'].append(criticalTemp)
						monthDict['value_list'].append(urgentTemp)
						monthDict['value_list'].append(majorTemp)
						monthDict['value_list'].append(minorTemp)
			
						# Append the dict
						dataSeries.append(monthDict)

						# Clear the type temp
						criticalTemp = 0
						urgentTemp = 0
						majorTemp = 0
						minorTemp = 0

						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]

					else:
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]
				# After the last iteration
				# Create the last monthDict
				if len(resultList) > 0:
					monthDict = {"month_name":"","value_list":[]}
					monthDict['month_name'] = previousMonth

					"""
					if criticalTemp == 0:
						criticalTemp = None;
					if urgentTemp == 0:
						urgentTemp = None;
					if majorTemp == 0:
						majorTemp = None;
					if minorTemp == 0:
						minorTemp = None;
					"""	

					monthDict['value_list'].append(criticalTemp)
					monthDict['value_list'].append(urgentTemp)
					monthDict['value_list'].append(majorTemp)
					monthDict['value_list'].append(minorTemp)
		
					# Append the dict
					dataSeries.append(monthDict)
				
				datasetDict['data_series'] = dataSeries
				responseDict['dataset'] = datasetDict

				resultJSON = processJSON(responseDict)
		
				return processResponse(resultJSON,'OK')
			else:
				resultJSON = {}
				return processResponse(resultJSON,'NOT FOUND')			
		elif category == 'inverter':

			if whichtype == 'all':	

				# Create the data_series list
				responseList = []

				queryStatement = "select station_id,system_id,subsystem_id,detail_code,COUNT(*) from "+config.WARNING_LOGS+" where not (status = '1' and is_ack = '1') and component like 'inverter%%' group by station_id,system_id,subsystem_id,detail_code order by station_id,system_id,subsystem_id,detail_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				inverterTemp = 0

				# The previous location
				previousLocation = ' '
				firstIteration = 'TRUE'

				# Declaration of the equipment_type. Default NA - Not applicable
				equipment_type = 'NA'

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# find the equipment_type for this asset using the station_id,system_id,subsystem_id,detail_code combo
					for te in equipmentInverterList:
						if te[5] == thisRow[0] and te[6] == thisRow[1] and te[7] == thisRow[2] and te[8] == thisRow[3]:
							equipment_type = te[3]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousLocation = thisRow[0]

						if equipment_type == config.INVERTER_INVERTER:
							# There is only one type for inverter
							inverterTemp += thisRow[4]

					# If the location for the previous element is not the same
					elif thisRow[0] != previousLocation:
						# Create the stationDict
						stationDict = {"station_code":"","alarm_count":""}
						for te in stationList:
							if te[0] == previousLocation:
								stationDict['station_code'] = te[1]
								break
						#stationDict['station_code'] = previousLocation

						"""
						if inverterTemp == 0:
							inverterTemp = None;
						"""

						stationDict['alarm_count'] = inverterTemp
			
						# Append the dict
						responseList.append(stationDict)

						# Clear the type temp
						inverterTemp = 0

						previousLocation = thisRow[0]

						if equipment_type == config.INVERTER_INVERTER:
							# There is only one type for inverter
							inverterTemp += thisRow[4]

					else:
						previousLocation = thisRow[0]

						if equipment_type == config.INVERTER_INVERTER:
							# There is only one type for inverter
							inverterTemp += thisRow[4]

				# After the last iteration
				# Create the last stationDict
				if len(resultList) > 0:
					stationDict = {"station_code":"","alarm_count":""}
					for te in stationList:
						if te[0] == previousLocation:
							stationDict['station_code'] = te[1]
							break
					#stationDict['station_code'] = previousLocation

					"""
					if inverterTemp == 0:
						inverterTemp = None;
					"""

					stationDict['alarm_count'] = inverterTemp
		
					# Append the dict
					responseList.append(stationDict)

				# Final check to populate stations without any warning counts
				# Loop through all the entries in the equipmentInverterList
				# Check for missing station(s)
				isStationFound = 'False'

				for te in equipmentInverterList:
					for li in responseList:
						if li['station_code'] == te[5]:
							isStationFound = 'True'
							break

					if isStationFound == 'False':
						stationDict = {"station_code":"","alarm_count":""}
						stationDict['station_code'] = te[5]
						stationDict['alarm_count'] = 0

						# Append the dict
						responseList.append(stationDict)

					isStationFound = 'False'
					
				resultJSON = processJSON(responseList)

				return processResponse(resultJSON,'OK')

			elif severity == 'all':

				now = datetime.datetime.now()
				month = now.month
				thisyear = now.year
				lastyear = now.year-1
							
				monthsCal = {
					"1":['Nov-'+str(lastyear)+'','Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+''],
					"2":['Dec-'+str(lastyear)+'','Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+''],
					"3":['Jan-'+str(thisyear)+'','Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+''],
					"4":['Feb-'+str(thisyear)+'','Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+''],
					"5":['Mar-'+str(thisyear)+'','Apr-'+str(thisyear)+'','May-'+str(thisyear)+''],
					"6":['Apr-'+str(thisyear)+'','May-'+str(thisyear)+'','Jun-'+str(thisyear)+''],
					"7":['May-'+str(thisyear)+'','Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+''],
					"8":['Jun-'+str(thisyear)+'','Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+''],
					"9":['Jul-'+str(thisyear)+'','Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+''],
					"10":['Aug-'+str(thisyear)+'','Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+''],
					"11":['Sep-'+str(thisyear)+'','Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+''],
					"12":['Oct-'+str(thisyear)+'','Nov-'+str(thisyear)+'','Dec-'+str(thisyear)+'']
					}

				lastThree = monthsCal[''+str(month)+'']

				responseDict = {
						"dataset":{}
						}
				datasetDict = {"category":"inverter","type_series":['Critical','Urgent','Major','Minor'],"data_series":[],"mark_lines":{}}

				# Data-series

				dataSeries = []

				queryStatement = "select EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code,COUNT(*) from "+config.WARNING_LOGS+" where TO_CHAR(record_time,'Mon-YYYY') in ('"+lastThree[0]+"','"+lastThree[1]+"','"+lastThree[2]+"') and component like 'inverter%%' group by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code order by EXTRACT(year from record_time),EXTRACT(month from record_time),warning_code"
				parameter = []
				resultList = queryPostgre(queryStatement,parameter)

				# Temp for the types values
				criticalTemp = 0
				urgentTemp = 0
				majorTemp = 0
				minorTemp = 0

				# The previous month
				previousMonth = ' '
				firstIteration = 'TRUE'

				# Declaration of thisSeverity. 
				thisSeverity = 0

				# Loop through the entire resultset, processing the data accordingly
				for thisRow in resultList:
					# Check to see which severity, derive from the warning code
					for te in warningDefList:
						if te[0] == thisRow[2]:
							thisSeverity = te[2]
							break

					# Always true for the first iteration
					if firstIteration == 'TRUE':
						firstIteration = 'FALSE'
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))  

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]

					# If the month for the previous element is not the same
					elif calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0])) != previousMonth:
						# Create the monthDict
						monthDict = {"month_name":"","value_list":[]}
						monthDict['month_name'] = previousMonth

						"""
						if criticalTemp == 0:
							criticalTemp = None;
						if urgentTemp == 0:
							urgentTemp = None;
						if majorTemp == 0:
							majorTemp = None;
						if minorTemp == 0:
							minorTemp = None;
						"""

						monthDict['value_list'].append(criticalTemp)
						monthDict['value_list'].append(urgentTemp)
						monthDict['value_list'].append(majorTemp)
						monthDict['value_list'].append(minorTemp)
			
						# Append the dict
						dataSeries.append(monthDict)

						# Clear the type temp
						criticalTemp = 0
						urgentTemp = 0
						majorTemp = 0
						minorTemp = 0

						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]

					else:
						previousMonth = calendar.month_abbr[int(thisRow[1])]+','+str(int(thisRow[0]))

						if thisSeverity == config.SEVERITY_CRITICAL:
							# severity is 4:Critical
							criticalTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_URGENT:
							# severity is 3:Urgent
							urgentTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MAJOR:
							# severity is 2:Major
							majorTemp += thisRow[3]
						elif thisSeverity == config.SEVERITY_MINOR:
							# severity is 1:Minor
							minorTemp += thisRow[3]
				# After the last iteration
				# Create the last monthDict
				if len(resultList) > 0:
					monthDict = {"month_name":"","value_list":[]}
					monthDict['month_name'] = previousMonth

					"""
					if criticalTemp == 0:
						criticalTemp = None;
					if urgentTemp == 0:
						urgentTemp = None;
					if majorTemp == 0:
						majorTemp = None;
					if minorTemp == 0:
						minorTemp = None;
					"""

					monthDict['value_list'].append(criticalTemp)
					monthDict['value_list'].append(urgentTemp)
					monthDict['value_list'].append(majorTemp)
					monthDict['value_list'].append(minorTemp)
		
					# Append the dict
					dataSeries.append(monthDict)
				
				datasetDict['data_series'] = dataSeries
				responseDict['dataset'] = datasetDict

				resultJSON = processJSON(responseDict)
		
				return processResponse(resultJSON,'OK')
			else:
				resultJSON = {}
				return processResponse(resultJSON,'NOT FOUND')		
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')


