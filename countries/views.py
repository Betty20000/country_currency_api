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
from requests.exceptions import RequestException

@api_view(['POST'])
def refresh_countries(request):
    """
    POST /countries/refresh
    - Fetch both external APIs first (fail early with 503 if either API fails).
    - If both succeed, open a transaction and insert/update records.
    - After commit, generate the summary image and return success.
    """
    # 1) Fetch external APIs first so we don't modify DB if they fail
    try:
        countries_data = utils.fetch_countries()           # must raise on error
    except RequestException:
        return Response(
            {"error": "External data source unavailable", "details": "Could not fetch data from Countries API"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    try:
        rates = utils.fetch_exchange_rates()               # must raise on error
    except RequestException:
        return Response(
            {"error": "External data source unavailable", "details": "Could not fetch data from Exchange rates API"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    now = utils.get_now()

    try:
        # Wrap DB changes in a single transaction so failures rollback
        with transaction.atomic():
            for item in countries_data:
                name = item.get('name')
                # required-ish: ensure we have a name at least; skip otherwise
                if not name:
                    # skip malformed country entry (could also collect/log)
                    continue

                capital = item.get('capital')
                region = item.get('region')
                population = item.get('population') or 0
                flag = item.get('flag')
                currencies = item.get('currencies') or []

                currency_code = None
                exchange_rate = None
                estimated_gdp = None

                # Currency-handling rules per spec:
                if currencies:
                    first = currencies[0] or {}
                    code = first.get('code')
                    currency_code = code
                    if code and code in rates:
                        # match currency to rate; rates come from USD base
                        try:
                            exchange_rate = float(rates.get(code))
                        except (TypeError, ValueError):
                            exchange_rate = None

                        if exchange_rate and exchange_rate != 0:
                            multiplier = utils.make_multiplier()
                            estimated_gdp = (population * multiplier) / exchange_rate
                        else:
                            estimated_gdp = None
                    else:
                        # currency_code present but not found in exchange rates
                        exchange_rate = None
                        estimated_gdp = None
                else:
                    # currencies array empty
                    currency_code = None
                    exchange_rate = None
                    estimated_gdp = 0

                # Match by name case-insensitive
                # Case-insensitive lookup (update if exists, else create)
                obj = Country.objects.filter(name__iexact=name).first()
                defaults = {
                    'name': name,
                    'capital': capital,
                    'region': region,
                    'population': population,
                    'flag_url': flag,
                    'currency_code': currency_code,
                    'exchange_rate': exchange_rate,
                    'estimated_gdp': estimated_gdp,
                    'last_refreshed_at': now,
                }

                if obj:
                    # Update existing
                    for field, value in defaults.items():
                        setattr(obj, field, value)
                    obj.save()
                else:
                    # Create new
                    Country.objects.create(**defaults)


            # At this point transaction will commit if no exception
            total = Country.objects.count()
            top5 = list(Country.objects.filter(estimated_gdp__isnull=False).order_by('-estimated_gdp')[:5])
            timestamp = now.isoformat()
            # generate image and save to disk (utils handles dirs)
            utils.generate_summary_image(total, top5, timestamp)
    except Exception:
        # Any unexpected error -> Internal server error (500)
        return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"message": "Refresh successful", "last_refreshed_at": now.isoformat()}, status=status.HTTP_200_OK)


@api_view(['GET'])
def list_countries(request):
    """
    GET /countries
    Optional filters:
      - ?region=...
      - ?currency=...
      - ?sort=gdp_desc
    """
    region = request.GET.get('region')
    currency = request.GET.get('currency')
    sort = request.GET.get('sort')

    qs = Country.objects.all()
    if region:
        qs = qs.filter(region__iexact=region)
    if currency:
        qs = qs.filter(currency_code__iexact=currency)
    if sort == 'gdp_desc':
        qs = qs.order_by('-estimated_gdp')

    serializer = CountrySerializer(qs, many=True)
    return Response(serializer.data)


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




'''
obj = Country.objects.filter(name__iexact=name).first()
if obj:
    for field, value in defaults.items():
        setattr(obj, field, value)
    obj.save()
else:
    Country.objects.create(**defaults)
'''

















'''from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.http import FileResponse
from .models import Country
from .serializers import CountrySerializer
from . import utils


@api_view(['POST'])
def refresh_countries(request):
    """
    Fetch and refresh country data.
    """
    try:
        countries_data = utils.fetch_countries_data()
        rates = utils.fetch_exchange_rates()
        now = utils.get_now()

        with transaction.atomic():
            for item in countries_data:
                name = item.get('name')
                capital = item.get('capital')
                region = item.get('region')
                population = item.get('population') or 0
                flag = item.get('flag')
                currencies = item.get('currencies') or []

                currency_code = None
                exchange_rate = None
                estimated_gdp = None

                if currencies:
                    first = currencies[0]
                    code = first.get('code')
                    currency_code = code
                    if code and code in rates:
                        exchange_rate = float(rates[code])
                        multiplier = utils.make_multiplier()
                        # Guard: avoid division by zero
                        if exchange_rate and exchange_rate != 0:
                            estimated_gdp = (population * multiplier) / exchange_rate
                        else:
                            estimated_gdp = None
                    else:
                        exchange_rate = None
                        estimated_gdp = None
                else:
                    currency_code = None
                    exchange_rate = None
                    estimated_gdp = 0

                # Case-insensitive match for existing country
                Country.objects.update_or_create(
                    name__iexact=name,
                    defaults={
                        'name': name,
                        'capital': capital,
                        'region': region,
                        'population': population,
                        'currency_code': currency_code,
                        'exchange_rate': exchange_rate,
                        'estimated_gdp': estimated_gdp,
                        'flag_url': flag,
                        'last_refreshed_at': now,
                    }
                )

            # Generate image: total & top 5 by estimated_gdp (exclude nulls)
            total = Country.objects.count()
            top5 = Country.objects.filter(estimated_gdp__isnull=False).order_by('-estimated_gdp')[:5]
            timestamp = now.isoformat()
            utils.generate_summary_image(total, top5, timestamp)

        return Response(
            {"message": "Refresh successful", "last_refreshed_at": now.isoformat()},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_countries(request):
    """
    List all countries with optional filters and sorting.
    Query parameters:
      - region: filter by region (case-insensitive)
      - currency: filter by currency code
      - sort=gdp_desc: sort by estimated GDP descending
    """
    region = request.GET.get('region')
    currency = request.GET.get('currency')
    sort = request.GET.get('sort')

    qs = Country.objects.all()
    if region:
        qs = qs.filter(region__iexact=region)
    if currency:
        qs = qs.filter(currency_code__iexact=currency)
    if sort == 'gdp_desc':
        qs = qs.order_by('-estimated_gdp')

    serializer = CountrySerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_country(request, name):
    """
    Retrieve details of a specific country by name (case-insensitive).
    """
    try:
        obj = Country.objects.get(name__iexact=name)
    except Country.DoesNotExist:
        return Response(
            {"error": "Country not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = CountrySerializer(obj)
    path = utils.get_country_image_path(obj.name)
    return FileResponse(open(path, 'rb'), content_type='image/png')



'''