from .models import UserProfile, Food, NGOProfile, Pickup


def user_role_context(request):
    is_ngo = False
    is_donor = False
    is_volunteer = False

    if request.user.is_authenticated:
        profile = UserProfile.objects.filter(
            user=request.user
        ).first()

        if profile:
            role = profile.role
        else:
            # Purane accounts ke liye role detect karo
            if NGOProfile.objects.filter(user=request.user).exists():
                role = 'NGO'
            elif Food.objects.filter(donor=request.user).exists():
                role = 'Donor'
            elif Pickup.objects.filter(volunteer=request.user).exists():
                role = 'Volunteer'
            else:
                role = None

        is_ngo = role == 'NGO'
        is_donor = role == 'Donor'
        is_volunteer = role == 'Volunteer'

    return {
        'is_ngo': is_ngo,
        'is_donor': is_donor,
        'is_volunteer': is_volunteer,
    }