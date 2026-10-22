from django.urls import path
from . import views

urlpatterns = [
    # Home and dashboard
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Food donation and discovery
    path('donate/', views.add_food, name='add_food'),
    path('find-food/', views.find_food, name='find_food'),
    path('food/<int:id>/', views.food_detail, name='food_detail'),
    path(
        'food/<int:id>/request/',
        views.request_food,
        name='request_food'
    ),

    # Food requests
    path('requests/', views.food_requests, name='food_requests'),
    path('ngo-requests/', views.ngo_requests, name='ngo_requests'),
    path('donor-requests/', views.donor_requests, name='donor_requests'),

    # NGO profile and food claim
    path('ngo-profile/', views.ngo_profile, name='ngo_profile'),
    path(
        'ngo-claim/<int:id>/',
        views.ngo_claim_food,
        name='ngo_claim_food'
    ),

    # Donor approval and rejection
    path(
        'accept-request/<int:id>/',
        views.accept_request,
        name='accept_request'
    ),
    path(
        'reject-request/<int:id>/',
        views.reject_request,
        name='reject_request'
    ),

    # Volunteer pickups
    path(
        'volunteer-pickups/',
        views.volunteer_pickups,
        name='volunteer_pickups'
    ),
    path(
        'take-pickup/<int:id>/',
        views.take_pickup,
        name='take_pickup'
    ),
    path('my-pickups/', views.my_pickups, name='my_pickups'),
    path(
        'complete-pickup/<int:id>/',
        views.complete_pickup,
        name='complete_pickup'
    ),

    # Authentication
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
]