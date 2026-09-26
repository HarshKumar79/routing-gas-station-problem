from django.urls import path
from .views import FuelRouteAPIView

urlpatterns = [
    path('route/', FuelRouteAPIView.as_view(), name='fuel-route'),
]