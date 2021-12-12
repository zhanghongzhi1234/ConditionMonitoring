
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

import random
import time

from backend.utilities.druidQuery import queryDruid
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
class SwitchgearReadingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global warningDef
	global swRangeList

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
			warningDef = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+""
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_count,max_count,min_shunt,max_shunt,min_busbar,max_busbar,min_cable,max_cable,min_control,max_control,min_rx,max_rx,min_rz,max_rz,equipment_type from "+config.SWITCHGEAR_RANGE+""
			parameter = []
			swRangeList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		# Title: Show switchgear individual elements' reading (#15)
		assetName = self.request.query_params.get('equipment_code')

		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None

		shuntMax = None
		busbarMax = None
		cableMax = None
		controlMax = None
		rxMax = None
		rzMax = None

		shuntMin = None
		busbarMin = None
		cableMin = None
		controlMin = None
		rxMin = None
		rzMin = None
		
		# find the equipment info given the asset_name
		for te in equipmentList:
			if te[1] == assetName:
				station_id = te[5]
				system_id = te[6]
				subsystem_id = te[7]
				detail_code = te[8]
				equipment_type = te[3]
				break

		# find the maximum allowable value for this equipment type
		for te in swRangeList:
			if te[14] == equipment_type:
				shuntMax = te[3]
				busbarMax = te[5]
				cableMax = te[7]
				controlMax = te[9]
				rxMax = te[11]
				rzMax = te[13]

				shuntMin = te[2]
				busbarMin = te[4]
				cableMin = te[6]
				controlMin = te[8]
				rxMin = te[10]
				rzMin = te[12]
				break

		responseDict = {
				"current_reading":[]
				}

		shunt = {"id":"shunt","name":"SHUNT","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		busbar = {"id":"busbar","name":"BUSBAR","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		cable = {"id":"cable","name":"CABLE","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		control = {"id":"control","name":"CONTROL","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		rx = {"id":"resistance-cts","name":"RESISTANCE CTS","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		rz = {"id":"resistance-ste","name":"RESISTANCE STE","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		
		# First treat everything as healthy
		shunt['status'] = 'Healthy'
		shunt['description'] = 'Healthy'
		control['status'] = 'Healthy'
		control['description'] = 'Healthy'
		busbar['status'] = 'Healthy'
		busbar['description'] = 'Healthy'
		cable['status'] = 'Healthy'
		cable['description'] = 'Healthy'
		rz['status'] = 'Healthy'
		rz['description'] = 'Healthy'
		rx['status'] = 'Healthy'
		rx['description'] = 'Healthy'

		queryStatement = "select shunt_temp,busbar_temp,cable_temp,control_temp,rx,rz from "+config.SWITCHGEAR_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
		parameter = [equipment_type]
		swThresholdList = queryPostgre(queryStatement,parameter)

		queryStatement = "select panel_temperature_shunt,panel_temperature_busbar,panel_temperature_cable,panel_temperature_control,cable_insulation_resistance_measurement_rx,cable_insulation_resistance_measurement_rz,record_time from "+config.SWITCHGEAR_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		if len(resultList) > 0:
			thisRow = resultList[0]
			shunt['current_val'] = thisRow[0]
			busbar['current_val'] = thisRow[1]
			cable['current_val'] = thisRow[2]
			control['current_val'] = thisRow[3]
			rx['current_val'] = thisRow[4]
			rz['current_val'] = thisRow[5]

			# Double check for null values status
			# Double check for out of range values
			if thisRow[0] == None:
				shunt['status'] = 'Unknown'
				shunt['description'] = 'Unknown'
				shunt['current_val'] = 'NO VALUE'
			elif thisRow[0] > int(shuntMax) and thisRow[0] < int(shuntMin):
				shunt['status'] = 'outrange'
				shunt['description'] = 'out of range'
				shunt['current_val'] = 'out of range'

			if thisRow[1] == None:
				busbar['status'] = 'Unknown'
				busbar['description'] = 'Unknown'
				busbar['current_val'] = 'NO VALUE'
			elif thisRow[1] > int(busbarMax) and thisRow[1] < int(busbarMin):
				busbar['status'] = 'outrange'
				busbar['description'] = 'out of range'
				busbar['current_val'] = 'out of range'

			if thisRow[2] == None:
				cable['status'] = 'Unknown'
				cable['description'] = 'Unknown'
				cable['current_val'] = 'NO VALUE'
			elif thisRow[2] > int(cableMax) and thisRow[2] < int(cableMin):
				cable['status'] = 'outrange'
				cable['description'] = 'out of range'
				cable['current_val'] = 'out of range'

			if thisRow[3] == None:
				control['status'] = 'Unknown'
				control['description'] = 'Unknown'
				control['current_val'] = 'NO VALUE'
			elif thisRow[3] > int(controlMax) and thisRow[3] < int(controlMin):
				control['status'] = 'outrange'
				control['description'] = 'out of range'
				control['current_val'] = 'out of range'

			if thisRow[4] == None:
				rx['status'] = 'Unknown'
				rx['description'] = 'Unknown'
				rx['current_val'] = 'NO VALUE'
			elif thisRow[4] > int(rxMax) and thisRow[4] < int(rxMin):
				rx['status'] = 'outrange'
				rx['description'] = 'out of range'
				rx['current_val'] = 'out of range'

			if thisRow[5] == None:
				rz['status'] = 'Unknown'
				rz['description'] = 'Unknown'
				rz['current_val'] = 'NO VALUE'
			elif thisRow[5] > int(rzMax) and thisRow[5] < int(rzMin):
				rz['status'] = 'outrange'
				rz['description'] = 'out of range'
				rz['current_val'] = 'out of range'
		else:
			shunt['current_val'] = 'NO VALUE'
			busbar['current_val'] = 'NO VALUE'
			cable['current_val'] = 'NO VALUE'
			control['current_val'] = 'NO VALUE'
			rx['current_val'] = 'NO VALUE'
			rz['current_val'] = 'NO VALUE'

			shunt['status'] = 'Unknown'
			shunt['description'] = 'Unknown'
			control['status'] = 'Unknown'
			control['description'] = 'Unknown'
			busbar['status'] = 'Unknown'
			busbar['description'] = 'Unknown'
			cable['status'] = 'Unknown'
			cable['description'] = 'Unknown'
			rz['status'] = 'Unknown'
			rz['description'] = 'Unknown'
			rx['status'] = 'Unknown'
			rx['description'] = 'Unknown'

		# Populate the static values from postgre
		for te in swRangeList:
			if te[14] == equipment_type:
				shunt['min_val'] = te[2]
				busbar['min_val'] = te[4]
				cable['min_val'] = te[6]
				control['min_val'] = te[8]
				rx['min_val'] = te[10]
				rz['min_val'] = te[12]
				shunt['max_val'] = te[3]
				busbar['max_val'] = te[5]
				cable['max_val'] = te[7]
				control['max_val'] = te[9]
				rx['max_val'] = te[11]
				rz['max_val'] = te[13]
				break
	
		for te in swThresholdList:
			shunt['threshold_val1'] = te[0]
			busbar['threshold_val1'] = te[1]
			cable['threshold_val1'] = te[2]
			control['threshold_val1'] = te[3]
			rx['threshold_val1'] = te[4]
			rz['threshold_val1'] = te[5]
			break

		queryStatement = "select record_time,component,warning_code from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component like 'switchgear:%%' and status = '0' order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		# Loop through the entire resultset, processing the data accordingly
		for thisRow in resultList:
			if thisRow[1] == 'switchgear:shunt':
				if thisRow[2] != 'NA':
					shunt['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							shunt['description'] = te[1]
							break

			elif thisRow[1] == 'switchgear:control':
				if thisRow[2] != 'NA':
					control['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							control['description'] = te[1]
							break

			elif thisRow[1] == 'switchgear:busbar':
				if thisRow[2] != 'NA':
					busbar['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							busbar['description'] = te[1]
							break

			elif thisRow[1] == 'switchgear:cable':
				if thisRow[2] != 'NA':
					cable['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							cable['description'] = te[1]
							break

			elif thisRow[1] == 'switchgear:rz':
				if thisRow[2] != 'NA':
					rz['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							rz['description'] = te[1]
							break

			elif thisRow[1] == 'switchgear:rx':
				if thisRow[2] != 'NA':
					rx['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							rx['description'] = te[1]
							break

		responseDict['current_reading'].append(shunt)
		responseDict['current_reading'].append(busbar)
		responseDict['current_reading'].append(cable)
		responseDict['current_reading'].append(control)
		responseDict['current_reading'].append(rx)
		responseDict['current_reading'].append(rz)

		resultJSON = processJSON(responseDict)

		return processResponse(resultJSON,'OK')






















