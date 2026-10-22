
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Food(models.Model):
    food_name = models.CharField(max_length=100)

    # Original quantity display, e.g. "50 plates"
    quantity = models.CharField(max_length=50)

    # Numeric stock for partial claims
    total_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    remaining_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    quantity_unit = models.CharField(
        max_length=30,
        default="plates"
    )

    description = models.TextField()
    location = models.CharField(max_length=200)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    contact = models.CharField(max_length=15)
    best_before = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    donor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    @property
    def is_available(self):
        return self.remaining_quantity > 0

    @property
    def urgency_level(self):
        if not self.best_before:
            return "Unknown"

        now = timezone.now()

        if self.best_before <= now:
            return "Expired"

        hours_left = (
            self.best_before - now
        ).total_seconds() / 3600

        if hours_left <= 6:
            return "Critical"
        elif hours_left <= 24:
            return "Urgent"

        return "Fresh"

    def __str__(self):
        return (
            f"{self.food_name} - "
            f"{self.remaining_quantity} {self.quantity_unit} left"
        )


class NGOProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="ngoprofile"
    )
    organization_name = models.CharField(max_length=150)
    contact = models.CharField(max_length=15)
    location = models.CharField(max_length=200)

    def __str__(self):
        return self.organization_name


class FoodRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
        ("Completed", "Completed"),
    ]

    food = models.ForeignKey(
        Food,
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    ngo = models.ForeignKey(
        NGOProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    requested_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1
    )

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    def __str__(self):
        return (
            f"{self.food.food_name} - "
            f"{self.requested_quantity} requested"
        )


class Pickup(models.Model):
    food_request = models.OneToOneField(
        FoodRequest,
        on_delete=models.CASCADE
    )

    volunteer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        default="Pending"
    )

    verification_otp = models.CharField(
        max_length=6,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.food_request.food.food_name


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("Donor", "Donor"),
        ("NGO", "NGO"),
        ("Volunteer", "Volunteer"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"
