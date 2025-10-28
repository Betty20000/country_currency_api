from django.urls import path
from . import views


urlpatterns = [
     # GET /status → Global system status summary
    path('status', views.get_status, name='get_status'),
    # POST /countries/refresh → Fetch and refresh all country data
    path('countries/refresh', views.refresh_countries, name='refresh_countries'),

    # GET /countries/image → Serve generated summary image
    path('countries/image', views.get_summary_image, name='get_summary_image'),
    # GET /countries → List countries (optional filters)
    path('countries', views.list_countries, name='list_countries'),
    path('countries/', views.list_countries, name='list_countries'),

    # GET or DELETE /countries/<name> → Country detail or delete
    path('countries/<str:name>', views.country_detail, name='country_detail'),
   
]

