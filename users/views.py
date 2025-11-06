from datetime import timedelta
from venv import logger
from django.shortcuts import get_object_or_404, render, redirect
from .forms import UserSignUpForm, CustomAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login, authenticate
import random
import time
from django.core.mail import send_mail
from .models import UserProfile, OTP, Notification
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import NotificationSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication

from rest_framework_simplejwt.tokens import RefreshToken  # ✅ ADD THIS IMPORT
from rest_framework_simplejwt.authentication import JWTAuthentication  # ✅ AND THIS
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken  # ✅ AND THIS

from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, 
    UserProfileSerializer, UserProfileUpdateSerializer,
    ChangePasswordSerializer
)
from django.contrib.auth import get_user_model, login, logout

from django.core.mail import send_mail
from django.conf import settings

from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken


User = get_user_model()
def signup(request):
    if request.method == 'POST':
        form = UserSignUpForm(request.POST)
        print("endered signup view")
        if form.is_valid():

            user = form.save(commit=False)
            user.is_active = False 
            user.save()
            opt = OTP.generate_otp(user, purpose='signup')

            Notification.send_notification(
                user=user,
                title="Welcome to Our Platform!",
                message="Thank you for signing up. Please verify your email to get started.",
                notification_type_code='system',
                priority=2
            )
            return redirect('verify-otp')
    else:
        form = UserSignUpForm()

    return render(request, 'users/signup.html', {'form': form})


'''def login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                try:
                    if user.is_2fa_enabled is True:
                        print("2FA is enabled, sending OTP")
                        # Generate and send OTP
                        otp = OTP.generate_otp(user, purpose='login')

                        print(f"OTP sent to {user.email}: {otp}")

                        return redirect('verify-otp')
                    else:
                        auth_login(request, user)
                        return redirect('dashboard')
                    
                except UserProfile.DoesNotExist:
                    print(f"No user profile for {user.username}, logging in without 2FA")
                    auth_login(request, user)
                    return redirect('dashboard')
        else:
            print("form invalid")
    else:
        form = CustomAuthenticationForm()

    return render(request, 'users/login.html', {'form': form})
    

def verify_otp(request):
    """Universal OTP verification for both signup and login"""
    if request.method == 'POST':
        entered_otp = request.POST.get('otp_code')
        
        if not entered_otp:
            return render(request, 'users/verify_otp.html', {
                'error': 'Please enter the verification code.'
            })
        
        # ✅ FIX: Use __in for multiple values
        latest_otp = OTP.objects.filter(
            purpose__in=['signup', 'login'],  # ✅ Use __in for list of values
            is_used=False
        ).order_by('-created_at').first()
        
        # ✅ ADD: Debug prints to see what's happening
        print(f"Latest OTP found: {latest_otp}")
        if latest_otp:
            print(f"OTP purpose: {latest_otp.purpose}")
            print(f"OTP user: {latest_otp.user}")
            print(f"OTP code: {latest_otp.code}")
        else:
            # ✅ Check if there are any OTPs at all
            all_otps = OTP.objects.all()
            print(f"Total OTPs in database: {all_otps.count()}")
            for otp in all_otps:
                print(f"OTP: {otp.user} - {otp.purpose} - {otp.code} - Used: {otp.is_used}")
        
        if not latest_otp:
            return render(request, 'users/verify_otp.html', {
                'error': 'No active verification session. Please try again.'
            })
        
        user = latest_otp.user
        
        # ✅ Verify with the correct purpose from the OTP record
        is_valid, message = OTP.verify_otp(user, entered_otp, purpose=latest_otp.purpose)
        
        if is_valid:
            # ✅ Handle different actions based on OTP purpose
            if latest_otp.purpose == 'signup':
                # Activate user account for signup
                user.is_active = True
                user.save()
                
                # Send welcome notification
                Notification.send_notification(
                    user=user,
                    title="Email Verified Successfully!",
                    message="Your email has been verified. Welcome to our platform!",
                    notification_type_code='security',
                    priority=3
                )
            
            elif latest_otp.purpose == 'login':
                # Send login notification for 2FA
                Notification.send_notification(
                    user=user,
                    title="2FA Login Successful",
                    message="You have successfully logged in with two-factor authentication.",
                    notification_type_code='security'
                )
            
            # ✅ Log the user in (works for both signup and login)
            auth_login(request, user)
            
            return redirect('dashboard')
        else:
            return render(request, 'users/verify_otp.html', {
                'error': message,
                'user': user,
                'purpose': latest_otp.purpose
            })
    
    # GET request - show the form
    return render(request, 'users/verify_otp.html')

def resend_otp(request):
    """Resend OTP for both signup and login"""
    # ✅ FIX: Use __in for multiple values
    latest_otp = OTP.objects.filter(
        purpose__in=['signup', 'login'],  # ✅ Use __in
        is_used=False
    ).order_by('-created_at').first()
    
    # ✅ ADD: Debug prints
    print(f"Resend - Latest OTP found: {latest_otp}")
    
    if latest_otp and latest_otp.is_valid():
        user = latest_otp.user
        
        # ✅ Resend with the same purpose
        otp_obj = OTP.generate_otp(user, purpose=latest_otp.purpose)
        
        print(f"New {latest_otp.purpose} OTP sent to {user.email}: {otp_obj.code}")
        return redirect('verify-otp')
    
    return redirect('login')'''

