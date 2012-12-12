'''
Created on Dec 12, 2012

@author: jm
'''

from django.db import models
from django.contrib.auth.models import User


class StudentGeoLocation(models.Model):
    """
    Geo location data inferred from user's ip address. 
    
    To fill in these records, we are using the MaxMind database (see dev.maxmind.com).
    Any of the field may be undefined as data may not be available.
    
    We keep a one to one mapping user to geo location as the location can be considered unique for 
    each individual. 
    """

    user = models.OneToOneField(User, unique=True, db_index=True)

    country = models.CharField(max_length=2, blank=True)                        # ISO 3166-1 country code
    region = models.CharField(max_length=2, null=True)                          # ISO 3166-2 region code
    city = models.CharField(max_length=255, null=True)                          # city name
    postal_code = models.CharField(max_length=6, null=True)                     # postal code
    latitude = models.DecimalField(max_digits=7, decimal_places=4, null=True)   # latitude
    longitude = models.DecimalField(max_digits=7, decimal_places=4, null=True)  # longitude
    metro_code = models.IntegerField(null=True)                                 # only for US locations
    area_code = models.CharField(max_length=3, null=True)                       # telephone area code, US only
