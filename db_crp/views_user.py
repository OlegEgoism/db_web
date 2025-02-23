from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.timezone import now
from .forms import UserCreateForm, UserEditForm
from django.shortcuts import render, redirect
from .models import UserLog, Audit
from django.contrib import messages

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
            user_requester = request.user.username if request.user.is_authenticated else "Аноним"

            # Проверка наличия пользователя в PostgreSQL
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [username])
                user_exists_in_pg = cursor.fetchone()

            # Проверка наличия email в UserLog
            email_exists = UserLog.objects.filter(email=email).exists() if email else False
            if user_exists_in_pg:
                messages.error(request, f"Неудачная попытка создания пользователя '{username}', пользователь уже существует.")
                Audit.objects.create(
                    username=user_requester,
                    action_type='create',
                    entity_type='user',
                    entity_name=username,
                    timestamp=now(),
                    details=f"Неудачная попытка создания пользователя '{username}', пользователь уже существует."
                )
                return render(request, 'users/user_create.html', {'form': form})
            if email_exists:
                messages.error(request, f"Неудачная попытка создания почты '{email}' у пользователя '{username}'. Почта уже используется.")
                Audit.objects.create(
                    username=user_requester,
                    action_type='create',
                    entity_type='user',
                    entity_name=username,
                    timestamp=now(),
                    details=f"Неудачная попытка создания почты '{email}' у пользователя '{username}'. Почта уже используется."
                )
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

                # Логирование в UserLog после успешного создания в PostgreSQL
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

                # Запись в журнал действий
                Audit.objects.create(
                    username=user_requester,
                    action_type='create',
                    entity_type='user',
                    entity_name=username,
                    timestamp=now(),
                    details=f"Пользователь '{username}' успешно создан в системе."
                )

                # Отправка уведомления на почту
                if email:
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
                    Audit.objects.create(
                        username=user_requester,
                        action_type='create',
                        entity_type='user',
                        entity_name=username,
                        timestamp=now(),
                        details=f"Уведомление об успешном создании пользователя '{username}' в системе отправлено на почту '{email}'. Права: "
                                f"Может создавать БД={can_create_db}. "
                                f"Суперпользователь={is_superuser}. "
                                f"Наследование={inherit}. "
                                f"Право создания роли={create_role}. "
                                f"Право входа={login}. "
                                f"Право репликации={replication}. "
                                f"Bypass RLS={bypass_rls}."
                    )
                messages.success(request, f"Пользователь '{username}' успешно создан в PostgreSQL.")
                return redirect('user_list')

            except Exception as e:
                messages.error(request, f"Ошибка при создании пользователя в PostgreSQL: {str(e)}.")
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
        messages.info(request, f"Автоматическое создание 'Дата создания' и 'Дата изменения' пользователя '{username}'.")
        Audit.objects.create(
            username=user_requester,
            action_type='create',
            entity_type='user',
            entity_name=username,
            timestamp=now(),
            details=f"Автоматическое создание 'Дата создания' и 'Дата изменения' пользователя '{username}'."
        )

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
        print(user_info)
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
        messages.error(request, f"Не удалось получить информацию о пользователе '{username}'.")
    return render(request, 'users/user_info.html', {'user_data': user_data})


