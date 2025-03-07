from datetime import datetime

import psycopg2
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.http import HttpResponseNotFound
from django.template.loader import render_to_string
from django.utils import timezone
from .forms import UserCreateForm
from django.shortcuts import render, redirect, get_object_or_404
from .models import UserLog, SettingsProject, ConnectingDB
from django.contrib import messages
from .audit_views import delete_user_messages_email, delete_user_messages_success, delete_user_messages_error, create_audit_log, create_user_messages_error, create_user_messages_error_email, create_user_messages_success, create_user_messages_email, \
    user_info_error, user_data, edit_user_messages_email_error, edit_user_messages_success, edit_user_messages_email_success, edit_user_messages_add_group_error, edit_user_messages_delete_group_success, edit_user_messages_delete_group_error, \
    edit_user_messages_add_group_success, edit_user_messages_role_permissions

created_at = datetime(2000, 1, 1, 0, 0)
updated_at = timezone.now()


@login_required
def user_list(request, db_id):
    """Список пользователей из подключенной базы данных"""
    connection_info = get_object_or_404(ConnectingDB, id=db_id)

    temp_db_settings = {
        'dbname': connection_info.name_db,
        'user': connection_info.user_db,
        'password': connection_info.get_decrypted_password(),
        'host': connection_info.host_db,
        'port': connection_info.port_db,
    }

    users_data = []
    try:
        conn = psycopg2.connect(**temp_db_settings)
        cursor = conn.cursor()

        # Получение списка пользователей
        cursor.execute("SELECT usename FROM pg_catalog.pg_user;")
        users = sorted([user[0] for user in cursor.fetchall()])

        # Получаем лог пользователей из Django
        user_logs = {log.username: log for log in UserLog.objects.filter(username__in=users)}

        # Получение количества групп для каждого пользователя
        for user in users:
            cursor.execute("""
                SELECT COUNT(*)
                FROM pg_user u
                JOIN pg_auth_members m ON u.usesysid = m.member
                JOIN pg_roles r ON m.roleid = r.oid
                WHERE u.usename = %s;
            """, [user])
            group_count = cursor.fetchone()[0]

            users_data.append({
                "username": user,
                "created_at": user_logs[user].created_at if user in user_logs else None,
                "updated_at": user_logs[user].updated_at if user in user_logs else None,
                "group_count": group_count
            })

        cursor.close()
        conn.close()
    except Exception as e:
        users_data = [{"username": f"Ошибка подключения: {str(e)}", "group_count": "-"}]

    return render(request, 'users/user_list.html', {'users_data': users_data, 'db_id': db_id})


