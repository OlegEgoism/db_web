from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from .audit_views import group_data, create_audit_log, delete_group_messages_success, delete_group_messages_error, create_group_messages_error, create_group_messages_error_pg, edit_group_messages_group_success, create_group_messages_error_info
from .forms import CreateGroupForm, GroupEditForm
from django.shortcuts import render, redirect
from .models import GroupLog, Audit
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


@login_required
def group_edit(request, group_name):
    """Редактирование группы"""
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
    if request.method == "POST":
        form = GroupEditForm(request.POST)
        if form.is_valid():
            new_groupname = form.cleaned_data['groupname']
            if new_groupname.startswith('pg_'):
                messages.error(request, f"Неудачная попытка переименовать группу с '{group_name}' в '{new_groupname}', запрещенный префикс 'pg_'.")
                Audit.objects.create(
                    username=user_requester,
                    action_type='update',
                    entity_type='group',
                    entity_name=group_name,
                    timestamp=now(),
                    details=f"Неудачная попытка переименовать группу с '{group_name}' в '{new_groupname}', запрещенный префикс 'pg_'"
                )
                return render(request, 'groups/group_edit.html', {
                    'form': form,
                    'group_name': group_name,
                    'group_log': group_log
                })
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [new_groupname])
                existing_group = cursor.fetchone()
            if existing_group:
                messages.error(request, f"Неудачная попытка переименовать группу с '{group_name}' в '{new_groupname}', группа уже существует.")
                Audit.objects.create(
                    username=user_requester,
                    action_type='update',
                    entity_type='group',
                    entity_name=group_name,
                    timestamp=now(),
                    details=f"Неудачная попытка переименовать группу с '{group_name}' в '{new_groupname}', группа уже существует."
                )
                return render(request, 'groups/group_edit.html', {
                    'form': form,
                    'group_name': group_name,
                    'group_log': group_log
                })
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"ALTER ROLE {group_name} RENAME TO {new_groupname};")
                group_log.groupname = new_groupname
                group_log.updated_at = timezone.now()
                group_log.save()
                messages.success(request, f"Группа '{group_name}' успешно переименована в '{new_groupname}'.")
                Audit.objects.create(
                    username=user_requester,
                    action_type='update',
                    entity_type='group',
                    entity_name=new_groupname,
                    timestamp=now(),
                    details=f"Группа '{group_name}' успешно переименована в '{new_groupname}'."
                )

                return redirect('group_list')
            except Exception as e:
                messages.error(request, f"Ошибка при редактировании группы: {e}")
                Audit.objects.create(
                    username=user_requester,
                    action_type='update',
                    entity_type='group',
                    entity_name=group_name,
                    timestamp=now(),
                    details=f"Ошибка при редактировании группы '{group_name}': {str(e)}"
                )
    else:
        form = GroupEditForm(initial={'groupname': group_log.groupname})
    return render(request, 'groups/group_edit.html', {
        'form': form,
        'group_name': group_name,
        'group_log': group_log
    })


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
