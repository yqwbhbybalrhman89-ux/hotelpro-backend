from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RoomGroupViewSet,
    RoomViewSet,
    ReservationViewSet,
    PaymentViewSet,
    ChatbotView,
)

router = DefaultRouter()
router.register("room-groups", RoomGroupViewSet, basename="roomgroup")
router.register("rooms", RoomViewSet, basename="room")
router.register("reservations", ReservationViewSet, basename="reservation")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
    path("chatbot/", ChatbotView.as_view(), name="chatbot"),
]
