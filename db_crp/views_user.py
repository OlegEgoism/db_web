from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.http import HttpResponseNotFound
from django.template.loader import render_to_string
from django.utils import timezone
from .forms import UserCreateForm
from django.shortcuts import render, redirect
from .models import UserLog, SettingsProject
from django.contrib import messages
from .audit_views import delete_user_messages_email, delete_user_messages_success, delete_user_messages_error, create_audit_log, create_user_messages_error, create_user_messages_error_email, create_user_messages_success, create_user_messages_email, \
    user_info_error, user_data, edit_user_messages_email_error, edit_user_messages_success, edit_user_messages_email_success, edit_user_messages_add_group_error, edit_user_messages_delete_group_success, edit_user_messages_delete_group_error, \
    edit_user_messages_add_group_success, edit_user_messages_role_permissions

created_at = datetime(2000, 1, 1, 0, 0)
updated_at = timezone.now()


@login_required
def user_list(request):
    """Список пользователей"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT usename FROM pg_user;")
        users = [user[0] for user in cursor.fetchall()]
    user_logs = {log.username: log for log in UserLog.objects.filter(username__in=users)}
    users_data = []
    for user in users:
        with connection.cursor() as cursor:
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
    return render(request, 'users/user_list.html', {'users_data': users_data})


@login_required
def user_create(request):
    """Создание пользователя"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    send_email = SettingsProject.objects.first().send_email if SettingsProject.objects.exists() else False
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

            # Проверка наличия пользователя в PostgreSQL
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [username])
                user_exists_in_pg = cursor.fetchone()
            if user_exists_in_pg:
                message = create_user_messages_error(username)
                messages.error(request, message)
                create_audit_log(user_requester, 'create', 'user', username, message)
                return render(request, 'users/user_create.html', {'form': form})

            # Проверка почты
            email_exists = UserLog.objects.filter(email=email).exists() if email else False
            if email_exists:
                message = create_user_messages_error_email(username, email)
                messages.error(request, message)
                create_audit_log(user_requester, 'create', 'user', username, message)
                return render(request, 'users/user_create.html', {'form': form})

            try:
                # Создание пользователя в PostgreSQL
                with connection.cursor() as cursor:
                    privileges = ' '.join([
                        'CREATEDB' if can_create_db else 'NOCREATEDB',
                        'SUPERUSER' if is_superuser else 'NOSUPERUSER',
                        'INHERIT' if inherit else 'NOINHERIT',
                        'CREATEROLE' if create_role else 'NOCREATEROLE',
                        'LOGIN' if login else 'NOLOGIN',
                        'REPLICATION' if replication else 'NOREPLICATION',
                        'BYPASSRLS' if bypass_rls else 'NOBYPASSRLS'
                    ])
                    cursor.execute(f"CREATE USER {username} WITH PASSWORD %s {privileges};", [password])
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
                message = create_user_messages_success(username)
                messages.success(request, message)
                create_audit_log(user_requester, 'create', 'user', username, message)
                # Отправка уведомления на почту
                if email and send_email == True:
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
                    message = create_user_messages_email(username, email, can_create_db, is_superuser, inherit, create_role, login, replication, bypass_rls)
                    messages.success(request, message)
                    create_audit_log(user_requester, 'create', 'user', username, message)
                return redirect('user_list')
            except Exception as e:
                messages.error(request, f"Ошибка при создании пользователя '{username}: {str(e)}.")
                return render(request, 'users/user_create.html', {'form': form})
    else:
        form = UserCreateForm()
    return render(request, 'users/user_create.html', {'form': form})


