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
import time


@api_view(['POST'])
def refresh_countries(request):
    """
    POST /countries/refresh
    Fetch countries and exchange rates, then update or create cached data.
    Uses bulk batching for DB speed and minimizes duplicate validation.
    """
    start_time = time.time()

    # Step 1: Fetch APIs safely
    try:
        countries_data = utils.fetch_countries()
    except RequestException:
        return Response(
            {"error": "External data source unavailable", "details": "Could not fetch data from Countries API"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        rates = utils.fetch_exchange_rates()
    except RequestException:
        return Response(
            {"error": "External data source unavailable", "details": "Could not fetch data from Exchange rates API"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    now = utils.get_now()
    validation_errors = []
    new_countries, update_countries = [], []

    # ✅ Step 2: Prefetch all existing countries once (avoid repeated queries)
    existing_countries = {c.name.lower(): c for c in Country.objects.all()}

    # ✅ Step 3: Build records for batch operations
    for item in countries_data:
        name = item.get("name")
        if not name:
            continue

        capital = item.get("capital")
        region = item.get("region")
        population = item.get("population") or 0
        flag = item.get("flag")
        currencies = item.get("currencies") or []

        currency_code = None
        exchange_rate = None
        estimated_gdp = None

        if currencies:
            first_currency = currencies[0] or {}
            currency_code = first_currency.get("code")
            if currency_code and currency_code in rates:
                try:
                    exchange_rate = float(rates.get(currency_code))
                    if exchange_rate > 0:
                        multiplier = utils.make_multiplier()
                        estimated_gdp = (population * multiplier) / exchange_rate
                except (TypeError, ValueError):
                    exchange_rate = None
                    estimated_gdp = None

        existing = existing_countries.get(name.lower())

        # ✅ Only validate new countries to avoid duplicate error
        if not existing:
            serializer = CountrySerializer(data={
                "name": name,
                "population": population,
                "currency_code": currency_code,
            }, context={"context_type": "refresh"})

            if not serializer.is_valid():
                validation_errors.append({
                    "name": name,
                    "details": serializer.errors.get("details", serializer.errors)
                })
                continue

        if existing:
            existing.capital = capital
            existing.region = region
            existing.population = population
            existing.flag_url = flag
            existing.currency_code = currency_code
            existing.exchange_rate = exchange_rate
            existing.estimated_gdp = estimated_gdp
            existing.last_refreshed_at = now
            update_countries.append(existing)
        else:
            new_countries.append(Country(
                name=name,
                capital=capital,
                region=region,
                population=population,
                flag_url=flag,
                currency_code=currency_code,
                exchange_rate=exchange_rate,
                estimated_gdp=estimated_gdp,
                last_refreshed_at=now,
            ))

    # ✅ Step 4: Apply bulk ops safely in batches
    try:
        with transaction.atomic():
            if new_countries:
                Country.objects.bulk_create(new_countries, batch_size=100, ignore_conflicts=True)
            if update_countries:
                Country.objects.bulk_update(
                    update_countries,
                    fields=[
                        "capital", "region", "population", "flag_url",
                        "currency_code", "exchange_rate", "estimated_gdp",
                        "last_refreshed_at"
                    ],
                    batch_size=100
                )

        valid_count = len(new_countries) + len(update_countries)

        # ✅ Step 5: Generate image AFTER DB commit
        total = Country.objects.count()
        top5 = list(Country.objects.filter(estimated_gdp__isnull=False).order_by("-estimated_gdp")[:5])
        utils.generate_summary_image(total, top5, now.isoformat())

    except Exception as e:
        return Response(
            {"error": "Internal server error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    duration = round(time.time() - start_time, 2)

    return Response(
        {
            "message": "Refresh successful",
            "last_refreshed_at": now.isoformat(),
            "valid_countries": valid_count,
            "duration_seconds": duration,
            "errors": validation_errors[:5],  # show only first few
        },
        status=status.HTTP_200_OK,
    )
@api_view(['GET'])
def list_countries(request):
    """
    GET /countries
    Filters:
      - name, capital, region, population, currency_code, exchange_rate, estimated_gdp
    Sorting:
      - ?sort=<field>_asc or <field>_desc
      - ?sort=gdp_desc
    Default:
      - Ordered by id ascending.
      - After sorting, IDs are reassigned (1, 2, 3, …) in the response only.
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
                    {"error": "Validation failed", "details": {key: "is not a valid filter"}},
                    status=status.HTTP_400_BAD_REQUEST
                )
            value = request.GET.get(key)
            if value is None or value == "":
                return Response(
                    {"error": "Validation failed", "details": {key: "is required"}},
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
                qs = qs.order_by("-estimated_gdp", "id")
            elif sort_param.endswith("_desc"):
                field = sort_param.replace("_desc", "")
                if field in allowed_sort_fields:
                    qs = qs.order_by(f"-{field}", "id")
                else:
                    return Response(
                        {"error": "Validation failed", "details": {field: "is not a valid sort field"}},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif sort_param.endswith("_asc"):
                field = sort_param.replace("_asc", "")
                if field in allowed_sort_fields:
                    qs = qs.order_by(field, "id")
                else:
                    return Response(
                        {"error": "Validation failed", "details": {field: "is not a valid sort field"}},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {"error": "Validation failed",
                     "details": {"sort": "invalid format (use <field>_asc or <field>_desc)"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            qs = qs.order_by("id")

        # --- 404 if no matches ---
        if not qs.exists():
            return Response({"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND)

        # --- Serialize ---
        serializer = CountrySerializer(qs, many=True)
        data = serializer.data

        # ✅ Reassign IDs sequentially for display only
        for i, item in enumerate(data, start=1):
            item["id"] = i

        return Response(data)

    except Exception as e:
        print(f"❌ Internal server error: {e}")
        return Response(
            {"error": "Internal server error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
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
