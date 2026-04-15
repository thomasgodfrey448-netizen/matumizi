from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from core.models import UserProfile, RegistrationCode, Department, Approver
import logging

logger = logging.getLogger(__name__)


def _get_user_profile(user):
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def _is_user_code_department_valid(user):
    try:
        profile = _get_user_profile(user)
        if not profile or not profile.registration_code_used:
            return True
        try:
            code_obj = RegistrationCode.objects.get(code=profile.registration_code_used)
        except RegistrationCode.DoesNotExist:
            return False
        if code_obj.department:
            return profile.department is not None and code_obj.department_id == profile.department_id
        return True
    except Exception as e:
        logger.exception(f"Error validating user code/department for user {user.id}: {e}")
        return True  # Allow user to proceed but log the error


def login_view(request):
    try:
        if request.user.is_authenticated:
            return redirect('core:home')
        if request.method == 'POST':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            try:
                user = authenticate(request, username=username, password=password)
            except Exception as e:
                logger.exception(f"Error during authentication for username {username}: {e}")
                messages.error(request, 'An error occurred during login. Please try again.')
                return render(request, 'accounts/login.html')
            
            if user:
                try:
                    if not _is_user_code_department_valid(user):
                        messages.error(request, 'Your registration code does not match your selected department.')
                        return render(request, 'accounts/login.html')
                    login(request, user)
                    next_url = request.GET.get('next', '/')
                    return redirect(next_url)
                except Exception as e:
                    logger.exception(f"Error after successful authentication for user {user.id}: {e}")
                    messages.error(request, 'An error occurred after login. Please try again.')
                    return render(request, 'accounts/login.html')
            else:
                messages.error(request, 'Invalid username or password.')
        return render(request, 'accounts/login.html')
    except Exception as e:
        logger.exception(f"Unhandled error in login_view: {e}")
        messages.error(request, 'An unexpected error occurred. Please contact administrator.')
        return render(request, 'accounts/login.html')


def register_view(request):
    try:
        departments = Department.objects.filter(is_active=True)
    except Exception as e:
        logger.exception(f"Error fetching departments in register_view: {e}")
        departments = []
        messages.warning(request, 'Unable to load departments. Please try again later.')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        reg_code = request.POST.get('registration_code', '').strip()
        department_id = request.POST.get('department', '').strip()

        errors = []
        code_obj = None
        if reg_code:
            try:
                code_obj = RegistrationCode.objects.get(code=reg_code)
                if not code_obj.is_valid():
                    errors.append('Invalid code.')
                if not department_id:
                    errors.append('Department is required.')
                elif code_obj.department and department_id != str(code_obj.department.id):
                    errors.append('Selected department does not match registration code.')
            except RegistrationCode.DoesNotExist:
                errors.append('Invalid code.')
            except Exception as e:
                logger.exception(f"Error validating registration code: {e}")
                errors.append('An error occurred validating the code. Please try again.')
        else:
            errors.append('Invalid code.')

        if not errors:  # Only check other fields if no code errors
            if not all([first_name, last_name, username, phone, password, confirm_password, reg_code, department_id]):
                errors.append('All fields are required.')
            if password != confirm_password:
                errors.append('Passwords do not match.')
            try:
                if User.objects.filter(username=username).exists():
                    errors.append('Username already taken.')
            except Exception as e:
                logger.exception(f"Error checking username availability: {e}")
                errors.append('An error occurred checking username. Please try again.')
            if len(password) < 6:
                errors.append('Password must be at least 6 characters.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'accounts/register.html', {
                'departments': departments,
                'form_values': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'username': username,
                    'phone_number': phone,
                    'registration_code': reg_code,
                    'department_id': department_id,
                }
            })

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = phone
            profile.is_approved = True
            profile.registration_code_used = reg_code
            profile.department_id = int(department_id) if department_id and department_id.isdigit() else None
            profile.save()

            if code_obj:
                code_obj.use_count += 1
                if code_obj.use_count >= code_obj.max_uses:
                    code_obj.is_used = True
                code_obj.used_by = user
                code_obj.save()

        messages.success(request, 'Account created successfully! Please login.')
        return redirect('accounts:login')

    return render(request, 'accounts/register.html', {
        'departments': departments,
        'form_values': {},
    })


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def get_department_from_code(request):
    code = request.GET.get('code', '').strip()
    if code:
        try:
            code_obj = RegistrationCode.objects.get(code=code)
            if code_obj.department:
                return JsonResponse({'department_id': code_obj.department.id, 'department_name': code_obj.department.name})
        except RegistrationCode.DoesNotExist:
            pass
        except Exception as e:
            logger.exception(f"Error fetching registration code: {e}")
    return JsonResponse({'department_id': None, 'department_name': None})


@login_required
def profile_view(request):
    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
    except Exception as e:
        logger.exception(f"Error getting user profile: {e}")
        messages.error(request, 'Unable to load profile. Please try again later.')
        return redirect('core:home')
    
    try:
        departments = Department.objects.filter(is_active=True)
    except Exception as e:
        logger.exception(f"Error fetching departments in profile_view: {e}")
        departments = []
    
    if request.method == 'POST':        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.save()
        profile.phone_number = request.POST.get('phone_number', profile.phone_number)
        dept_id = request.POST.get('department')
        if dept_id:
            try:
                profile.department = Department.objects.get(id=dept_id)
            except Department.DoesNotExist:
                pass
        profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'profile': profile, 'departments': departments})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully.')
    return redirect('accounts:profile')
