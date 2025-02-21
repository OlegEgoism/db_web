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

    def clean_email(self):
        """Проверка уникальности email"""
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Почта уже используется другим пользователем!")
        return email


class UserCreateForm(forms.Form):
    """Форма для создания пользователя с уникальной почтой"""
    username = forms.CharField(label="Логин", max_length=150)
    email = forms.EmailField(label="Почта")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)


# class ChangePasswordForm(forms.Form):
#     """Смена пароля"""
#     new_password = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)

class UserEditForm(forms.Form):
    """Форма для редактирования пользователя"""
    email = forms.EmailField(label="Почта", required=False)
    new_password = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)
    can_create_db = forms.BooleanField(label="Может создавать БД", required=False)
    is_superuser = forms.BooleanField(label="Суперпользователь", required=False)



class GroupEditForm(forms.Form):
    """Редактирование группы"""
    groupname = forms.CharField(label="Название", max_length=150)


class CreateGroupForm(forms.Form):
    """Форма для создания группы с уникальным именем"""
    groupname = forms.CharField(label="Название", max_length=150)
