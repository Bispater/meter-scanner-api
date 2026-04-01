from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import MeasurementViewSet, ocr_analyze

router = DefaultRouter()
router.register('', MeasurementViewSet, basename='measurement')

urlpatterns = [
    path('ocr/', ocr_analyze, name='measurement-ocr'),
] + router.urls
