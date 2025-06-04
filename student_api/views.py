from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import OTP
from django.urls import reverse
from django.http import JsonResponse
import json
import logging
import traceback
from django.core.files.storage import FileSystemStorage
import os
from datetime import datetime
import subprocess
import sys

# Set up logging
logger = logging.getLogger(__name__)

def login(request):
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Log the login attempt
        logger.info(f"Login attempt for username: {username}")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:  # Only allow staff/teachers to login
            try:
                # Check if user has an email
                if not user.email:
                    logger.error(f"No email address found for user {username}")
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': 'No email address associated with this account. Please contact admin.'
                        })
                    messages.error(request, 'No email address associated with this account. Please contact admin.')
                    return render(request, 'login.html')

                # Generate and send OTP
                try:
                    otp = OTP.generate_otp(user)
                    logger.info(f"Generated OTP for user {username}")

                    # Send OTP via email
                    logger.info(f"Attempting to send OTP email to {user.email}")
                    send_mail(
                        'Your OTP for Student API Login',
                        f'Your OTP is: {otp}\nThis OTP will expire in 5 minutes.',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    logger.info(f"Successfully sent OTP email to {user.email}")
                    
                    # Store user ID in session for OTP verification
                    request.session['user_id_for_otp'] = user.id
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'require_otp': True,
                            'message': f'OTP has been sent to {user.email}'
                        })
                    return redirect('verify_otp')
                    
                except Exception as e:
                    logger.error(f"Failed to send OTP email: {str(e)}")
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': 'Error sending OTP. Please try again later.'
                        })
                    messages.error(request, 'Error sending OTP. Please try again later.')
                    return render(request, 'login.html')
                    
            except Exception as e:
                logger.error(f"Error in login process: {str(e)}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'An error occurred during login. Please try again.'
                    })
                messages.error(request, 'An error occurred during login. Please try again.')
                return render(request, 'login.html')
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid credentials or insufficient permissions.'
                })
            messages.error(request, 'Invalid credentials or insufficient permissions.')
            return render(request, 'login.html')
    
    return render(request, 'login.html')

def verify_otp(request):
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    user_id = request.session.get('user_id_for_otp')
    
    if not user_id:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Please log in first.'
            })
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
                request.session.pop('user_id_for_otp', None)
                otp_obj.delete()
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'redirect_url': reverse('dashboard')
                    })
                return redirect('dashboard')
            else:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid or expired OTP. Please try again.'
                    })
                messages.error(request, 'Invalid or expired OTP. Please try again.')
        except OTP.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'OTP not found. Please request a new one.'
                })
            messages.error(request, 'OTP not found. Please request a new one.')
            return redirect('login')
    
    # For GET requests or failed POST requests in non-AJAX context
    if not is_ajax:
        return redirect('login')
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

def resend_otp(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    user_id = request.session.get('user_id_for_otp')
    
    if not user_id:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Please log in first.'
            })
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
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': 'New OTP has been sent to your email.'
            })
        messages.success(request, 'New OTP has been sent to your email.')
    except Exception as e:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Error sending new OTP. Please try again.'
            })
        messages.error(request, 'Error sending new OTP. Please try again.')
    
    return redirect('verify_otp')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def download_report(request):
    # TODO: Implement report download logic
    return render(request, 'download_report.html')

def get_pdf_files(directory):
    """Get list of PDF files from a directory."""
    try:
        if os.path.exists(directory):
            return [f for f in os.listdir(directory) if f.endswith('.pdf')]
    except Exception as e:
        print(f"Error reading directory {directory}: {str(e)}")
    return []

