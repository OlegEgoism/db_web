from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from .audit_views import group_data, create_audit_log, delete_group_messages_success, delete_group_messages_error, create_group_messages_error, create_group_messages_error_pg, edit_group_messages_group_success, create_group_messages_error_info, \
    edit_group_messages_error_pg, edit_group_messages_error_name, edit_group_messages_success_name, edit_group_messages_error
from .forms import CreateGroupForm, GroupEditForm
from django.shortcuts import render, redirect
from .models import GroupLog, Audit, ConnectingDB
from django.contrib import messages

created_at = datetime(2000, 1, 1, 0, 0)
updated_at = timezone.now()


@login_required
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
    return render(request, 'groups/group_list.html', {'user_groups_data': user_groups_data, })


@login_required
def group_create(request):
    """Создание группы"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    if request.method == "POST":
        form = CreateGroupForm(request.POST)
        if form.is_valid():
            groupname = form.cleaned_data['groupname']
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [groupname])
                existing_group = cursor.fetchone()
            if existing_group:
                message = create_group_messages_error(groupname)
                messages.error(request, message)
                create_audit_log(user_requester, 'create', 'group', groupname, message)
                return render(request, 'groups/group_create.html', {'form': form})
            if groupname.startswith('pg_'):
                message = create_group_messages_error_pg(groupname)
                messages.error(request, message)
                create_audit_log(user_requester, 'create', 'group', groupname, message)
                return render(request, 'groups/group_create.html', {'form': form})
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"CREATE ROLE {groupname};")
                GroupLog.objects.create(groupname=groupname, created_at=timezone.now(), updated_at=updated_at)
                message = edit_group_messages_group_success(groupname)
                messages.success(request, message)
                create_audit_log(user_requester, 'create', 'group', groupname, message)
                return redirect('group_list')
            except Exception:
                message = create_group_messages_error_info(groupname)
                messages.error(request, message)
                create_audit_log(user_requester, 'create', 'group', groupname, message)
    else:
        form = CreateGroupForm()
    return render(request, 'groups/group_create.html', {'form': form})


# @login_required
# def group_edit(request, group_name):
#     """Редактирование группы"""
#     user_requester = request.user.username if request.user.is_authenticated else "Аноним"
#     group_log, created = GroupLog.objects.get_or_create(
#         groupname=group_name,
#         defaults={
#             'created_at': created_at,
#             'updated_at': updated_at
#         }
#     )
#     if created:
#         message = group_data(group_name)
#         messages.success(request, message)
#         create_audit_log(user_requester, 'create', 'group', group_name, message)
#     if request.method == "POST":
#         form = GroupEditForm(request.POST)
#         if form.is_valid():
#             new_group_name = form.cleaned_data['groupname']
#             if new_group_name.startswith('pg_'):
#                 message = edit_group_messages_error_pg(group_name, new_group_name)
#                 messages.error(request, message)
#                 create_audit_log(user_requester, 'update', 'group', group_name, message)
#                 return render(request, 'groups/group_edit.html', {
#                     'form': form,
#                     'group_name': group_name,
#                     'group_log': group_log
#                 })
#             with connection.cursor() as cursor:
#                 cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [new_group_name])
#                 existing_group = cursor.fetchone()
#             if existing_group:
#                 message = edit_group_messages_error_name(group_name, new_group_name)
#                 messages.error(request, message)
#                 create_audit_log(user_requester, 'update', 'group', group_name, message)
#                 return render(request, 'groups/group_edit.html', {
#                     'form': form,
#                     'group_name': group_name,
#                     'group_log': group_log
#                 })
#             try:
#                 with connection.cursor() as cursor:
#                     cursor.execute(f"ALTER ROLE {group_name} RENAME TO {new_group_name};")
#                 group_log.groupname = new_group_name
#                 group_log.updated_at = timezone.now()
#                 group_log.save()
#                 message = edit_group_messages_success_name(group_name, new_group_name)
#                 messages.success(request, message)
#                 create_audit_log(user_requester, 'update', 'group', group_name, message)
#                 return redirect('group_list')
#             except Exception:
#                 message = edit_group_messages_error(group_name)
#                 messages.error(request, message)
#                 create_audit_log(user_requester, 'update', 'group', group_name, message)
#     else:
#         form = GroupEditForm(initial={'groupname': group_log.groupname})
#     return render(request, 'groups/group_edit.html', {
#         'form': form,
#         'group_name': group_name,
#         'group_log': group_log
#     })


@login_required
def group_edit(request, group_name):
    """Редактирование группы"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    group_log, created = GroupLog.objects.get_or_create(
        groupname=group_name,
        defaults={
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
    )
    if created:
        message = group_data(group_name)
        messages.success(request, message)
        create_audit_log(user_requester, 'create', 'group', group_name, message)
    if request.method == "POST":
        form = GroupEditForm(request.POST)
        if form.is_valid():
            new_group_name = form.cleaned_data['groupname']
            if new_group_name.startswith('pg_'):
                message = edit_group_messages_error_pg(group_name, new_group_name)
                messages.error(request, message)
                create_audit_log(user_requester, 'update', 'group', group_name, message)
                return render(request, 'groups/group_edit.html', {
                    'form': form,
                    'group_name': group_name,
                    'group_log': group_log
                })
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [new_group_name])
                existing_group = cursor.fetchone()
            if existing_group:
                message = edit_group_messages_error_name(group_name, new_group_name)
                messages.error(request, message)
                create_audit_log(user_requester, 'update', 'group', group_name, message)
                return render(request, 'groups/group_edit.html', {
                    'form': form,
                    'group_name': group_name,
                    'group_log': group_log
                })
            try:
                with connection.cursor() as cursor:  # Получение текущих прав доступа группы
                    cursor.execute("SELECT * FROM pg_roles WHERE rolname = %s;", [group_name])
                    current_privileges = cursor.fetchone()
                with connection.cursor() as cursor:
                    cursor.execute(f"ALTER ROLE {group_name} RENAME TO {new_group_name};")
                group_log.groupname = new_group_name
                group_log.updated_at = timezone.now()
                group_log.save()
                message = edit_group_messages_success_name(group_name, new_group_name)
                messages.success(request, message)
                create_audit_log(user_requester, 'update', 'group', group_name, message)
                return redirect('group_list')
            except Exception as e:
                message = edit_group_messages_error(group_name)
                messages.error(request, message)
                create_audit_log(user_requester, 'update', 'group', group_name, message)
    else:
        form = GroupEditForm(initial={'groupname': group_log.groupname})
    return render(request, 'groups/group_edit.html', {
        'form': form,
        'group_name': group_name,
        'group_log': group_log
    })


