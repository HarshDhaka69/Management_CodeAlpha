from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Row, Column
from .models import Project


class ProjectForm(forms.ModelForm):
    """Form for creating and editing projects."""

    class Meta:
        model = Project
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Website Redesign, Mobile App v2...',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Describe the project goals, scope, and team...',
                'rows': 4,
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('name'),
            Field('description'),
            Submit(
                'submit',
                'Save Project',
                css_class='btn btn-primary'
            ),
        )


class AddMemberForm(forms.Form):
    """Form to search and add a member to a project by username."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter username...',
            'class': 'form-control',
            'autocomplete': 'off',
        }),
        label='Add Member by Username'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('username'),
            Submit('submit', 'Add Member', css_class='btn btn-success'),
        )