@login_required
def user_info(request, username):
    """Информация пользователя"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_user WHERE usename = %s;", [username])
    user_log, created = UserLog.objects.get_or_create(
        username=username,
        defaults={
            'email': None,
            'created_at': created_at,
            'updated_at': updated_at
        }
    )
    if created:
        message = user_data(username)
        messages.success(request, message)
        create_audit_log(user_requester, 'create', 'user', username, message)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                r.rolname,         -- Имя роли (логин пользователя или имя группы)
                r.oid,             -- Уникальный идентификатор роли в системе (Object ID)
                r.rolcreatedb,     -- Может ли роль создавать базы данных (True/False)
                r.rolsuper,        -- Является ли роль суперпользователем (True/False)
                r.rolinherit,      -- Наследует ли роль права групп, в которых состоит (True/False)
                r.rolcreaterole,   -- Может ли роль создавать другие роли (True/False)
                r.rolcanlogin,     -- Разрешен ли вход в систему под этой ролью (True/False)
                r.rolreplication,  -- Разрешено ли использовать роль для репликации данных (True/False)
                r.rolbypassrls,    -- Игнорирует ли роль политики безопасности на уровне строк (RLS) (True/False)
                r.rolpassword     -- Хешированный пароль роли (если он установлен)
            FROM pg_roles r
            WHERE r.rolname = %s;
        """, [username])
        user_info = cursor.fetchone()
        cursor.execute("""
            SELECT r.rolname 
            FROM pg_roles r
            JOIN pg_auth_members m ON r.oid = m.roleid
            JOIN pg_roles u ON u.oid = m.member
            WHERE u.rolname = %s;
        """, [username])
        groups = cursor.fetchall()
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
            'email': user_log.email,
            'created_at': user_log.created_at,
            'updated_at': user_log.updated_at,
        }
    else:
        user_data = None
        message = user_info_error(username)
        messages.success(request, message)
        create_audit_log(user_requester, 'create', 'user', username, message)
    return render(request, 'users/user_info.html', {'user_data': user_data})


