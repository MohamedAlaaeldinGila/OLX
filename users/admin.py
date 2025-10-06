from django.contrib import admin
from .models import UserProfile, Notification, OTP

admin.site.register(UserProfile)
admin.site.register(Notification)
admin.site.register(OTP)

