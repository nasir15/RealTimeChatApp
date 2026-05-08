from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.text import slugify

from .models import ChatGroup

User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if hasattr(user, 'user_type') and not user.user_type:
            user.user_type = 'RGU'
        if hasattr(user, 'role') and not user.role:
            user.role = 'UTL'
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput())


class ChatGroupForm(forms.ModelForm):
    class Meta:
        model = ChatGroup
        fields = ('name', 'description')

    def save(self, creator, commit=True):
        group = super().save(commit=False)
        if not group.slug:
            group.slug = slugify(group.name)
        if commit:
            group.save()
            group.members.add(creator)
        return group
