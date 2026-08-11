from rest_framework import serializers
from .models import RoomGroup, Room, Reservation, Payment


class RoomGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomGroup
        fields = ["id", "nom", "description"]


class RoomSerializer(serializers.ModelSerializer):
    room_group_nom = serializers.CharField(source="room_group.nom", read_only=True)

    class Meta:
        model = Room
        fields = [
            "id",
            "room_group",
            "room_group_nom",
            "numero_nom",
            "prix_par_unite",
            "statut",
            "image",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "reservation",
            "client_nom",
            "client_telephone",
            "mode_paiement",
            "montant",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class ReservationSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    room_nom = serializers.CharField(source="room.numero_nom", read_only=True)
    prix_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "room",
            "room_nom",
            "client_nom",
            "client_telephone",
            "date_debut",
            "date_fin",
            "prix_total",
            "statut",
            "payments",
            "created_at",
        ]
        read_only_fields = ["prix_total", "created_at"]


class PriceEstimateSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    date_debut = serializers.DateTimeField()
    date_fin = serializers.DateTimeField()

    def validate(self, data):
        if data["date_fin"] <= data["date_debut"]:
            raise serializers.ValidationError(
                "La date de fin doit être postérieure à la date de début."
            )
        return data


class ChatbotSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    locale = serializers.CharField(max_length=5, default="fr")
