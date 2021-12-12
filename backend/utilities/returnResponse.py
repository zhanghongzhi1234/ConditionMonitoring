from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status

from django.http import HttpResponse

import requests
import json
import datetime
import calendar

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

def processResponse(resultJSON,responseStatus):
	#print('Processing response...')
	if responseStatus == 'OK':

		return Response(
			data=resultJSON,
			status=status.HTTP_200_OK,
			headers=config.headers
			)

	elif responseStatus == 'NOT FOUND':

		return Response(
			status=status.HTTP_404_NOT_FOUND,
			headers=config.headers
			)

	elif responseStatus == 'INSERTED':

		return Response(
			status=status.HTTP_201_CREATED,
			headers=config.headers
			)

	elif responseStatus == 'NOT INSERTED':

		return Response(
			status=status.HTTP_400_BAD_REQUEST,
			headers=config.headers
			)

	elif responseStatus == 'UNAUTHORIZED':
		response = HttpResponse('Your ID and the password entered did not match our records. Please try again.',status = '401',reason = 'Your ID and the password entered did not match our records. Please try again.')
		return response


	else:
		response = HttpResponse('Request timed out. Please try again.',status = '408',reason = 'Request timed out. Please try again.')
		return response

		"""
		return Response(
			'Your ID and the password entered did not match our records. Please try again.',
			status=status.HTTP_401_UNAUTHORIZED,
			headers=config.headers
			)
		"""

	

