
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

from backend.utilities.postgreQuery import queryPostgre
from backend.utilities.postgreUpdate import updatePostgre
from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnResponse import processResponse
from backend.utilities.returnJSON import processJSON
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Create your views here.
class DoubleconverterReadingsView(APIView):

	# Declare the static class variables
	global equipmentList
	global warningDef
	global dcRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQ' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here
			queryStatement = "select warning_code,warning_message,severity,recommended_action from "+config.WARNING_DEF+""
			parameter = []
			warningDef = queryPostgre(queryStatement,parameter)

			queryStatement = "select equipment,acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer from "+config.EQUIPMENT_INFO+" order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_panel_temp_1_rec1, max_panel_temp_1_rec1, min_panel_temp_1_rec2, max_panel_temp_1_rec2, min_panel_temp_1_inv, max_panel_temp_1_inv, min_module_temp_thy1,max_module_temp_thy1, min_module_temp_thy2,max_module_temp_thy2, min_module_temp_igbt1,max_module_temp_igbt1, min_max_power_rec, max_max_power_rec, min_max_power_inv, max_max_power_inv, min_panel_temp_2_rec1, max_panel_temp_2_rec1, min_panel_temp_2_rec2, max_panel_temp_2_rec2, min_panel_temp_2_inv, max_panel_temp_2_inv, min_num_operations_rec,max_num_operations_rec,min_num_operations_inv,max_num_operations_inv,equipment_type from "+config.DOUBLECONVERTER_RANGE+""
			parameter = []
			dcRangeList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: Druid service connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		# Title: Show transformer individual readings

		assetName = self.request.query_params.get('equipment_code')
		
		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None

		# The max values
		rec1TopMax = None
		rec2TopMax = None
		invTopMax = None
		thy1Max = None
		thy2Max = None
		igbt1Max = None
		recModeMax = None
		invModeMax = None
		rec1BottomMax = None
		rec2BottomMax = None
		invBottomMax = None
		opCountRecMax = None
		opCountInvMax = None

		# The min values
		rec1TopMin = None
		rec2TopMin = None
		invTopMin = None
		thy1Min = None
		thy2Min = None
		igbt1Min = None
		recModeMin = None
		invModeMin = None
		rec1BottomMin = None
		rec2BottomMin = None
		invBottomMin = None
		opCountRecMin = None
		opCountInvMin = None

		# find the equipment info given the asset_name
		for te in equipmentList:
			if te[1] == assetName:
				station_id = te[5]
				system_id = te[6]
				subsystem_id = te[7]
				detail_code = te[8]
				equipment_type = te[3]
				break

		# find the maximum and minimum allowable value for this equipment type
		for te in dcRangeList:
			if te[26] == equipment_type:
				rec1TopMax = te[1]
				rec2TopMax = te[3]
				invTopMax = te[5]
				thy1Max = te[7]
				thy2Max = te[9]
				igbt1Max = te[11]
				recModeMax = te[13]
				invModeMax = te[15]
				rec1BottomMax = te[17]
				rec2BottomMax = te[19]
				invBottomMax = te[21]
				opCountRecMax = te[23]
				opCountInvMax = te[25]

				rec1TopMin = te[0]
				rec2TopMin = te[2]
				invTopMin = te[4]
				thy1Min = te[6]
				thy2Min = te[8]
				igbt1Min = te[10]
				recModeMin = te[12]
				invModeMin = te[14]
				rec1BottomMin = te[16]
				rec2BottomMin = te[18]
				invBottomMin = te[20]
				opCountRecMin = te[22]
				opCountInvMin = te[24]
				break

		responseDict = {
				"current_reading":[]
				}

		currentReadingList = []

		opCountInvDict = {"id":"operation-counts-inv-mode","name":"Inv Mode","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		opCountRecDict = {"id":"operation-counts-rec-mode","name":"Rec Mode","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}

		rec1TopDict = {"id":"rec1-top","name":"Rectifier 1 - Top","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		rec1BottomDict = {"id":"rec1-bottom","name":"Rectifier 1 - Bottom","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		rec2TopDict = {"id":"rec2-top","name":"Rectifier 2 - Top","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		rec2BottomDict = {"id":"rec2-bottom","name":"Rectifier 2 - Bottom","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		invTopDict = {"id":"inv-top","name":"Inverter - Top","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		invBottomDict = {"id":"inv-bottom","name":"Inverter - Bottom","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}

		thy1Dict = {"id":"mod-thy1","name":"Thyristor 1","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		thy2Dict = {"id":"mod-thy2","name":"Thyristor 2","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		igbt1Dict = {"id":"mod-igbt1","name":"IGBT 1","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}

		recModeDict = {"id":"max-power-rec-mode","name":"Rec Mode","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		invModeDict = {"id":"max-power-inv-mode","name":"Inv Mode","min_val":"","max_val":"","current_val":"","status":"","description":"","threshold_val1":""}
		
		# First treat everything as healthy
		rec1TopDict['status'] = 'Healthy'
		rec1TopDict['description'] = 'Healthy'
		rec2TopDict['status'] = 'Healthy'
		rec2TopDict['description'] = 'Healthy'
		invTopDict['status'] = 'Healthy'
		invTopDict['description'] = 'Healthy'
		thy1Dict['status'] = 'Healthy'
		thy1Dict['description'] = 'Healthy'
		thy2Dict['status'] = 'Healthy'
		thy2Dict['description'] = 'Healthy'
		igbt1Dict['status'] = 'Healthy'
		igbt1Dict['description'] = 'Healthy'
		recModeDict['status'] = 'Healthy'
		recModeDict['description'] = 'Healthy'
		invModeDict['status'] = 'Healthy'
		invModeDict['description'] = 'Healthy'
		rec1BottomDict['status'] = 'Healthy'
		rec1BottomDict['description'] = 'Healthy'
		rec2BottomDict['status'] = 'Healthy'
		rec2BottomDict['description'] = 'Healthy'
		invBottomDict['status'] = 'Healthy'
		invBottomDict['description'] = 'Healthy'
		opCountRecDict['status'] = 'Healthy'
		opCountRecDict['description'] = 'Healthy'
		opCountInvDict['status'] = 'Healthy'
		opCountInvDict['description'] = 'Healthy'

		queryStatement = "select panel_temp_1_rec1,panel_temp_1_rec2,panel_temp_1_inv,panel_temp_2_rec1,panel_temp_2_rec2,panel_temp_2_inv,module_temp_thy1,module_temp_thy2,module_temp_igbt1,num_operations_rec,num_operations_inv,max_power_rec,max_power_inv from "+config.DOUBLECONVERTER_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
		parameter = [equipment_type]
		dcThresholdList = queryPostgre(queryStatement,parameter)

		queryStatement = "select record_time, panel_temperature_1_rec1, panel_temperature_1_rec2, panel_temperature_1_inv, module_temperature_thy1, module_temperature_thy2, module_temperature_igbt1, maximum_power_rec_mode, maximum_power_inv_mode, panel_temperature_2_rec1, panel_temperature_2_rec2, panel_temperature_2_inv, number_of_operations_rec_mode, number_of_operations_inv_mode from "+config.DOUBLECONVERTER_DATA+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s order by record_time DESC LIMIT 1"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		if len(resultList) > 0:		
			thisRow = resultList[0]
			rec1TopDict['current_val'] = thisRow[1]
			rec1BottomDict['current_val'] = thisRow[9]
			rec2TopDict['current_val'] = thisRow[2]
			rec2BottomDict['current_val'] = thisRow[10]
			invTopDict['current_val'] = thisRow[3]
			invBottomDict['current_val'] = thisRow[11]
			thy1Dict['current_val'] = thisRow[4]
			thy2Dict['current_val'] = thisRow[5]
			igbt1Dict['current_val'] = thisRow[6]
			recModeDict['current_val'] = thisRow[7]
			invModeDict['current_val'] = thisRow[8]
			opCountInvDict['current_val'] = thisRow[13]
			opCountRecDict['current_val'] = thisRow[12]

			# Double check for null values status
			# Double check for out of range values
			if thisRow[1] == None:
				rec1TopDict['status'] = 'Unknown'
				rec1TopDict['description'] = 'Unknown'
				rec1TopDict['current_val'] = 'NO VALUE'
			elif thisRow[1] > int(rec1TopMax) and thisRow[1] < int(rec1TopMin):
				rec1TopDict['status'] = 'outrange'
				rec1TopDict['description'] = 'out of range'
				rec1TopDict['current_val'] = 'out of range'

			if thisRow[9] == None:
				rec1BottomDict['status'] = 'Unknown'
				rec1BottomDict['description'] = 'Unknown'
				rec1BottomDict['current_val'] = 'NO VALUE'
			elif thisRow[9] > int(rec1BottomMax) and thisRow[9] < int(rec1BottomMin):
				rec1BottomDict['status'] = 'outrange'
				rec1BottomDict['description'] = 'out of range'
				rec1BottomDict['current_val'] = 'out of range'

			if thisRow[2] == None:
				rec2TopDict['status'] = 'Unknown'
				rec2TopDict['description'] = 'Unknown'
				rec2TopDict['current_val'] = 'NO VALUE'
			elif thisRow[2] > int(rec2TopMax) and thisRow[2] < int(rec2TopMin):
				rec2TopDict['status'] = 'outrange'
				rec2TopDict['description'] = 'out of range'
				rec2TopDict['current_val'] = 'out of range'

			if thisRow[10] == None:
				rec2BottomDict['status'] = 'Unknown'
				rec2BottomDict['description'] = 'Unknown'
				rec2BottomDict['current_val'] = 'NO VALUE'
			elif thisRow[10] > int(rec2BottomMax) and thisRow[10] < int(rec2BottomMin):
				rec2BottomDict['status'] = 'outrange'
				rec2BottomDict['description'] = 'out of range'
				rec2BottomDict['current_val'] = 'out of range'

			if thisRow[3] == None:
				invTopDict['status'] = 'Unknown'
				invTopDict['description'] = 'Unknown'
				invTopDict['current_val'] = 'NO VALUE'
			elif thisRow[3] > int(invTopMax) and thisRow[3] < int(invTopMin):
				invTopDict['status'] = 'outrange'
				invTopDict['description'] = 'out of range'
				invTopDict['current_val'] = 'out of range'

			if thisRow[11] == None:
				invBottomDict['status'] = 'Unknown'
				invBottomDict['description'] = 'Unknown'
				invBottomDict['current_val'] = 'NO VALUE'
			elif thisRow[11] > int(invBottomMax) and thisRow[11] < int(invBottomMin):
				invBottomDict['status'] = 'outrange'
				invBottomDict['description'] = 'out of range'
				invBottomDict['current_val'] = 'out of range'

			if thisRow[4] == None:
				thy1Dict['status'] = 'Unknown'
				thy1Dict['description'] = 'Unknown'
				thy1Dict['current_val'] = 'NO VALUE'
			elif thisRow[4] > int(thy1Max) and thisRow[4] < int(thy1Min):
				thy1Dict['status'] = 'outrange'
				thy1Dict['description'] = 'out of range'
				thy1Dict['current_val'] = 'out of range'

			if thisRow[5] == None:
				thy2Dict['status'] = 'Unknown'
				thy2Dict['description'] = 'Unknown'
				thy2Dict['current_val'] = 'NO VALUE'
			elif thisRow[5] > int(thy2Max) and thisRow[5] < int(thy2Min):
				thy2Dict['status'] = 'outrange'
				thy2Dict['description'] = 'out of range'
				thy2Dict['current_val'] = 'out of range'

			if thisRow[6] == None:
				igbt1Dict['status'] = 'Unknown'
				igbt1Dict['description'] = 'Unknown'
				igbt1Dict['current_val'] = 'NO VALUE'
			elif thisRow[6] > int(igbt1Max) and thisRow[6] < int(igbt1Min):
				igbt1Dict['status'] = 'outrange'
				igbt1Dict['description'] = 'out of range'
				igbt1Dict['current_val'] = 'out of range'

			if thisRow[7] == None:
				recModeDict['status'] = 'Unknown'
				recModeDict['description'] = 'Unknown'
				recModeDict['current_val'] = 'NO VALUE'
			elif thisRow[7] > int(recModeMax) and thisRow[7] < int(recModeMin):
				recModeDict['status'] = 'outrange'
				recModeDict['description'] = 'out of range'
				recModeDict['current_val'] = 'out of range'

			if thisRow[8] == None:
				invModeDict['status'] = 'Unknown'
				invModeDict['description'] = 'Unknown'
				invModeDict['current_val'] = 'NO VALUE'
			elif thisRow[8] > int(invModeMax) and thisRow[8] < int(invModeMin):
				invModeDict['status'] = 'outrange'
				invModeDict['description'] = 'out of range'
				invModeDict['current_val'] = 'out of range'

			if thisRow[13] == None:
				opCountRecDict['status'] = 'Unknown'
				opCountRecDict['description'] = 'Unknown'
				opCountRecDict['current_val'] = 'NO VALUE'
			elif thisRow[13] > int(opCountRecMax) and thisRow[13] < int(opCountRecMin):
				opCountRecDict['status'] = 'outrange'
				opCountRecDict['description'] = 'out of range'
				opCountRecDict['current_val'] = 'out of range'

			if thisRow[12] == None:
				opCountInvDict['status'] = 'Unknown'
				opCountInvDict['description'] = 'Unknown'
				opCountInvDict['current_val'] = 'NO VALUE'
			elif thisRow[12] > int(opCountInvMax) and thisRow[12] < int(opCountInvMin):
				opCountInvDict['status'] = 'outrange'
				opCountInvDict['description'] = 'out of range'
				opCountInvDict['current_val'] = 'out of range'

		else:
			rec1TopDict['current_val'] = 'NO VALUE'
			rec1BottomDict['current_val'] = 'NO VALUE'
			rec2TopDict['current_val'] = 'NO VALUE'
			rec2BottomDict['current_val'] = 'NO VALUE'
			invTopDict['current_val'] = 'NO VALUE'
			invBottomDict['current_val'] = 'NO VALUE'
			thy1Dict['current_val'] = 'NO VALUE'
			thy2Dict['current_val'] = 'NO VALUE'
			igbt1Dict['current_val'] = 'NO VALUE'
			recModeDict['current_val'] = 'NO VALUE'
			invModeDict['current_val'] = 'NO VALUE'
			opCountInvDict['current_val'] = 'NO VALUE'
			opCountRecDict['current_val'] = 'NO VALUE'

			rec1TopDict['status'] = 'Unknown'
			rec1TopDict['description'] = 'Unknown'
			rec2TopDict['status'] = 'Unknown'
			rec2TopDict['description'] = 'Unknown'
			invTopDict['status'] = 'Unknown'
			invTopDict['description'] = 'Unknown'
			thy1Dict['status'] = 'Unknown'
			thy1Dict['description'] = 'Unknown'
			thy2Dict['status'] = 'Unknown'
			thy2Dict['description'] = 'Unknown'
			igbt1Dict['status'] = 'Unknown'
			igbt1Dict['description'] = 'Unknown'
			recModeDict['status'] = 'Unknown'
			recModeDict['description'] = 'Unknown'
			invModeDict['status'] = 'Unknown'
			invModeDict['description'] = 'Unknown'
			rec1BottomDict['status'] = 'Unknown'
			rec1BottomDict['description'] = 'Unknown'
			rec2BottomDict['status'] = 'Unknown'
			rec2BottomDict['description'] = 'Unknown'
			invBottomDict['status'] = 'Unknown'
			invBottomDict['description'] = 'Unknown'
			opCountRecDict['status'] = 'Unknown'
			opCountRecDict['description'] = 'Unknown'
			opCountInvDict['status'] = 'Unknown'
			opCountInvDict['description'] = 'Unknown'
	
		# Populate the static values from postgre
		for te in dcRangeList:
			if te[26] == equipment_type:
				rec1TopDict['min_val'] = te[0]
				rec1TopDict['max_val'] = te[1]
				rec1BottomDict['min_val'] = te[2]
				rec1BottomDict['max_val'] = te[3]
				invTopDict['min_val'] = te[4]
				invTopDict['max_val'] = te[5]
				thy1Dict['min_val'] = te[6]
				thy1Dict['max_val'] = te[7]
				thy2Dict['min_val'] = te[8]
				thy2Dict['max_val'] = te[9]
				igbt1Dict['min_val'] = te[10]
				igbt1Dict['max_val'] = te[11]
				recModeDict['min_val'] = te[12]
				recModeDict['max_val'] = te[13]
				invModeDict['min_val'] = te[14]
				invModeDict['max_val'] = te[15]
				rec2TopDict['min_val'] = te[16]
				rec2TopDict['max_val'] = te[17]
				rec2BottomDict['min_val'] = te[18]
				rec2BottomDict['max_val'] = te[19]
				invBottomDict['min_val'] = te[20]
				invBottomDict['max_val'] = te[21]
				opCountRecDict['min_val'] = te[22]
				opCountRecDict['max_val'] = te[23]
				opCountInvDict['min_val'] = te[24]
				opCountInvDict['max_val'] = te[25]
				break
				
		for te in dcThresholdList:
			rec1TopDict['threshold_val1'] = te[0]
			rec1BottomDict['threshold_val1'] = te[3]
			invTopDict['threshold_val1'] = te[2]
			rec2TopDict['threshold_val1'] = te[1]
			rec2BottomDict['threshold_val1'] = te[4]
			invBottomDict['threshold_val1'] = te[5]
			thy1Dict['threshold_val1'] = te[6]
			thy2Dict['threshold_val1'] = te[7]
			igbt1Dict['threshold_val1'] = te[8]
			opCountRecDict['threshold_val1'] = te[9]
			opCountInvDict['threshold_val1'] = te[10]
			recModeDict['threshold_val1'] = te[11]
			invModeDict['threshold_val1'] = te[12]
			break

		queryStatement = "select record_time,component,warning_code from "+config.WARNING_LOGS+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code = %s and component like 'doubleconverter:%%' and status = '0' order by record_time DESC"
		parameter = [station_id,system_id,subsystem_id,detail_code]
		resultList = queryPostgre(queryStatement,parameter)

		# Loop through the entire resultset, processing the data accordingly
		for thisRow in resultList:
			if thisRow[1] == 'doubleconverter:paneltemp1rec1':
				if thisRow[2] != 'NA':
					rec1TopDict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							rec1TopDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:paneltemp1rec2' :
				if thisRow[2] != 'NA':
					rec2TopDict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							rec2TopDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:paneltemp1inv' :
				if thisRow[2] != 'NA':
					invTopDict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							invTopDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:moduletempthy1' :
				if thisRow[2] != 'NA':
					thy1Dict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							thy1Dict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:moduletempthy2':
				if thisRow[2] != 'NA':
					thy2Dict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							thy2Dict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:moduletempigbt1':
				if thisRow[2] != 'NA':
					igbt1Dict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							igbt1Dict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:maxpowerrec':
				if thisRow[2] != 'NA':
					recModeDict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							recModeDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:maxpowerinv' :
				if thisRow[2] != 'NA':
					invModeDict['status'] = 'Warning'
					for te in warningDef:
						if te[2] == thisRow[2]:
							invModeDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:paneltemp2rec1' :
				if thisRow[2] != 'NA':
					rec1BottomDict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							rec1BottomDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:paneltemp2rec2':
				if thisRow[2] != 'NA':
					rec2BottomDict['status'] = 'Warning'
					for te in warningDef:
						if te[2] == thisRow[2]:
							rec2BottomDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:paneltemp2inv':
				if thisRow[2] != 'NA':
					invBottomDict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							invBottomDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:operationrec':
				if thisRow[2] != 'NA':
					opCountRecDict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							opCountRecDict['description'] = te[1]
							break

			elif thisRow[1] == 'doubleconverter:operationinv':
				if thisRow[2] != 'NA':
					opCountInvDict['status'] = 'Warning'
					for te in warningDef:
						if te[0] == thisRow[2]:
							opCountInvDict['description'] = te[1]
							break

		currentReadingList.append(rec1TopDict)
		currentReadingList.append(rec1BottomDict)
		currentReadingList.append(rec2TopDict)
		currentReadingList.append(rec2BottomDict)
		currentReadingList.append(invTopDict)
		currentReadingList.append(invBottomDict)
		currentReadingList.append(thy1Dict)
		currentReadingList.append(thy2Dict)
		currentReadingList.append(igbt1Dict)
		currentReadingList.append(recModeDict)
		currentReadingList.append(invModeDict)
		currentReadingList.append(opCountRecDict)
		currentReadingList.append(opCountInvDict)

		responseDict['current_reading'] = currentReadingList

		resultJSON = processJSON(responseDict)

		return processResponse(resultJSON,'OK')


