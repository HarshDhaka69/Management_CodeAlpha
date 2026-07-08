from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import Project, ProjectMember
from .forms import ProjectForm, AddMemberForm


@login_required
def project_list(request):
    """Show all projects the current user is a member of."""
    # Get projects where user is a member via ProjectMember
    memberships = ProjectMember.objects.filter(
        user=request.user
    ).select_related('project', 'project__owner').order_by('-project__created_at')

    projects = [m.project for m in memberships]

    context = {
        'projects': projects,
        'memberships': memberships,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_create(request):
    """Create a new project and auto-add creator as owner."""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()

            # Auto-add creator as owner in ProjectMember
            ProjectMember.objects.create(
                project=project,
                user=request.user,
                role='owner'
            )

            messages.success(request, f'Project "{project.name}" created successfully!')
            return redirect('projects:project_detail', pk=project.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {
        'form': form,
        'action': 'Create',
        'title': 'New Project'
    })


@login_required
def project_detail(request, pk):
    """Show project details + task board."""
    project = get_object_or_404(Project, pk=pk)

    # Security: only members can view the project
    if not project.is_member(request.user):
        messages.error(request, 'You do not have access to this project.')
        return redirect('projects:project_list')

    # Get tasks grouped by status
    from tasks.models import Task
    tasks_todo = project.tasks.filter(status='todo').select_related('assigned_to', 'created_by')
    tasks_inprogress = project.tasks.filter(status='inprogress').select_related('assigned_to', 'created_by')
    tasks_done = project.tasks.filter(status='done').select_related('assigned_to', 'created_by')

    members = ProjectMember.objects.filter(project=project).select_related('user', 'user__profile')
    user_membership = ProjectMember.objects.get(project=project, user=request.user)

    context = {
        'project': project,
        'tasks_todo': tasks_todo,
        'tasks_inprogress': tasks_inprogress,
        'tasks_done': tasks_done,
        'members': members,
        'user_membership': user_membership,
        'is_owner_or_admin': project.is_owner_or_admin(request.user),
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_edit(request, pk):
    """Edit project (owner/admin only)."""
    project = get_object_or_404(Project, pk=pk)

    if not project.is_owner_or_admin(request.user):
        messages.error(request, 'Only project owners and admins can edit this project.')
        return redirect('projects:project_detail', pk=pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated successfully!')
            return redirect('projects:project_detail', pk=pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/project_form.html', {
        'form': form,
        'project': project,
        'action': 'Edit',
        'title': f'Edit — {project.name}'
    })


@login_required
def project_delete(request, pk):
    """Delete project (owner only)."""
    project = get_object_or_404(Project, pk=pk)

    if project.owner != request.user:
        messages.error(request, 'Only the project owner can delete this project.')
        return redirect('projects:project_detail', pk=pk)

    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Project "{project_name}" deleted.')
        return redirect('projects:project_list')

    return render(request, 'projects/project_confirm_delete.html', {'project': project})


@login_required
def project_members(request, pk):
    """Manage project members (add/remove)."""
    project = get_object_or_404(Project, pk=pk)

    if not project.is_member(request.user):
        return redirect('projects:project_list')

    is_owner_or_admin = project.is_owner_or_admin(request.user)
    members = ProjectMember.objects.filter(project=project).select_related('user', 'user__profile')
    form = AddMemberForm()

    if request.method == 'POST' and is_owner_or_admin:
        form = AddMemberForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                new_user = User.objects.get(username=username)

                if ProjectMember.objects.filter(project=project, user=new_user).exists():
                    messages.warning(request, f'{username} is already a member of this project.')
                else:
                    ProjectMember.objects.create(project=project, user=new_user, role='member')
                    messages.success(request, f'{username} added to the project!')

            except User.DoesNotExist:
                messages.error(request, f'User "{username}" not found. Check the username and try again.')

        return redirect('projects:project_members', pk=pk)

    context = {
        'project': project,
        'members': members,
        'form': form,
        'is_owner_or_admin': is_owner_or_admin,
    }
    return render(request, 'projects/project_members.html', context)


@login_required
def remove_member(request, pk, user_id):
    """Remove a member from a project (owner/admin only, cannot remove owner)."""
    project = get_object_or_404(Project, pk=pk)

    if not project.is_owner_or_admin(request.user):
        messages.error(request, 'You do not have permission to remove members.')
        return redirect('projects:project_members', pk=pk)

    member_to_remove = get_object_or_404(User, pk=user_id)

    if member_to_remove == project.owner:
        messages.error(request, 'Cannot remove the project owner.')
        return redirect('projects:project_members', pk=pk)

    if request.method == 'POST':
        ProjectMember.objects.filter(project=project, user=member_to_remove).delete()
        messages.success(request, f'{member_to_remove.username} removed from the project.')

    return redirect('projects:project_members', pk=pk)
