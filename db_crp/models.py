from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Пользователь"""
    photo = models.ImageField(verbose_name="Фото", upload_to='user_photo/', default='user_photo/default.png', blank=True, null=True)
    phone_number = models.CharField(verbose_name="Телефон", max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


# class InfoUserDataBase(models.Model):
#     user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
#     db_date_create = models.DateTimeField(verbose_name="Дата создания", auto_now_add=True)
#     db_date_edit = models.DateTimeField(verbose_name="Дата изменения", auto_now=True)