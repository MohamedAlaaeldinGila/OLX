from django.shortcuts import render, redirect
from .forms import UserSignUpForm, CustomAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login, authenticate
import random
import time
from django.core.mail import send_mail
from .models import UserProfile, OTP, Notification
from django.conf import settings


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


def login(request):
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
    
    return redirect('login')