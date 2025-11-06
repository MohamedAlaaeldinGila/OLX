from django.urls import path
from .views import VerifyOTPAPIView, VerifyResetOTPAPIView,  NotificationListAPIView, NotificationDetailAPIView, NotificationUnreadListAPIView, NotificationMarkUnreadAPIView, NotificationMarkReadAPIView
from django.contrib.auth import views as auth_views
from .views import UserRegistrationAPIView, UserLoginAPIView, UserLogoutAPIView, UserProfileAPIView, ChangePasswordAPIView, DeleteAccountAPIView, CheckAuthAPIView, ForgotPasswordAPIView, ResetPasswordAPIView


urlpatterns = [
    #path('login/', login, name='login'), 
    #path('signup/', signup, name='signup'),
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), 
         name='password_reset_complete'),

    #path('verify-otp/', verify_otp, name='verify-otp'),
    #path('resend-otp/', resend_otp, name='resend-otp'),
    path('notifications/', NotificationListAPIView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', NotificationDetailAPIView.as_view(), name='notification-detail'),
    path('notifications/unread/', NotificationUnreadListAPIView.as_view(), name='notification-unread-list'),
    path('notifications/<int:pk>/mark-unread/', NotificationMarkUnreadAPIView.as_view(), name='notification-mark-unread'),
    path('notifications/<int:pk>/mark-read/', NotificationMarkReadAPIView.as_view(), name='notification-mark-read'),
    
    # Authentication
    path('register/', UserRegistrationAPIView.as_view(), name='user-register'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('logout/', UserLogoutAPIView.as_view(), name='user-logout'),
    
    # Profile Management
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='change-password'),
    path('delete-account/', DeleteAccountAPIView.as_view(), name='delete-account'),
    
    # Auth Check
    path('check-auth/', CheckAuthAPIView.as_view(), name='check-auth'),

    # Password Reset
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset-password'),
    path('verify-reset-otp/', VerifyResetOTPAPIView.as_view(), name='verify-reset-otp'),
    path('verify-otp/', VerifyOTPAPIView.as_view(), name='verify-otp'),

]

