"""
Forms for authentication and user management
"""

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import UserProfile
# from .models import Booking, Room


class TULoginForm(forms.Form):
    """
    Form for TU REST API login
    Requirement: FR-AUTH-01
    """
    username = forms.CharField(
        label=_('ชื่อผู้ใช้งาน'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('ชื่อผู้ใช้งาน'),
            'autocomplete': 'username',
            'required': True
        })
    )
    password = forms.CharField(
        label=_('รหัสผ่าน'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('รหัสผ่าน'),
            'autocomplete': 'current-password',
            'required': True
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if not username or not password:
            raise forms.ValidationError(
                _('กรุณากรอกชื่อผู้ใช้งานและรหัสผ่าน')
            )
        
        return cleaned_data


class UserRoleAssignmentForm(forms.Form):
    """
    Form for Admin to assign user roles
    Requirement: FR-AUTH-05
    """
    ROLE_CHOICES = [
        ('lecturer', _('อาจารย์')),
        ('admin', _('เจ้าหน้าที่')),
    ]

    role = forms.ChoiceField(
        label=_('บทบาท'),
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop('user_profile', None)
        super().__init__(*args, **kwargs)

    def save(self):
        if self.user_profile:
            self.user_profile.role = self.cleaned_data['role']
            self.user_profile.save()
            return self.user_profile
        return None


