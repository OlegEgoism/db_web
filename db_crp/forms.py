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


from django import forms
from .models import UserLog

class UserCreateForm(forms.Form):
    """Форма для создания пользователя с уникальной почтой"""
    username = forms.CharField(label="Логин", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)

    def clean_email(self):
        """Проверяем, что email уникален"""
        email = self.cleaned_data.get('email')
        if email and UserLog.objects.filter(email=email).exists():
            raise forms.ValidationError("❌ Ошибка: Этот email уже используется другим пользователем!")
        return email



class ChangePasswordForm(forms.Form):
    """Смена пароля"""
    new_password = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)


class GroupEditForm(forms.Form):
    """Редактирование группы"""
    groupname = forms.CharField(label="Название", max_length=150)


from .models import GroupLog
from django.db import connection

class CreateGroupForm(forms.Form):
    """Форма для создания группы с уникальным именем"""
    groupname = forms.CharField(label="Название", max_length=150)

    # def clean_groupname(self):
    #     """Проверяем, что группа с таким именем еще не существует"""
    #     groupname = self.cleaned_data['groupname']
    #
    #     # Проверяем в PostgreSQL
    #     with connection.cursor() as cursor:
    #         cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [groupname])
    #         if cursor.fetchone():
    #             raise forms.ValidationError(f"❌ Ошибка: Группа '{groupname}' уже существует!")
    #
    #     # Проверяем в логах (если логов нет, можно убрать)
    #     if GroupLog.objects.filter(groupname=groupname).exists():
    #         raise forms.ValidationError(f"❌ Ошибка: Группа '{groupname}' уже зарегистрирована в системе!")
    #
    #     return groupname
