from django.utils.timezone import now
from db_crp.models import Audit


def create_audit_log(user_requester, action_type, entity_type, entity_name, details):
    """Функция для создания записи аудита"""
    Audit.objects.create(
        username=user_requester,
        action_type=action_type,
        entity_type=entity_type,
        entity_name=entity_name,
        timestamp=now(),
        details=details
    )


# РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ
def user_register(username, email, phone_number):
    return f"Пользователь {username} зарегистрирован, почта {email}, телефон {phone_number}."


# ИНФОРМАЦИЯ ПОЛЗОВАТЕЛЯ
def user_data(username):
    return f"Автоматическое создание 'Дата создания' и 'Дата изменения' пользователя '{username}'."


def user_info_error(username):
    return f"Не удалось получить информацию о пользователе '{username}'."


# СОЗДАНИЕ ПОЬЗОВАТЕЛЯ
def create_user_messages_error(username):
    return f"Неудачная попытка создания пользователя '{username}', пользователь уже существует."


def create_user_messages_error_email(username, email):
    return f"Неудачная попытка привязки почты '{email}' к пользователю '{username}'. Почта уже используется."


def create_user_messages_success(username):
    return f"Пользователь '{username}' успешно создан."


def create_user_messages_email(username, email, can_create_db, is_superuser, inherit, create_role, login, replication, bypass_rls):
    return (f"Уведомление об успешном создании пользователя '{username}' в системе отправлено на почту '{email}'. "
            f"Права: Может создавать БД={can_create_db}. Суперпользователь={is_superuser}. Наследование={inherit}. "
            f"Создание роли={create_role}. Входа={login}. Репликация={replication}. Bypass RLS={bypass_rls}.")


# РЕДАКТИРОВАИЕ ПОЬЗОВАТЕЛЯ
def edit_user_messages_email_error(username, new_email):
    return f"Неудачная попытка изменить почту '{new_email}' у пользователя '{username}', почта уже используется."


def edit_user_messages_success(username, new_email):
    return f"Почта пользователя '{username}' изменена на '{new_email}'."


def edit_user_messages_email_success(username, email):
    return f"Уведомление об изменении учетной записи отправлено пользователю '{username}' на почту '{email}'."


def edit_user_messages_delete_group_success(username, groupname):
    return f"Пользователь '{username}' удален из группы '{groupname}'."


def edit_user_messages_delete_group_error(username, groupname):
    return f"Ошибка при удалении группы '{groupname}' пользователю '{username}'"


def edit_user_messages_add_group_success(username, groupname):
    return f"Пользователь '{username}' добавлен из группы '{groupname}'."


def edit_user_messages_add_group_error(username, groupname):
    return f"Ошибка при добавлении группы '{groupname}' пользователю '{username}'"


def edit_user_messages_role_permissions(username, role_permissions):
    return f"Изменение прав доступа пользователя '{username}'. Обновленные права: '{role_permissions}'."


# УДАЛЕНИЕ ПОЬЗОВАТЕЛЯ
def delete_user_messages_error(username):
    return f"Неудачная попытка при удалении пользователя '{username}' из базы данных, пользователь не может быть удален, так как существуют зависимые объекты в базе данных."


def delete_user_messages_success(username):
    return f"Пользователь '{username}' был удален из базы данных."


def delete_user_messages_email(username, user_email):
    return f"Уведомление об удалении пользователя '{username}' из базы данных отправлено на почту'{user_email}'."


# ---------------------------------------------------------------------------------------------------------------
# ИНФОРМАЦИЯ ГРУППЫ
def group_data(groupname):
    return f"Автоматическое создание 'Дата создания' и 'Дата изменения' группы '{groupname}'."


# УДАЛЕНИЕ ГРУППЫ
def delete_group_messages_success(groupname):
    return f"Группа '{groupname}' была удалена из базы данных."


def delete_group_messages_error(groupname):
    return f"Неудачная попытка при удалении группы '{groupname}' из базы данных, группа не может быть удален, так как существуют зависимые объекты в базе данных."


# СОЗДАНИЕ ГРУППЫ
def create_group_messages_error(groupname):
    return f"Неудачная попытка создания группы '{groupname}', группа уже существует."


def create_group_messages_error_pg(groupname):
    return f"Неудачная попытка создания группы '{groupname}', запрещенный префикс 'pg_'."


def edit_group_messages_group_success(groupname):
    return f"Группа '{groupname}' успешно создана."


def create_group_messages_error_info(groupname):
    return f"Неудачная попытка создания группы '{groupname}'."
