"""
Forms for authentication and user management
"""

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import UserProfile
from .models import Booking, Room


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


class BookingForm(forms.ModelForm):
    DAYS_CHOICES = [
        ("0", "วันจันทร์"),
        ("1", "วันอังคาร"),
        ("2", "วันพุธ"),
        ("3", "วันพฤหัสบดี"),
        ("4", "วันศุกร์"),
        ("5", "วันเสาร์"),
        ("6", "วันอาทิตย์"),
    ]

    selected_days = forms.MultipleChoiceField(
        choices=DAYS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label=_("วันในสัปดาห์ที่ต้องการใช้งาน"),
    )

    class Meta:
        model = Booking
        fields = [
            "room",
            "purpose_type",
            "subject_code",
            "subject_name",
            "curriculum",
            "topic",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
        ]
        widgets = {
            "room": forms.Select(attrs={"class": "form-control", "required": True}),
            "purpose_type": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "subject_code": forms.TextInput(attrs={"class": "form-control"}),
            "subject_name": forms.TextInput(attrs={"class": "form-control"}),
            "curriculum": forms.Select(attrs={"class": "form-control"}),
            "topic": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "required": True}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "required": True}
            ),
            "start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time", "required": True}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time", "required": True}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        purpose_type = cleaned_data.get("purpose_type")

        if purpose_type == "class":
            if not cleaned_data.get("subject_code") or not cleaned_data.get(
                "subject_name"
            ):
                raise forms.ValidationError("กรุณาระบุรหัสวิชาและชื่อวิชา สำหรับการสอน")
        elif purpose_type == "training":
            if not cleaned_data.get("topic"):
                raise forms.ValidationError("กรุณาระบุชื่อเรื่อง สำหรับการจัดอบรม/จัดติว")

        return cleaned_data
