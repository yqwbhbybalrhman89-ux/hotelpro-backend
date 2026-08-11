import traceback
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RoomGroup, Room, Reservation, Payment
from .serializers import (
    RoomGroupSerializer,
    RoomSerializer,
    ReservationSerializer,
    PaymentSerializer,
    PriceEstimateSerializer,
    ChatbotSerializer,
)


class RoomGroupViewSet(viewsets.ModelViewSet):
    queryset = RoomGroup.objects.all()
    serializer_class = RoomGroupSerializer


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.select_related("room_group").all()
    serializer_class = RoomSerializer

    @action(detail=False, methods=["get"])
    def disponibles(self, request):
        """
        Retourne la liste des chambres qui ne sont pas occupées à l'instant présent
        et met à jour dynamiquement leur statut.
        """
        rooms = self.queryset.exclude(statut=Room.StatutChoices.MAINTENANCE)
        available_rooms = []

        for room in rooms:
            # Met à jour le statut en fonction des réservations actuelles
            room.update_statut_auto()
            if room.statut == Room.StatutChoices.DISPONIBLE:
                available_rooms.append(room)

        serializer = self.get_serializer(available_rooms, many=True)
        return Response(serializer.data)


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related("room", "room__room_group").prefetch_related("payments")
    serializer_class = ReservationSerializer

    @action(detail=False, methods=["post"])
    def estimer_prix(self, request):
        """
        Estime le prix total d'un séjour pour une période donnée.
        """
        serializer = PriceEstimateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            room = Room.objects.get(pk=serializer.validated_data["room_id"])
        except Room.DoesNotExist:
            return Response({"error": "Chambre introuvable."}, status=status.HTTP_404_NOT_FOUND)

        reservation = Reservation(
            room=room,
            client_nom="",
            client_telephone="",
            date_debut=serializer.validated_data["date_debut"],
            date_fin=serializer.validated_data["date_fin"],
        )
        return Response({"prix_total": str(reservation.calculer_prix_total())})


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("reservation").all()
    serializer_class = PaymentSerializer


