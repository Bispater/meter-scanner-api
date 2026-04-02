from rest_framework.routers import DefaultRouter
from .views import MeasurementCycleViewSet

router = DefaultRouter()
router.register(r'cycles', MeasurementCycleViewSet, basename='cycle')

urlpatterns = router.urls