# @login_required
# def user_edit(request, username):
#     """Редактирование пользователя"""
#     user_requester = request.user.username if request.user.is_authenticated else "Аноним"
#
#     # Проверка существования пользователя в PostgreSQL
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT
#                 usename, usesysid, usecreatedb, usesuper, valuntil,
#                 rolname, rolinherit, rolcreaterole, rolcanlogin,
#                 rolreplication, rolbypassrls
#             FROM pg_user u
#             JOIN pg_roles r ON u.usename = r.rolname
#             WHERE usename = %s;
#         """, [username])
#         user_info = cursor.fetchone()
#
#     # Получаем данные пользователя
#     (username, user_id, can_create_db, is_superuser, valid_until, rolname, inherit, create_role, login, replication, bypass_rls) = user_info
#     # Получаем или создаем лог пользователя
#     user_log, created = UserLog.objects.get_or_create(
#         username=username,
#         defaults={
#             'email': None,
#             'created_at': created_at,
#             'updated_at': updated_at
#         }
#     )
#     if created:
#         messages.info(request, f"Автоматическое создание 'Дата создания' и 'Дата изменения' пользователя '{username}'.")
#         Audit.objects.create(
#             username=user_requester,
#             action_type='create',
#             entity_type='user',
#             entity_name=username,
#             timestamp=now(),
#             details=f"Автоматическое создание 'Дата создания' и 'Дата изменения' пользователя '{username}'."
#         )
#
#     # groups
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT r.rolname
#             FROM pg_user u
#             JOIN pg_auth_members m ON u.usesysid = m.member
#             JOIN pg_roles r ON m.roleid = r.oid
#             WHERE u.usename = %s;
#         """, [username])
#         current_groups = {group[0] for group in cursor.fetchall()}
#         cursor.execute("""
#             SELECT rolname
#             FROM pg_roles
#             WHERE rolcanlogin = FALSE AND rolname NOT LIKE 'pg_%';
#         """)
#         all_groups = {group[0] for group in cursor.fetchall()}
#     available_groups = all_groups - current_groups
#     has_changes = False
#     errors = []
#     group_changes = []
#     # groups
#
#     if request.method == "POST":
#         form = UserEditForm(request.POST)
#
#
#
#         # groups
#         selected_groups = set(filter(None, request.POST.get('selected_groups', '').split(',')))
#         deleted_groups = set(filter(None, request.POST.get('deleted_groups', '').split(',')))
#         # groups
#
#         # groups
#         if selected_groups != current_groups:
#             has_changes = True
#             for groupname in deleted_groups:
#                 try:
#                     with connection.cursor() as cursor:
#                         cursor.execute(f"REVOKE {groupname} FROM {username};")
#                     group_changes.append(f"Удален из группы: {groupname}")
#                     Audit.objects.create(
#                         username=user_requester,
#                         action_type='update',
#                         entity_type='user',
#                         entity_name=username,
#                         timestamp=now(),
#                         details=f"Пользователь '{username}' был удален из группы '{groupname}'."
#                     )
#                 except Exception as e:
#                     errors.append(f"Ошибка при удалении группы '{groupname}': {str(e)}")
#             for groupname in selected_groups:
#                 if groupname not in current_groups:
#                     try:
#                         with connection.cursor() as cursor:
#                             cursor.execute(f"GRANT {groupname} TO {username};")
#                         group_changes.append(f"Добавлен в группу: {groupname}")
#                         Audit.objects.create(
#                             username=user_requester,
#                             action_type='update',
#                             entity_type='user',
#                             entity_name=username,
#                             timestamp=now(),
#                             details=f"Пользователь '{username}' был добавлен в группу '{groupname}'."
#                         )
#                     except Exception as e:
#                         errors.append(f"Ошибка при добавлении группы '{groupname}': {str(e)}")
#         # groups
#
#         if form.is_valid():
#             new_email = form.cleaned_data['email']
#             new_password = form.cleaned_data['password']
#             can_create_db = form.cleaned_data['can_create_db']
#             is_superuser = form.cleaned_data['is_superuser']
#             inherit = form.cleaned_data['inherit']
#             create_role = form.cleaned_data['create_role']
#             login = form.cleaned_data['login']
#             replication = form.cleaned_data['replication']
#             bypass_rls = form.cleaned_data['bypass_rls']
#             try:
#                 with connection.cursor() as cursor:
#                     # Обновление прав пользователя в PostgreSQL
#                     cursor.execute(f"ALTER USER {username} WITH {'CREATEDB' if can_create_db else 'NOCREATEDB'};")
#                     cursor.execute(f"ALTER USER {username} WITH {'SUPERUSER' if is_superuser else 'NOSUPERUSER'};")
#                     cursor.execute(f"ALTER USER {username} WITH {'INHERIT' if inherit else 'NOINHERIT'};")
#                     cursor.execute(f"ALTER USER {username} WITH {'CREATEROLE' if create_role else 'NOCREATEROLE'};")
#                     cursor.execute(f"ALTER USER {username} WITH {'LOGIN' if login else 'NOLOGIN'};")
#                     cursor.execute(f"ALTER USER {username} WITH {'REPLICATION' if replication else 'NOREPLICATION'};")
#                     cursor.execute(f"ALTER USER {username} WITH {'BYPASSRLS' if bypass_rls else 'NOBYPASSRLS'};")
#
#                     if new_password:  # Обновление пароля
#                         cursor.execute(f"ALTER USER {username} WITH PASSWORD %s;", [new_password])
#                         Audit.objects.create(
#                             username=user_requester,
#                             action_type='update',
#                             entity_type='user',
#                             entity_name=username,
#                             timestamp=now(),
#                             details=f"Обновление пароля пользователя '{username}'."
#                         )
#                     if new_email != user_log.email:  # Обновление почты
#                         if UserLog.objects.filter(email=new_email).exclude(username=username).exists():
#                             messages.error(request, f"Неудачная попытка изменить почту '{new_email}' у пользователя '{username}', почта уже используется.")
#                             Audit.objects.create(
#                                 username=user_requester,
#                                 action_type='update',
#                                 entity_type='user',
#                                 entity_name=username,
#                                 timestamp=now(),
#                                 details=f"Неудачная попытка изменить почту '{new_email}' у пользователя '{username}', почта уже используется."
#                             )
#                             return render(request, 'users/user_edit.html', {
#                                 'form': form,
#                             })
#                         else:
#                             Audit.objects.create(
#                                 username=user_requester,
#                                 action_type='update',
#                                 entity_type='user',
#                                 entity_name=username,
#                                 timestamp=now(),
#                                 details=f"Обновление почты пользователя '{username}' c '{user_log.email}' на '{new_email}'."
#                             )
#
#                 user_log.save()
#                 messages.success(request, f"Пользователь '{username}' успешно обновлен.")
#
#                 subject = "Изменение учетной записи"
#                 html_message = render_to_string('send_email/send_user_edit.html', {
#                     'username': username,
#                     'password': new_password if new_password else "Пароль не изменен",
#                 })
#                 email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [user_log.email])
#                 email_message.attach_alternative(html_message, "text/html")
#                 email_message.send()
#                 Audit.objects.create(
#                     username=user_requester,
#                     action_type='update',
#                     entity_type='user',
#                     entity_name=username,
#                     timestamp=now(),
#                     details=f"Уведомление об изменении учетной записи отправлено пользователю '{username}' на почту '{new_email}'."
#                 )
#                 return redirect('user_list')
#
#             except Exception as e:
#                 messages.error(request, f"Ошибка при обновлении пользователя: {str(e)}.")
#                 return render(request, 'users/user_edit.html', {'form': form, 'username': username})
#     else:
#         form = UserEditForm(initial={
#             'email': user_log.email,
#             'can_create_db': can_create_db,
#             'is_superuser': is_superuser,
#             'inherit': inherit,
#             'create_role': create_role,
#             'login': login,
#             'replication': replication,
#             'bypass_rls': bypass_rls
#         })
#
#     return render(request, 'users/user_edit.html', {'form': form, 'username': username})





