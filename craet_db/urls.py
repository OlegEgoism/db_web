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

from db_crp.views import (
    user_list,
    user_create,
    user_change_password,
    user_delete,
    user_info,
    user_add_to_group,
    create_group,

    user_groups,
    users_with_groups,
    create_table,

)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('user_list/', user_list, name='user_list'),  # Список пользователей в базе данных
    path('user_create/', user_create, name='user_create'),  # Создать нового пользователя в базе данных
    path('user_change_password/<str:username>/', user_change_password, name='user_change_password'),  # Сменить пароль пользователя в базе данных
    path('user_delete/<str:username>/', user_delete, name='user_delete'),  # Удалить пользователя из базы данных
    path('user_info/<str:username>/', user_info, name='user_info'),  # Информация о пользователе из базы данных
    path('user_add_to_group/', user_add_to_group, name='user_add_to_group'),  # Добавления пользователя в группы
    path('create_group/', create_group, name='create_group'),  # Создание новой группы в базе данных



    path('users_with_groups/', users_with_groups, name='users_with_groups'),
    path('user_groups/', user_groups, name='user_groups'),  # Список групп пользователей в базе данных

    path('create_table/', create_table, name='create_table'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
