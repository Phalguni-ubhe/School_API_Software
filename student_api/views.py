from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import OTP
from django.urls import reverse

def login(request):
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:  # Only allow staff/teachers to login
            # Generate and send OTP
            otp = OTP.generate_otp(user)            # Check if user has an email
            if not user.email:
                messages.error(request, 'No email address associated with this account. Please contact admin.')
                return render(request, 'login.html')

            # Send OTP via email
            try:
                print(f"Attempting to send OTP to {user.email}")  # Debug log
                print(f"Using email settings: HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}")  # Debug log
                
                send_mail(
                    'Your OTP for Student API Login',
                    f'Your OTP is: {otp}\nThis OTP will expire in 5 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                print("Email sent successfully")  # Debug log
                
                # Store user ID in session for OTP verification
                request.session['user_id_for_otp'] = user.id
                return redirect('verify_otp')
            except Exception as e:
                import traceback
                print(f"Email error: {str(e)}")
                print("Full traceback:")
                print(traceback.format_exc())
                messages.error(request, f'Error sending OTP. Please try again later. Error: {str(e)}')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
    
    return render(request, 'login.html')

def verify_otp(request):
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    user_id = request.session.get('user_id_for_otp')
    if not user_id:
        messages.error(request, 'Please log in first.')
        return redirect('login')
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        try:
            otp_obj = OTP.objects.get(user_id=user_id)
            if otp_obj.is_valid() and otp_obj.otp == entered_otp:
                user = otp_obj.user
                auth_login(request, user)
                # Clean up only after successful verification
                request.session.pop('user_id_for_otp', None)  # Safely remove the session key
                otp_obj.delete()
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid or expired OTP. Please try again.')
                # Don't delete session key here to allow retry
        except OTP.DoesNotExist:
            messages.error(request, 'OTP not found. Please request a new one.')
            # Don't delete session key here to allow resend
    
    return render(request, 'verify_otp.html')

def resend_otp(request):
    user_id = request.session.get('user_id_for_otp')
    if not user_id:
        return redirect('login')
    
    try:
        user = User.objects.get(id=user_id)
        otp = OTP.generate_otp(user)
        
        # Send new OTP via email
        send_mail(
            'Your New OTP for Student API Login',
            f'Your new OTP is: {otp}\nThis OTP will expire in 5 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        messages.success(request, 'New OTP has been sent to your email.')
    except Exception as e:
        messages.error(request, 'Error sending new OTP. Please try again.')
    
    return redirect('verify_otp')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

def logout(request):
    # Clear any session data
    request.session.flush()
    auth_logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')
