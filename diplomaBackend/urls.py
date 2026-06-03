from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from rest_api.views import FlatAPIView, market_stats, price_by_district, price_histogram, correlation_analysis

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/flats/', FlatAPIView.as_view()),
    path('api/v1/analytics/stats/', market_stats),
    path('api/v1/analytics/by_district/', price_by_district),
    path('api/v1/analytics/histogram/', price_histogram),
    path('api/v1/analytics/correlation/', correlation_analysis),
    path('analytics/', TemplateView.as_view(template_name='analytics.html')),
]