from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status

import requests
import json
import datetime
import calendar

import hmac
import hashlib
import base64
import binascii

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

def performEncodedHash(key,message):
	
	hash = hmac.new(str.encode(key),str.encode(message),hashlib.sha256)
	digest = hash.digest()
	#print(digest.hex())
	encodedHash = base64.b64encode(str.encode(digest.hex()))
	#print(encodedHash.decode('utf-8'))

	return encodedHash.decode('utf-8')
	

	
