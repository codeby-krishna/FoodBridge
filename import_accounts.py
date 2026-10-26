import json
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodbridge.settings")
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile

with open("accounts.json", "r", encoding="utf-16") as file:
    records = json.load(file)

wanted = {"donor1": "Donor", "ngo1": "NGO", "volunteer1": "Volunteer"}
users_data = {}
profiles_data = {}

for record in records:
    model = record.get("model")
    fields = record.get("fields", {})

    if model == "auth.user" and fields.get("username") in wanted:
        users_data[fields["username"]] = fields

    elif model == "core.userprofile":
        profiles_data[fields.get("user")] = fields.get("role")

for username, role in wanted.items():
    fields = users_data.get(username)

    if not fields:
        print(f"{username}: accounts.json mein nahi mila.")
        continue

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "password": fields["password"],
            "first_name": fields.get("first_name", ""),
            "last_name": fields.get("last_name", ""),
            "email": fields.get("email", ""),
            "is_staff": fields.get("is_staff", False),
            "is_active": fields.get("is_active", True),
            "is_superuser": fields.get("is_superuser", False),
        },
    )

    if not created:
        print(f"{username}: Neon mein pehle se hai; user change nahi kiya.")
    else:
        print(f"{username}: user import ho gaya.")

    old_pk = next(
        (r["pk"] for r in records
         if r.get("model") == "auth.user"
         and r.get("fields", {}).get("username") == username),
        None,
    )
    profile_role = profiles_data.get(old_pk, role)

    profile, profile_created = UserProfile.objects.get_or_create(
        user=user,
        defaults={"role": profile_role},
    )
    print(f"{username}: role={profile.role}")