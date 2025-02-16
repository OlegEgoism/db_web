from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db import connection
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from .forms import UserCreateForm, CreateGroupForm, CustomUserRegistrationForm, GroupEditForm
from django.shortcuts import render, redirect, get_object_or_404
from .models import GroupLog, UserLog


def home(request):
    return render(request, 'home.html')


def register(request):
    """Регистрация пользователя"""
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('home')
        else:
            messages.error(request, 'Ошибка регистрации. Проверьте введённые данные.')
    else:
        form = CustomUserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    """Выход пользователя"""
    logout(request)
    return redirect('home')


# TODO ГРУППЫ
def group_list(request):
    """Список групп"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT groname FROM pg_group;")
        groups = cursor.fetchall()
    group_names = [group[0] for group in groups]
    group_user_counts = {}
    for group in group_names:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM pg_user u
                JOIN pg_auth_members m ON u.usesysid = m.member
                JOIN pg_roles r ON m.roleid = r.oid
                WHERE r.rolname = %s;
            """, [group])
            count = cursor.fetchone()[0]
            group_user_counts[group] = count
    user_groups = {g: group_user_counts[g] for g in group_user_counts if not g.startswith('pg_')}
    group_logs = {log.groupname: log for log in GroupLog.objects.filter(groupname__in=user_groups.keys())}
    user_groups_data = [
        (group, count, group_logs[group].created_at if group in group_logs else None,
         group_logs[group].updated_at if group in group_logs else None)
        for group, count in user_groups.items()
    ]
    return render(request, 'groups/group_list.html', {
        'user_groups_data': user_groups_data,
    })


def group_create(request):
    """Создание группы"""
    if request.method == "POST":
        form = CreateGroupForm(request.POST)
        if form.is_valid():
            groupname = form.cleaned_data['groupname']
            if groupname.startswith('pg_'):
                return HttpResponse("⚠️ Ошибка: Имя группы не может начинаться с 'pg_', так как это зарезервировано системой.")
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"CREATE ROLE {groupname};")
                GroupLog.objects.get_or_create(groupname=groupname, defaults={"created_at": timezone.now(), "updated_at": timezone.now()})
                return redirect('group_list')
            except Exception as e:
                return HttpResponse(f"Ошибка при создании группы: {e}")
    else:
        form = CreateGroupForm()
    return render(request, 'groups/group_create.html', {'form': form})


def group_edit(request, group_name):
    """Редактирование группы"""
    group_log = get_object_or_404(GroupLog, groupname=group_name)
    if request.method == "POST":
        form = GroupEditForm(request.POST)
        if form.is_valid():
            new_groupname = form.cleaned_data['groupname']
            if new_groupname.startswith('pg_'):
                return HttpResponse("⚠️ Ошибка: Имя группы не может начинаться с 'pg_', так как это зарезервировано системой.")
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"ALTER ROLE {group_name} RENAME TO {new_groupname};")
                group_log.groupname = new_groupname
                group_log.updated_at = timezone.now()
                group_log.save()
                return redirect('group_list')
            except Exception as e:
                return HttpResponse(f"Ошибка при редактировании группы: {e}")
    else:
        form = GroupEditForm(initial={'groupname': group_log.groupname})
    return render(request, 'groups/group_edit.html', {
        'form': form,
        'group_name': group_name,
        'group_log': group_log
    })


def group_delete(request, group_name):
    """Удаление группы из базы и логов"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP ROLE IF EXISTS "{group_name}";')
        group_log = GroupLog.objects.filter(groupname=group_name).first()
        if group_log:
            group_log.delete()
        messages.success(request, f'Группа "{group_name}" успешно удалена.')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении группы: {e}')
    return HttpResponseRedirect(reverse('group_list'))


def group_users(request, group_name):
    """Пользователи в группе"""
    group_log = get_object_or_404(GroupLog, groupname=group_name)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT usename 
            FROM pg_user 
            JOIN pg_group ON (pg_user.usesysid = ANY(pg_group.grolist)) 
            WHERE groname = %s;
        """, [group_name])
        users = cursor.fetchall()
    user_names = [user[0] for user in users]
    return render(request, 'groups/group_users.html', {
        'group_name': group_name,
        'users': user_names,
        'user_count': len(user_names),  # Передаем количество пользователей отдельно
        'group_log': group_log
    })


# TODO ПОЛЬЗОВАТЕЛИ
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
            "group_count": group_count  # Количество групп пользователя
        })
    return render(request, 'users/user_list.html', {'users_data': users_data})


