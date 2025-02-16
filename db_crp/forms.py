from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class CustomUserRegistrationForm(UserCreationForm):
    """Регистрация пользователя"""
    phone_number = forms.CharField(max_length=15, required=True, help_text='Формат с кодом телефона')
    photo = forms.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone_number', 'photo', 'password1', 'password2')


class UserCreateForm(forms.Form):
    """Создать пользователя"""
    username = forms.CharField(label="Логин", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)


class ChangePasswordForm(forms.Form):
    """Смена пароля"""
    new_password = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)


class GroupEditForm(forms.Form):
    """Редактирование группы"""
    groupname = forms.CharField(label="Название", max_length=150)


class CreateGroupForm(forms.Form):
    """Создание группы"""
    groupname = forms.CharField(label="Название", max_length=150)