@login_required
def upload_results(request):
    # Get existing PDFs for each class
    base_dir = os.path.join('student_api', 'text_recognition', 'data')
    existing_pdfs = {
        'class_10': get_pdf_files(os.path.join(base_dir, 'class_10')),
        'class_12_science': get_pdf_files(os.path.join(base_dir, 'class_12_science')),
        'class_12_commerce': get_pdf_files(os.path.join(base_dir, 'class_12_commerce')),
        'class_12_humanities': get_pdf_files(os.path.join(base_dir, 'class_12_humanities'))
    }

    if request.method == 'POST':
        academic_year = request.POST.get('academic_year')
        if not academic_year:
            messages.error(request, 'Please provide the Academic Year')
            return render(request, 'upload_results.html', {'existing_pdfs': existing_pdfs})

        # Create base directories if they don't exist
        base_dir = os.path.join('student_api', 'text_recognition', 'data')
        class_dirs = {
            'class_x_file': ('class_10', os.path.join(base_dir, 'class_10')),
            'class_12_science_file': ('class_12_science', os.path.join(base_dir, 'class_12_science')),
            'class_12_commerce_file': ('class_12_commerce', os.path.join(base_dir, 'class_12_commerce')),
            'class_12_humanities_file': ('class_12_humanities', os.path.join(base_dir, 'class_12_humanities'))
        }

        # Create directories if they don't exist
        for _, dir_path in class_dirs.values():
            os.makedirs(dir_path, exist_ok=True)

        files_uploaded = False
        results = {}

        # Process each class file
        for field_name, (class_name, dir_path) in class_dirs.items():
            if field_name in request.FILES:
                files_uploaded = True
                file = request.FILES[field_name]
                
                try:
                    # Delete existing files in the directory
                    for existing_file in os.listdir(dir_path):
                        if existing_file.endswith('.pdf'):
                            try:
                                os.remove(os.path.join(dir_path, existing_file))
                                logger.info(f"Deleted old file: {existing_file}")
                            except Exception as e:
                                logger.error(f"Error deleting file {existing_file}: {str(e)}")

                    # Create timestamp for unique filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{academic_year}_{timestamp}_{file.name}"
                    
                    # Full path for file storage
                    file_path = os.path.join(dir_path, filename)
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # Save file
                    with open(file_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)
                    
                    # Store results
                    results[field_name] = {
                        'status': 'Success',
                        'filename': filename,
                        'path': file_path
                    }
                    
                    messages.success(request, f'File uploaded successfully for {field_name.replace("_file", "").replace("_", " ").title()}')
                    
                except Exception as e:
                    results[field_name] = {
                        'status': 'Failed',
                        'error': str(e)
                    }
                    messages.error(request, f'Error uploading file for {field_name}: {str(e)}')

        if not files_uploaded:
            messages.error(request, 'Please upload at least one file')
        
        return render(request, 'upload_results.html', {'existing_pdfs': existing_pdfs})

    # For GET requests, show upload form with existing PDFs
    return render(request, 'upload_results.html', {'existing_pdfs': existing_pdfs})

@login_required
def view_charts(request):
    # TODO: Implement charts view logic
    return render(request, 'view_charts.html')

@login_required
def results_view(request):
    """Display the results of file processing."""
    results = request.session.get('processing_results', {})
    academic_year = request.session.get('academic_year', '')
    
    context = {
        'results': results,
        'academic_year': academic_year
    }
    return render(request, 'results_view.html', context)

def logout(request):
    # Clear any session data
    request.session.flush()
    auth_logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def process_pdf(request):
    if request.method == 'POST':
        class_name = request.POST.get('class_name')
        file_name = request.POST.get('file_name')
        
        if class_name == 'class_10':
            try:
                # Construct paths
                pdf_path = os.path.join('student_api', 'text_recognition', 'data', 'class_10', file_name)
                analyzer_path = os.path.join('student_api', 'text_recognition', 'src', 'class_10', 'result_analyzer.py')
                
                if not os.path.exists(analyzer_path):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Result analyzer script not found'
                    })
                
                if not os.path.exists(pdf_path):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'PDF file not found'
                    })
                
                # Run the analyzer script
                process = subprocess.Popen(
                    [sys.executable, analyzer_path, pdf_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    return JsonResponse({
                        'status': 'success',
                        'message': 'PDF processing completed successfully',
                        'output': stdout.decode('utf-8')
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Error processing PDF: {stderr.decode("utf-8")}'
                    })
                    
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error: {str(e)}'
                })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Processing not implemented for this class yet'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
def get_pdf_files_list(request):
    """API endpoint to get list of PDF files."""
    base_dir = os.path.join('student_api', 'text_recognition', 'data')
    existing_pdfs = {
        'class_10': get_pdf_files(os.path.join(base_dir, 'class_10')),
        'class_12_science': get_pdf_files(os.path.join(base_dir, 'class_12_science')),
        'class_12_commerce': get_pdf_files(os.path.join(base_dir, 'class_12_commerce')),
        'class_12_humanities': get_pdf_files(os.path.join(base_dir, 'class_12_humanities'))
    }
    return JsonResponse({'files': existing_pdfs})
