from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Row, Column, Submit
from .models import Task, Comment


class TaskForm(forms.ModelForm):
    """Form for creating and editing tasks within a project."""

    class Meta:
        model = Task
        fields = ('title', 'description', 'assigned_to', 'status', 'priority', 'due_date')
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'What needs to be done?',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Add more details about this task...',
                'rows': 4,
                'class': 'form-control'
            }),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

    def __init__(self, project, *args, is_owner_or_admin=True, **kwargs):
        super().__init__(*args, **kwargs)
        from projects.models import ProjectMember

        # Limit assigned_to choices to project members only
        member_ids = ProjectMember.objects.filter(
            project=project
        ).values_list('user_id', flat=True)

        from django.contrib.auth.models import User
        self.fields['assigned_to'].queryset = User.objects.filter(id__in=member_ids)
        self.fields['assigned_to'].empty_label = '— Unassigned —'
        self.fields['assigned_to'].required = False

        if is_owner_or_admin:
            top_row = Row(
                Column('assigned_to', css_class='col-md-6'),
                Column('status', css_class='col-md-6'),
            )
        else:
            # Regular members can't set status directly here — new tasks
            # always start as To Do, and existing tasks only move through
            # the Accept / Submit / Approve / Reject workflow.
            del self.fields['status']
            top_row = Field('assigned_to')

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('title'),
            Field('description'),
            top_row,
            Row(
                Column('priority', css_class='col-md-6'),
                Column('due_date', css_class='col-md-6'),
            ),
        )


class CommentForm(forms.ModelForm):
    """Form to post a comment on a task."""

    class Meta:
        model = Comment
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'placeholder': 'Write a comment...',
                'rows': 3,
                'class': 'form-control',
            }),
        }
        labels = {
            'content': '',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('content'),
            Submit('submit', 'Post Comment', css_class='btn btn-primary'),
        )