class ChatbotView(APIView):
    """Endpoint chatbot IA pour répondre aux questions clients."""

    def post(self, request):
        serializer = ChatbotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data["message"]
        locale = serializer.validated_data["locale"]

        reply = self._generate_reply(message, locale)
        return Response({"reply": reply})

    def _generate_reply(self, message: str, locale: str) -> str:
        msg_lower = message.lower().strip()

        # ------------------------------------------------------------------
        # ÉTAPE 1 : INTENTION DE RÉSERVATION
        # ------------------------------------------------------------------
        mots_reservation = ["reserver", "réserver", "reservation", "réservation", "je veux reserver", "comment reserver", "book"]
        if any(m in msg_lower for m in mots_reservation):
            heure_actuelle = datetime.now().hour
            souhait_fr = "une excellente nuit" if (heure_actuelle >= 18 or heure_actuelle < 6) else "une très bonne journée"
            souhait_en = "a wonderful night" if (heure_actuelle >= 18 or heure_actuelle < 6) else "a great day"
            souhait_ar = "ليلة سعيدة" if (heure_actuelle >= 18 or heure_actuelle < 6) else "يوماً سعيداً"

            responses = {
                "fr": f"Avec plaisir ! Vous pouvez effectuer votre réservation directement en cliquant sur le bouton **'Réserver'** sous la chambre de votre choix. Je vous souhaite {souhait_fr} ! 😊✨",
                "en": f"With pleasure! You can place your reservation directly by clicking the **'Réserver'** button under your chosen room. I wish you {souhait_en}! 😊✨",
                "ar": f"بكل سرور! يمكنك الحجز مباشرة بالضغط على زر **'Réserver'** أسفل الغرفة التي تختارها. أتمنى لك {souhait_ar}! 😊✨",
            }
            return responses.get(locale, responses["fr"])

        # ------------------------------------------------------------------
        # ÉTAPE 2 : GESTION DES SALUTATIONS ET REMERCIEMENTS
        # ------------------------------------------------------------------
        if msg_lower in ["merci", "merci beaucoup", "thanks", "thank you", "شكرا", "شكراً"]:
            responses = {
                "fr": "Je vous en prie ! N'hésitez pas si vous avez d'autres questions. 😊",
                "en": "You're welcome! Let me know if you have any other questions. 😊",
                "ar": "على الرحب والسعة! لا تتردد في السؤال إذا كان لديك أي استفسار آخر. 😊",
            }
            return responses.get(locale, responses["fr"])

        if msg_lower in ["ok", "d'accord", "dac", "dacc", "okay", "حسنا", "تمام"]:
            responses = {
                "fr": "Parfait ! Que souhaitez-vous savoir d'autre sur nos chambres ?",
                "en": "Great! Is there anything else you would like to know about our rooms?",
                "ar": "ممتاز! هل هناك أي شيء آخر تود معرفته عن غرفنا؟",
            }
            return responses.get(locale, responses["fr"])

        if msg_lower in ["bonjour", "salut", "hi", "hello", "مرحبا", "أهلا"]:
            responses = {
                "fr": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
                "en": "Hello! How can I help you today?",
                "ar": "مرحباً! كيف يمكنني مساعدتك اليوم؟",
            }
            return responses.get(locale, responses["fr"])

        # ------------------------------------------------------------------
        # ÉTAPE 3 : DEMANDES DE PRIX OU INFOS SUR UNE SALLE/CHAMBRE SPÉCIFIQUE
        # ------------------------------------------------------------------
        rooms = Room.objects.all().select_related("room_group")
        for room in rooms:
            room.update_statut_auto()  # Met à jour son statut réel avant de répondre
            nom_chambre = room.numero_nom.lower()
            nom_groupe = room.room_group.nom.lower()

            if (nom_chambre and nom_chambre in msg_lower) or (nom_groupe and nom_groupe in msg_lower):
                statut_fr = "Disponible" if room.statut == Room.StatutChoices.DISPONIBLE else "Non disponible"
                return (
                    f"La {room.numero_nom} (Groupe : {room.room_group.nom}) "
                    f"coûte {room.prix_par_unite} MRU. "
                    f"Statut actuel : {statut_fr}."
                )

        # ------------------------------------------------------------------
        # ÉTAPE 4 : DEMANDES DE NOMBRE DE DISPONIBILITÉS
        # ------------------------------------------------------------------
        mots_prix = ["coute", "coûte", "prix", "tarif", "combien coute", "combien coûte"]
        demande_prix = any(p in msg_lower for p in mots_prix)

        if "combien" in msg_lower and not demande_prix and ("salle" in msg_lower or "chambre" in msg_lower or "disponible" in msg_lower):
            # Rafraîchissement des statuts de toutes les chambres
            for r in Room.objects.exclude(statut=Room.StatutChoices.MAINTENANCE):
                r.update_statut_auto()

            count_dispo = Room.objects.filter(statut=Room.StatutChoices.DISPONIBLE).count()
            return f"Nous avons actuellement {count_dispo} chambre(s)/salle(s) disponible(s)."

        # ------------------------------------------------------------------
        # ÉTAPE 5 : RECHERCHE FAQ (Si existe)
        # ------------------------------------------------------------------
        try:
            from .models import FAQ
            for faq in FAQ.objects.all():
                if faq.keyword:
                    keywords = [kw.strip().lower() for kw in faq.keyword.split(',') if kw.strip()]
                    if any(kw in msg_lower for kw in keywords):
                        return faq.answer
        except (ImportError, Exception):
            pass

        # ------------------------------------------------------------------
        # ÉTAPE 6 : APPEL OPENAI
        # ------------------------------------------------------------------
        api_key = getattr(settings, 'OPENAI_API_KEY', None)

        if not api_key:
            return self._fallback_reply(message, locale)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)

            chambres_donnees = list(
                Room.objects.all().values('numero_nom', 'prix_par_unite', 'statut', 'room_group__nom')
            )

            system_prompts = {
                "fr": f"""
                    Tu es l'assistant de HotelSmart.
                    Chambres de l'hôtel : {chambres_donnees}
                    Réponds très brièvement et poliment. Si l'utilisateur réserve ou demande à réserver, réponds 'Avec plaisir !' et souhaite-lui une bonne journée ou bonne nuit.
                """,
                "en": f"You are the HotelSmart assistant. Rooms: {chambres_donnees}. Reply briefly and wish a good day/night if they want to book.",
                "ar": f"أنت مساعد HotelSmart. الغرف: {chambres_donnees}. أجب بإيجاز وتمنّى له يوماً سعيداً أو ليلة سعيدة إذا أراد الحجز.",
            }

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompts.get(locale, system_prompts["fr"])},
                    {"role": "user", "content": message},
                ],
                max_tokens=250,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print("❌ ERREUR OPENAI :", str(e))
            return self._fallback_reply(message, locale)

    def _fallback_reply(self, message: str, locale: str) -> str:
        fallbacks = {
            "fr": "Je suis à votre disposition ! Vous pouvez me poser des questions sur la disponibilité ou le prix d'une chambre.",
            "en": "I'm at your service! Feel free to ask about room availability or prices.",
            "ar": "أنا في خدمتك! يمكنك سؤالي عن تفرغ الغرف أو أسعارها.",
        }
        return fallbacks.get(locale, fallbacks["fr"])