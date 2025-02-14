from django.contrib import messages
from django.contrib.auth import login, logout
from django.db import connection
from django.http import HttpResponse
from .forms import TableCreateForm, UserCreateForm, ChangePasswordForm, AddUserToGroupForm, CreateGroupForm, CustomUserRegistrationForm
from django.shortcuts import render, redirect


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


# TODO
def user_list(request):
    """Список пользователей в базе данных"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT usename FROM pg_user;")
        users = cursor.fetchall()
    user_names = [user[0] for user in users]
    return render(request, 'users/user_list.html', {'users': user_names})


def group_list(request):
    """Список групп в базе данных"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT groname FROM pg_group;")
        groups = cursor.fetchall()
    group_names = [group[0] for group in groups]

    system_groups = [g for g in group_names if g.startswith('pg_')]
    user_groups = [g for g in group_names if not g.startswith('pg_')]

    return render(request, 'users/group_list.html', {
        'system_groups': system_groups,
        'user_groups': user_groups
    })

def group_users(request, group_name):
    """Cписок пользователей в выбранной группе"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT usename FROM pg_user JOIN pg_group ON (pg_user.usesysid = ANY(pg_group.grolist)) WHERE groname = %s;", [group_name])
        users = cursor.fetchall()
    user_names = [user[0] for user in users]

    return render(request, 'users/group_users.html', {
        'group_name': group_name,
        'users': user_names
    })


def group_users(request, group_name):
    """Отобразить список пользователей в выбранной группе"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT usename FROM pg_user JOIN pg_group ON (pg_user.usesysid = ANY(pg_group.grolist)) WHERE groname = %s;", [group_name])
        users = cursor.fetchall()
    user_names = [user[0] for user in users]

    return render(request, 'users/group_users.html', {
        'group_name': group_name,
        'users': user_names
    })


def user_create(request):
    """Создать нового пользователя в базе данных"""
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            query = f"CREATE USER {username} WITH PASSWORD %s;"
            with connection.cursor() as cursor:
                cursor.execute(query, [password])
            return redirect('user_list')
    else:
        form = UserCreateForm()
    return render(request, 'users/user_create.html', {'form': form})


def user_change_password(request, username):
    """Сменить пароль пользователя в базе данных"""
    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            query = f"ALTER USER {username} WITH PASSWORD %s;"
            with connection.cursor() as cursor:
                cursor.execute(query, [new_password])
            return redirect('user_list')
    else:
        form = ChangePasswordForm(initial={'username': username})
    return render(request, 'users/user_change_password.html', {'form': form, 'username': username})


