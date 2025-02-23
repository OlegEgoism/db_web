from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import connection

from .models import CustomUser, UserLog


class CustomUserRegistrationForm(UserCreationForm):
    """Регистрация администратора"""
    phone_number = forms.CharField(max_length=15, required=True, help_text='Формат с кодом телефона')
    photo = forms.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone_number', 'photo', 'password1', 'password2')

    def clean_email(self):
        """Проверка уникальности email"""
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Почта уже используется другим администратором.")
        return email


class UserCreateForm(forms.Form):
    """Создания пользователя"""
    username = forms.CharField(label="Логин", max_length=150)
    email = forms.EmailField(label="Почта")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    can_create_db = forms.BooleanField(label="Может создавать БД", required=False)
    is_superuser = forms.BooleanField(label="Суперпользователь", required=False)
    inherit = forms.BooleanField(label="Наследование", required=False)
    create_role = forms.BooleanField(label="Право создания роли", required=False)
    login = forms.BooleanField(label="Право входа", required=False, initial=True)
    replication = forms.BooleanField(label="Право репликации", required=False)
    bypass_rls = forms.BooleanField(label="Bypass RLS", required=False)



class UserEditForm(forms.Form):
    """Редактирование пользователя"""
    email = forms.EmailField(label="Почта", required=False)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput, required=False)
    can_create_db = forms.BooleanField(label="Может создавать БД", required=False)
    is_superuser = forms.BooleanField(label="Суперпользователь", required=False)
    inherit = forms.BooleanField(label="Наследование", required=False)
    create_role = forms.BooleanField(label="Право создания роли", required=False)
    login = forms.BooleanField(label="Право входа", required=False)
    replication = forms.BooleanField(label="Право репликации", required=False)
    bypass_rls = forms.BooleanField(label="Bypass RLS", required=False)


class GroupEditForm(forms.Form):
    """Редактирование группы"""
    groupname = forms.CharField(label="Название", max_length=150)


class CreateGroupForm(forms.Form):
    """Создание группы"""
    groupname = forms.CharField(label="Название", max_length=150)





PRIVILEGES_CHOICES = [
    ('SELECT', 'Чтение (SELECT)'),
    ('INSERT', 'Вставка (INSERT)'),
    ('UPDATE', 'Обновление (UPDATE)'),
    ('DELETE', 'Удаление (DELETE)'),
    ('TRUNCATE', 'Очистка (TRUNCATE)'),
    ('REFERENCES', 'Ссылки (REFERENCES)'),
    ('TRIGGER', 'Триггер (TRIGGER)'),
]

def get_roles_from_db():
    """Получить список ролей из базы данных PostgreSQL"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT rolname 
            FROM pg_roles 
            WHERE rolcanlogin = FALSE AND rolname NOT LIKE 'pg_%';
        """)
        roles = cursor.fetchall()
    return [(role[0], role[0]) for role in roles]  # Преобразуем кортежи в формат для формы

def get_tables_from_db():
    """Получить список таблиц из базы данных PostgreSQL"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_schema || '.' || table_name AS full_table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name;
        """)
        tables = cursor.fetchall()
    return [(table[0], table[0]) for table in tables]




PRIVILEGES_CHOICES = [
    ('SELECT', 'Чтение (SELECT)'),
    ('INSERT', 'Вставка (INSERT)'),
    ('UPDATE', 'Обновление (UPDATE)'),
    ('DELETE', 'Удаление (DELETE)'),
]

class GrantPrivilegesForm(forms.Form):
    # role_name = forms.CharField(label='Имя роли')
    # table_name = forms.CharField(label='Имя таблицы')
    # privileges = forms.MultipleChoiceField(
    #     choices=PRIVILEGES_CHOICES,
    #     widget=forms.CheckboxSelectMultiple,
    #     label='Привилегии'
    # )

#
#
# class GrantPrivilegesForm(forms.Form):
    role_name = forms.ChoiceField(
        label='Имя роли',
        choices=[],  # Заполним в конструкторе
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    table_name = forms.ChoiceField(
        label='Имя таблицы',
        choices=[],  # Заполним в конструкторе
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    privileges = forms.MultipleChoiceField(
        choices=PRIVILEGES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='Привилегии'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role_name'].choices = get_roles_from_db()
        self.fields['table_name'].choices = get_tables_from_db()
