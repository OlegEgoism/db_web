from django.contrib import admin
from django.utils.safestring import mark_safe

from db_crp.models import CustomUser, GroupLog, UserLog


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    """Пользователь"""
    fieldsets = (
        ('ЛИЧНЫЕ ДАННЫЕ', {
            'fields': ('username', 'preview_photo', 'photo', 'email', 'phone_number', 'last_login', 'date_joined',)},),
        ('РАЗРЕШЕНИЯ', {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)}),
    )
    list_display = 'username', 'preview_photo', 'email', 'phone_number', 'last_login', 'is_active',
    list_filter = 'is_staff', 'is_active', 'date_joined',
    list_editable = 'is_active',
    search_fields = 'username', 'email', 'phone_number',
    search_help_text = 'Поиск по имени пользователя, адресу электронной почты и номеру телефона'
    readonly_fields = 'last_login', 'date_joined', 'preview_photo',
    date_hierarchy = 'date_joined'
    list_per_page = 20

    def preview_photo(self, obj):
        if obj.photo:
            return mark_safe(f'<img src="{obj.photo.url}" width="80" height="80" style="border-radius: 20%;" />')
        else:
            return 'Нет фотографии'

    preview_photo.short_description = 'Фотография'

    def save_model(self, request, obj, form, change):
        """Проверка, есть ли еще один пользователь с таким же адресом электронной почты"""
        if obj.email:
            if CustomUser.objects.filter(email=obj.email).exclude(pk=obj.pk).exists():
                self.message_user(request, "Этот адрес электронной почты уже связан с другим аккаунтом", level='ERROR')
                return
        super().save_model(request, obj, form, change)


@admin.register(GroupLog)
class GroupLogAdmin(admin.ModelAdmin):
    """Логи групп"""
    list_display = 'groupname', 'created_at', 'updated_at'
    search_fields = 'groupname',
    search_help_text = 'Поиск по имени группы'
    list_per_page = 20


@admin.register(UserLog)
class UserLogAdmin(admin.ModelAdmin):
    """Логи пользователей"""
    list_display = 'username', 'email', 'created_at', 'updated_at'
    search_fields = 'username', 'email',
    search_help_text = 'Поиск по имени пользователя и адресу электронной почты'
    list_per_page = 20
