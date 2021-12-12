from django.db import models

# Create your models here.

class Alarms(models.Model):
 
  # asset_name
  asset_name = models.CharField(max_length=255, null=False)

  # location_key
  location_key = models.CharField(max_length=255, null=False)

  # severity_key
  severity_key = models.CharField(max_length=255, null=False)

  # subsystem_key
  subsystem_key = models.CharField(max_length=255, null=False)

  # system_key
  system_key = models.CharField(max_length=255, null=False)

  # timestamp
  timestamp = models.DateTimeField()


  def __str__(self):
  	return """ asset_name  - {}
		 location_key  - {}
		 severity_key  - {}
		 subsystem_key - {}
		 system_key    - {}
		 timestamp     - {}
		""".format(self.asset_name,self.location_key,self.severity_key,self.subsystem_key,self.system_key,self.timestamp)


class AlarmsCount(models.Model):

  # location_key
  location_key = models.CharField(max_length=255, null=False)

  # alarm_count
  alarm_count = models.IntegerField()
