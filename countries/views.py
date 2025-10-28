import os
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.http import FileResponse
from .models import Country
from .serializers import CountrySerializer
from . import utils
from requests.exceptions import RequestException, Timeout


@api_view(['POST'])
def refresh_countries(request):
    """
    POST /countries/refresh
    Fetch countries and exchange rates, then update or create cached data.
    Generates summary image after successful refresh.
    """
    # Step 1: External API fetch with error handling
    try:
        countries_data = utils.fetch_countries()
    except RequestException:
        return Response(
            {"error": "External data source unavailable", "details": "Could not fetch data from Countries API"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        rates = utils.fetch_exchange_rates()
    except RequestException:
        return Response(
            {"error": "External data source unavailable", "details": "Could not fetch data from Exchange rates API"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    now = utils.get_now()
    valid_count = 0
    validation_errors = []

    try:
        with transaction.atomic():
            for item in countries_data:
                # Extract raw data
                name = item.get('name')
                capital = item.get('capital')
                region = item.get('region')
                population = item.get('population') or 0
                flag = item.get('flag')
                currencies = item.get('currencies') or []

                # --- Currency Handling Logic ---
                currency_code = None
                exchange_rate = None
                estimated_gdp = None

                if currencies:
                    first_currency = currencies[0] or {}
                    currency_code = first_currency.get('code')

                    if currency_code and currency_code in rates:
                        try:
                            exchange_rate = float(rates.get(currency_code))
                            if exchange_rate > 0:
                                multiplier = utils.make_multiplier()
                                estimated_gdp = (population * multiplier) / exchange_rate
                        except (TypeError, ValueError):
                            # if invalid data in API
                            exchange_rate = None
                            estimated_gdp = None
                    else:
                        # currency not found in exchange rate API
                        exchange_rate = None
                        estimated_gdp = None
                else:
                    # empty currencies array
                    currency_code = None
                    exchange_rate = None
                    estimated_gdp = 0  # still store the record as per spec

                                # --- Validation & Upsert Logic ---
                obj = Country.objects.filter(name__iexact=name).first()
                payload = {
                    "name": name,
                    "population": population,
                    "currency_code": currency_code,
                }

                                # Use serializer differently for create vs update
                if obj:
                    serializer = CountrySerializer(obj, data=payload, partial=True, context={"context_type": "refresh"})
                else:
                    serializer = CountrySerializer(data=payload, context={"context_type": "refresh"})

                if not serializer.is_valid():
                    validation_errors.append({
                        "name": name or "Unknown",
                        "details": serializer.errors.get("details", serializer.errors)
                    })
                    continue  # skip invalid record

                # --- Save or update record ---
                defaults = {
                    "name": name,
                    "capital": capital,
                    "region": region,
                    "population": population,
                    "flag_url": flag,
                    "currency_code": currency_code,
                    "exchange_rate": exchange_rate,
                    "estimated_gdp": estimated_gdp,
                    "last_refreshed_at": now,
                }               
                obj = Country.objects.filter(name__iexact=name).first()
                if obj:
                    for field, value in defaults.items():
                        setattr(obj, field, value)
                    obj.save()
                else:
                    Country.objects.create(**defaults)

                valid_count += 1

            # --- Validation summary ---
            if valid_count == 0:
                transaction.set_rollback(True)
                return Response(
                    {"error": "Validation failed", "details": validation_errors or {"general": "No valid countries found"}},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # --- Generate summary image ---
            total = Country.objects.count()
            top5 = list(Country.objects.filter(estimated_gdp__isnull=False).order_by('-estimated_gdp')[:5])
            utils.generate_summary_image(total, top5, now.isoformat())

    except Exception as e:
        return Response(
            {"error": "Internal server error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        {
            "message": "Refresh successful",
            "last_refreshed_at": now.isoformat(),
            "valid_countries": valid_count
        },
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
def list_countries(request):
    """
    GET /countries
    Filters:
      - name, capital, region, population, currency_code, exchange_rate, estimated_gdp
    Sorting:
      - ?sort=<field>_asc or <field>_desc
      - or ?sort=gdp_desc
    """

    try:
        allowed_filters = {
            "name": "name__iexact",
            "capital": "capital__iexact",
            "region": "region__iexact",
            "population": "population",
            "currency_code": "currency_code__iexact",
            "currency": "currency_code__iexact",
            "exchange_rate": "exchange_rate",
            "estimated_gdp": "estimated_gdp",
        }

        allowed_sort_fields = list(allowed_filters.keys())

        qs = Country.objects.all()

        # --- Validate filters ---
        for key in request.GET.keys():
            if key == "sort":
                continue
            if key not in allowed_filters:
                return Response(
                    {
                        "error": "Validation failed",
                        "details": {key: "is not a valid filter"}
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            value = request.GET.get(key)
            if value is None or value == "":
                return Response(
                    {
                        "error": "Validation failed",
                        "details": {key: "is required"}
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # --- Apply filters ---
        for key, lookup in allowed_filters.items():
            value = request.GET.get(key)
            if value:
                qs = qs.filter(**{lookup: value})

        # --- Sorting ---
        sort_param = request.GET.get("sort")
        if sort_param:
            if sort_param == "gdp_desc":
                qs = qs.order_by("-estimated_gdp")
            elif sort_param.endswith("_desc"):
                field = sort_param.replace("_desc", "")
                if field in allowed_sort_fields:
                    qs = qs.order_by(f"-{field}")
                else:
                    return Response(
                        {
                            "error": "Validation failed",
                            "details": {field: "is not a valid sort field"}
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif sort_param.endswith("_asc"):
                field = sort_param.replace("_asc", "")
                if field in allowed_sort_fields:
                    qs = qs.order_by(field)
                else:
                    return Response(
                        {
                            "error": "Validation failed",
                            "details": {field: "is not a valid sort field"}
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {
                        "error": "Validation failed",
                        "details": {"sort": "invalid format (use <field>_asc or <field>_desc)"}
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # --- 404 if no matches ---
        if not qs.exists():
            return Response({"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND)

        # --- Success ---
        serializer = CountrySerializer(qs, many=True)
        return Response(serializer.data)

    except Exception as e:
        print(f"❌ Internal server error: {e}")
        return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET', 'DELETE'])
def country_detail(request, name):
    """
    GET /countries/:name  -> return 404 JSON if not found
    DELETE /countries/:name -> delete, return 204 or 404
    """
    try:
        country = Country.objects.get(name__iexact=name)
    except Country.DoesNotExist:
        return Response({"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = CountrySerializer(country)
        return Response(serializer.data)
    else:  # DELETE
        country.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def get_status(request):
    """
    GET /status -> { total_countries, last_refreshed_at }
    last_refreshed_at is taken as the max(last_refreshed_at) across records (or null)
    """
    total = Country.objects.count()
    last = Country.objects.order_by('-last_refreshed_at').first()
    last_refreshed = last.last_refreshed_at.isoformat() if last and last.last_refreshed_at else None
    return Response({"total_countries": total, "last_refreshed_at": last_refreshed})


@api_view(['GET'])
def get_summary_image(request):
    """
    GET /countries/image
    Serve the summary image at cache/summary.png (or utils.get_summary_image_path()).
    If not found, return specified JSON error.
    """
    path = utils.get_summary_image_path()
    if not os.path.exists(path):
        return Response({"error": "Summary image not found"}, status=status.HTTP_404_NOT_FOUND)
    return FileResponse(open(path, 'rb'), content_type='image/png')