def user_edit(request, username):
    """Редактирование пользователя"""
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
        messages.info(request, f"Автоматическое создание 'Дата создания' и 'Дата изменения' пользователя '{username}'.")
        Audit.objects.create(
            username=user_requester,
            action_type='create',
            entity_type='user',
            entity_name=username,
            timestamp=now(),
            details=f"Автоматическое создание 'Дата создания' и 'Дата изменения' пользователя '{username}'."
        )

    # groups
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
    errors = []
    group_changes = []
    # groups

    if request.method == "POST":
        new_email = request.POST.get('new_email')
        new_password = request.POST.get('new_password')

        # groups
        selected_groups = set(filter(None, request.POST.get('selected_groups', '').split(',')))
        deleted_groups = set(filter(None, request.POST.get('deleted_groups', '').split(',')))
        # groups

        if user_log.email != new_email:
            if UserLog.objects.filter(email=new_email).exclude(username=username).exists():
                messages.error(request, f"Неудачная попытка изменить почту '{new_email}' у пользователя '{username}', почта уже используется.")
                Audit.objects.create(
                    username=user_requester,
                    action_type='update',
                    entity_type='user',
                    entity_name=username,
                    timestamp=now(),
                    details=f"Неудачная попытка изменить почту '{new_email}' у пользователя '{username}', почта уже используется."
                )
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
                Audit.objects.create(
                    username=user_requester,
                    action_type='update',
                    entity_type='user',
                    entity_name=username,
                    timestamp=now(),
                    details=f"Почта пользователя '{username}' изменена на '{new_email}'."
                )
            except Exception as e:
                errors.append(f"Ошибка при обновлении почты: {str(e)}")

        # groups
        if selected_groups != current_groups:
            has_changes = True
            for groupname in deleted_groups:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"REVOKE {groupname} FROM {username};")
                    group_changes.append(f"Удален из группы: {groupname}")
                    Audit.objects.create(
                        username=user_requester,
                        action_type='update',
                        entity_type='user',
                        entity_name=username,
                        timestamp=now(),
                        details=f"Пользователь '{username}' был удален из группы '{groupname}'."
                    )
                except Exception as e:
                    errors.append(f"Ошибка при удалении группы '{groupname}': {str(e)}")
            for groupname in selected_groups:
                if groupname not in current_groups:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(f"GRANT {groupname} TO {username};")
                        group_changes.append(f"Добавлен в группу: {groupname}")
                        Audit.objects.create(
                            username=user_requester,
                            action_type='update',
                            entity_type='user',
                            entity_name=username,
                            timestamp=now(),
                            details=f"Пользователь '{username}' был добавлен в группу '{groupname}'."
                        )
                    except Exception as e:
                        errors.append(f"Ошибка при добавлении группы '{groupname}': {str(e)}")
        # groups

        if has_changes and user_log.email:
            subject = "Изменение учетной записи"
            html_message = render_to_string('send_email/send_user_edit.html', {
                'username': username,
                'password': new_password if new_password else "Пароль не изменен",
                'group_changes': group_changes if group_changes else None
            })
            email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [user_log.email])
            email_message.attach_alternative(html_message, "text/html")
            email_message.send()
            Audit.objects.create(
                username=user_requester,
                action_type='update',
                entity_type='user',
                entity_name=username,
                timestamp=now(),
                details=f"Уведомление об изменении учетной записи отправлено пользователю '{username}'."
            )
        if errors:
            messages.error(request, "<br>".join(errors))
            return render(request, 'users/user_edit.html', {
                'username': username,
                'user_log': user_log,
                'user_groups': sorted(current_groups),
                'available_groups': sorted(available_groups),
            })

        return redirect('user_list')

    return render(request, 'users/user_edit.html', {
        'username': username,
        'user_log': user_log,
        'user_groups': sorted(current_groups),
        'available_groups': sorted(available_groups),
    })


