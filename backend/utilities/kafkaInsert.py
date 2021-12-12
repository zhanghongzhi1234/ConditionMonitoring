from django.shortcuts import render

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import status

from kafka import KafkaProducer, KafkaConsumer

import requests
import json
import datetime
import calendar

import importlib.util

#spec = importlib.util.spec_from_file_location("config","backend/configuration/config.py")
spec = importlib.util.spec_from_file_location("config","/u01/transactive/cm/backend_service/backend/configuration/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

def insertKafkaDictList(topic_name,messageList):
	kafka_producer = connect_kafka_producer()

	# Publish message to kafka topic
	for message in messageList:
		message = json.dumps(message)
		publish_message(kafka_producer,topic_name,message.strip())
	
	# Do a flush
	kafka_producer.flush

	if kafka_producer is not None:
		kafka_producer.close()

def insertKafkaDict(topic_name,message):
	kafka_producer = connect_kafka_producer()

	message = json.dumps(message)
	publish_message(kafka_producer,topic_name,message.strip())
	
	# Do a flush
	kafka_producer.flush

	if kafka_producer is not None:
		kafka_producer.close()

def insertKafkaStringList(topic_name,messageList):
	kafka_producer = connect_kafka_producer()

	# Publish message to kafka topic
	for message in messageList:
		print(message)
		publish_message(kafka_producer,topic_name,message.strip())
	
	
	# Do a flush
	#kafka_producer.flush

	if kafka_producer is not None:
		kafka_producer.close()

def insertKafkaString(topic_name,message):
	kafka_producer = connect_kafka_producer()

	publish_message(kafka_producer,topic_name,message.strip())
	
	# Do a flush
	kafka_producer.flush

	if kafka_producer is not None:
		kafka_producer.close()

def publish_message(producer_instance,topic_name,message):

	try:
		print('publishing....')
		message = bytes(message, encoding='utf-8')
		producer_instance.send(topic_name,message)
		#producer_instance.flush()

	except Exception as ex:

		print('Exception in publishing message')
		print(str(ex))

def connect_kafka_producer():

	_producer = None

	try:
		print('Producer setup....')
		_producer = KafkaProducer(bootstrap_servers=config.kafka_bootstrap)

	except Exception as ex:

		print('Exception while connecting Kafka')
		print(str(ex))

	finally:
		return _producer




