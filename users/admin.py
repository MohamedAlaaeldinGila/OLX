from django.contrib import admin
from .models import UserProfile, Notification, OTP, NotificationType

admin.site.register(UserProfile)
admin.site.register(Notification)
admin.site.register(OTP)
admin.site.register(NotificationType)