@login_required
def user_delete(request, username):
    """Удаление пользователя"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    user_log = UserLog.objects.filter(username=username).first()
    user_email = user_log.email if user_log else None
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"REASSIGN OWNED BY {username} TO postgres;")
            cursor.execute(f"DROP OWNED BY {username};")
            cursor.execute(f"DROP USER IF EXISTS {username};")
        except Exception:
            messages.error(request, f"Неудачная попытка при удалении пользователя '{username}', не может быть удален, так как существуют зависимые объекты в базе данных.")
            Audit.objects.create(
                username=user_requester,
                action_type='delete',
                entity_type='user',
                entity_name=username,
                timestamp=now(),
                details=f"Неудачная попытка при удалении пользователя '{username}', не может быть удален, так как существуют зависимые объекты в базе данных."
            )
            return redirect('user_list')
    if user_log:
        user_log.delete()
    Audit.objects.create(
        username=user_requester,
        action_type='delete',
        entity_type='user',
        entity_name=username,
        timestamp=now(),
        details=f"Пользователь '{username}' был удален из системы"
    )
    if user_email:
        subject = "Ваш аккаунт был удален"
        html_message = render_to_string('send_email/send_user_delete.html', {
            'username': username
        })
        email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [user_email])
        email_message.attach_alternative(html_message, "text/html")
        email_message.send()
        Audit.objects.create(
            username=user_requester,
            action_type='delete',
            entity_type='user',
            entity_name=username,
            timestamp=now(),
            details=f"Уведомление об удалении аккаунта пользователя '{username}' отправлено на '{user_email}'."
        )
    return redirect('user_list')
