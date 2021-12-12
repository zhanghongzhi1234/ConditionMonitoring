
from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status
from rest_framework.views import APIView

from operator import itemgetter, attrgetter

import requests
import json
import datetime
import calendar

import time
import math

from backend.utilities.druidQuery import queryDruid
from backend.utilities.postgreQuery import queryPostgre
from backend.utilities.postgreUpdate import updatePostgre
from backend.utilities.hiveQuery import queryHive
from backend.utilities.returnResponse import processResponse
from backend.utilities.returnTimeSeries import processTimeSeries
from backend.utilities.returnJSON import processJSON
from backend.utilities.returnInterval import processInterval
from backend.utilities.verifyConnection import checkConnection

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

class SwitchgearPartialDischargeView(APIView):

	# Declare the static class variables
	global equipmentList
	global swRangeList

	staticDataInitDone = 'FALSE'

	while staticDataInitDone == "FALSE":

		if config.CHECKPOSTGRECONNECTION == 'TRUE':
			connection_status = checkConnection()
		elif config.CHECKPOSTGRECONNECTION == 'FALSE':
			connection_status = 200

		if connection_status == 200 and (connection_status != 'Error while connecting to PostgreSQL' or connection_status != 'Errors encountered!'):
			# Add all the static datasources here

			queryStatement = "select acronym_asset_name,equipment_category,equipment_type,equipment_type_name,station_id,system_id,subsystem_id,detail_code,manufacturer,child_entity from "+config.EQUIPMENT_INFO+"  where equipment = 'switchgear' order by acronym_asset_name"
			parameter = []
			equipmentList = queryPostgre(queryStatement,parameter)

			queryStatement = "select min_average_powercountrate,max_average_powercountrate,min_average_power_peakhold,max_average_power_peakhold,min_pd_event_count,max_pd_event_count,min_peak_power_peak_hold,max_peak_power_peak_hold,equipment_type from "+config.PDM_RANGE+""
			parameter = []
			swRangeList = queryPostgre(queryStatement,parameter)

			staticDataInitDone = 'TRUE'
		else:
			# Wait/Sleep for 10 seconds before retrying connection
			print('Attention: PostgreSQL connection error.')
			print('Retrying connection in 10 seconds. Please wait.')
			time.sleep(10)

	def get (self, request, *args, **kwargs):
		periodicity = self.request.query_params.get('periodicity')
		whichType = self.request.query_params.get('type')
		assetName = self.request.query_params.get('equipment_code')

		# If periodicity is custom, then default it as 'daily'
		if periodicity == 'custom':
			periodicity = 'daily'

		station_id = None
		system_id = None
		subsystem_id = None
		detail_code = None
		equipment_type = None

		# find the system_id given the asset_name
		for te in equipmentList:
			if te[0] == assetName:
				child_entity = te[9]
				equipment_type = te[2]
				child_info = child_entity.split(",")
				# PDM is the third 
				entity_name = child_info[2]
				entity_info = entity_name.split(".")
				station_id = entity_info[0]
				system_id = entity_info[1]
				subsystem_id = entity_info[2]
				detail_code = entity_info[3]
				break

		entityName = ''+station_id+'.'+system_id+'.'+subsystem_id+'.'+detail_code+''

		if periodicity == 'daily':

			startHour = (datetime.datetime.utcnow() - datetime.timedelta(hours=24) + datetime.timedelta(hours=8))
			start_time = ""+str(startHour.year)+"-"+str(startHour.month)+"-"+str(startHour.day)+" "+str(startHour.hour)+":"+str(startHour.minute)+":"+str(startHour.second)+""
			endHour = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))			
			end_time = ""+str(endHour.year)+"-"+str(endHour.month)+"-"+str(endHour.day)+" "+str(endHour.hour)+":"+str(endHour.minute)+":"+str(endHour.second)+""	
		
		elif periodicity == 'weekly':

			startHour = (datetime.datetime.utcnow() - datetime.timedelta(days=7) + datetime.timedelta(hours=8))
			start_time = ""+str(startHour.year)+"-"+str(startHour.month)+"-"+str(startHour.day)+" "+str(startHour.hour)+":"+str(startHour.minute)+":"+str(startHour.second)+""
			endHour = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))			
			end_time = ""+str(endHour.year)+"-"+str(endHour.month)+"-"+str(endHour.day)+" "+str(endHour.hour)+":"+str(endHour.minute)+":"+str(endHour.second)+""

		elif periodicity == 'monthly':

			startHour = (datetime.datetime.utcnow() - datetime.timedelta(days=30) + datetime.timedelta(hours=8))
			start_time = ""+str(startHour.year)+"-"+str(startHour.month)+"-"+str(startHour.day)+" "+str(startHour.hour)+":"+str(startHour.minute)+":"+str(startHour.second)+""
			endHour = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))			
			end_time = ""+str(endHour.year)+"-"+str(endHour.month)+"-"+str(endHour.day)+" "+str(endHour.hour)+":"+str(endHour.minute)+":"+str(endHour.second)+""
			
		elif periodicity == 'yearly':

			startHour = (datetime.datetime.utcnow() - datetime.timedelta(days=365) + datetime.timedelta(hours=8))
			start_time = ""+str(startHour.year)+"-"+str(startHour.month)+"-"+str(startHour.day)+" "+str(startHour.hour)+":"+str(startHour.minute)+":"+str(startHour.second)+""
			endHour = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))			
			end_time = ""+str(endHour.year)+"-"+str(endHour.month)+"-"+str(endHour.day)+" "+str(endHour.hour)+":"+str(endHour.minute)+":"+str(endHour.second)+""

		interval = processInterval(start_time,end_time)
		
		if whichType == 'ap-count-rate':
			# Get the ap-count-rate for the past 24 hours

			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}

			channelList = []
			timeList = []
			count = 1
			pdmcount = 1
			lowestPDM = 0
			highestPDM = 0

			retrieveData = 'FALSE'

			channelOne = {"name":"CH1","data":[]}
			channelTwo = {"name":"CH2","data":[]}
			channelThree = {"name":"CH3","data":[]}
			channelFour = {"name":"CH4","data":[]}
			channelFive = {"name":"CH5","data":[]}
			channelSix = {"name":"CH6","data":[]}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#for te in swRangeList:
			#	if te[8] == equipment_type:
			#		responseDict['min_val'] = te[0]
			#		responseDict['max_val'] = te[1]	

			if end_time == None:		

				queryStatement = "select DATE_FORMAT(record_time,'dd-MM-yyyy HH:mm:ss') as time_interval, average_powercountrate,station_id,system_id,subsystem_id,detail_code from "+config.PARTIAL_DISCHARGE_MONITOR+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code like %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id like %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:	

				queryStatement = "select DATE_FORMAT(record_time,'dd-MM-yyyy HH:mm:ss') as time_interval, average_powercountrate,station_id,system_id,subsystem_id,detail_code from "+config.PARTIAL_DISCHARGE_MONITOR+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code like %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id like %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,end_time,entityName]

			pdmList = queryHive(queryStatement,parameter)

			if pdmList != None:
				if len(pdmList) > 0:
					pdmList = sorted(pdmList, key=itemgetter(0))

				for thisRow in pdmList:
					# Take careful consideration when adding timestamp to time axis
					# For each timestamp, there would be 6 values for each 6 channels
					# Take note that pdmList is already sorted according to the timestamp
					if thisRow[0] != previousDate:
						if count == interval:
							timeList.append(thisRow[0])	
							previousDate = thisRow[0]
							retrieveData = 'TRUE'
							count = 1
						else:
							count += 1
							retrieveData = 'FALSE'

					if retrieveData == 'TRUE':
						if thisRow[1] != None:
							pdmData = round(thisRow[1],2) 
							
							if thisRow[5].find(config.PDM_CHANNEL_1) != -1:
								channelOne['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_2) != -1:
								channelTwo['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_3) != -1:
								channelThree['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_4) != -1:
								channelFour['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_5) != -1:
								channelFive['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_6) != -1:
								channelSix['data'].append(pdmData)

						elif thisRow[1] == None:
							if thisRow[5].find(config.PDM_CHANNEL_1) != -1:
								channelOne['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_2) != -1:
								channelTwo['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_3) != -1:
								channelThree['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_4) != -1:
								channelFour['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_5) != -1:
								channelFive['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_6) != -1:
								channelSix['data'].append(None)

							pdmData = 0

						if pdmData > highestPDM:
							highestPDM = pdmData
						elif pdmData < lowestPDM:
							lowestPDM = pdmData

			channelList.append(channelOne)
			channelList.append(channelTwo)
			channelList.append(channelThree)
			channelList.append(channelFour)
			channelList.append(channelFive)
			channelList.append(channelSix)

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList
			responseDict['data_series'] = channelList

			responseDict['min_val'] = round(lowestPDM - (highestPDM*0.3))
			responseDict['max_val'] = round(highestPDM + (highestPDM*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestPDM) + 0.5) / (1 + 0.3)

			if highestPDM < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestPDM + (highestPDM*0.3)) + 1

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')


		elif whichType == 'pd-event-count':
			# Get the pd-event-count for the past 24 hours
			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}

			channelList = []
			timeList = []
			count = 1
			pdmcount = 1
			lowestPDM = 0
			highestPDM = 0

			retrieveData = 'FALSE'

			channelOne = {"name":"CH1","data":[]}
			channelTwo = {"name":"CH2","data":[]}
			channelThree = {"name":"CH3","data":[]}
			channelFour = {"name":"CH4","data":[]}
			channelFive = {"name":"CH5","data":[]}
			channelSix = {"name":"CH6","data":[]}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#for te in swRangeList:
			#	if te[8] == equipment_type:
			#		responseDict['min_val'] = te[4]
			#		responseDict['max_val'] = te[5]	

			if end_time == None:		

				queryStatement = "select DATE_FORMAT(record_time,'dd-MM-yyyy HH:mm:ss') as time_interval, pd_event_count,station_id,system_id,subsystem_id,detail_code from "+config.PARTIAL_DISCHARGE_MONITOR+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code like %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id like %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:	

				queryStatement = "select DATE_FORMAT(record_time,'dd-MM-yyyy HH:mm:ss') as time_interval, pd_event_count,station_id,system_id,subsystem_id,detail_code from "+config.PARTIAL_DISCHARGE_MONITOR+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code like %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id like %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,end_time,entityName]

			pdmList = queryHive(queryStatement,parameter)

			if pdmList != None:
				if len(pdmList) > 0:
					pdmList = sorted(pdmList, key=itemgetter(0))

				for thisRow in pdmList:
					# Take careful consideration when adding timestamp to time axis
					# For each timestamp, there would be 6 values for each 6 channels
					# Take note that pdmList is already sorted according to the timestamp
					if thisRow[0] != previousDate:
						if count == interval:
							timeList.append(thisRow[0])	
							previousDate = thisRow[0]
							retrieveData = 'TRUE'
							count = 1
						else:
							count += 1
							retrieveData = 'FALSE'

					if retrieveData == 'TRUE':
						if thisRow[1] != None:
							pdmData = round(thisRow[1],2) 
							
							if thisRow[5].find(config.PDM_CHANNEL_1) != -1:
								channelOne['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_2) != -1:
								channelTwo['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_3) != -1:
								channelThree['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_4) != -1:
								channelFour['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_5) != -1:
								channelFive['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_6) != -1:
								channelSix['data'].append(pdmData)

						elif thisRow[1] == None:
							if thisRow[5].find(config.PDM_CHANNEL_1) != -1:
								channelOne['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_2) != -1:
								channelTwo['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_3) != -1:
								channelThree['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_4) != -1:
								channelFour['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_5) != -1:
								channelFive['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_6) != -1:
								channelSix['data'].append(None)

							pdmData = 0

						if pdmData > highestPDM:
							highestPDM = pdmData
						elif pdmData < lowestPDM:
							lowestPDM = pdmData

			channelList.append(channelOne)
			channelList.append(channelTwo)
			channelList.append(channelThree)
			channelList.append(channelFour)
			channelList.append(channelFive)
			channelList.append(channelSix)

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList
			responseDict['data_series'] = channelList

			responseDict['min_val'] = round(lowestPDM - (highestPDM*0.3))
			responseDict['max_val'] = round(highestPDM + (highestPDM*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestPDM) + 0.5) / (1 + 0.3)

			if highestPDM < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestPDM + (highestPDM*0.3)) + 1

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')
			

		elif whichType == 'ap-peak-hold':
			# Get the ap-peak-hold for the past 24 hours
			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}

			channelList = []
			timeList = []
			count = 1
			pdmcount = 1
			lowestPDM = 0
			highestPDM = 0

			retrieveData = 'FALSE'

			channelOne = {"name":"CH1","data":[]}
			channelTwo = {"name":"CH2","data":[]}
			channelThree = {"name":"CH3","data":[]}
			channelFour = {"name":"CH4","data":[]}
			channelFive = {"name":"CH5","data":[]}
			channelSix = {"name":"CH6","data":[]}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#for te in swRangeList:
			#	if te[8] == equipment_type:
			#		responseDict['min_val'] = te[2]
			#		responseDict['max_val'] = te[3]	

			if end_time == None:		

				queryStatement = "select DATE_FORMAT(record_time,'dd-MM-yyyy HH:mm:ss') as time_interval, average_power_peakhold,station_id,system_id,subsystem_id,detail_code from "+config.PARTIAL_DISCHARGE_MONITOR+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code like %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id like %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:	

				queryStatement = "select DATE_FORMAT(record_time,'dd-MM-yyyy HH:mm:ss') as time_interval, average_power_peakhold,station_id,system_id,subsystem_id,detail_code from "+config.PARTIAL_DISCHARGE_MONITOR+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code like %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id like %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,end_time,entityName]

			pdmList = queryHive(queryStatement,parameter)

			if pdmList != None:
				if len(pdmList) > 0:
					pdmList = sorted(pdmList, key=itemgetter(0))

				for thisRow in pdmList:
					# Take careful consideration when adding timestamp to time axis
					# For each timestamp, there would be 6 values for each 6 channels
					# Take note that pdmList is already sorted according to the timestamp
					if thisRow[0] != previousDate:
						if count == interval:
							timeList.append(thisRow[0])	
							previousDate = thisRow[0]
							retrieveData = 'TRUE'
							count = 1
						else:
							count += 1
							retrieveData = 'FALSE'

					if retrieveData == 'TRUE':
						if thisRow[1] != None:
							pdmData = round(thisRow[1],2) 
							
							if thisRow[5].find(config.PDM_CHANNEL_1) != -1:
								channelOne['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_2) != -1:
								channelTwo['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_3) != -1:
								channelThree['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_4) != -1:
								channelFour['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_5) != -1:
								channelFive['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_6) != -1:
								channelSix['data'].append(pdmData)

						elif thisRow[1] == None:
							if thisRow[5].find(config.PDM_CHANNEL_1) != -1:
								channelOne['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_2) != -1:
								channelTwo['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_3) != -1:
								channelThree['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_4) != -1:
								channelFour['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_5) != -1:
								channelFive['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_6) != -1:
								channelSix['data'].append(None)

							pdmData = 0

						if pdmData > highestPDM:
							highestPDM = pdmData
						elif pdmData < lowestPDM:
							lowestPDM = pdmData

			channelList.append(channelOne)
			channelList.append(channelTwo)
			channelList.append(channelThree)
			channelList.append(channelFour)
			channelList.append(channelFive)
			channelList.append(channelSix)

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList
			responseDict['data_series'] = channelList

			responseDict['min_val'] = round(lowestPDM - (highestPDM*0.3))
			responseDict['max_val'] = round(highestPDM + (highestPDM*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestPDM) + 0.5) / (1 + 0.3)

			if highestPDM < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestPDM + (highestPDM*0.3)) + 1

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')
			

		elif whichType == 'pp-peak-hold':
			# Get the pp-peak-hold for the past 24 hours
			responseDict = {
					"min_val":"",
					"max_val":"",
					"time_series":[],
					"data_series":[]
					}

			channelList = []
			timeList = []
			count = 1
			pdmcount = 1
			lowestPDM = 0
			highestPDM = 0

			retrieveData = 'FALSE'

			channelOne = {"name":"CH1","data":[]}
			channelTwo = {"name":"CH2","data":[]}
			channelThree = {"name":"CH3","data":[]}
			channelFour = {"name":"CH4","data":[]}
			channelFive = {"name":"CH5","data":[]}
			channelSix = {"name":"CH6","data":[]}

			# Patch to make the range more flexible. Patch to be found below
			# This section will be commented off
			#for te in swRangeList:
			#	if te[8] == equipment_type:
			#		responseDict['min_val'] = te[6]
			#		responseDict['max_val'] = te[7]	

			if end_time == None:		

				queryStatement = "select DATE_FORMAT(record_time,'dd-MM-yyyy HH:mm:ss') as time_interval, peak_power_peak_hold,station_id,system_id,subsystem_id,detail_code from "+config.PARTIAL_DISCHARGE_MONITOR+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code like %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp() and equipment_id like %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,entityName]

			else:	

				queryStatement = "select DATE_FORMAT(record_time,'dd-MM-yyyy HH:mm:ss') as time_interval, peak_power_peak_hold,station_id,system_id,subsystem_id,detail_code from "+config.PARTIAL_DISCHARGE_MONITOR+" where station_id = %s and system_id = %s and subsystem_id= %s and detail_code like %s and unix_timestamp(record_time,'dd-MM-yyyy HH:mm:ss') between unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and unix_timestamp(%s,'yyyy-MM-dd HH:mm:ss') and equipment_id like %s and year = cast(DATE_FORMAT(record_time,'yyyy') as int) and month = cast(DATE_FORMAT(record_time,'MM') as int)"
				parameter = [station_id,system_id,subsystem_id,detail_code,start_time,end_time,entityName]
						
			pdmList = queryHive(queryStatement,parameter)

			if pdmList != None:
				if len(pdmList) > 0:
					pdmList = sorted(pdmList, key=itemgetter(0))

				for thisRow in pdmList:
					# Take careful consideration when adding timestamp to time axis
					# For each timestamp, there would be 6 values for each 6 channels
					# Take note that pdmList is already sorted according to the timestamp
					if thisRow[0] != previousDate:
						if count == interval:
							timeList.append(thisRow[0])	
							previousDate = thisRow[0]
							retrieveData = 'TRUE'
							count = 1
						else:
							count += 1
							retrieveData = 'FALSE'

					if retrieveData == 'TRUE':
						if thisRow[1] != None:
							pdmData = round(thisRow[1],2) 
							
							if thisRow[5].find(config.PDM_CHANNEL_1) != -1:
								channelOne['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_2) != -1:
								channelTwo['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_3) != -1:
								channelThree['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_4) != -1:
								channelFour['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_5) != -1:
								channelFive['data'].append(pdmData)
							elif thisRow[5].find(config.PDM_CHANNEL_6) != -1:
								channelSix['data'].append(pdmData)

						elif thisRow[1] == None:
							if thisRow[5].find(config.PDM_CHANNEL_1) != -1:
								channelOne['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_2) != -1:
								channelTwo['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_3) != -1:
								channelThree['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_4) != -1:
								channelFour['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_5) != -1:
								channelFive['data'].append(None)
							elif thisRow[5].find(config.PDM_CHANNEL_6) != -1:
								channelSix['data'].append(None)

							pdmData = 0

						if pdmData > highestPDM:
							highestPDM = pdmData
						elif pdmData < lowestPDM:
							lowestPDM = pdmData

			channelList.append(channelOne)
			channelList.append(channelTwo)
			channelList.append(channelThree)
			channelList.append(channelFour)
			channelList.append(channelFive)
			channelList.append(channelSix)

			# if no timestamp is added, meaning no data is added.
			# Add a representational time axis of the periodicity requested
			# To shows signs of inactivity, LTA request
			if len(timeList) == 0:
				timeInfo = processTimeSeries(periodicity,'historical')
				timeList = timeInfo['displaySeries']

			responseDict['time_series'] = timeList
			responseDict['data_series'] = channelList

			responseDict['min_val'] = round(lowestPDM - (highestPDM*0.3))
			responseDict['max_val'] = round(highestPDM + (highestPDM*0.3))

			# Do a double check here.
			# If both min_val and max_val are the same. Nothing will be plotted.
			# In order to round to the next number, we need to add for highest value, at least floor(highest value) + 0.5
			# Since round() function >= 0.5 goes to the next number
			# Let highest value be A
			# A + (A * 0.3) >= math.floor(A) + 0.5
			# A (1 + 0.3) >= math.floor(A) + 0.5
			# A >= (math.floor(A) + 0.5) / (1 + 0.3) 

			toNext = (math.floor(highestPDM) + 0.5) / (1 + 0.3)

			if highestPDM < toNext:
				# Add one to the highest value
				responseDict['max_val'] = round(highestPDM + (highestPDM*0.3)) + 1

			resultJSON = processJSON(responseDict)

			return processResponse(resultJSON,'OK')			

		else:
			resultJSON = {}
			return processResponse(resultJSON,'NOT FOUND')












