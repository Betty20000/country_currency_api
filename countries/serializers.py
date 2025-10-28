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
        """
        Validation rules for Country:
        - name, population, and currency_code are required for client-facing requests
        - During refresh (context_type='refresh'), currency_code may be null
        """
        context_type = self.context.get("context_type")
        errors = {}

        # For refresh mode (when data comes from the external APIs)
        if context_type == "refresh":
            if not data.get("name"):
                errors["name"] = "is required"
            if data.get("population") is None:
                errors["population"] = "is required"
            # currency_code can be null in refresh mode (per spec)
        else:
            # Strict validation for client POST/PUT requests
            if not data.get("name"):
                errors["name"] = "is required"
            if data.get("population") is None:
                errors["population"] = "is required"
            if not data.get("currency_code"):
                errors["currency_code"] = "is required"

        if errors:
            raise serializers.ValidationError({
                "error": "Validation failed",
                "details": errors
            })

        return data