def user_delete(request, username):
    """Удалить пользователя в базе данных"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP USER IF EXISTS {username};")
        return redirect('user_list')
    except Exception as e:
        return HttpResponse(f"Ошибка при удалении пользователя: {e}")


def user_info(request, username):
    """Информация о пользователе из базы данных"""
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
    if user_info:
        user_data = {
            'username': user_info[0],
            'user_id': user_info[1],
            'can_create_db': user_info[2],
            'is_superuser': user_info[3],
            'password_hash': user_info[4],
            'valid_until': user_info[5],
            'groups': [group[0] for group in groups],
        }
    else:
        user_data = None
    return render(request, 'users/user_info.html', {'user_data': user_data})


# def user_add_to_group(request):
#     """Добавления пользователя в группы"""
#     if request.method == "POST":
#         form = AddUserToGroupForm(request.POST)
#         if form.is_valid():
#             username = form.cleaned_data['username']
#             groupname = form.cleaned_data['groupname']
#             if groupname.startswith('pg_'):
#                 return HttpResponse(f"⚠️ Ошибка: Нельзя добавить пользователя в системную группу '{groupname}'")
#             query = f"GRANT {groupname} TO {username};"
#             try:
#                 with connection.cursor() as cursor:
#                     cursor.execute(query)  # Выполняем SQL-запрос
#                 return redirect('user_list')  # Перенаправляем на список пользователей
#             except Exception as e:
#                 return HttpResponse(f"Ошибка при добавлении в группу: {e}")
#     else:
#         form = AddUserToGroupForm()
#     return render(request, 'users/user_add_to_group.html', {'form': form})


from django.shortcuts import render, redirect
from django.db import connection
from django.http import HttpResponse


def user_add_to_group(request):
    """Добавление или удаление пользователя из групп"""
    username = request.GET.get('username')

    # Получаем список групп
    all_groups = set()
    user_groups = set()

    with connection.cursor() as cursor:
        # Получаем все доступные группы (кроме системных)
        cursor.execute("""
            SELECT rolname 
            FROM pg_roles 
            WHERE rolcanlogin = FALSE AND rolname NOT LIKE 'pg_%';
        """)
        all_groups = {group[0] for group in cursor.fetchall()}

        # Получаем группы пользователя
        cursor.execute("""
            SELECT r.rolname
            FROM pg_user u
            JOIN pg_auth_members m ON u.usesysid = m.member
            JOIN pg_roles r ON m.roleid = r.oid
            WHERE u.usename = %s;
        """, [username])
        user_groups = {group[0] for group in cursor.fetchall()}

    # Определяем группы, которых у пользователя нет
    available_groups = all_groups - user_groups

    if request.method == "POST":
        # Получаем группы для добавления
        selected_groups = request.POST.get('selected_groups').split(',')
        selected_groups = [group.strip() for group in selected_groups if group.strip()]

        # Получаем группы для удаления
        deleted_groups = request.POST.get('deleted_groups').split(',')
        deleted_groups = [group.strip() for group in deleted_groups if group.strip()]

        errors = []

        # Удаляем группы
        for groupname in deleted_groups:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"REVOKE {groupname} FROM {username};")
            except Exception as e:
                errors.append(f"Ошибка при удалении группы '{groupname}': {e}")

        # Добавляем выбранные группы
        for groupname in selected_groups:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"GRANT {groupname} TO {username};")
            except Exception as e:
                errors.append(f"Ошибка при добавлении группы '{groupname}': {e}")

        if errors:
            return HttpResponse("<br>".join(errors))
        return redirect('user_list')

    return render(request, 'users/user_add_to_group.html', {
        'username': username,
        'user_groups': sorted(user_groups),
        'available_groups': sorted(available_groups),
    })


def create_group(request):
    """Создание новой группы в базе данных"""
    if request.method == "POST":
        form = CreateGroupForm(request.POST)
        if form.is_valid():
            groupname = form.cleaned_data['groupname']
            if groupname.startswith('pg_'):
                return HttpResponse("⚠️ Ошибка: Имя группы не может начинаться с 'pg_', так как это зарезервировано системой.")
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"CREATE ROLE {groupname};")
                return redirect('user_list')
            except Exception as e:
                return HttpResponse(f"Ошибка при создании группы: {e}")
    else:
        form = CreateGroupForm()
    return render(request, 'users/create_group.html', {'form': form})


# TODO


def users_with_groups(request):
    """Пользователи и их группы"""
    query = """
        SELECT u.usename, g.rolname
        FROM pg_user u
        LEFT JOIN pg_auth_members m ON u.usesysid = m.member
        LEFT JOIN pg_roles g ON m.roleid = g.oid
        ORDER BY u.usename;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        users_groups = cursor.fetchall()
    user_groups_dict = {}
    for username, group in users_groups:
        if username not in user_groups_dict:
            user_groups_dict[username] = []
        if group:
            user_groups_dict[username].append(group)
    return render(request, 'users/users_with_groups.html', {'users_groups': user_groups_dict})


def create_table(request):
    if request.method == "POST":
        form = TableCreateForm(request.POST)
        if form.is_valid():
            table_name = form.cleaned_data['table_name']
            columns = []
            for i in range(1, 6):
                column_name = form.cleaned_data.get(f'column_{i}_name')
                column_type = form.cleaned_data.get(f'column_{i}_type')
                if column_name and column_type:
                    columns.append(f'"{column_name}" {column_type}')
            if columns:
                create_table_sql = f'CREATE TABLE "{table_name}" (id SERIAL PRIMARY KEY, {", ".join(columns)});'
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(create_table_sql)
                    messages.success(request, f'Таблица "{table_name}" успешно создана!')
                except Exception as e:
                    messages.error(request, f'Ошибка: {str(e)}')
            else:
                messages.error(request, "Необходимо указать хотя бы один столбец.")
    else:
        form = TableCreateForm()
    return render(request, 'create_table.html', {'form': form})
