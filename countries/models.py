from django.db import models

# Create your models h

class Country(models.Model):
    # id — auto-generated
    name = models.CharField(max_length=200, unique=True)
    capital = models.CharField(max_length=200, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    # population — required (but default to 0 in case)
    population = models.BigIntegerField(default=0)
    # currency_code — NOTE: allow null in DB to support external-data rules,
    # but API serializers validate presence on create/update requests.
    currency_code = models.CharField(max_length=10, null=True, blank=True)
    # exchange_rate — external-sourced; allow null (when not available)
    exchange_rate = models.FloatField(null=True, blank=True)
    # estimated_gdp — computed; allow null (when not computable)
    estimated_gdp = models.FloatField(null=True, blank=True)
    flag_url = models.URLField(null=True, blank=True)
    # last_refreshed_at — updated on successful refresh per-record
    last_refreshed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