@login_required
def user_create(request, db_id):
    """Создание пользователя в конкретной подключенной базе данных"""
    connection_info = get_object_or_404(ConnectingDB, id=db_id)

    # Подключение к БД
    temp_db_settings = {
        'dbname': connection_info.name_db,
        'user': connection_info.user_db,
        'password': connection_info.get_decrypted_password(),
        'host': connection_info.host_db,
        'port': connection_info.port_db,
    }

    send_email = SettingsProject.objects.first().send_email if SettingsProject.objects.exists() else False
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"

    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data.get('email', None)
            password = form.cleaned_data['password']
            can_create_db = form.cleaned_data['can_create_db']
            is_superuser = form.cleaned_data['is_superuser']
            inherit = form.cleaned_data['inherit']
            create_role = form.cleaned_data['create_role']
            login = form.cleaned_data.get('login', True)
            replication = form.cleaned_data['replication']
            bypass_rls = form.cleaned_data['bypass_rls']

            try:
                # Подключение к нужной базе данных
                conn = psycopg2.connect(**temp_db_settings)
                cursor = conn.cursor()

                # Проверка, существует ли пользователь в PostgreSQL
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [username])
                user_exists_in_pg = cursor.fetchone()
                if user_exists_in_pg:
                    message = create_user_messages_error(username)
                    messages.error(request, message)
                    create_audit_log(user_requester, 'create', 'user', username, message)
                    return render(request, 'users/user_create.html', {'form': form})

                # Проверка наличия email в UserLog
                email_exists = UserLog.objects.filter(email=email).exists() if email else False
                if email_exists:
                    messages.error(request, f"Пользователь с почтой {email} уже существует.")
                    return render(request, 'users/user_create.html', {'form': form})

                # Формируем строку привилегий
                privileges = ' '.join([
                    'CREATEDB' if can_create_db else 'NOCREATEDB',
                    'SUPERUSER' if is_superuser else 'NOSUPERUSER',
                    'INHERIT' if inherit else 'NOINHERIT',
                    'CREATEROLE' if create_role else 'NOCREATEROLE',
                    'LOGIN' if login else 'NOLOGIN',
                    'REPLICATION' if replication else 'NOREPLICATION',
                    'BYPASSRLS' if bypass_rls else 'NOBYPASSRLS'
                ])

                # Создаем пользователя в подключенной базе
                cursor.execute(f"CREATE USER {username} WITH PASSWORD %s {privileges};", [password])
                conn.commit()

                # Записываем в лог Django
                UserLog.objects.create(
                    username=username,
                    email=email,
                    can_create_db=can_create_db,
                    is_superuser=is_superuser,
                    inherit=inherit,
                    create_role=create_role,
                    login=login,
                    replication=replication,
                    bypass_rls=bypass_rls
                )

                # Аудит
                message = create_user_messages_success(username)
                messages.success(request, message)
                create_audit_log(user_requester, 'create', 'user', username, message)

                # Отправка уведомления на email
                if email and send_email:
                    subject = "Ваш аккаунт создан"
                    html_message = render_to_string('send_email/send_user_create.html', {
                        'username': username,
                        'password': password,
                        'can_create_db': can_create_db,
                        'is_superuser': is_superuser,
                        'inherit': inherit,
                        'create_role': create_role,
                        'login': login,
                        'replication': replication,
                        'bypass_rls': bypass_rls
                    })
                    email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [email])
                    email_message.attach_alternative(html_message, "text/html")
                    email_message.send()
                cursor.close()
                conn.close()
                return redirect('user_list', db_id=db_id)
            except Exception as e:
                messages.error(request, f"Ошибка при создании пользователя '{username}': {str(e)}.")
                return render(request, 'users/user_create.html', {'form': form})
    else:
        form = UserCreateForm()
    return render(request, 'users/user_create.html', {'form': form, 'db_id': db_id})


