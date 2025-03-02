from django.shortcuts import redirect
from django.db import connections, connection
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from db_crp.forms import GrantPrivilegesForm
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








# def get_databases():
#     """Получает список всех баз данных, используя подключение к postgres"""
#     temp_db_settings = settings.DATABASES['default'].copy()
#     temp_db_settings['NAME'] = 'postgres'  # Переключаемся на postgres
#
#     # Временное подключение
#     connections.databases['temp_db'] = temp_db_settings
#
#     try:
#         with connections['temp_db'].cursor() as cursor:
#             cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
#             return [db[0] for db in cursor.fetchall()]
#     except Exception as e:
#         return [f"Ошибка: {str(e)}"]
#     finally:
#         connections['temp_db'].close()  # Закрываем соединение
#
#
# def get_tables_from_database(db_name):
#     """Получает список таблиц из указанной базы данных, используя подключение к postgres"""
#     temp_db_settings = settings.DATABASES['default'].copy()
#     temp_db_settings['NAME'] = db_name  # Подключаемся к нужной базе
#
#     connections.databases['temp_db'] = temp_db_settings
#
#     try:
#         with connections['temp_db'].cursor() as cursor:
#             cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public';")
#             return [table[0] for table in cursor.fetchall()]
#     except Exception as e:
#         return [f"Ошибка: {str(e)}"]
#     finally:
#         connections['temp_db'].close()  # Закрываем соединение
#
#
# def database_info(request):
#     """Страница со списком всех баз данных (получаем их из postgres)"""
#     databases = get_databases()
#     return render(request, "database_info.html", {"databases": databases})
#
#
# def tables_in_database(request, db_name):
#     """Страница со списком таблиц для конкретной базы данных"""
#     tables = get_tables_from_database(db_name)
#     return render(request, "tables_info.html", {"db_name": db_name, "tables": tables})


@login_required
def databases_and_tables_list(request):
    """Отображение всех баз данных и их таблиц в PostgreSQL"""
    databases_with_tables = []

    try:
        # Получение списка всех баз данных
        with connection.cursor() as cursor:
            cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
            databases = [row[0] for row in cursor.fetchall()]

        # Для каждой базы данных получаем таблицы
        for db_name in databases:
            if not db_name.startswith('postgres'):
                tables = []
                try:
                    # Динамическое подключение к каждой базе данных
                    with connections['default'].cursor() as cursor:
                        cursor.execute(f"SET search_path TO {db_name};")
                        cursor.execute("""
                            SELECT table_schema, table_name 
                            FROM information_schema.tables 
                            WHERE table_type = 'BASE TABLE' 
                              AND table_schema NOT IN ('pg_catalog', 'information_schema');
                        """)
                        tables = [{'schema': row[0], 'table_name': row[1]} for row in cursor.fetchall()]

                    databases_with_tables.append({'database': db_name, 'tables': tables})

                except Exception as e:
                    messages.error(request, f'Ошибка при получении таблиц из базы данных {db_name}: {str(e)}')

        return render(request, 'tables/databases_and_tables_list.html', {'databases_with_tables': databases_with_tables})

    except Exception as e:
        messages.error(request, f'Ошибка при получении списка баз данных: {str(e)}')
        return render(request, 'tables/databases_and_tables_list.html', {'databases_with_tables': []})


def grant_table_privileges_to_role(role_name, table_name, schema='public', privileges=('SELECT',)):
    """
    Назначение привилегий на таблицу для роли
    """
    privileges_str = ', '.join(privileges)
    sql = f'GRANT {privileges_str} ON TABLE {schema}.{table_name} TO {role_name};'
    with connection.cursor() as cursor:
        cursor.execute(sql)


def revoke_table_privileges_from_role(role_name, table_name, schema='public', privileges=('SELECT',)):
    """
    Отзыв привилегий на таблицу у роли
    """
    privileges_str = ', '.join(privileges)
    sql = f'REVOKE {privileges_str} ON TABLE {schema}.{table_name} FROM {role_name};'
    with connection.cursor() as cursor:
        cursor.execute(sql)


@login_required
def grant_privileges_view(request):
    if request.method == 'POST':
        form = GrantPrivilegesForm(request.POST)
        if form.is_valid():
            role_name = form.cleaned_data['role_name']
            table_name = form.cleaned_data['table_name']
            privileges = form.cleaned_data['privileges']

            try:
                grant_table_privileges_to_role(role_name, table_name, privileges=privileges)
                messages.success(request, f'Привилегии успешно назначены роли {role_name} на таблицу {table_name}.')
            except Exception as e:
                messages.error(request, f'Ошибка при назначении привилегий: {e}')

            return redirect('home')
    else:
        form = GrantPrivilegesForm()

    return render(request, 'grant_privileges.html', {'form': form})
