from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from django.db.models import Sum
import secrets
import math
import os
from .forms import FoodForm, NGOProfileForm
from .models import Food, FoodRequest, NGOProfile, Pickup, UserProfile


# --------------------------------------------------
# HOME
# --------------------------------------------------

def home(request):
    role = None
    has_pickups = False
    is_ngo = False
    is_donor = False
    is_volunteer = False

    if request.user.is_authenticated:
        from .models import UserProfile

        profile = UserProfile.objects.filter(
            user=request.user
        ).first()

        if profile:
            role = profile.role
        elif NGOProfile.objects.filter(user=request.user).exists():
            role = "NGO"
        elif Food.objects.filter(donor=request.user).exists():
            role = "Donor"
        else:
            role = "Volunteer"

        is_ngo = role == "NGO"
        is_donor = role == "Donor"
        is_volunteer = role == "Volunteer"

        has_pickups = Pickup.objects.filter(
            volunteer=request.user
        ).exists()

    return render(request, "home.html", {
        "role": role,
        "is_ngo": is_ngo,
        "is_donor": is_donor,
        "is_volunteer": is_volunteer,
        "has_pickups": has_pickups,
    })


# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

def register_user(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        role = request.POST.get("role", "")

        if not username or not password:
            return render(request, "register.html", {
                "error": "Username and password are required."
            })

        if role not in ["Donor", "NGO", "Volunteer"]:
            return render(request, "register.html", {
                "error": "Please select a valid role."
            })

        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {
                "error": "Username already exists."
            })

        user = User.objects.create_user(
            username=username,
            password=password
        )

        from .models import UserProfile

        UserProfile.objects.create(
            user=user,
            role=role
        )

        login(request, user)

        if role == "NGO":
            return redirect("ngo_profile")

        return redirect("home")

    return render(request, "register.html")


# --------------------------------------------------
# LOGIN / LOGOUT
# --------------------------------------------------

def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("home")

        return render(request, "login.html", {
            "error": "Invalid username or password."
        })

    return render(request, "login.html")


def logout_user(request):
    logout(request)
    return redirect("home")


# --------------------------------------------------
# ROLE HELPERS
# --------------------------------------------------


def is_volunteer_user(user):
    profile = UserProfile.objects.filter(user=user).first()
    return profile is not None and profile.role == "Volunteer"



# --------------------------------------------------
# ADD FOOD
# --------------------------------------------------

@login_required
def add_food(request):
    from .models import UserProfile

    profile = UserProfile.objects.filter(
        user=request.user
    ).first()

    if profile and profile.role != "Donor":
        messages.error(request, "Only donors can donate food.")
        return redirect("home")

    if NGOProfile.objects.filter(user=request.user).exists():
        messages.error(request, "NGOs cannot donate food.")
        return redirect("home")

    if request.method == "POST":
        form = FoodForm(request.POST)

        if form.is_valid():
            try:
                total = Decimal(request.POST.get("total_quantity", "0"))
                unit = request.POST.get(
                    "quantity_unit", "plates"
                ).strip()

                if total <= 0 or not unit:
                    raise InvalidOperation

            except (InvalidOperation, TypeError, ValueError):
                messages.error(
                    request,
                    "Enter a valid quantity greater than zero and a unit."
                )
                return render(
                    request, "add_food.html", {"form": form}
                )

            food = form.save(commit=False)
            food.donor = request.user
            food.total_quantity = total
            food.remaining_quantity = total
            food.quantity_unit = unit
            food.quantity = f"{total} {unit}"
            food.save()

            messages.success(
                request, "Food donation added successfully!"
            )
            return redirect("home")
    else:
        form = FoodForm()

    return render(request, "add_food.html", {"form": form})


# --------------------------------------------------
# FIND FOOD
# --------------------------------------------------

