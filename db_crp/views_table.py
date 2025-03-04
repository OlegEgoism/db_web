from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.db.backends.postgresql.base import DatabaseWrapper
from django.conf import settings

from .forms import DatabaseConnectForm
from .models import ConnectingDB


def database_list(request):
    """Список баз данных"""
    databases = ConnectingDB.objects.all()
    return render(request, "databases/database_list.html", {"databases": databases})


def tables_list(request, db_id):
    """Список таблиц в выбранной базе данных"""
    connection_info = get_object_or_404(ConnectingDB, id=db_id)
    temp_db_settings = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': connection_info.name_db,
        'USER': connection_info.user_db,
        'PASSWORD': connection_info.password_db,
        'HOST': connection_info.host_db,
        'PORT': connection_info.port_db,
        'ATOMIC_REQUESTS': False,
        'OPTIONS': {},
        'TIME_ZONE': settings.TIME_ZONE,
        'CONN_HEALTH_CHECKS': False,
        'CONN_MAX_AGE': 0,
        'AUTOCOMMIT': True,
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
    if request.method == "POST":
        form = DatabaseConnectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Подключение успешно сохранено!")
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
