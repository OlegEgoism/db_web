from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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
