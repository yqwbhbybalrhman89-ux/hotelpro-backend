from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal


class RoomGroup(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Groupe de salles"
        verbose_name_plural = "Groupes de salles"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Room(models.Model):
    class StatutChoices(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        RESERVE = "reserve", "Réservé"
        MAINTENANCE = "maintenance", "Maintenance"

    room_group = models.ForeignKey(
        RoomGroup,
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    numero_nom = models.CharField(max_length=50, unique=True)
    prix_par_unite = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Prix par heure ou par jour selon la configuration.",
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutChoices.choices,
        default=StatutChoices.DISPONIBLE,
    )
    image = models.ImageField(upload_to="rooms/", blank=True, null=True)

    class Meta:
        verbose_name = "Salle / Chambre"
        verbose_name_plural = "Salles / Chambres"
        ordering = ["numero_nom"]

    def is_currently_occupied(self):
        """Vérifie si un client occupe actuellement la chambre."""
        now = timezone.now()
        return self.reservations.filter(
            statut=Reservation.StatutChoices.CONFIRME,
            date_debut__lte=now,
            date_fin__gte=now
        ).exists()

    def update_statut_auto(self):
        """Met à jour le statut en fonction des réservations actives."""
        if self.statut == self.StatutChoices.MAINTENANCE:
            return  # Ne pas modifier si la chambre est en maintenance
            
        if self.is_currently_occupied():
            self.statut = self.StatutChoices.RESERVE
        else:
            self.statut = self.StatutChoices.DISPONIBLE
        self.save(update_fields=['statut'])

    def __str__(self):
        return f"{self.numero_nom} ({self.room_group.nom})"


class Reservation(models.Model):
    class StatutChoices(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        CONFIRME = "confirme", "Confirmé"

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    client_nom = models.CharField(max_length=150)
    client_telephone = models.CharField(max_length=20)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    prix_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    statut = models.CharField(
        max_length=20,
        choices=StatutChoices.choices,
        default=StatutChoices.EN_ATTENTE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ["-created_at"]

    def clean(self):
        # 1. Vérification de la cohérence des dates
        if self.date_fin and self.date_debut and self.date_fin <= self.date_debut:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")

        # 2. Empêcher les réservations simultanées (Chevauchement de dates)
        if self.room_id and self.date_debut and self.date_fin:
            chevauchement = Reservation.objects.filter(
                room=self.room,
                statut__in=[self.StatutChoices.CONFIRME, self.StatutChoices.EN_ATTENTE],
                date_debut__lt=self.date_fin,
                date_fin__gt=self.date_debut
            ).exclude(pk=self.pk)

            if chevauchement.exists():
                raise ValidationError(
                    "Cette chambre est déjà réservée pour cette période. Veuillez choisir d'autres dates."
                )

    def calculer_prix_total(self):
        """Calcule le prix selon la durée (heures, arrondi au jour si >= 24h)."""
        if not self.room_id or not self.date_debut or not self.date_fin:
            return Decimal("0.00")

        duree = self.date_fin - self.date_debut
        heures = Decimal(str(duree.total_seconds() / 3600))

        if heures <= 0:
            return Decimal("0.00")

        if heures >= 24:
            jours = (heures / Decimal("24")).quantize(Decimal("1"))
            if heures % 24 > 0:
                jours += 1
            return (jours * self.room.prix_par_unite).quantize(Decimal("0.01"))

        return (heures * self.room.prix_par_unite).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        self.full_clean()
        self.prix_total = self.calculer_prix_total()
        super().save(*args, **kwargs)
        
        # Mettre à jour le statut de la chambre associée
        if self.room:
            self.room.update_statut_auto()

    def __str__(self):
        return f"Réservation {self.client_nom} - {self.room.numero_nom}"


class Payment(models.Model):
    class ModePaiementChoices(models.TextChoices):
        BANKILY = "bankily", "Bankily"
        MASRIVI = "masrivi", "Masrivi"
        SEDAD = "sedad", "Sedad"
        ESPECES = "especes", "Espèces"

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    client_nom = models.CharField(max_length=150)
    client_telephone = models.CharField(max_length=20)
    mode_paiement = models.CharField(
        max_length=20,
        choices=ModePaiementChoices.choices,
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Paiement {self.client_nom} - {self.montant}"