def user_create(request):
    """Создать пользователя"""
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            query = f"CREATE USER {username} WITH PASSWORD %s;"
            with connection.cursor() as cursor:
                cursor.execute(query, [password])
            UserLog.objects.create(username=username, email=email)
            if email:
                subject = ""
                html_message = render_to_string('send_email/send_user_create.html', {
                    'username': username,
                    'password': password
                })
                email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [email])
                email_message.attach_alternative(html_message, "text/html")
                email_message.send()
            return redirect('user_list')
    else:
        form = UserCreateForm()
    return render(request, 'users/user_create.html', {'form': form})


def user_info(request, username):
    """Информация пользователя"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT usename, usesysid, usecreatedb, usesuper, passwd, valuntil
            FROM pg_user
            WHERE usename = %s;
        """, [username])
        user_info = cursor.fetchone()
        cursor.execute("""
            SELECT r.rolname 
            FROM pg_user u
            JOIN pg_auth_members m ON u.usesysid = m.member
            JOIN pg_roles r ON m.roleid = r.oid
            WHERE u.usename = %s;
        """, [username])
        groups = cursor.fetchall()
    user_log = get_object_or_404(UserLog, username=username)
    if user_info:
        group_list = [group[0] for group in groups]  # Преобразуем в список имен групп
        user_data = {
            'username': user_info[0],
            'user_id': user_info[1],
            'can_create_db': user_info[2],
            'is_superuser': user_info[3],
            'password_hash': user_info[4],
            'valid_until': user_info[5],
            'groups': group_list,
            'group_count': len(group_list),  # Подсчитываем количество групп
            'email': user_log.email,
            'created_at': user_log.created_at,
            'updated_at': user_log.updated_at,
        }
    else:
        user_data = None
    return render(request, 'users/user_info.html', {'user_data': user_data})


def user_edit(request):
    """Редактирование почты, пароля и управление группами пользователя с уведомлением"""
    username = request.GET.get('username')
    user_log = get_object_or_404(UserLog, username=username)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT r.rolname
            FROM pg_user u
            JOIN pg_auth_members m ON u.usesysid = m.member
            JOIN pg_roles r ON m.roleid = r.oid
            WHERE u.usename = %s;
        """, [username])
        current_groups = {group[0] for group in cursor.fetchall()}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT rolname 
            FROM pg_roles 
            WHERE rolcanlogin = FALSE AND rolname NOT LIKE 'pg_%';
        """)
        all_groups = {group[0] for group in cursor.fetchall()}
    available_groups = all_groups - current_groups
    if request.method == "POST":
        new_email = request.POST.get('new_email')
        new_password = request.POST.get('new_password')
        selected_groups = set(filter(None, request.POST.get('selected_groups', '').split(',')))
        deleted_groups = set(filter(None, request.POST.get('deleted_groups', '').split(',')))
        errors = []
        has_changes = False
        group_changes = []
        if user_log.email != new_email:
            try:
                user_log.email = new_email if new_email else None
                user_log.save()
                has_changes = True
            except Exception as e:
                errors.append(f"Ошибка при обновлении email: {e}")
        if new_password:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"ALTER USER {username} WITH PASSWORD %s;", [new_password])
                has_changes = True
            except Exception as e:
                errors.append(f"Ошибка при смене пароля: {e}")
        if selected_groups != current_groups:
            has_changes = True
            for groupname in deleted_groups:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"REVOKE {groupname} FROM {username};")
                    group_changes.append(f"Удален из группы: {groupname}")
                except Exception as e:
                    errors.append(f"Ошибка при удалении группы '{groupname}': {e}")
            for groupname in selected_groups:
                if groupname not in current_groups:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(f"GRANT {groupname} TO {username};")
                        group_changes.append(f"Добавлен в группу: {groupname}")
                    except Exception as e:
                        errors.append(f"Ошибка при добавлении группы '{groupname}': {e}")
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
        if errors:
            return HttpResponse("<br>".join(errors))
        return redirect('user_list')
    return render(request, 'users/user_edit.html', {
        'username': username,
        'user_log': user_log,
        'user_groups': sorted(current_groups),
        'available_groups': sorted(available_groups),
    })


def user_delete(request, username):
    """Удаление пользователя"""
    try:
        user_log = UserLog.objects.filter(username=username).first()
        user_email = user_log.email if user_log else None
        with connection.cursor() as cursor:
            cursor.execute(f"DROP USER IF EXISTS {username};")
        if user_log:
            user_log.delete()
        if user_email:
            subject = "Ваш аккаунт был удален"
            html_message = render_to_string('send_email/send_user_delete.html', {
                'username': username
            })
            email_message = EmailMultiAlternatives(subject, "", settings.EMAIL_HOST_USER, [user_email])
            email_message.attach_alternative(html_message, "text/html")
            email_message.send()
        return redirect('user_list')
    except Exception as e:
        return HttpResponse(f"Ошибка при удалении пользователя: {e}")
