from django.db import models
from django.contrib.auth.models import AbstractUser

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
import random 
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from .constants import DEFAULT_NotificationType



class UserProfile(AbstractUser):
    USER_TYPES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    ]

    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPES, 
        default='customer'
    )

    email = models.EmailField(
        unique=True,
        blank=False,
        null=False,
        error_messages={
            'unique': "A user with that email already exists.",
        }
    )

    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_2fa_enabled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} Profile"
    
    @property
    def is_vendor(self):
        return self.user_type == 'vendor'
    
    @property
    def is_customer(self):
        return self.user_type == 'customer'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin'
    
    def generate_otp(self):
        """Generate a 6-digit OTP and send via email"""
        otp = random.randint(100000, 999999)
        
        # Send OTP via email
        send_mail(
            'Your Verification Code',
            f'Your verification code is: {otp}\n\nThis code will expire in 5 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [self.email],
            fail_silently=False,
        )
        return otp

class NotificationType(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    default_template = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    priority = models.CharField(max_length=10, default='normal')
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return self.name
    
class Notification(models.Model):
    """NOTIFICATION_TYPES = [
        ('order', 'Order Update'),
        ('promotion', 'Promotion'),
        ('security', 'Security Alert'),
        ('system', 'System Notification'),
        ('product', 'Product Update'),
    ]"""
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.ForeignKey(
        NotificationType, 
        on_delete=models.PROTECT,
        related_name='notifications',  # ✅ Add related_name
        default= DEFAULT_NotificationType.SYSTEM
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    action_url = models.URLField(blank=True, null=True)  # URL to redirect when clicked
    image = models.ImageField(upload_to='notifications/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def mark_as_unread(self):
        """Mark notification as unread"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save()
    
    def archive(self):
        """Archive the notification"""
        self.is_archived = True
        self.save()
    
    def is_expired(self):
        """Check if notification is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @classmethod
    def send_notification(cls, user, title, message, notification_type_code, **kwargs):
        """Helper method to send notifications"""
        try:
            notification_type = NotificationType.objects.get(code=notification_type_code)
            notification = cls.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=kwargs.get('priority', notification_type.priority),
                action_url=kwargs.get('action_url'),
                image=kwargs.get('image'),
                data=kwargs.get('data'),
                expires_at=kwargs.get('expires_at'),
            )
            return notification
        except NotificationType.DoesNotExist:
            return None
    
    @classmethod
    def send_bulk_notification(cls, users, title, message, notification_type_code, **kwargs):
        """Send notification to multiple users"""
        notifications = []
        notification_type = NotificationType.objects.get(code=notification_type_code)
        
        for user in users:
            notifications.append(cls(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=kwargs.get('priority', notification_type.priority),
                action_url=kwargs.get('action_url'),
                data=kwargs.get('data'),
            ))
        
        cls.objects.bulk_create(notifications)
        return len(notifications)
    

class OTP(models.Model):
    """Secure OTP storage instead of session"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)  # 6-digit OTP
    purpose = models.CharField(max_length=50, default='login')  # login, password_reset, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.user.username} - {self.code}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return not self.is_expired() and not self.is_used and self.attempts < 3
    
    def mark_used(self):
        self.is_used = True
        self.save()
    
    def increment_attempts(self):
        self.attempts += 1
        self.save()
    
    @classmethod
    def generate_otp(cls, user, purpose='login'):
        """Generate and send OTP"""
        # Delete any existing unused OTPs for this user and purpose
        cls.objects.filter(user=user, purpose=purpose, is_used=False).delete()
        
        # Generate secure 6-digit code
        code = str(random.randint(100000, 999999))
        
        # Create OTP record (expires in 5 minutes)
        otp = cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        # Send email
        send_mail(
            'Your Verification Code',
            f'Your verification code is: {code}\n\nThis code will expire in 5 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return otp
    
    @classmethod
    def verify_otp(cls, user, code, purpose='login'):
        """Verify OTP code"""
        try:
            otp = cls.objects.get(
                user=user, 
                purpose=purpose, 
                is_used=False
            )
            
            if not otp.is_valid():
                return False, "OTP expired or invalid"
            
            if otp.code != code:
                otp.increment_attempts()
                remaining_attempts = 3 - otp.attempts
                if remaining_attempts > 0:
                    return False, f"Invalid code. {remaining_attempts} attempts remaining."
                else:
                    return False, "Too many failed attempts. Please request a new OTP."
            
            # Valid OTP
            otp.mark_used()
            return True, "OTP verified successfully"
            
        except cls.DoesNotExist:
            return False, "No active OTP found. Please request a new one."
         
