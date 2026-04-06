from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, Event, Club, Venue


# ─────────────────────────────────────────────
# AUTH FORMS
# ─────────────────────────────────────────────

class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password'}),
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
        label='Confirm Password'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'college']
        widgets = {
            'username':   forms.TextInput(attrs={'placeholder': 'Choose a username'}),
            'email':      forms.EmailInput(attrs={'placeholder': 'Your email address'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name':  forms.TextInput(attrs={'placeholder': 'Last name'}),
            'college':    forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['college'].empty_label = "— Select your college —"

    def clean(self):
        cleaned_data = super().clean()

        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        email = cleaned_data.get('email')
        college = cleaned_data.get('college')

        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")

        if not college:
            raise forms.ValidationError("Please select your college.")

        if email and college:
            if not email.endswith(college.email_domain):
                raise forms.ValidationError(
                    f"Use your college email (must end with {college.email_domain})"
                )

        return cleaned_data


# ✅ LOGIN FORM
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username'}),
        label='Username'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        label='Password'
    )


# ─────────────────────────────────────────────
# EVENT FORM (UPDATED 🔥)
# ─────────────────────────────────────────────

class EventForm(forms.ModelForm):

    class Meta:
        model  = Event
        fields = ['title', 'description', 'club', 'venue', 'date', 'start_time', 'end_time', 'poster']

        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Annual Tech Symposium 2025',
                'autocomplete': 'off',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'What is this event about?',
                'rows': 4,
            }),
            'club': forms.Select(),
            'venue': forms.Select(),

            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),

            'poster': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 🔥 CLUB LOGIC FIX
        if self.user:

            # ✅ CLUB ADMIN → only their club
            if self.user.is_club_admin:
                self.fields['club'].queryset = Club.objects.filter(
                    admin=self.user,
                    college=self.user.college,
                    status='approved'
                )
                self.fields['club'].required = True

            # ✅ COLLEGE ADMIN → NO club selection
            elif self.user.is_college_admin:
                self.fields['club'].required = False
                self.fields['club'].queryset = Club.objects.none()
                self.fields['club'].widget = forms.HiddenInput()

        self.fields['club'].empty_label = '— Select a club —'

        # 🔥 VENUE FILTER (same as before)
        if self.user:
            self.fields['venue'].queryset = Venue.objects.filter(
                college=self.user.college
            )

        self.fields['venue'].empty_label = '— Select venue —'

    def clean(self):
        cleaned = super().clean()

        start = cleaned.get('start_time')
        end   = cleaned.get('end_time')
        date  = cleaned.get('date')
        venue = cleaned.get('venue')

        # 🔥 TIME VALIDATION
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")

        # 🔥 CONFLICT CHECK
        if venue and date and start and end:
            conflict = Event.objects.filter(
                venue=venue,
                date=date,
                start_time__lt=end,
                end_time__gt=start
            ).exists()

            if conflict:
                raise forms.ValidationError(
                    "This venue is already booked for the selected time."
                )

        return cleaned