def user_edit(request, username):
    """Редактирование пользователя"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    send_email = SettingsProject.objects.first().send_email if SettingsProject.objects.exists() else False
    # Проверка наличия пользователя в PostgreSQL
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_user WHERE usename = %s;", [username])
        user_exists = cursor.fetchone()
    if not user_exists:
        return HttpResponseNotFound(f"Пользователь '{username}' не найден в базе данных PostgreSQL.")
    user_log, created = UserLog.objects.get_or_create(
        username=username,
        defaults={
            'email': None,
            'created_at': created_at,
            'updated_at': updated_at
        }
    )

    # Получение актуальных прав пользователя из PostgreSQL
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT rolcreatedb, rolsuper, rolinherit, rolcreaterole, 
                   rolcanlogin, rolreplication, rolbypassrls
            FROM pg_roles 
            WHERE rolname = %s;
        """, [username])
        result = cursor.fetchone()
        if result:
            role_permissions = {
                'can_create_db': result[0],
                'is_superuser': result[1],
                'inherit': result[2],
                'create_role': result[3],
                'login': result[4],
                'replication': result[5],
                'bypass_rls': result[6]
            }
            print("Роль пользователя:", role_permissions)  # Отладка
        else:
            role_permissions = {key: False for key in [
                'can_create_db', 'is_superuser', 'inherit',
                'create_role', 'login', 'replication', 'bypass_rls'
            ]}
    if request.method == "POST":
        role_permissions = {
            'can_create_db': 'can_create_db' in request.POST,
            'is_superuser': 'is_superuser' in request.POST,
            'inherit': 'inherit' in request.POST,
            'create_role': 'create_role' in request.POST,
            'login': 'login' in request.POST,
            'replication': 'replication' in request.POST,
            'bypass_rls': 'bypass_rls' in request.POST
        }
        message = edit_user_messages_role_permissions(username, role_permissions)
        messages.success(request, message)
        create_audit_log(user_requester, 'update', 'user', username, message)
    if created:
        message = user_data(username)
        messages.success(request, message)
        create_audit_log(user_requester, 'create', 'user', username, message)

    # Получение актуальных групп пользователя из PostgreSQL
    with connection.cursor() as cursor:
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
    has_changes = False
    group_changes = []
    if request.method == "POST":
        new_email = request.POST.get('new_email')
        new_password = request.POST.get('new_password')
        selected_groups = set(filter(None, request.POST.get('selected_groups', '').split(',')))
        deleted_groups = set(filter(None, request.POST.get('deleted_groups', '').split(',')))

        # Получение значений чекбоксов
        can_create_db = 'can_create_db' in request.POST
        is_superuser = 'is_superuser' in request.POST
        inherit = 'inherit' in request.POST
        create_role = 'create_role' in request.POST
        login = 'login' in request.POST
        replication = 'replication' in request.POST
        bypass_rls = 'bypass_rls' in request.POST

        user_log.can_create_db = can_create_db
        user_log.is_superuser = is_superuser
        user_log.inherit = inherit
        user_log.create_role = create_role
        user_log.login = login
        user_log.replication = replication
        user_log.bypass_rls = bypass_rls
        user_log.save()

        # Сохранение в PostgreSQL
        with connection.cursor() as cursor:
            cursor.execute(f"""
                ALTER ROLE {username}
                {'CREATEDB' if can_create_db else 'NOCREATEDB'}
                {'SUPERUSER' if is_superuser else 'NOSUPERUSER'}
                {'INHERIT' if inherit else 'NOINHERIT'}
                {'CREATEROLE' if create_role else 'NOCREATEROLE'}
                {'LOGIN' if login else 'NOLOGIN'}
                {'REPLICATION' if replication else 'NOREPLICATION'}
                {'BYPASSRLS' if bypass_rls else 'NOBYPASSRLS'};
            """)

        if user_log.email != new_email:
            if UserLog.objects.filter(email=new_email).exclude(username=username).exists():
                message = edit_user_messages_email_error(username, new_email)
                messages.error(request, message)
                create_audit_log(user_requester, 'update', 'user', username, message)
                return render(request, 'users/user_edit.html', {
                    'username': username,
                    'user_log': user_log,
                    'user_groups': sorted(current_groups),
                    'available_groups': sorted(available_groups),
                })
            try:
                user_log.email = new_email if new_email else None
                user_log.save()
                has_changes = True
                message = edit_user_messages_success(username, new_email)
                messages.success(request, message)
                create_audit_log(user_requester, 'update', 'user', username, message)
            except Exception:
                message = edit_user_messages_email_error(username, new_email)
                messages.error(request, message)
                create_audit_log(user_requester, 'update', 'user', username, message)
        if selected_groups != current_groups:
            has_changes = True
            for groupname in deleted_groups:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"REVOKE {groupname} FROM {username};")
                    group_changes.append(f"Удален из группы: {groupname}")
                    message = edit_user_messages_delete_group_success(username, groupname)
                    messages.success(request, message)
                    create_audit_log(user_requester, 'update', 'user', username, message)
                except Exception:
                    message = edit_user_messages_delete_group_error(username, groupname)
                    messages.success(request, message)
                    create_audit_log(user_requester, 'update', 'user', username, message)
            for groupname in selected_groups:
                if groupname not in current_groups:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(f"GRANT {groupname} TO {username};")
                        group_changes.append(f"Добавлен в группу: {groupname}")
                        message = edit_user_messages_add_group_success(username, groupname)
                        messages.success(request, message)
                        create_audit_log(user_requester, 'update', 'user', username, message)
                    except Exception:
                        message = edit_user_messages_add_group_error(username, groupname)
                        messages.success(request, message)
                        create_audit_log(user_requester, 'update', 'user', username, message)
        if has_changes and user_log.email and send_email == True:
            subject = "Изменение учетной записи"
            html_message = render_to_string('send_email/send_user_edit.html', {
                'username': username,
                'password': new_password if new_password else "Пароль не изменен",
                'group_changes': group_changes if group_changes else None
            })
            email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [user_log.email])
            email_message.attach_alternative(html_message, "text/html")
            email_message.send()
            message = edit_user_messages_email_success(username, user_log.email)
            messages.success(request, message)
            create_audit_log(user_requester, 'create', 'user', username, message)
        return redirect('user_list')

    return render(request, 'users/user_edit.html', {
        'username': username,
        'user_log': user_log,
        'user_groups': sorted(current_groups),
        'available_groups': sorted(available_groups),
        'form': user_log,
        'role_permissions': role_permissions
    })


@login_required
def user_delete(request, username):
    """Удаление пользователя"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    send_email = SettingsProject.objects.first().send_email if SettingsProject.objects.exists() else False
    user_log = UserLog.objects.filter(username=username).first()
    user_email = user_log.email if user_log else None
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"REASSIGN OWNED BY {username} TO postgres;")
            cursor.execute(f"DROP OWNED BY {username};")
            cursor.execute(f"DROP USER IF EXISTS {username};")
        except Exception:
            message = delete_user_messages_error(username)
            messages.error(request, message)
            create_audit_log(user_requester, 'delete', 'user', username, message)
            return redirect('user_list')
    if user_log:
        user_log.delete()
        message = delete_user_messages_success(username)
        messages.success(request, message)
        create_audit_log(user_requester, 'delete', 'user', username, message)
    if user_email and send_email == True:
        subject = "Ваш аккаунт был удален"
        html_message = render_to_string('send_email/send_user_delete.html', {'username': username})
        email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [user_email])
        email_message.attach_alternative(html_message, "text/html")
        email_message.send()
        message = delete_user_messages_email(username, user_email)
        messages.success(request, message)
        create_audit_log(user_requester, 'delete', 'user', username, message)
    return redirect('user_list')
