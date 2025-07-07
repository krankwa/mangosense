from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import render
import json

# Validation Functions
def validate_password_strength(password):
    """Validate password strength - minimum 8 characters"""
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    return errors

def validate_name(name, field_name):
    """Validate first name and last name"""
    errors = []
    if not name or len(name.strip()) < 2:
        errors.append(f"{field_name} must be at least 2 characters long.")
    return errors

def validate_address(address):
    """Validate address field"""
    errors = []
    if not address or len(address.strip()) < 5:
        errors.append("Address must be at least 5 characters long.")
    if len(address) > 200:
        errors.append("Address cannot exceed 200 characters.")
    return errors

# Authentication Views
def register_view(request):
    if request.method == 'GET':
        return render(request, 'mangosense/register.html')

@csrf_exempt
@require_http_methods(["POST"])
def register_api(request):
    try:
        data = json.loads(request.body)
        
        # Handle both camelCase (Ionic) and snake_case (Django) field names
        first_name = (data.get('first_name') or data.get('firstName', '')).strip()
        last_name = (data.get('last_name') or data.get('lastName', '')).strip()
        address = data.get('address', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password') or data.get('confirmPassword') or password
        
        errors = []

        # Required fields validation
        if not all([first_name, last_name, address, email, password]):
            return JsonResponse({
                'success': False,
                'error': 'All required fields must be provided.'
            }, status=400)
        
        # Validation
        errors.extend(validate_name(first_name, "First name"))
        errors.extend(validate_name(last_name, "Last name"))
        errors.extend(validate_address(address))

        # Email validation
        try:
            validate_email(email)
        except ValidationError:
            errors.append("Invalid email format.")

        # Check for existing email
        if User.objects.filter(email=email).exists():
            errors.append("An account with this email already exists.")

        # Password validation
        if confirm_password and password != confirm_password:
            errors.append("Passwords do not match.")
        
        errors.extend(validate_password_strength(password))

        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        
        # Create user
        user = User.objects.create_user(
            username=email,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        return JsonResponse({
            'success': True,
            'message': 'Account created successfully! You may now log in',
            'user_id': user.id,
            'note': 'Address received but not stored (requires profile model)'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid data format.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An unexpected error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def login_api(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return JsonResponse({
                'success': False,
                'error': 'Email and password are required.'
            }, status=400)
        
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid email address.'
            }, status=400)
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Login successful.',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'firstName': user.first_name,
                        'lastName': user.last_name,
                        'full_name': f"{user.first_name} {user.last_name}"
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Your account is deactivated. Please contact support.'
                }, status=401)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid email or password.'
            }, status=401)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid data format.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An unexpected error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def logout_api(request):
    if request.user.is_authenticated:
        logout(request)
        return JsonResponse({
            'success': True,
            'message': 'Logout successful.'
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'You are not logged in.'
        }, status=401)