def find_food(request):
    query = request.GET.get("q", "").strip()
    user_lat = request.GET.get("lat")
    user_lon = request.GET.get("lon")

    foods = Food.objects.filter(
        remaining_quantity__gt=0
    ).filter(
        Q(best_before__isnull=True) |
        Q(best_before__gt=timezone.now())
    )

    if query:
        foods = foods.filter(
            Q(food_name__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query)
        )

    ngo_profile_exists = False

    if request.user.is_authenticated:
        ngo_profile_exists = NGOProfile.objects.filter(
            user=request.user
        ).exists()

    try:
        user_lat = float(user_lat)
        user_lon = float(user_lon)

        if not (
            -90 <= user_lat <= 90
            and -180 <= user_lon <= 180
        ):
            raise ValueError
    except (TypeError, ValueError):
        user_lat = None
        user_lon = None

    food_list = list(foods)

    for food in food_list:
        food.distance_km = None

        if (
            user_lat is not None
            and user_lon is not None
            and food.latitude is not None
            and food.longitude is not None
        ):
            lat1 = math.radians(user_lat)
            lon1 = math.radians(user_lon)
            lat2 = math.radians(float(food.latitude))
            lon2 = math.radians(float(food.longitude))

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(lat1) * math.cos(lat2)
                * math.sin(dlon / 2) ** 2
            )

            a = max(0, min(1, a))
            food.distance_km = round(
                6371 * 2 * math.asin(math.sqrt(a)), 2
            )

    if user_lat is not None and user_lon is not None:
        food_list.sort(
            key=lambda food: (
                food.distance_km is None,
                food.distance_km
                if food.distance_km is not None
                else float("inf")
            )
        )

    food_locations = []

    for food in food_list:
        if food.latitude is not None and food.longitude is not None:
            food_locations.append({
                "id": food.id,
                "name": food.food_name,
                "quantity": food.quantity,
                "location": food.location,
                "latitude": float(food.latitude),
                "longitude": float(food.longitude),
                "distance_km": food.distance_km,
                "detail_url": reverse(
                    "food_detail", args=[food.id]
                ),
            })

    return render(request, "find_food.html", {
        "foods": food_list,
        "query": query,
        "ngo_profile_exists": ngo_profile_exists,
        "food_locations": food_locations,
        "user_lat": user_lat,
        "user_lon": user_lon,
        "maptiler_api_key": os.environ.get("MAPTILER_API_KEY", ""),
    })


# --------------------------------------------------
# FOOD DETAILS
# --------------------------------------------------

def food_detail(request, id):
    food = get_object_or_404(Food, id=id)

    already_requested = False
    ngo_profile_exists = False
    is_donor = False
    is_volunteer = False

    if request.user.is_authenticated:
        already_requested = FoodRequest.objects.filter(
            food=food,
            user=request.user,
            status__in=["Pending", "Accepted"]
        ).exists()

        ngo_profile_exists = NGOProfile.objects.filter(
            user=request.user
        ).exists()

        is_donor = Food.objects.filter(
            donor=request.user
        ).exists()

        is_volunteer = is_volunteer_user(request.user)

    return render(request, "food_detail.html", {
        "food": food,
        "already_requested": already_requested,
        "ngo_profile_exists": ngo_profile_exists,
        "is_donor": is_donor,
        "is_volunteer": is_volunteer,
    })


# --------------------------------------------------
# NGO FOOD REQUESTS
# --------------------------------------------------

@login_required
@require_POST
def request_food(request, id):
    return _create_food_request(request, id)


@login_required
@require_POST
def ngo_claim_food(request, id):
    return _create_food_request(request, id)



@login_required
def food_requests(request):
    user_requests = FoodRequest.objects.filter(
        user=request.user
    ).select_related(
        "food", "ngo"
    ).order_by("-created_at")

    return render(request, "requests.html", {
        "requests": user_requests
    })


@login_required
def ngo_requests(request):
    ngo_profile = get_object_or_404(
        NGOProfile,
        user=request.user
    )

    user_requests = FoodRequest.objects.filter(
        ngo=ngo_profile
    ).select_related(
        "food"
    ).order_by("-created_at")

    for food_request in user_requests:
        food_request.pickup_info = Pickup.objects.filter(
            food_request=food_request
        ).first()

    return render(request, "ngo_requests.html", {
        "requests": user_requests
    })


def _create_food_request(request, id):
    food = get_object_or_404(Food, id=id)

    ngo_profile = NGOProfile.objects.filter(
        user=request.user
    ).first()

    if not ngo_profile:
        messages.error(
            request,
            "Only registered NGOs can request food."
        )
        return redirect("home")

    if food.best_before and food.best_before <= timezone.now():
        messages.error(request, "This food has expired.")
        return redirect("food_detail", id=id)

    try:
        requested = Decimal(
            request.POST.get("requested_quantity", "0")
        )

        if not requested.is_finite() or requested <= 0:
            raise InvalidOperation

    except (InvalidOperation, TypeError, ValueError):
        messages.error(request, "Enter a valid requested quantity.")
        return redirect("food_detail", id=id)

    with transaction.atomic():
        food = Food.objects.select_for_update().get(id=id)

        if requested > food.remaining_quantity:
            messages.error(
                request,
                f"Only {food.remaining_quantity} "
                f"{food.quantity_unit} currently remain."
            )
            return redirect("food_detail", id=id)

        already_requested = FoodRequest.objects.filter(
            food=food,
            ngo=ngo_profile,
            status__in=["Pending", "Accepted"]
        ).exists()

        if already_requested:
            messages.warning(
                request,
                "You have already requested this food."
            )
            return redirect("ngo_requests")

        FoodRequest.objects.create(
            food=food,
            user=request.user,
            ngo=ngo_profile,
            requested_quantity=requested,
            status="Pending"
        )

    messages.success(
        request,
        "Food request submitted. Waiting for donor approval."
    )
    return redirect("ngo_requests")




