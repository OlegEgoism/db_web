from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.db.backends.postgresql.base import DatabaseWrapper
from django.conf import settings
from .audit_views import connect_data_base_success, create_audit_log, delete_data_base_success, delete_data_base_error
from .forms import DatabaseConnectForm
from .models import ConnectingDB, UserLog, GroupLog
from django.db import connection
from django.db import transaction


def database_list(request):
    """Список баз данных с их размером"""
    databases = ConnectingDB.objects.all()
    databases_info = []
    for db in databases:
        try:
            with transaction.atomic():  # Используем atomic() для управления транзакцией
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT pg_size_pretty(pg_database_size(%s));", [db.name_db])
                    db_size = cursor.fetchone()[0] if cursor.rowcount > 0 else "Неизвестно"
        except Exception as e:
            db_size = f"Ошибка: {str(e)}"
        databases_info.append({
            "db": db,
            "size": db_size
        })
    return render(request, "databases/database_list.html", {"databases_info": databases_info})


def tables_list(request, db_id):
    """Список таблиц в выбранной базе данных"""
    connection_info = get_object_or_404(ConnectingDB, id=db_id)
    db_settings = settings.DATABASES.get('default', {})
    temp_db_settings = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': connection_info.name_db,
        'USER': connection_info.user_db,
        'PASSWORD': connection_info.get_decrypted_password(),
        'HOST': connection_info.host_db,
        'PORT': connection_info.port_db,
        'ATOMIC_REQUESTS': db_settings.get('ATOMIC_REQUESTS'),
        'CONN_HEALTH_CHECKS': db_settings.get('CONN_HEALTH_CHECKS'),
        'CONN_MAX_AGE': db_settings.get('CONN_MAX_AGE'),
        'AUTOCOMMIT': db_settings.get('AUTOCOMMIT'),
        'OPTIONS': db_settings.get('OPTIONS'),
        'TIME_ZONE': db_settings.get('TIME_ZONE'),
    }
    temp_connection = DatabaseWrapper(temp_db_settings, alias="temp_connection")
    temp_connection.connect()
    tables_info = []
    db_size = "Неизвестно"
    try:
        with temp_connection.cursor() as cursor:
            cursor.execute("""
                    SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size('"' || schemaname || '"."' || tablename || '"'))
                    FROM pg_catalog.pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
                """)
            tables_info = [{"schema": row[0], "name": row[1], "size": row[2]} for row in cursor.fetchall()]
            cursor.execute(f"SELECT pg_size_pretty(pg_database_size('{connection_info.name_db}'));")
            db_size = cursor.fetchone()[0]
    except Exception as e:
        tables_info = [{"name": f"Ошибка: {str(e)}", "size": "—"}]
    finally:
        temp_connection.close()
    return render(request, "databases/tables_info.html", {
        "db_name": connection_info.name_db,
        "db_size": db_size,
        "tables_info": tables_info,
    })


def database_connect(request):
    """Подключение к базе данных"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    if request.method == "POST":
        form = DatabaseConnectForm(request.POST)
        if form.is_valid():
            form.save()
            name_db = form.cleaned_data['name_db']
            user_db = form.cleaned_data['user_db']
            port_db = form.cleaned_data['port_db']
            host_db = form.cleaned_data['host_db']
            message = connect_data_base_success(name_db, user_db, port_db, host_db)
            messages.success(request, message)
            create_audit_log(user_requester, 'create', 'database', name_db, message)
            return redirect('database_list')
    else:
        form = DatabaseConnectForm()
    return render(request, "databases/database_connect.html", {"form": form})


def database_edit(request, db_id):
    """Редактирование подключения к базе данных"""
    database = get_object_or_404(ConnectingDB, id=db_id)
    if request.method == "POST":
        form = DatabaseConnectForm(request.POST, instance=database)
        if form.is_valid():
            form.save()
            messages.success(request, "Подключение успешно обновлено!")
            return redirect('database_list')
    else:
        form = DatabaseConnectForm(instance=database)
    return render(request, "databases/database_edit.html", {"form": form, "database": database})


def database_delete(request, db_id):
    """Удаление подключения к базе данных"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    database = get_object_or_404(ConnectingDB, id=db_id)
    name_db = database.name_db
    user_db = database.user_db
    port_db = database.port_db
    host_db = database.host_db
    try:
        database.delete()
        message = delete_data_base_success(name_db, user_db, port_db, host_db)
        messages.success(request, message)
        create_audit_log(user_requester, 'delete', 'database', name_db, message)
    except Exception:
        message = delete_data_base_error(name_db, user_db, port_db, host_db)
        messages.success(request, message)
        create_audit_log(user_requester, 'delete', 'database', name_db, message)
    return redirect('database_list')


from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.backends.postgresql.base import DatabaseWrapper
from django.conf import settings
from .models import ConnectingDB, UserLog, GroupLog
import psycopg2


def sync_users_and_groups(request, db_id):
    """Синхронизация пользователей и групп из базы данных"""
    connection_info = ConnectingDB.objects.get(id=db_id)

    # Настройки подключения
    temp_db_settings = {
        'dbname': connection_info.name_db,
        'user': connection_info.user_db,
        'password': connection_info.get_decrypted_password(),
        'host': connection_info.host_db,
        'port': connection_info.port_db,
    }

    try:
        # Подключение к базе данных
        conn = psycopg2.connect(**temp_db_settings)
        cursor = conn.cursor()

        # Получение списка пользователей и их привилегий
        cursor.execute("""
            SELECT
                rolname,       -- Имя пользователя
                rolcreatedb,   -- Может создавать БД
                rolsuper,      -- Суперпользователь
                rolinherit,    -- Наследование прав
                rolcreaterole, -- Может создавать роли
                rolcanlogin,   -- Может входить в систему
                rolreplication,-- Репликация
                rolbypassrls   -- Обход Row-Level Security
            FROM pg_catalog.pg_roles;
        """)
        users = cursor.fetchall()

        # Очистка таблицы перед записью новых данных
        UserLog.objects.all().delete()
        for user in users:
            (
                username, can_create_db, is_superuser,
                inherit, create_role, login, replication, bypass_rls
            ) = user
            UserLog.objects.create(
                username=username,
                can_create_db=can_create_db,
                is_superuser=is_superuser,
                inherit=inherit,
                create_role=create_role,
                login=login,
                replication=replication,
                bypass_rls=bypass_rls,
            )
        cursor.execute("""
            SELECT groname FROM pg_catalog.pg_group;
        """)
        groups = cursor.fetchall()
        GroupLog.objects.all().delete()
        for group in groups:
            GroupLog.objects.create(groupname=group[0])
        messages.success(request, "Синхронизация завершена успешно.")
    except Exception as e:
        messages.error(request, f"Ошибка синхронизации: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect("database_list")  # Или перенаправить на страницу с логами
