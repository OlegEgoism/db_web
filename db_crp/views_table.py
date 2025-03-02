from django.shortcuts import render, get_object_or_404
from django.db.backends.postgresql.base import DatabaseWrapper
from django.conf import settings
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
    try:
        with temp_connection.cursor() as cursor:
            cursor.execute("""
                SELECT schemaname, tablename 
                FROM pg_catalog.pg_tables 
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
            """)
            tables = [f"{schema}.{table}" for schema, table in cursor.fetchall()]
    except Exception as e:
        tables = [f"Ошибка: {str(e)}"]
    finally:
        temp_connection.close()
    return render(request, "databases/tables_info.html", {"db_name": connection_info.name_db, "tables": tables})
