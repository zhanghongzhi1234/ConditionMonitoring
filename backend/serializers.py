from rest_framework import serializers
from .models import Alarms

class AlarmsSerializer(serializers.ModelSerializer):
	class Meta:
		model = Alarms
		fields = ("asset_name","location_key","severity_key","subsystem_key","system_key","timestamp")
