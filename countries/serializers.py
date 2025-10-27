
from rest_framework import serializers
from .models import Country

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            'id', 'name', 'capital', 'region', 'population',
            'currency_code', 'exchange_rate', 'estimated_gdp',
            'flag_url', 'last_refreshed_at'
        ]

    def validate(self, data):
        # Enforce required fields for incoming API requests
        # (name, population, currency_code are required per spec)
        # Note: DB allows null currency_code for refresh flow; serializer enforces it for client requests.
        errors = {}
        if self.instance is None:
            # creation requests
            if 'name' not in data or not data.get('name'):
                errors['name'] = 'is required'
            if 'population' not in data or data.get('population') is None:
                errors['population'] = 'is required'
            if 'currency_code' not in data or not data.get('currency_code'):
                errors['currency_code'] = 'is required'
        else:
            # updates via serializer: if provided, they must be non-empty
            if 'name' in data and not data.get('name'):
                errors['name'] = 'is required'
            if 'population' in data and data.get('population') is None:
                errors['population'] = 'is required'
            if 'currency_code' in data and not data.get('currency_code'):
                errors['currency_code'] = 'is required'

        if errors:
            raise serializers.ValidationError({"error": "Validation failed", "details": errors})

        return data