# --------------------------------------------------
# DONOR REQUESTS
# --------------------------------------------------

@login_required
def donor_requests(request):
    user_requests = FoodRequest.objects.filter(
        food__donor=request.user
    ).select_related(
        "food", "ngo", "pickup"
    ).order_by("-created_at")

    return render(request, "donor_requests.html", {
        "requests": user_requests
    })


@login_required
@require_POST
def accept_request(request, id):
    with transaction.atomic():
        food_request = get_object_or_404(
            FoodRequest.objects.select_related("food").filter(
                id=id, food__donor=request.user
            ),
            id=id
        )

        food = Food.objects.select_for_update().get(
            id=food_request.food_id
        )

        food_request = FoodRequest.objects.select_for_update().get(
            id=id
        )

        if food_request.status != "Pending":
            messages.warning(
                request, "This request has already been processed."
            )
            return redirect("donor_requests")

        reserved = FoodRequest.objects.filter(
            food=food,
            status="Accepted"
        ).exclude(
            pickup__status="Completed"
        ).aggregate(
            total=Sum("requested_quantity")
        )["total"] or Decimal("0")

        available = food.remaining_quantity - reserved

        if food_request.requested_quantity > available:
            messages.error(
                request,
                f"Not enough stock. Available to approve: "
                f"{max(available, Decimal('0'))} {food.quantity_unit}."
            )
            return redirect("donor_requests")

        food_request.status = "Accepted"
        food_request.save(update_fields=["status"])

        Pickup.objects.get_or_create(
            food_request=food_request,
            defaults={
                "status": "Pending",
                "verification_otp": (
                    f"{secrets.randbelow(1000000):06d}"
                ),
            }
        )

    messages.success(
        request, "Request accepted and pickup created successfully."
    )
    return redirect("donor_requests")


@login_required
@require_POST
def reject_request(request, id):
    food_request = get_object_or_404(
        FoodRequest,
        id=id,
        food__donor=request.user
    )

    if food_request.status != "Pending":
        messages.error(
            request,
            "Only pending requests can be rejected."
        )
        return redirect("donor_requests")

    food_request.status = "Rejected"
    food_request.save(update_fields=["status"])

    messages.success(
        request,
        "Food request rejected successfully."
    )
    return redirect("donor_requests")


# --------------------------------------------------
# NGO PROFILE
# --------------------------------------------------

@login_required
def ngo_profile(request):
    profile, created = NGOProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        form = NGOProfileForm(
            request.POST,
            instance=profile
        )

        if form.is_valid():
            ngo = form.save(commit=False)
            ngo.user = request.user
            ngo.save()

            messages.success(
                request,
                "NGO profile saved successfully."
            )
            return redirect("home")
    else:
        form = NGOProfileForm(instance=profile)

    return render(request, "ngo_profile.html", {
        "form": form
    })


# --------------------------------------------------
# VOLUNTEER AVAILABLE PICKUPS
# --------------------------------------------------

@login_required
def volunteer_pickups(request):
    if not is_volunteer_user(request.user):
        messages.error(
            request,
            "Only volunteers can access available pickups."
        )
        return redirect("home")

    pickups = Pickup.objects.filter(
        status="Pending",
        volunteer__isnull=True,
        food_request__status="Accepted"
    ).select_related(
        "food_request",
        "food_request__food",
        "food_request__ngo"
    ).order_by("-created_at")

    return render(request, "volunteer_pickups.html", {
        "pickups": pickups
    })


# --------------------------------------------------
# VOLUNTEER TAKES A PICKUP
# --------------------------------------------------

@login_required
@require_POST
def take_pickup(request, id):
    if not is_volunteer_user(request.user):
        messages.error(
            request,
            "Only volunteers can take pickups."
        )
        return redirect("home")

    with transaction.atomic():
        pickup = Pickup.objects.select_for_update().filter(
            id=id,
            status="Pending",
            volunteer__isnull=True,
            food_request__status="Accepted"
        ).first()

        if pickup is None:
            messages.warning(
                request,
                "This pickup is no longer available."
            )
            return redirect("volunteer_pickups")

        pickup.volunteer = request.user
        pickup.status = "Assigned"
        pickup.save(update_fields=["volunteer", "status"])

    messages.success(
        request,
        "Pickup assigned successfully! Open My Pickups."
    )
    return redirect("my_pickups")


# --------------------------------------------------
# VOLUNTEER MY PICKUPS
# --------------------------------------------------

