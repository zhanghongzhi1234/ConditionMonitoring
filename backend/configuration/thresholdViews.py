
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
from backend.utilities.verifyConnection import checkConnection
from backend.utilities.hashMessage import performEncodedHash

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

# Create your views here.

class ThresholdView(APIView):
	# Declare the static class variables
	global equipmentList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200
	
		if connection_status == 200 and (connection_status != 'No route to host' or connection_status != 'Errors encountered!'):	
			# Add all the static datasources here

			queryStatement = "select DISTINCT equipment,equipment_type,equipment_type_name from "+config.EQUIPMENT_INFO+""
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		category = self.request.query_params.get('category')
		configSet = self.request.query_params.get('configset_code')

		#queryStatement = "select equipment_type from "+config.EQUIPMENT_INFO+" where equipment_type_name = '"+configSet+"'"
		#resultItem = queryPostgre(queryStatement,parameter)
		#resultItem = resultItem[0][0]

		resultItem = configSet

		if category == 'transformer':
		
			responseDict = {
					"item_code":"",
					"category":"",
					"equipment_type":"",
					"key_gas":{},
					"winding_oil_temperature":{},
					"current_reading":{},
					"last_update_by":"",
					"last_update_at":""
					}

			keyGas = {
				"h2":"",
				"ch4":"",
				"c2h2":"",
				"c2h4":"",
				"c2h6":"",
				"co":""
				}

			windingOilTemperature = {
						"winding_warning1":"",
						"winding_warning2":"",
						"oil_warning1":"",
						"oil_warning2":"",
						"ambient":""
						}

			currentReadings = {
					"l1":"",
					"l2":"",
					"l3":"",
					"total_loading":""
					}

			queryStatement = "select windings1,windings2,currentl1,currentl2,currentl3,total_loading,oils1,oils2,gas_h2,gas_ch4,gas_c2h2,gas_c2h4,gas_c2h6,gas_co,ambient,last_update_by,TO_CHAR(record_time,'yyyy-MM-dd HH24:MI:ss') from "+config.TRANSFORMER_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
			parameter = [resultItem] 
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				thisData = resultList[0]

				keyGas['h2'] = thisData[8]
				keyGas['ch4'] = thisData[9]
				keyGas['c2h2'] = thisData[10]
				keyGas['c2h4'] = thisData[11]
				keyGas['c2h6'] = thisData[12]
				keyGas['co'] = thisData[13]

				windingOilTemperature['winding_warning1'] = thisData[0]
				windingOilTemperature['winding_warning2'] = thisData[1]
				windingOilTemperature['oil_warning1'] = thisData[6]
				windingOilTemperature['oil_warning2'] = thisData[7]
				windingOilTemperature['ambient'] = thisData[14]

				currentReadings['l1'] = thisData[2]
				currentReadings['l2'] = thisData[3]
				currentReadings['l3'] = thisData[4]
				currentReadings['total_loading'] = thisData[5]

				responseDict['last_update_by'] = thisData[15]
				responseDict['last_update_at'] = thisData[16]

			responseDict['key_gas'] = keyGas
			responseDict['winding_oil_temperature'] = windingOilTemperature
			responseDict['current_reading'] = currentReadings

			responseDict['item_code'] = configSet
			responseDict['category'] = category
			responseDict['equipment_type'] = resultItem
		
			resultJSON = processJSON(responseDict)
			return processResponse(resultJSON,'OK')

		elif category == 'switchgear':

			responseDict = {
					"item_code":"",
					"category":"",
					"equipment_type":"",
					"operation_count":{},
					"panel_temperature":{},
					"dc_feeder":{},
					"last_update_by":"",
					"last_update_at":""
					}

			countParameter = {
				"pm":"",
				"service":"",
				"trip":""
				}

			panelTemperatures = {
				"shunt":"",
				"busbar":"",
				"cable":"",
				"control":""
				}

			resistances = {
				"cts":"",
				"ste":""
				}

			queryStatement = "select pm_count,service_count,trip_count,shunt_temp,busbar_temp,cable_temp,control_temp,rx,rz,last_update_by,TO_CHAR(record_time,'yyyy-MM-dd HH24:MI:ss') from "+config.SWITCHGEAR_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
			parameter = [resultItem]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				thisData = resultList[0]

				countParameter['pm'] = thisData[0]
				countParameter['service'] = thisData[1]
				countParameter['trip'] = thisData[2]

				panelTemperatures['shunt'] = thisData[3]
				panelTemperatures['busbar'] = thisData[4]
				panelTemperatures['cable'] = thisData[5]
				panelTemperatures['control'] = thisData[6]

				resistances['cts'] = thisData[7]
				resistances['ste'] = thisData[8]

				responseDict['last_update_by'] = thisData[9]
				responseDict['last_update_at'] = thisData[10]

			responseDict['operation_count'] = countParameter
			responseDict['panel_temperature'] = panelTemperatures
			responseDict['dc_feeder'] = resistances

			responseDict['item_code'] = configSet
			responseDict['category'] = category
			responseDict['equipment_type'] = resultItem

			resultJSON = processJSON(responseDict)
			return processResponse(resultJSON,'OK')

		elif category == 'dconverter':

			responseDict = {
					"item_code":"",
					"category":"",
					"equipment_type":"",
					"operation_count":{},
					"max_power":{},
					"operational_time":{},
					"module_temperature":{},
					"panel_temperature":{},
					"cooling_fan":{},
					"last_update_by":"",
					"last_update_at":""
					}

			moduleTemperatures = {
				"thy1":"",
				"thy2":"",
				"igbt1":""
				}

			panelTemperatures = {
				"rec1_top":"",
				"rec2_top":"",
				"inv_top":"",
				"rec1_bottom":"",
				"rec2_bottom":"",
				"inv_bottom":""
				}

			num_operations = {
				"rec_mode":"",
				"inv_mode":""
				}

			operating_time = {
				"rec_mode":"",
				"inv_mode":""
				}

			operating_cycle = {
                                "rec_mode":"",
                                "inv_mode":""
                                }

			max_power = {
				"rec_mode":"",
				"inv_mode":""
				}

			fans = {
				"operational_time":"",
				"min_current":"",
				"max_current":""
				}

			queryStatement = "select module_temp_thy1,module_temp_thy2,module_temp_igbt1,panel_temp_1_rec1,panel_temp_1_rec2,panel_temp_1_inv,panel_temp_2_rec1,panel_temp_2_rec2,panel_temp_2_inv,num_operations_rec,num_operations_inv,operating_time_rec,operating_time_inv,operating_cycle_rec,operating_cycle_inv,max_power_rec,max_power_inv,operational_time_fans,min_operational_current_fans,max_operational_current_fans,last_update_by,TO_CHAR(record_time,'yyyy-MM-dd HH24:MI:ss') from "+config.DOUBLECONVERTER_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
			parameter = [resultItem]
			resultList = queryPostgre(queryStatement,parameter)


			if len(resultList) > 0:
				thisData = resultList[0]

				moduleTemperatures['thy1'] = thisData[0]
				moduleTemperatures['thy2'] = thisData[1]
				moduleTemperatures['igbt1'] = thisData[2]

				panelTemperatures['rec1_top'] = thisData[3]
				panelTemperatures['rec2_top'] = thisData[4]
				panelTemperatures['inv_top'] = thisData[5]
				panelTemperatures['rec1_bottom'] = thisData[6]
				panelTemperatures['rec2_bottom'] = thisData[7]
				panelTemperatures['inv_bottom'] = thisData[8]

				num_operations['rec_mode'] = thisData[9]
				num_operations['inv_mode'] = thisData[10]

				operating_time['rec_mode'] = thisData[11]
				operating_time['inv_mode'] = thisData[12]

				operating_cycle['rec_mode'] = thisData[13]
				operating_cycle['inv_mode'] = thisData[14]

				max_power['rec_mode'] = thisData[15]
				max_power['inv_mode'] = thisData[16]

				fans['operational_time'] = thisData[17]
				fans['min_current'] = thisData[18]
				fans['max_current'] = thisData[19]

				responseDict['last_update_by'] = thisData[20]
				responseDict['last_update_at'] = thisData[21]

			responseDict['module_temperature'] = moduleTemperatures
			responseDict['panel_temperature'] = panelTemperatures
			responseDict['operation_count'] = num_operations
			responseDict['operational_time'] = operating_time
			responseDict['max_power'] = max_power
			responseDict['cooling_fan'] = fans

			responseDict['item_code'] = configSet
			responseDict['category'] = category 
			responseDict['equipment_type'] = resultItem

			resultJSON = processJSON(responseDict)
			return processResponse(resultJSON,'OK')

		elif category == 'rectifier':

			responseDict = {
					"item_code":"",
					"category":"",
					"equipment_type":"",
					"panel_temperature":{},
					"last_update_by":"",
					"last_update_at":""
					}

			panelTemperatures = {
				"panel_temp1":"",
				"panel_temp2":"",
				"panel_temp3":"",
				"panel_temp4":""
				}

			queryStatement = "select panel_temp_1,panel_temp_2,panel_temp_3,panel_temp_4,last_update_by,TO_CHAR(record_time,'yyyy-MM-dd HH24:MI:ss') from "+config.RECTIFIER_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
			parameter = [resultItem]
			resultList = queryPostgre(queryStatement,parameter)

			if len(resultList) > 0:
				thisData = resultList[0]

				panelTemperatures['panel_temp1'] = thisData[0]
				panelTemperatures['panel_temp2'] = thisData[1]
				panelTemperatures['panel_temp3'] = thisData[2]
				panelTemperatures['panel_temp4'] = thisData[3]

				responseDict['last_update_by'] = thisData[4]
				responseDict['last_update_at'] = thisData[5]

			responseDict['panel_temperature'] = panelTemperatures

			responseDict['item_code'] = configSet
			responseDict['category'] = category
			responseDict['equipment_type'] = resultItem

			resultJSON = processJSON(responseDict)
			return processResponse(resultJSON,'OK')

		elif category == 'inverter':
		
			responseDict = {
					"item_code":"",
					"category":"",
					"equipment_type":"",
					"operation_count":{},
					"max_power":{},
					"operational_time":{},
					"panel_temperature":{},
					"last_update_by":"",
					"last_update_at":""
					}
			operationCount = {
				"value":""
				}					
			maxPower = {
				"value":""
				}					
			operationalTime = {
				"value":""
				}		
			panelTemperatures = {
				"panel_temp1":"",
				"panel_temp2":""
				}		

			queryStatement = "select operation_counts,operation_time,max_power,panel_temp_1,panel_temp_2,last_update_by,TO_CHAR(record_time,'yyyy-MM-dd HH24:MI:ss') from "+config.INVERTER_THRESHOLD+" where equipment_type = %s order by record_time DESC LIMIT 1"
			parameter = [resultItem]
			resultList = queryPostgre(queryStatement,parameter)		

			if len(resultList) > 0:
				thisData = resultList[0]
			
				operationCount['value'] = thisData[0]
				operationalTime['value'] = thisData[1]
				maxPower['value'] = thisData[2]
				panelTemperatures['panel_temp1'] = thisData[3]
				panelTemperatures['panel_temp2'] = thisData[4]

				responseDict['last_update_by'] = thisData[5]
				responseDict['last_update_at'] = thisData[6]

			responseDict['operation_count'] = operationCount
			responseDict['operational_time'] = operationalTime	
			responseDict['max_power'] = maxPower	
			responseDict['panel_temperature'] = panelTemperatures

			responseDict['item_code'] = configSet
			responseDict['category'] = category
			responseDict['equipment_type'] = resultItem			
							
			resultJSON = processJSON(responseDict)
			return processResponse(resultJSON,'OK')
		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')
		
	def put (self, request, *args, **kwargs):

		requestData = self.request.data
		operator_id = requestData['operator_id']
		signature = requestData['signature']
		contentInfo = requestData['object']
		category = contentInfo['category']	
		item_code = contentInfo['item_code']
		equipment_type = contentInfo['equipment_type']
		last_update_by = contentInfo['last_update_by']
		last_update_at = contentInfo['last_update_at']

		if last_update_by == None:
			last_update_by = 'null'

		# For switchgear 22kv or 66kv, there are no panel temperatures nor resistances(dc feeder values).
		# Therefore, we have to set these values as 'null'	
		if category == 'switchgear':
			if contentInfo['panel_temperature']['shunt'] == None or contentInfo['panel_temperature']['shunt'] == '':
				contentInfo['panel_temperature']['shunt'] = 'null'

			if contentInfo['panel_temperature']['busbar'] == None or contentInfo['panel_temperature']['busbar'] == '':
				contentInfo['panel_temperature']['busbar'] = 'null'

			if contentInfo['panel_temperature']['cable'] == None or contentInfo['panel_temperature']['cable'] == '':
				contentInfo['panel_temperature']['cable'] = 'null'

			if contentInfo['panel_temperature']['control'] == None or contentInfo['panel_temperature']['control'] == '':
				contentInfo['panel_temperature']['control'] = 'null'

			if contentInfo['dc_feeder']['cts'] == None or contentInfo['dc_feeder']['cts'] == '':
				contentInfo['dc_feeder']['cts'] = 'null'

			if contentInfo['dc_feeder']['ste'] == None or contentInfo['dc_feeder']['ste'] == '':
				contentInfo['dc_feeder']['ste'] = 'null'

		# 3 parts of the message(to be used for the signature)
		message = None
		# Header
		header = item_code+'.'+category+'.'+equipment_type
		# Body (to be created based on the different categories)
		body = None
		# Trailer
		trailer = last_update_by+'.'+last_update_at

		# Generate the message(to be used for the signature)
		if category == 'transformer':
			body = str(contentInfo['key_gas']['h2'])+'.'+str(contentInfo['key_gas']['ch4'])+'.'+str(contentInfo['key_gas']['c2h2'])+'.'+str(contentInfo['key_gas']['c2h4'])+'.'+str(contentInfo['key_gas']['c2h6'])+'.'+str(contentInfo['key_gas']['co'])+'.'+str(contentInfo['winding_oil_temperature']['winding_warning1'])+'.'+str(contentInfo['winding_oil_temperature']['winding_warning2'])+'.'+str(contentInfo['winding_oil_temperature']['oil_warning1'])+'.'+str(contentInfo['winding_oil_temperature']['oil_warning2'])+'.'+str(contentInfo['winding_oil_temperature']['ambient'])+'.'+str(contentInfo['current_reading']['l1'])+'.'+str(contentInfo['current_reading']['l2'])+'.'+str(contentInfo['current_reading']['l3'])+'.'+str(contentInfo['current_reading']['total_loading'])

			message = header+'.'+body+'.'+trailer
			
		elif category == 'switchgear':
			body = str(contentInfo['operation_count']['pm'])+'.'+str(contentInfo['operation_count']['service'])+'.'+str(contentInfo['operation_count']['trip'])+'.'+str(contentInfo['panel_temperature']['shunt'])+'.'+str(contentInfo['panel_temperature']['busbar'])+'.'+str(contentInfo['panel_temperature']['cable'])+'.'+str(contentInfo['panel_temperature']['control'])+'.'+str(contentInfo['dc_feeder']['cts'])+'.'+str(contentInfo['dc_feeder']['ste'])
			
			message = header+'.'+body+'.'+trailer

		elif category == 'dconverter':
			body = str(contentInfo['operation_count']['inv_mode'])+'.'+str(contentInfo['operation_count']['rec_mode'])+'.'+str(contentInfo['max_power']['inv_mode'])+'.'+str(contentInfo['max_power']['rec_mode'])+'.'+str(contentInfo['operational_time']['inv_mode'])+'.'+str(contentInfo['operational_time']['rec_mode'])+'.'+str(contentInfo['module_temperature']['thy1'])+'.'+str(contentInfo['module_temperature']['thy2'])+'.'+str(contentInfo['module_temperature']['igbt1'])+'.'+str(contentInfo['panel_temperature']['rec1_top'])+'.'+str(contentInfo['panel_temperature']['rec2_top'])+'.'+str(contentInfo['panel_temperature']['inv_top'])+'.'+str(contentInfo['panel_temperature']['rec1_bottom'])+'.'+str(contentInfo['panel_temperature']['rec2_bottom'])+'.'+str(contentInfo['panel_temperature']['inv_bottom'])+'.'+str(contentInfo['cooling_fan']['operational_time'])+'.'+str(contentInfo['cooling_fan']['max_current'])+'.'+str(contentInfo['cooling_fan']['min_current'])
			
			message = header+'.'+body+'.'+trailer
			
		elif category == 'rectifier':
			body = str(contentInfo['panel_temperature']['panel_temp1'])+'.'+str(contentInfo['panel_temperature']['panel_temp2'])+'.'+str(contentInfo['panel_temperature']['panel_temp3'])+'.'+str(contentInfo['panel_temperature']['panel_temp4'])
			
			message = header+'.'+body+'.'+trailer	

		elif category == 'inverter':
			body = str(contentInfo['operation_count']['value'])+'.'+str(contentInfo['max_power']['value'])+'.'+str(contentInfo['operational_time']['value'])+'.'+str(contentInfo['panel_temperature']['panel_temp1'])+'.'+str(contentInfo['panel_temperature']['panel_temp2'])
			
			message = header+'.'+body+'.'+trailer

		# First check whether the operator_id and password is correct

		queryStatement = "select operator_password from "+config.OPERATOR_ID_PASSWORD+" where operator_id = %s order by record_time DESC LIMIT 1"
		parameter = [operator_id]
		resultList = queryPostgre(queryStatement,parameter)

		if len(resultList) > 0:
			passwordInfo = resultList[0]
			operatorPassword = passwordInfo[0]
		else:
			operatorPassword = 'NO PASSWORD'

		thisSignature=performEncodedHash(operatorPassword,""+message+"")

		if thisSignature == signature:

			if category == 'transformer':

				#updatePostgre("update "+config.TRANSFORMER_THRESHOLD+" set gas_h2 = '"+str(contentInfo['key_gas']['h2'])+"', gas_ch4 = '"+str(contentInfo['key_gas']['ch4'])+"', gas_c2h2 = '"+str(contentInfo['key_gas']['c2h2'])+"', gas_c2h4 = '"+str(contentInfo['key_gas']['c2h4'])+"', gas_c2h6 = '"+str(contentInfo['key_gas']['c2h6'])+"', gas_co = '"+str(contentInfo['key_gas']['co'])+"', windings1 = '"+str(contentInfo['winding_oil_temperature']['winding_warning1'])+"', windings2 = '"+str(contentInfo['winding_oil_temperature']['winding_warning2'])+"', oils1 = '"+str(contentInfo['winding_oil_temperature']['oil_warning1'])+"', oils2 = '"+str(contentInfo['winding_oil_temperature']['oil_warning2'])+"', ambient = '"+str(contentInfo['winding_oil_temperature']['ambient'])+"', currentl1 = '"+str(contentInfo['current_reading']['l1'])+"', currentl2 = '"+str(contentInfo['current_reading']['l2'])+"', currentl3 = '"+str(contentInfo['current_reading']['l3'])+"', total_loading = '"+str(contentInfo['current_reading']['total_loading'])+"', last_update_by = '"+operator_id+"', last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = '"+equipment_type+"'")	
				updateStatement = "update "+config.TRANSFORMER_THRESHOLD+" set gas_h2 = %s, gas_ch4 = %s, gas_c2h2 = %s, gas_c2h4 = %s, gas_c2h6 = %s, gas_co = %s, windings1 = %s, windings2 = %s, oils1 = %s, oils2 = %s, ambient = %s, currentl1 = %s, currentl2 = %s, currentl3 = %s, total_loading = %s, last_update_by = %s, last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = %s"
				parameter = [str(contentInfo['key_gas']['h2']),str(contentInfo['key_gas']['ch4']),str(contentInfo['key_gas']['c2h2']),str(contentInfo['key_gas']['c2h4']),str(contentInfo['key_gas']['c2h6']),str(contentInfo['key_gas']['co']),str(contentInfo['winding_oil_temperature']['winding_warning1']),str(contentInfo['winding_oil_temperature']['winding_warning2']),str(contentInfo['winding_oil_temperature']['oil_warning1']),str(contentInfo['winding_oil_temperature']['oil_warning2']),str(contentInfo['winding_oil_temperature']['ambient']),str(contentInfo['current_reading']['l1']),str(contentInfo['current_reading']['l2']),str(contentInfo['current_reading']['l3']),str(contentInfo['current_reading']['total_loading']),operator_id,equipment_type]
				updatePostgre(updateStatement,parameter)

			elif category == 'switchgear':

				if equipment_type == '750VDC':
					#updatePostgre("update "+config.SWITCHGEAR_THRESHOLD+" set pm_count = '"+str(contentInfo['operation_count']['pm'])+"', service_count = '"+str(contentInfo['operation_count']['service'])+"' , trip_count = '"+str(contentInfo['operation_count']['trip'])+"', shunt_temp = '"+str(contentInfo['panel_temperature']['shunt'])+"', busbar_temp = '"+str(contentInfo['panel_temperature']['busbar'])+"', cable_temp = '"+str(contentInfo['panel_temperature']['cable'])+"', control_temp = '"+str(contentInfo['panel_temperature']['control'])+"', rx = '"+str(contentInfo['dc_feeder']['cts'])+"', rz = '"+str(contentInfo['dc_feeder']['ste'])+"', last_update_by = '"+operator_id+"', last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = '"+equipment_type+"'")	
					updateStatement = "update "+config.SWITCHGEAR_THRESHOLD+" set pm_count = %s, service_count = %s, trip_count = %s, shunt_temp = %s, busbar_temp = %s, cable_temp = %s, control_temp = %s, rx = %s, rz = %s, last_update_by = %s, last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = %s"
					parameter = [str(contentInfo['operation_count']['pm']),str(contentInfo['operation_count']['service']),str(contentInfo['operation_count']['trip']),str(contentInfo['panel_temperature']['shunt']),str(contentInfo['panel_temperature']['busbar']),str(contentInfo['panel_temperature']['cable']),str(contentInfo['panel_temperature']['control']),str(contentInfo['dc_feeder']['cts']),str(contentInfo['dc_feeder']['ste']),operator_id,equipment_type]
					updatePostgre(updateStatement,parameter)
				else:
					#updatePostgre("update "+config.SWITCHGEAR_THRESHOLD+" set pm_count = '"+str(contentInfo['operation_count']['pm'])+"', service_count = '"+str(contentInfo['operation_count']['service'])+"' , trip_count = '"+str(contentInfo['operation_count']['trip'])+"', last_update_by = '"+operator_id+"', last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = '"+equipment_type+"'")	
					updateStatement = "update "+config.SWITCHGEAR_THRESHOLD+" set pm_count = %s, service_count = %s, trip_count = %s, last_update_by = %s, last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = %s"
					parameter = [str(contentInfo['operation_count']['pm']),str(contentInfo['operation_count']['service']),str(contentInfo['operation_count']['trip']),operator_id,equipment_type]
					updatePostgre(updateStatement,parameter)

			elif category == 'dconverter':

				#updatePostgre("update "+config.DOUBLECONVERTER_THRESHOLD+" set module_temp_thy1 = '"+str(contentInfo['module_temperature']['thy1'])+"', module_temp_thy2 = '"+str(contentInfo['module_temperature']['thy2'])+"', module_temp_igbt1 = '"+str(contentInfo['module_temperature']['igbt1'])+"', panel_temp_1_rec1 = '"+str(contentInfo['panel_temperature']['rec1_top'])+"', panel_temp_1_rec2 = '"+str(contentInfo['panel_temperature']['rec2_top'])+"', panel_temp_1_inv = '"+str(contentInfo['panel_temperature']['inv_top'])+"', panel_temp_2_rec1 = '"+str(contentInfo['panel_temperature']['rec1_bottom'])+"', panel_temp_2_rec2 = '"+str(contentInfo['panel_temperature']['rec2_bottom'])+"', panel_temp_2_inv = '"+str(contentInfo['panel_temperature']['inv_bottom'])+"', num_operations_rec = '"+str(contentInfo['operation_count']['rec_mode'])+"', num_operations_inv = '"+str(contentInfo['operation_count']['inv_mode'])+"', operating_time_rec = '"+str(contentInfo['operational_time']['rec_mode'])+"', operating_time_inv = '"+str(contentInfo['operational_time']['inv_mode'])+"', max_power_rec = '"+str(contentInfo['max_power']['rec_mode'])+"', max_power_inv = '"+str(contentInfo['max_power']['inv_mode'])+"', operational_time_fans = '"+str(contentInfo['cooling_fan']['operational_time'])+"', min_operational_current_fans = '"+str(contentInfo['cooling_fan']['min_current'])+"', max_operational_current_fans = '"+str(contentInfo['cooling_fan']['max_current'])+"', last_update_by = '"+operator_id+"', last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = '"+equipment_type+"'")
				updateStatement = "update "+config.DOUBLECONVERTER_THRESHOLD+" set module_temp_thy1 = %s, module_temp_thy2 = %s, module_temp_igbt1 = %s, panel_temp_1_rec1 = %s, panel_temp_1_rec2 = %s, panel_temp_1_inv = %s, panel_temp_2_rec1 = %s, panel_temp_2_rec2 = %s, panel_temp_2_inv = %s, num_operations_rec = %s, num_operations_inv = %s, operating_time_rec = %s, operating_time_inv = %s, max_power_rec = %s, max_power_inv = %s, operational_time_fans = %s, min_operational_current_fans = %s, max_operational_current_fans = %s, last_update_by = %s, last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = %s"
				parameter = [str(contentInfo['module_temperature']['thy1']),str(contentInfo['module_temperature']['thy2']),str(contentInfo['module_temperature']['igbt1']),str(contentInfo['panel_temperature']['rec1_top']),str(contentInfo['panel_temperature']['rec2_top']),str(contentInfo['panel_temperature']['inv_top']),str(contentInfo['panel_temperature']['rec1_bottom']),str(contentInfo['panel_temperature']['rec2_bottom']),str(contentInfo['panel_temperature']['inv_bottom']),str(contentInfo['operation_count']['rec_mode']),str(contentInfo['operation_count']['inv_mode']),str(contentInfo['operational_time']['rec_mode']),str(contentInfo['operational_time']['inv_mode']),str(contentInfo['max_power']['rec_mode']),str(contentInfo['max_power']['inv_mode']),str(contentInfo['cooling_fan']['operational_time']),str(contentInfo['cooling_fan']['min_current']),str(contentInfo['cooling_fan']['max_current']),operator_id,equipment_type]
				updatePostgre(updateStatement,parameter)	

			elif category == 'rectifier':

				#updatePostgre("update "+config.RECTIFIER_THRESHOLD+" set panel_temp_1 = '"+str(contentInfo['panel_temperature']['panel_temp1'])+"',panel_temp_2 = '"+str(contentInfo['panel_temperature']['panel_temp2'])+"',panel_temp_3 = '"+str(contentInfo['panel_temperature']['panel_temp3'])+"',panel_temp_4 = '"+str(contentInfo['panel_temperature']['panel_temp4'])+"', last_update_by = '"+operator_id+"', last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = '"+equipment_type+"'")	
				updateStatement = "update "+config.RECTIFIER_THRESHOLD+" set panel_temp_1 = %s,panel_temp_2 = %s,panel_temp_3 = %s,panel_temp_4 = %s, last_update_by = %s, last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = %s"
				parameter = [str(contentInfo['panel_temperature']['panel_temp1']),str(contentInfo['panel_temperature']['panel_temp2']),str(contentInfo['panel_temperature']['panel_temp3']),str(contentInfo['panel_temperature']['panel_temp4']),operator_id,equipment_type]
				updatePostgre(updateStatement,parameter)

			elif category == 'inverter':

				#updatePostgre("update "+config.INVERTER_THRESHOLD+" set panel_temp_1 = '"+str(contentInfo['panel_temperature']['panel_temp1'])+"',panel_temp_2 = '"+str(contentInfo['panel_temperature']['panel_temp2'])+"',operation_counts = '"+str(contentInfo['operation_count']['value'])+"',operation_time = '"+str(contentInfo['operational_time']['value'])+"',max_power = '"+str(contentInfo['max_power']['value'])+"', last_update_by = '"+operator_id+"', last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = '"+equipment_type+"'")	
				updateStatement = "update "+config.INVERTER_THRESHOLD+" set panel_temp_1 = %s,panel_temp_2 = %s,operation_counts = %s,operation_time = %s,max_power = %s, last_update_by = %s, last_update_at = CURRENT_TIMESTAMP, record_time = CURRENT_TIMESTAMP where equipment_type = %s"
				parameter = [str(contentInfo['panel_temperature']['panel_temp1']),str(contentInfo['panel_temperature']['panel_temp2']),str(contentInfo['operation_count']['value']),str(contentInfo['operational_time']['value']),str(contentInfo['max_power']['value']),operator_id,equipment_type]
				updatePostgre(updateStatement,parameter)
				
			return processResponse(None,'INSERTED')

		else:
			responseDict = {"error_code":"401","error_message":"Your ID and the password entered did not match our records. Please try again."}
			resultJSON = processJSON(responseDict)
			return processResponse(resultJSON,'UNAUTHORIZED')





















		

