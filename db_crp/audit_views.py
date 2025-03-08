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
def user_register(user_name, email, phone_number):
    return f"Пользователь {user_name} зарегистрирован, почта {email}, телефон {phone_number}."


# ИНФОРМАЦИЯ ПОЛЗОВАТЕЛЯ
def user_data(user_name):
    return f"Автоматическое создание 'Дата создания' и 'Дата изменения' пользователя '{user_name}'."


def user_info_error(user_name):
    return f"Не удалось получить информацию о пользователе '{user_name}'."


# СОЗДАНИЕ ПОЬЗОВАТЕЛЯ
def create_user_messages_error(user_name):
    return f"Неудачная попытка создания пользователя '{user_name}', пользователь уже существует."


def create_user_messages_error_email(user_name, email):
    return f"Неудачная попытка привязки почты '{email}' к пользователю '{user_name}'. Почта уже используется."


def create_user_messages_success(user_name):
    return f"Пользователь '{user_name}' успешно создан."


def create_user_messages_email(user_name, email, can_create_db, is_superuser, inherit, create_role, login, replication, bypass_rls):
    return (f"Уведомление об успешном создании пользователя '{user_name}' в системе отправлено на почту '{email}'. "
            f"Права: Может создавать БД={can_create_db}. Суперпользователь={is_superuser}. Наследование={inherit}. "
            f"Создание роли={create_role}. Входа={login}. Репликация={replication}. Bypass RLS={bypass_rls}.")


# РЕДАКТИРОВАИЕ ПОЬЗОВАТЕЛЯ
def edit_user_messages_email_error(user_name, new_email):
    return f"Неудачная попытка изменить почту '{new_email}' у пользователя '{user_name}', почта уже используется."


def edit_user_messages_success(user_name, new_email):
    return f"Почта пользователя '{user_name}' изменена на '{new_email}'."


def edit_user_messages_email_success(user_name, email):
    return f"Уведомление об изменении учетной записи отправлено пользователю '{user_name}' на почту '{email}'."


def edit_user_messages_delete_group_success(user_name, group_name):
    return f"Пользователь '{user_name}' удален из группы '{group_name}'."


def edit_user_messages_delete_group_error(user_name, group_name):
    return f"Ошибка при удалении группы '{group_name}' пользователю '{user_name}'"


def edit_user_messages_add_group_success(user_name, group_name):
    return f"Пользователь '{user_name}' добавлен в группу '{group_name}'."


def edit_user_messages_add_group_error(user_name, group_name):
    return f"Ошибка при добавлении группы '{group_name}' пользователю '{user_name}'"


def edit_user_messages_role_permissions(user_name, role_permissions):
    return f"Изменение прав доступа пользователя '{user_name}'. Обновленные права: '{role_permissions}'."


# УДАЛЕНИЕ ПОЬЗОВАТЕЛЯ
def delete_user_messages_error(user_name):
    return f"Неудачная попытка при удалении пользователя '{user_name}' из базы данных, пользователь не может быть удален, так как существуют зависимые объекты в базе данных."


def delete_user_messages_success(user_name):
    return f"Пользователь '{user_name}' был удален из базы данных."


def delete_user_messages_email(user_name, user_email):
    return f"Уведомление об удалении пользователя '{user_name}' из базы данных отправлено на почту'{user_email}'."


# ---------------------------------------------------------------------------------------------------------------
# ИНФОРМАЦИЯ ГРУППЫ
def group_data(group_name):
    return f"Автоматическое создание 'Дата создания' и 'Дата изменения' группы '{group_name}'."


def user_groups_data_error(user_groups_data):
    return f"Ошибка подключения '{user_groups_data}'."


# УДАЛЕНИЕ ГРУППЫ
def delete_group_messages_success(group_name):
    return f"Группа '{group_name}' была удалена из базы данных."


def delete_group_messages_error(group_name):
    return f"Неудачная попытка при удалении группы '{group_name}' из базы данных, группа не может быть удален, так как существуют зависимые объекты в базе данных."


# СОЗДАНИЕ ГРУППЫ
def create_group_messages_error(group_name):  # +
    return f"Неудачная попытка создания группы '{group_name}', группа уже существует."


def create_group_messages_error_pg(group_name):  # +
    return f"Неудачная попытка создания группы '{group_name}', запрещенный префикс 'pg_'."


def create_group_messages_group_success(group_name):  # +
    return f"Группа '{group_name}' успешно создана."


def create_group_messages_error_info(group_name):  # +
    return f"Неудачная попытка создания группы '{group_name}'."


# РЕДАКТИРОВАИЕ ГРУППЫ
def edit_group_messages_error_pg(group_name, new_group_name):
    return f"Неудачная попытка переименовать группу с '{group_name}' в '{new_group_name}', запрещенный префикс 'pg_'."


def edit_group_messages_error_name(group_name, new_group_name):
    return f"Неудачная попытка переименовать группу с '{group_name}' в '{new_group_name}', группа уже существует."


def edit_group_messages_success_name(group_name, new_group_name):
    return f"Группа '{group_name}' успешно переименована в '{new_group_name}'."


def edit_group_messages_error(group_name):
    return f"Ошибка при редактировании группы '{group_name}'."


def edit_groups_privileges_tables_success(group_name):
    return f"Права успешно обновлены для группы '{group_name}'."


def edit_groups_privileges_tables_error(group_name):
    return f"Ошибка при выдаче прав для группы '{group_name}'."


def groups_tables_error(group_name, table):
    return f"Ошибка при загрузке таблиц '{table}' в группе '{group_name}'."


# ---------------------------------------------------------------------------------------------------------------
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
def connect_data_base_success(name_db, user_db, port_db, host_db):
    return f"Подключение к базе данных '{name_db}' успешно сохранено. Пользователь: '{user_db}'. Пароль: ****. Порт: '{port_db}'. Хост: '{host_db}'."


def delete_data_base_success(name_db, user_db, port_db, host_db):
    return f"Подключение к базе данных '{name_db}' успешно удалено. Пользователь: '{user_db}'. Пароль: ****. Порт: '{port_db}'. Хост: '{host_db}'."


def delete_data_base_error(name_db, user_db, port_db, host_db):
    return f"Ошибка при удалении подключения к базе данных '{name_db}'. Пользователь: '{user_db}'. Пароль: ****. Порт: '{port_db}'. Хост: '{host_db}'."


# ---------------------------------------------------------------------------------------------------------------
# АУДИТ
def logout_user_success(user_logout, user_requester):
    return f"Пользователь '{user_logout}' был деактивирован из системы пользователем '{user_requester}'."


def export_audit_log_success(user_requester):
    return f"Пользователь '{user_requester}' скачал файл 'Audit Log'."


# ---------------------------------------------------------------------------------------------------------------
# НАСТРОЙКИ
def project_settings_success(user_requester, pagination_size, send_email):
    return f"Настройки проекта успешно обновлены. Размер пагинации на странице '{pagination_size} записей. Отправка сообщений на почту '{send_email}'. "
# ---------------------------------------------------------------------------------------------------------------
