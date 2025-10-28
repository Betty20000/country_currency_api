"""
URL configuration for country_currency project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.http import JsonResponse
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('countries.urls'))
]

def custom_404(request, exception):
    return JsonResponse({"error": "Endpoint not found,try /countries or /status"}, status=404)

def custom_500(request):
    return JsonResponse({"error": "Internal server error,try to add /countries or /status"}, status=500)

handler404 = "country_currency.urls.custom_404"
handler500 = "country_currency.urls.custom_500"