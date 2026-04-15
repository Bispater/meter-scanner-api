from rest_framework.routers import DefaultRouter
from .views import UserViewSet, OrganizationViewSet

router = DefaultRouter()
router.register('organizations', OrganizationViewSet, basename='organization')
router.register('users', UserViewSet, basename='user')

urlpatterns = router.urls