def groups_edit_privileges(request, group_name):
    """Список баз данных в группе"""
    databases = ConnectingDB.objects.all()
    return render(request, "databases/database_list.html", {
        'group_name': group_name,
        'databases': databases
    })



# def groups_edit_privileges(request, group_name):
#     """Список баз данных"""
#     databases = ConnectingDB.objects.all()
#     return render(request, 'groups/groups_edit_privileges.html', {
#         'group_name': group_name,
#         'databases': databases,
#     })
#
#
#
# def groups_edit_privileges_db(request, group_name, db_id):
#     """Редактирование прав для группы в выбранной базе данных"""
#     connection_info = get_object_or_404(ConnectingDB, id=db_id)
#
#     return render(request, 'groups/groups_edit_privileges_db.html', {
#         'group_name': group_name,
#         'database': connection_info,
#     })


@login_required
def group_delete(request, group_name):
    """Удаление группы"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    group_log = GroupLog.objects.filter(groupname=group_name).first()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP ROLE IF EXISTS "{group_name}";')
        if group_log:
            group_log.delete()
            message = delete_group_messages_success(group_name)
            messages.success(request, message)
            create_audit_log(user_requester, 'delete', 'group', group_name, message)
    except Exception:
        message = delete_group_messages_error(group_name)
        messages.error(request, message)
        create_audit_log(user_requester, 'delete', 'group', group_name, message)
    return HttpResponseRedirect(reverse('group_list'))


@login_required
def group_info(request, group_name):
    """Пользователи в группе"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    group_log, created = GroupLog.objects.get_or_create(
        groupname=group_name,
        defaults={
            'created_at': created_at,
            'updated_at': updated_at
        }
    )
    if created:
        message = group_data(group_name)
        messages.success(request, message)
        create_audit_log(user_requester, 'create', 'group', group_name, message)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT usename 
            FROM pg_user 
            JOIN pg_group ON (pg_user.usesysid = ANY(pg_group.grolist)) 
            WHERE groname = %s;
        """, [group_name])
        users = cursor.fetchall()
    user_names = [user[0] for user in users]
    return render(request, 'groups/group_info.html', {
        'group_name': group_name,
        'users': user_names,
        'user_count': len(user_names),
        'group_log': group_log
    })






from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import connection
from django.utils.timezone import now
from .models import GroupLog
from .forms import GroupEditForm

#
# @login_required
# def groups_edit_privileges(request, group_name):
#     """Редактирование группы и получение актуальных прав доступа"""
#     user_requester = request.user.username if request.user.is_authenticated else "Аноним"
#
#     # Получаем или создаем запись о группе
#     group_log, created = GroupLog.objects.get_or_create(groupname=group_name)
#
#     # Получаем список всех таблиц в базе
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT schemaname || '.' || tablename
#             FROM pg_catalog.pg_tables
#             WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
#         """)
#         tables = [table[0] for table in cursor.fetchall()]
#
#     # Получаем права доступа из БД
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT table_schema || '.' || table_name, privilege_type
#             FROM information_schema.role_table_grants
#             WHERE grantee = %s
#         """, [group_name])
#         granted_tables = {}
#         for table, privilege in cursor.fetchall():
#             if table not in granted_tables:
#                 granted_tables[table] = set()
#             granted_tables[table].add(privilege)
#     if request.method == "POST":
#         form = GroupEditForm(request.POST)
#         if form.is_valid():
#             new_groupname = form.cleaned_data['groupname']
#             # Переименовываем группу
#             if new_groupname != group_name:
#                 with connection.cursor() as cursor:
#                     cursor.execute(f"ALTER ROLE {group_name} RENAME TO {new_groupname};")
#                 group_log.groupname = new_groupname
#                 group_log.updated_at = now()
#                 group_log.save()
#                 messages.success(request, f"Группа успешно переименована в '{new_groupname}'.")
#
#         # **Обновляем права доступа**
#         table_permissions = {table: request.POST.getlist(f'permissions_{table}') for table in tables}
#
#         try:
#             with connection.cursor() as cursor:
#                 # Удаляем все текущие права
#                 for table in granted_tables:
#                     cursor.execute(f"REVOKE ALL ON {table} FROM {group_name};")
#
#                 # Выдаём права на выбранные таблицы
#                 for table, permissions in table_permissions.items():
#                     if permissions:
#                         permissions_str = ", ".join(permissions)
#                         cursor.execute(f"GRANT {permissions_str} ON {table} TO {group_name};")
#
#             messages.success(request, f"Права на таблицы успешно обновлены для группы '{group_name}'.")
#
#         except Exception as e:
#             messages.error(request, f"Ошибка при выдаче прав: {e}")
#
#         return redirect('group_list')
#
#     else:
#         form = GroupEditForm(initial={'groupname': group_log.groupname})
#
#     return render(request, 'groups/groups_edit_privileges.html', {
#         'form': form,
#         'group_name': group_name,
#         'group_log': group_log,
#         'tables': tables,
#         'granted_tables': granted_tables
#     })