@login_required
def user_info(request, db_id, username):
    """Информация о пользователе из подключенной базы данных"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"

    # Получаем информацию о подключенной базе
    connection_info = get_object_or_404(ConnectingDB, id=db_id)

    temp_db_settings = {
        'dbname': connection_info.name_db,
        'user': connection_info.user_db,
        'password': connection_info.get_decrypted_password(),
        'host': connection_info.host_db,
        'port': connection_info.port_db,
    }

    try:
        conn = psycopg2.connect(**temp_db_settings)
        cursor = conn.cursor()
    except Exception as e:
        messages.error(request, f"Ошибка подключения к базе данных: {str(e)}")
        return redirect('user_list', db_id=db_id)

    # Проверяем, существует ли пользователь
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [username])
    user_exists = cursor.fetchone()

    if not user_exists:
        cursor.close()
        conn.close()
        messages.error(request, f"Пользователь '{username}' не найден в базе {connection_info.name_db}.")
        return redirect('user_list', db_id=db_id)

    # Получение информации о пользователе
    cursor.execute("""
        SELECT 
            r.rolname,         -- Имя роли
            r.oid,             -- ID пользователя
            r.rolcreatedb,     -- Может ли создавать БД
            r.rolsuper,        -- Суперпользователь
            r.rolinherit,      -- Наследование
            r.rolcreaterole,   -- Может создавать роли
            r.rolcanlogin,     -- Может входить в систему
            r.rolreplication,  -- Право репликации
            r.rolbypassrls,    -- Игнорирует RLS
            r.rolpassword      -- Хеш пароля (если установлен)
        FROM pg_roles r
        WHERE r.rolname = %s;
    """, [username])
    user_info = cursor.fetchone()

    # Получение групп пользователя
    cursor.execute("""
        SELECT r.rolname 
        FROM pg_roles r
        JOIN pg_auth_members m ON r.oid = m.roleid
        JOIN pg_roles u ON u.oid = m.member
        WHERE u.rolname = %s;
    """, [username])
    groups = cursor.fetchall()

    user_log = UserLog.objects.filter(username=username).first()

    if user_info:
        group_list = [group[0] for group in groups]
        user_data = {
            'username': user_info[0],
            'user_id': user_info[1],
            'can_create_db': user_info[2],
            'is_superuser': user_info[3],
            'inherit': user_info[4],
            'create_role': user_info[5],
            'login': user_info[6],
            'replication': user_info[7],
            'bypass_rls': user_info[8],
            'password_hash': user_info[9],
            'groups': group_list,
            'group_count': len(group_list),
            'email': user_log.email if user_log else None,
            'created_at': user_log.created_at if user_log else None,
            'updated_at': user_log.updated_at if user_log else None,
        }
    else:
        user_data = None
        messages.error(request, f"Не удалось получить информацию о пользователе '{username}'.")

    cursor.close()
    conn.close()

    return render(request, 'users/user_info.html', {'user_data': user_data, 'db_id': db_id})


@login_required
def user_edit(request, db_id, username):
    """Редактирование пользователя в подключенной базе данных"""
    connection_info = get_object_or_404(ConnectingDB, id=db_id)

    temp_db_settings = {
        'dbname': connection_info.name_db,
        'user': connection_info.user_db,
        'password': connection_info.get_decrypted_password(),
        'host': connection_info.host_db,
        'port': connection_info.port_db,
    }

    try:
        conn = psycopg2.connect(**temp_db_settings)
        cursor = conn.cursor()
    except Exception as e:
        return HttpResponseNotFound(f"Ошибка подключения к базе данных: {str(e)}")

    # Проверяем, существует ли пользователь в PostgreSQL
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [username])
    user_exists = cursor.fetchone()
    if not user_exists:
        return HttpResponseNotFound(f"Пользователь '{username}' не найден в базе данных {connection_info.name_db}.")

    # Получаем email из модели UserLog
    user_log = UserLog.objects.filter(username=username).first()
    user_email = user_log.email if user_log else ""

    # Получение прав доступа пользователя
    cursor.execute("""
        SELECT rolcreatedb, rolsuper, rolinherit, rolcreaterole, 
               rolcanlogin, rolreplication, rolbypassrls
        FROM pg_roles 
        WHERE rolname = %s;
    """, [username])
    result = cursor.fetchone()

    role_permissions = {
        'can_create_db': result[0],
        'is_superuser': result[1],
        'inherit': result[2],
        'create_role': result[3],
        'login': result[4],
        'replication': result[5],
        'bypass_rls': result[6]
    } if result else {key: False for key in [
        'can_create_db', 'is_superuser', 'inherit',
        'create_role', 'login', 'replication', 'bypass_rls'
    ]}

    # Получение списка групп
    cursor.execute("""
        SELECT r.rolname
        FROM pg_user u
        JOIN pg_auth_members m ON u.usesysid = m.member
        JOIN pg_roles r ON m.roleid = r.oid
        WHERE u.usename = %s;
    """, [username])
    current_groups = {group[0] for group in cursor.fetchall()}

    cursor.execute("""
        SELECT rolname
        FROM pg_roles
        WHERE rolcanlogin = FALSE AND rolname NOT LIKE 'pg_%';
    """)
    all_groups = {group[0] for group in cursor.fetchall()}
    available_groups = all_groups - current_groups

    if request.method == "POST":
        # Получаем обновленный email из формы
        new_email = request.POST.get('email', '')

        # Обновляем email в UserLog
        if user_log:
            user_log.email = new_email
            user_log.save()

        # Обновляем права в PostgreSQL
        role_permissions = {
            'can_create_db': 'can_create_db' in request.POST,
            'is_superuser': 'is_superuser' in request.POST,
            'inherit': 'inherit' in request.POST,
            'create_role': 'create_role' in request.POST,
            'login': 'login' in request.POST,
            'replication': 'replication' in request.POST,
            'bypass_rls': 'bypass_rls' in request.POST
        }

        cursor.execute(f"""
            ALTER ROLE {username}
            {'CREATEDB' if role_permissions['can_create_db'] else 'NOCREATEDB'}
            {'SUPERUSER' if role_permissions['is_superuser'] else 'NOSUPERUSER'}
            {'INHERIT' if role_permissions['inherit'] else 'NOINHERIT'}
            {'CREATEROLE' if role_permissions['create_role'] else 'NOCREATEROLE'}
            {'LOGIN' if role_permissions['login'] else 'NOLOGIN'}
            {'REPLICATION' if role_permissions['replication'] else 'NOREPLICATION'}
            {'BYPASSRLS' if role_permissions['bypass_rls'] else 'NOBYPASSRLS'};
        """)
        conn.commit()

        # Обновление групп пользователя
        selected_groups = set(request.POST.getlist('selected_groups'))
        deleted_groups = current_groups - selected_groups
        new_groups = selected_groups - current_groups

        for groupname in deleted_groups:
            cursor.execute(f"REVOKE {groupname} FROM {username};")

        for groupname in new_groups:
            cursor.execute(f"GRANT {groupname} TO {username};")

        conn.commit()
        cursor.close()
        conn.close()

        messages.success(request, f"Пользователь {username} обновлен в базе {connection_info.name_db}.")
        return redirect('user_list', db_id=db_id)

    cursor.close()
    conn.close()

    return render(request, 'users/user_edit.html', {
        'db_id': db_id,
        'username': username,
        'role_permissions': role_permissions,
        'user_groups': sorted(current_groups),
        'available_groups': sorted(available_groups),
        'user_email': user_email  # ✅ Передаём email в шаблон
    })


@login_required
def user_delete(request, db_id, username):
    """Удаление пользователя из подключенной базы данных"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    connection_info = get_object_or_404(ConnectingDB, id=db_id)

    temp_db_settings = {
        'dbname': connection_info.name_db,
        'user': connection_info.user_db,
        'password': connection_info.get_decrypted_password(),
        'host': connection_info.host_db,
        'port': connection_info.port_db,
    }

    try:
        conn = psycopg2.connect(**temp_db_settings)
        cursor = conn.cursor()
    except Exception as e:
        messages.error(request, f"Ошибка подключения к базе данных: {str(e)}")
        return redirect('user_list', db_id=db_id)

    # Проверяем, существует ли пользователь в базе
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [username])
    user_exists = cursor.fetchone()

    if not user_exists:
        messages.error(request, f"Пользователь '{username}' не найден в базе {connection_info.name_db}.")
        cursor.close()
        conn.close()
        return redirect('user_list', db_id=db_id)

    user_log = UserLog.objects.filter(username=username).first()
    user_email = user_log.email if user_log else None

    try:
        # Перед удалением передаем права и удаляем объекты пользователя
        cursor.execute(f"REASSIGN OWNED BY {username} TO {connection_info.user_db};")
        cursor.execute(f"DROP OWNED BY {username};")
        cursor.execute(f"DROP USER IF EXISTS {username};")
        conn.commit()

        # Удаляем пользователя из логов, если он есть
        if user_log:
            user_log.delete()

        message = f"Пользователь {username} удален из базы {connection_info.name_db}."
        messages.success(request, message)
        create_audit_log(user_requester, 'delete', 'user', username, message)

        # Отправка уведомления на почту
        send_email = SettingsProject.objects.first().send_email if SettingsProject.objects.exists() else False
        if user_email and send_email:
            subject = "Ваш аккаунт был удален"
            html_message = render_to_string('send_email/send_user_delete.html', {'username': username})
            email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [user_email])
            email_message.attach_alternative(html_message, "text/html")
            email_message.send()
            messages.success(request, f"Пользователю {username} отправлено уведомление о удалении.")

    except Exception as e:
        conn.rollback()
        messages.error(request, f"Ошибка при удалении пользователя '{username}': {str(e)}.")
        create_audit_log(user_requester, 'delete', 'user', username, f"Ошибка удаления: {str(e)}")

    finally:
        cursor.close()
        conn.close()

    return redirect('user_list', db_id=db_id)
