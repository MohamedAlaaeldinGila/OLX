from django.urls import path
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import UserProfile
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import UserProfile


class UserSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    date_of_birth = forms.DateField(required=False)

    class Meta:
        model = UserProfile
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'address', 'date_of_birth', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        """user.phone = self.cleaned_data['phone']
        user.address = self.cleaned_data['address']
        user.date_of_birth = self.cleaned_data['date_of_birth']"""
        if commit:
            user.save()
        return user
    

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'autofocus': True,

        })
    )

    class Meta:
        model = UserProfile
        fields = ('username', 'password')

    def clean(self):
        email = self.cleaned_data.get('username')  
        password = self.cleaned_data.get('password')

        if email and password:
            # Find user by email
            try:
                user = UserProfile.objects.get(email=email)
                # Replace email with actual username for authentication
                self.cleaned_data['username'] = user.username
            except UserProfile.DoesNotExist:
                raise ValidationError("Invalid email or password.")
        
        return super().clean()