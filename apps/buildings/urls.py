from rest_framework.routers import DefaultRouter
from .views import BuildingViewSet, TowerViewSet, ApartmentViewSet

router = DefaultRouter()
router.register('buildings', BuildingViewSet, basename='building')
router.register('towers', TowerViewSet, basename='tower')
router.register('apartments', ApartmentViewSet, basename='apartment')

urlpatterns = router.urls
