from django.contrib import admin
from .models import RoomGroup, Room, Reservation, Payment


@admin.register(RoomGroup)
class RoomGroupAdmin(admin.ModelAdmin):
    list_display = ["nom"]
    search_fields = ["nom"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["numero_nom", "room_group", "prix_par_unite", "statut"]
    list_filter = ["statut", "room_group"]
    search_fields = ["numero_nom"]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["client_nom", "room", "date_debut", "date_fin", "prix_total", "statut"]
    list_filter = ["statut"]
    search_fields = ["client_nom", "client_telephone"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["client_nom", "reservation", "mode_paiement", "montant", "created_at"]
    list_filter = ["mode_paiement"]
