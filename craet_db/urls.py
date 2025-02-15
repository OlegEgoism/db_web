"""
URL configuration for craet_db project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from db_crp.views import (
    home,

    register,
    logout_view,

    group_list,
    group_create,
    group_edit,
    group_delete,
    group_users,

    user_list,
    user_create,
    user_info,
    user_change_password,
    user_add_to_group,
    user_delete,

    # users_with_groups,
    # create_table,
)

urlpatterns = [
    # Админка
    path('admin/', admin.site.urls),
    # Главная
    path('', home, name='home'),
    # Регистрация пользователя
    path('register/', register, name='register'),
    # Вход пользователя
    path('login/', auth_views.LoginView.as_view(), name='login'),
    # Выход пользователя
    path('logout/', logout_view, name='logout'),

    # Список групп
    path('group_list/', group_list, name='group_list'),
    # Создание группы
    path('group_create/', group_create, name='group_create'),
    # Редактирование группы
    path('groups/edit/<str:group_name>/', group_edit, name='group_edit'),
    # Удаление группы
    path('group_delete/<str:group_name>/', group_delete, name='group_delete'),
    # Пользователи в группе
    path('group_users/<str:group_name>/', group_users, name='group_users'),




    path('user_list/', user_list, name='user_list'),  # Список пользователей
    path('user_create/', user_create, name='user_create'),  # Создать пользователя
    path('user_info/<str:username>/', user_info, name='user_info'),  # Информация о пользователе
    path('user_change_password/<str:username>/', user_change_password, name='user_change_password'),  # Сменить пароль
    path('user_add_to_group/', user_add_to_group, name='user_add_to_group'),  # Добавление удаление пользователя в группы
    path('user_delete/<str:username>/', user_delete, name='user_delete'),  # Удаление пользователя

    # path('users_with_groups/', users_with_groups, name='users_with_groups'),
    # # path('user_groups/', user_groups, name='user_groups'),  # Список групп пользователей в базе данных
    #
    # path('create_table/', create_table, name='create_table'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
