from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt
# --- Password Reset Views ---
@csrf_exempt
def forgot_password(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})
    username = request.POST.get('username')
    if not username:
        return JsonResponse({'success': False, 'message': 'Username required.'})
    try:
        user = User.objects.get(username=username)
        if not user.email:
            return JsonResponse({'success': False, 'message': 'No email associated with this account.'})
        # Generate OTP and send email
        otp = OTP.generate_otp(user)
        send_mail(
            'Your Password Reset OTP',
            f'Your OTP for password reset is: {otp}\nThis OTP will expire in 5 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        # Store user id in session for reset
        request.session['user_id_for_reset'] = user.id
        return JsonResponse({'success': True, 'message': f'OTP sent to {user.email}'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@csrf_exempt
def reset_password(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})
    username = request.POST.get('username')
    otp = request.POST.get('otp')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')
    if not (username and otp and new_password and confirm_password):
        return JsonResponse({'success': False, 'message': 'All fields are required.'})
    if new_password != confirm_password:
        return JsonResponse({'success': False, 'message': 'Passwords do not match.'})
    try:
        user = User.objects.get(username=username)
        # Find all OTPs for this user
        otp_objs = OTP.objects.filter(user=user)
        if not otp_objs.exists():
            return JsonResponse({'success': False, 'message': 'OTP not found. Please request a new one.'})
        # Find a valid OTP
        valid_otp_obj = None
        for otp_obj in otp_objs:
            if otp_obj.is_valid() and otp_obj.otp == otp:
                valid_otp_obj = otp_obj
                break
        if not valid_otp_obj:
            return JsonResponse({'success': False, 'message': 'Invalid or expired OTP.'})
        # Set new password
        user.password = make_password(new_password)
        user.is_active = True  # Ensure user is active after reset
        user.save()
        # Delete all OTPs for this user
        otp_objs.delete()
        return JsonResponse({'success': True, 'message': 'Password reset successful. You can now log in.'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
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
from django.views.decorators.csrf import csrf_exempt

# Set up logging
logger = logging.getLogger(__name__)

def get_academic_years():
    """Generate a list of academic years including past years"""
    current_year = datetime.now().year
    # Generate years from 10 years before current to 3 years after
    years = []
    for year in range(current_year - 10, current_year + 4):
        academic_year = f"{year}-{year + 1}"
        years.append({
            'value': academic_year,
            'label': academic_year,
            'selected': year == current_year
        })
    # Sort in descending order (most recent first)
    years.sort(key=lambda x: x['value'], reverse=True)
    return years

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
        
        if user is not None and user.is_active:  # Allow any active user to login
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
                    'message': 'Invalid credentials, inactive user, or insufficient permissions.'
                })
            messages.error(request, 'Invalid credentials, inactive user, or insufficient permissions.')
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
            return render(request, 'upload_results.html', {
                'existing_pdfs': existing_pdfs,
                'academic_years': get_academic_years()
            })

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
        
        return render(request, 'upload_results.html', {
            'existing_pdfs': existing_pdfs,
            'academic_years': get_academic_years()
        })

    # For GET requests, show upload form with existing PDFs
    return render(request, 'upload_results.html', {
        'existing_pdfs': existing_pdfs,
        'academic_years': get_academic_years()
    })

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
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if class_name == 'class_10':
            analyzer_path = os.path.abspath(os.path.join(base_dir, 'student_api', 'text_recognition', 'src', 'class_10', 'test10th.py'))
            pdf_path = os.path.abspath(os.path.join(base_dir, 'student_api', 'text_recognition', 'data', 'class_10', file_name))
            pdf_files = [pdf_path]
            analyzer_args = [sys.executable, analyzer_path] + pdf_files
        elif class_name == 'class_12_all':
            # Parse file_name from JSON string to dict
            try:
                file_name_dict = json.loads(file_name)
            except Exception:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid file_name format for class_12_all.'
                })
            analyzer_path = os.path.abspath(os.path.join(base_dir, 'student_api', 'text_recognition', 'src', 'class_12', 'test12th.py'))
            pdf_files = []
            if file_name_dict.get('science'):
                pdf_science = os.path.abspath(os.path.join(base_dir, 'student_api', 'text_recognition', 'data', 'class_12_science', file_name_dict['science']))
                pdf_files.append(pdf_science)
            if file_name_dict.get('commerce'):
                pdf_commerce = os.path.abspath(os.path.join(base_dir, 'student_api', 'text_recognition', 'data', 'class_12_commerce', file_name_dict['commerce']))
                pdf_files.append(pdf_commerce)
            if file_name_dict.get('humanities'):
                pdf_humanities = os.path.abspath(os.path.join(base_dir, 'student_api', 'text_recognition', 'data', 'class_12_humanities', file_name_dict['humanities']))
                pdf_files.append(pdf_humanities)
            if not pdf_files:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No valid Class XII PDF files found to process.'
                })
            analyzer_args = [sys.executable, analyzer_path] + pdf_files
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Processing not implemented for this class yet'
            })

        try:
            if not os.path.exists(analyzer_path):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Result analyzer script not found'
                })

            for pdf in pdf_files:
                if not os.path.exists(pdf):
                    return JsonResponse({
                        'status': 'error',
                        'message': f'PDF file not found: {pdf}'
                    })

            # Run the analyzer script with all PDFs as arguments
            process = subprocess.Popen(
                analyzer_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            # Log output for debugging
            logger.info(f"Analyzer stdout: {stdout}")
            logger.error(f"Analyzer stderr: {stderr}")

            try:
                output_text = stdout.decode('utf-8', errors='replace')
            except Exception as e:
                output_text = str(stdout)
            try:
                error_text = stderr.decode('utf-8', errors='replace')
            except Exception as e:
                error_text = str(stderr)

            if process.returncode == 0:
                # Try to parse output as JSON (for API results)
                try:
                    api_results = json.loads(output_text)
                    return JsonResponse({
                        'status': 'success',
                        'message': 'PDF processing completed successfully',
                        'api_results': api_results
                    })
                except Exception:
                    # If not JSON, return raw output
                    return JsonResponse({
                        'status': 'success',
                        'message': 'PDF processing completed successfully',
                        'output': output_text
                    })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error processing PDF',
                    'output': output_text,
                    'error': error_text
                })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
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

@csrf_exempt
def delete_pdf(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
    class_name = request.POST.get('class_name')
    file_name = request.POST.get('file_name')
    if not class_name or not file_name:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters.'})
    # Map class_name to folder
    folder_map = {
        'class_10': os.path.join('student_api', 'text_recognition', 'data', 'class_10'),
        'class_12_science': os.path.join('student_api', 'text_recognition', 'data', 'class_12_science'),
        'class_12_commerce': os.path.join('student_api', 'text_recognition', 'data', 'class_12_commerce'),
        'class_12_humanities': os.path.join('student_api', 'text_recognition', 'data', 'class_12_humanities'),
    }
    folder = folder_map.get(class_name)
    if not folder:
        return JsonResponse({'status': 'error', 'message': 'Invalid class name.'})
    file_path = os.path.join(folder, file_name)
    if not os.path.isfile(file_path):
        return JsonResponse({'status': 'error', 'message': 'File not found.'})
    try:
        os.remove(file_path)
        return JsonResponse({'status': 'success', 'message': f'{file_name} deleted successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error deleting file: {str(e)}'})
