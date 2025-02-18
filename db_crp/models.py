from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.timezone import now


class CustomUser(AbstractUser):
    """Пользователь"""
    photo = models.ImageField(verbose_name="Фото", upload_to='user_photo/', default='user_photo/default.png', blank=True, null=True)
    phone_number = models.CharField(verbose_name="Телефон", max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class GroupLog(models.Model):
    """Логи групп"""
    groupname = models.CharField(verbose_name="Имя группы", max_length=100, unique=True)
    created_at = models.DateTimeField(verbose_name="Дата создания", default=timezone.now)
    updated_at = models.DateTimeField(verbose_name="Дата последнего изменения", auto_now=True)

    def __str__(self):
        return self.groupname

    class Meta:
        verbose_name = "Лог группы"
        verbose_name_plural = "Логи групп"


class UserLog(models.Model):
    """Логи пользователей"""
    username = models.CharField(verbose_name="Имя пользователя", max_length=150, unique=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True, unique=True)
    created_at = models.DateTimeField(verbose_name="Дата создания", default=timezone.now)
    updated_at = models.DateTimeField(verbose_name="Дата последнего изменения", auto_now=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Лог пользователя"
        verbose_name_plural = "Логи пользователей"


class Audit(models.Model):
    """Журнал действий"""
    ACTION_TYPES = [
        ('create', 'Создание'),
        ('update', 'Обновление'),
        ('delete', 'Удаление'),
        ('register', 'Регистрация пользователя')
    ]

    ENTITY_TYPES = [
        ('user', 'Пользователь'),
        ('group', 'Группа'),
        ('other', 'Другое'),
    ]

    username = models.CharField(verbose_name="Имя пользователя", max_length=150)
    action_type = models.CharField(verbose_name="Тип действия", max_length=10, choices=ACTION_TYPES)
    entity_type = models.CharField(verbose_name="Тип объекта", max_length=10, choices=ENTITY_TYPES)
    entity_name = models.CharField(verbose_name="Имя объекта", max_length=150, blank=True, null=True)
    timestamp = models.DateTimeField(verbose_name="Дата и время", default=now)
    details = models.TextField(verbose_name="Подробности", blank=True, null=True)

    def __str__(self):
        return f"{self.timestamp} - {self.username} {self.get_action_type_display()} {self.get_entity_type_display()} '{self.entity_name}'"

    class Meta:
        verbose_name = "Журнал действий"
        verbose_name_plural = "Журнал действий"