class UserRegistrationAPIView(APIView):
    """
    POST: Register a new user
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(is_verified=False)  # Inactive until email verification
            otp_obj = OTP.generate_otp(user, purpose='signup')

            send_mail(
                subject="Your OTP Code for Account Verification",
                message=f"Hello {user.first_name},\n\nYour OTP code is: {otp_obj.code}\n\nUse this code to verify your account.\n\nThank you!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
                        
            
            return Response({
                'message': 'User registered successfully. Please verify your email with the OTP sent.',
                'user_id': user.id,
                'email': user.email,
                'next_step': 'verify_otp'
            }, status=status.HTTP_201_CREATED)

        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginAPIView(APIView):
    """
    POST: Login user with email and password
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        print(f"🔍 DEBUG: Login attempt with email: {email}")
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find user by email
            user = UserProfile.objects.get(email=email)
            print(f"🔍 DEBUG: User found: {user.username}")
            
            # Check password
            if user.check_password(password):
                if user.is_active:
                    # ✅ Create or get token (NO login() function!)
                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)
                    refresh_token = str(refresh)
                    
                    return Response({
                        'message': 'Login successful',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'user_type': user.user_type
                        },
                        'tokens': {
                            'refresh': refresh_token,
                            'access': access_token,
                        }
                    })
                else:
                    return Response(
                        {'error': 'Account is disabled'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                print("🔍 DEBUG: Password incorrect")
                return Response(
                    {'error': 'Invalid email or password'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except UserProfile.DoesNotExist:
            print("🔍 DEBUG: User not found")
            return Response(
                {'error': 'Invalid email or password'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class UserLogoutAPIView(APIView):
    """
    POST: Logout user and delete token
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Delete the token
        try:
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            pass
        
        logout(request)
        
        return Response({
            'message': 'Logout successful'
        })

class UserProfileAPIView(APIView):
    """
    GET: Get user profile
    PUT: Update user profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request):
        try:
            user = request.user
            serializer = UserProfileUpdateSerializer(user, data=request.data)
            
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Profile updated successfully',
                    'profile': UserProfileSerializer(user).data
                })
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class ChangePasswordAPIView(APIView):
    """
    POST: Change user password
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            
            # Check old password
            if not request.user.check_password(old_password):
                return Response(
                    {'error': 'Current password is incorrect'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            request.user.set_password(new_password)
            request.user.save()
            
            # Update token (optional: create new token on password change)
            try:
                request.user.auth_token.delete()
            except (AttributeError, Token.DoesNotExist):
                pass
            
            new_token = Token.objects.create(user=request.user)
            
            return Response({
                'message': 'Password changed successfully',
                'token': new_token.key  # Return new token
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeleteAccountAPIView(APIView):
    """
    DELETE: Delete user account
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        user = request.user
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'error': 'Password is required to delete account'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.check_password(password):
            return Response(
                {'error': 'Invalid password'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete user (this will cascade to UserProfile and other related models)
        user.delete()
        
        return Response({
            'message': 'Account deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

class CheckAuthAPIView(APIView):
    """
    GET: Check if user is authenticated and return user data
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            serializer = UserProfileSerializer(profile)
            return Response({
                'is_authenticated': True,
                'user': serializer.data
            })
        except UserProfile.DoesNotExist:
            return Response({
                'is_authenticated': True,
                'user': {
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'email': request.user.email,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name
                }
            })

#-------------------------------------------------------Notification APIs-------------------------------------------------------#

class NotificationListAPIView(APIView):
    """
    Get: Returns all notifications as JSON
    """
    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user, 
            is_archived=False
        )

        serializer = NotificationSerializer(notifications, many=True)

        return Response(serializer.data)
    

class NotificationDetailAPIView(APIView):
    def get(self, request, pk):
        """Get specific notification"""
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            serializer = NotificationSerializer(notification)
            return Response(serializer.data)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        

class NotificationMarkUnreadAPIView(APIView):
    def post(self, request, pk):
        """Mark notification as unread"""
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.mark_as_unread()
            serializer = NotificationSerializer(notification)
            return Response({
                'message': 'Notification marked as unread',
                'notification': serializer.data
            })
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class NotificationMarkReadAPIView(APIView):
    def post(self, request, pk):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.mark_as_read()
            serializer = NotificationSerializer(notification)
            return Response({
                'message': 'Notification marked as read',
                'notification': serializer.data
            })
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class NotificationUnreadListAPIView(APIView):
    def get(self, request):
        """Get all unread notifications"""
        notifications = Notification.objects.filter(
            user=request.user, 
            is_read=False,
            is_archived=False
        ).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'notifications': serializer.data
        })
    


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=400)

        user = get_object_or_404(User, email=email)
        otp_obj = OTP.generate_otp(user, purpose="reset_password")

        print(f"🔑 Password reset OTP for {user.email}: {otp_obj.code}")  # For dev/testing

        # Only return success message
        return Response({"message": "OTP sent to your email"}, status=200)


class VerifyResetOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp_code = request.data.get("otp_code")

        if not email or not otp_code:
            return Response({"error": "Email and OTP are required"}, status=400)

        user = get_object_or_404(UserProfile, email=email)
        is_valid, message = OTP.verify_otp(user, otp_code, purpose="reset_password")

        if not is_valid:
            return Response({"error": message}, status=400)

        # ✅ Create a short-lived JWT for reset
        refresh = RefreshToken.for_user(user)
        reset_token = str(refresh.access_token)  # can also add custom claims if needed

        return Response({
            "message": "OTP verified",
            "reset_token": reset_token
        }, status=200)

class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")
        reset_token = request.data.get("reset_token")

        if not all([email, new_password, confirm_password, reset_token]):
            return Response({"error": "All fields are required"}, status=400)
        if new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=400)

        user = get_object_or_404(UserProfile, email=email)

        # ✅ Verify the token belongs to this user
        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(reset_token)
            token_user = jwt_auth.get_user(validated_token)
            if token_user != user:
                return Response({"error": "Invalid token for this user"}, status=400)
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=400)

        # ✅ Reset password
        user.set_password(new_password)
        user.save()

        return Response({"message": "Password reset successful. You can now log in."}, status=200)


class VerifyOTPAPIView(APIView):
    """
    POST: Verify OTP for signup
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response({"error": "Email and code are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            otp = OTP.objects.filter(user=user, is_used=False, purpose="signup").order_by("-created_at").first()
            print(f"🔍 DEBUG: Found OTP - {otp}")
            if not otp:
                return Response({"error": "No active OTP found."}, status=status.HTTP_400_BAD_REQUEST)

            # call your OTP verification method
            is_valid, message = OTP.verify_otp(user, code, purpose="signup")

            if not is_valid:
                return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ Mark user verified and active
            user.is_verified = True
            user.is_active = True
            user.save()

            # Mark OTP as used
            otp.is_used = True
            #otp.used_at = timezone.now()
            otp.save()



            return Response({"message": "Email verified successfully!"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"OTP verification error: {e}")
            return Response({"error": "Internal server error. {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
