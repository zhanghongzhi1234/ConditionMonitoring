from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status

from backend.utilities.kafkaInsert import insertKafkaDict

import requests
import json
import datetime
import calendar

import socket

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

def processLogging(logType,messageContent,process_id,thread_id,filename,linenumber,tag):

	proceed = 'FALSE'

	if logType == config.INFO and config.INFO_MODE == 'ON':
		proceed = 'TRUE'
	elif logType == config.DEBUG and config.DEBUG_MODE == 'ON':
		proceed = 'TRUE'
	elif logType == config.WARNING and config.WARNING_MODE == 'ON':
		proceed = 'TRUE'
	elif logType == config.ERROR and config.ERROR_MODE == 'ON':
		proceed = 'TRUE'
	elif logType == config.ALERT and config.ALERT_MODE == 'ON':
		proceed = 'TRUE'

	if proceed == 'TRUE':
		now = (datetime.datetime.utcnow() + datetime.timedelta(hours=8))
		datetimenow = ""+str(now.month)+"-"+str(now.day)+"-"+str(now.year)+" "+str(now.hour)+":"+str(now.minute)+":"+str(now.second)+""
		filename = filename.split("/")
		filename = filename[-1]

		full_message = "["+str(process_id)+"/"+str(thread_id)+"] "+datetimenow+" "+filename+":"+str(linenumber)+"@"+socket.gethostname()+" "+logType+"  "+messageContent+" "+tag+""
		print(full_message)

		element = {"__time":"","type":"","full_message":"","tag":""}
		element['full_message'] = full_message
		element['tag'] = tag
		element['type'] = logType

		now = datetime.datetime.utcnow()
		element['__time'] = ""+str(now.month)+"-"+str(now.day)+"-"+str(now.year)+" "+str(now.hour)+":"+str(now.minute)+":"+str(now.second)+" +00:00"

		#insertKafkaDict(config.APPLICATION_LOGS,element)
	
