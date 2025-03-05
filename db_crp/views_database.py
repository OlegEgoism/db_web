from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.db.backends.postgresql.base import DatabaseWrapper
from django.conf import settings
from .audit_views import connect_data_base_success, create_audit_log, delete_data_base_success, delete_data_base_error
from .forms import DatabaseConnectForm
from .models import ConnectingDB
from django.db import connection

def database_list(request):
    """Список баз данных с их размером"""
    databases = ConnectingDB.objects.all()
    databases_info = []
    for db in databases:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT pg_size_pretty(pg_database_size('{db.name_db}'));")
                db_size = cursor.fetchone()[0] if cursor.rowcount > 0 else "Неизвестно"
        except Exception:
            db_size = "Ошибка"
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
        'PASSWORD': connection_info.password_db,
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
