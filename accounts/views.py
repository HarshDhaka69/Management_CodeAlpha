from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import RegisterForm, LoginForm, ProfileUpdateForm, UserProfileUpdateForm
from .models import UserProfile


def register_view(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('projects:project_list')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to ProjectFlow, {user.username}! 🎉')
            return redirect('projects:project_list')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('projects:project_list')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            # Redirect to 'next' param if present (from @login_required redirect)
            next_url = request.GET.get('next', 'projects:project_list')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """Log out and redirect to login page."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def profile_view(request, username=None):
    """View and edit a user profile."""
    if username:
        profile_user = get_object_or_404(User, username=username)
        is_own_profile = (profile_user == request.user)
    else:
        profile_user = request.user
        is_own_profile = True

    # Ensure profile exists (safety net in case signal missed)
    profile, _ = UserProfile.objects.get_or_create(user=profile_user)

    if request.method == 'POST' and is_own_profile:
        user_form = ProfileUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileUpdateForm(
            request.POST, request.FILES, instance=profile
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        user_form = ProfileUpdateForm(instance=profile_user)
        profile_form = UserProfileUpdateForm(instance=profile)

    # Get projects this user is a member of
    from projects.models import ProjectMember
    user_projects = ProjectMember.objects.filter(user=profile_user).select_related('project')

    context = {
        'profile_user': profile_user,
        'profile': profile,
        'user_form': user_form,
        'profile_form': profile_form,
        'is_own_profile': is_own_profile,
        'user_projects': user_projects,
    }
    return render(request, 'accounts/profile.html', context)
