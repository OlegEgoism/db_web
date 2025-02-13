from django import forms
from django.db import connection

COLUMN_TYPES = [
    ('INTEGER', 'Integer'),
    ('TEXT', 'Text'),
    ('BOOLEAN', 'Boolean'),
    ('DATE', 'Date'),
    ('FLOAT', 'Float'),
]


class TableCreateForm(forms.Form):
    table_name = forms.CharField(label="Имя таблицы", max_length=50)

    # Динамически создаем 5 полей для столбцов
    column_1_name = forms.CharField(label="Имя столбца 1", required=False)
    column_1_type = forms.ChoiceField(choices=COLUMN_TYPES, required=False)

    column_2_name = forms.CharField(label="Имя столбца 2", required=False)
    column_2_type = forms.ChoiceField(choices=COLUMN_TYPES, required=False)

    column_3_name = forms.CharField(label="Имя столбца 3", required=False)
    column_3_type = forms.ChoiceField(choices=COLUMN_TYPES, required=False)

    column_4_name = forms.CharField(label="Имя столбца 4", required=False)
    column_4_type = forms.ChoiceField(choices=COLUMN_TYPES, required=False)

    column_5_name = forms.CharField(label="Имя столбца 5", required=False)
    column_5_type = forms.ChoiceField(choices=COLUMN_TYPES, required=False)


class UserCreateForm(forms.Form):
    username = forms.CharField(label="Имя пользователя", max_length=150)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)


class ChangePasswordForm(forms.Form):
    new_password = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)


# class AddUserToGroupForm(forms.Form):
#     username = forms.CharField(label="Имя пользователя", max_length=150)
#     groupname = forms.ChoiceField(label="Выберите группу")
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['groupname'].choices = self.get_groups()
#
#     @staticmethod
#     def get_groups():
#         """Получаем список групп PostgreSQL без системных ролей."""
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT rolname
#                 FROM pg_roles
#                 WHERE rolcanlogin = FALSE
#                 AND rolname NOT LIKE 'pg_%';
#             """)
#             groups = cursor.fetchall()
#         return [(group[0], group[0]) for group in groups]

from django import forms
from django.db import connection

class AddUserToGroupForm(forms.Form):
    username = forms.CharField(label="Имя пользователя", max_length=150, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    groups = forms.MultipleChoiceField(label="Выберите группы", widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['groups'].choices = self.get_groups()

    @staticmethod
    def get_groups():
        """Получаем список доступных групп PostgreSQL без системных."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT rolname 
                FROM pg_roles 
                WHERE rolcanlogin = FALSE AND rolname NOT LIKE 'pg_%';
            """)
            groups = cursor.fetchall()
        return [(group[0], group[0]) for group in groups]



class CreateGroupForm(forms.Form):
    groupname = forms.CharField(label="Название группы", max_length=150)
