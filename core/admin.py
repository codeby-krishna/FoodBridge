from django.contrib import admin
from .models import Food, FoodRequest


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ('food_name', 'quantity', 'location', 'contact', 'created_at')


@admin.register(FoodRequest)
class FoodRequestAdmin(admin.ModelAdmin):
    list_display = ('food', 'created_at', 'status')
    list_filter = ('status', 'created_at')