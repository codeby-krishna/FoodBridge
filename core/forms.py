
from django import forms
from django.utils import timezone
from .models import Food, NGOProfile


class FoodForm(forms.ModelForm):
    total_quantity = forms.DecimalField(
        label="Quantity",
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "0.01",
            "placeholder": "Enter quantity"
        })
    )

    quantity_unit = forms.ChoiceField(
        label="Unit",
        choices=[
            ("kg", "Kilograms (kg)"),
            ("plates", "Plates"),
            ("packets", "Packets"),
            ("litres", "Litres"),
        ],
        widget=forms.Select(attrs={
            "class": "form-control"
        })
    )

    best_before = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M"
        )
    )

    class Meta:
        model = Food
        fields = [
            "food_name",
            "total_quantity",
            "quantity_unit",
            "description",
            "location",
            "contact",
            "best_before",
            "latitude",
            "longitude",
        ]
        widgets = {
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def clean_best_before(self):
        best_before = self.cleaned_data.get("best_before")
        if best_before and best_before <= timezone.now():
            raise forms.ValidationError(
                "Best Before date and time must be in the future."
            )
        return best_before


class NGOProfileForm(forms.ModelForm):
    class Meta:
        model = NGOProfile
        fields = ["organization_name", "contact", "location"]

