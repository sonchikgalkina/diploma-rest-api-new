from django.db import models



class Flat(models.Model):
    link = models.CharField(max_length=512, primary_key=True)
    floor = models.IntegerField()
    floors_count = models.IntegerField()
    total_meters = models.FloatField()
    price_per_m2 = models.IntegerField()
    price_per_month = models.IntegerField()
    commissions = models.IntegerField()
    region = models.CharField(max_length=256)
    district = models.CharField(max_length=256)
    street = models.CharField(max_length=256)
    underground = models.CharField(max_length=256)
    house = models.CharField(max_length=256)
    time_to_underground = models.IntegerField()
    rooms = models.IntegerField()
    common_ecology_coeff = models.IntegerField()
    population_density_coeff = models.IntegerField()
    green_spaces_coeff = models.IntegerField()
    negative_impact_coeff = models.IntegerField()
    phone_nets_coeff = models.IntegerField()
    crime_coeff = models.FloatField()