from django.shortcuts import render, redirect
from django.db import connection, connections
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from db_crp.forms import GrantPrivilegesForm


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




from django.db import connection

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