@login_required
def my_pickups(request):
    if not is_volunteer_user(request.user):
        messages.error(
            request,
            "Only volunteers can view their pickups."
        )
        return redirect("home")

    pickups = Pickup.objects.filter(
        volunteer=request.user
    ).select_related(
        "food_request",
        "food_request__food",
        "food_request__ngo"
    ).order_by("-created_at")

    return render(request, "my_pickups.html", {
        "pickups": pickups
    })


# --------------------------------------------------
# COMPLETE PICKUP WITH OTP
# --------------------------------------------------

@login_required
@require_POST
def complete_pickup(request, id):
    if not is_volunteer_user(request.user):
        messages.error(request, "Only volunteers can complete pickups.")
        return redirect("home")

    entered_otp = request.POST.get("otp", "").strip()

    if len(entered_otp) != 6 or not entered_otp.isdigit():
        messages.error(request, "Enter a valid 6-digit OTP.")
        return redirect("my_pickups")

    with transaction.atomic():
        pickup = Pickup.objects.select_for_update().filter(
            id=id,
            volunteer=request.user,
            status="Assigned"
        ).first()

        if pickup is None:
            messages.error(
                request, "Pickup not found or it is not assigned to you."
            )
            return redirect("my_pickups")

        if not pickup.verification_otp:
            messages.error(request, "OTP is unavailable.")
            return redirect("my_pickups")

        if entered_otp != str(pickup.verification_otp).strip():
            messages.error(request, "Incorrect OTP. Please try again.")
            return redirect("my_pickups")

        food_request = FoodRequest.objects.select_for_update().get(
            id=pickup.food_request_id
        )
        food = Food.objects.select_for_update().get(
            id=food_request.food_id
        )

        if food_request.status != "Accepted":
            messages.error(request, "This request is not accepted.")
            return redirect("my_pickups")

        amount = food_request.requested_quantity

        if amount > food.remaining_quantity:
            messages.error(
                request, "Stock is insufficient; please contact the donor."
            )
            return redirect("my_pickups")

        food.remaining_quantity -= amount
        food.quantity = (
            f"{food.remaining_quantity} {food.quantity_unit}"
        )
        food.save(update_fields=["remaining_quantity", "quantity"])

        pickup.status = "Completed"
        pickup.save(update_fields=["status"])

        food_request.status = "Completed"
        food_request.save(update_fields=["status"])

    messages.success(
        request, "Pickup completed! Stock updated and OTP verified."
    )
    return redirect("my_pickups")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------


@login_required
def dashboard(request):
    user = request.user

    # User ka saved role profile se lo
    user_profile = UserProfile.objects.filter(user=user).first()
    saved_role = user_profile.role if user_profile else None

    # NGO profile
    ngo_profile = NGOProfile.objects.filter(user=user).first()

    # Role identify karo
    is_ngo = saved_role == "NGO" or ngo_profile is not None
    is_donor = saved_role == "Donor"
    is_volunteer = saved_role == "Volunteer" or is_volunteer_user(user)

    # Donor activity
    donated_foods = Food.objects.filter(donor=user)

    received_requests = FoodRequest.objects.filter(food__donor=user)
    accepted_received_requests = received_requests.filter(
        status="Accepted"
    )

    # NGO activity
    ngo_request_list = FoodRequest.objects.none()

    if ngo_profile:
        ngo_request_list = FoodRequest.objects.filter(ngo=ngo_profile)

    pending_ngo_requests = ngo_request_list.filter(status="Pending")
    accepted_ngo_requests = ngo_request_list.filter(status="Accepted")

    # Volunteer activity
    my_pickup_list = Pickup.objects.filter(volunteer=user)
    assigned_pickups = my_pickup_list.filter(status="Assigned")
    completed_pickups = my_pickup_list.filter(status="Completed")

    # Dashboard role
    if is_ngo:
        role = "ngo"
    elif is_donor:
        role = "donor"
    elif is_volunteer:
        role = "volunteer"
    else:
        role = "new"

    context = {
        "user": user,
        "role": role,
        "is_ngo": is_ngo,
        "is_donor": is_donor,
        "is_volunteer": is_volunteer,
        "ngo_profile": ngo_profile,

        "donated_foods_count": donated_foods.count(),
        "received_requests_count": received_requests.count(),
        "accepted_received_count": accepted_received_requests.count(),

        "ngo_requests_count": ngo_request_list.count(),
        "pending_ngo_count": pending_ngo_requests.count(),
        "accepted_ngo_count": accepted_ngo_requests.count(),

        "my_pickups_count": my_pickup_list.count(),
        "assigned_pickups_count": assigned_pickups.count(),
        "completed_pickups_count": completed_pickups.count(),
    }

    return render(request, "dashboard.html", context)

