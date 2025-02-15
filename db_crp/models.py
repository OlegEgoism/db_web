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
    groupname = models.CharField(max_length=100, unique=True, verbose_name="Имя группы")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата последнего изменения")

    def __str__(self):
        return self.groupname

    class Meta:
        verbose_name = "Лог группы"
        verbose_name_plural = "Логи групп"
