from django.db import models
from django.contrib.auth.models import User

from . import models_bav

# Create your models here.

# from .models_bav import *

class UserSettings(models.Model):
    lng_EN = 'en'
    lng_RU = 'ru'
    LNG_CHOISES = [
        (lng_EN, 'EN'),
        (lng_RU, 'RU'),
    ]

    # В модели ты указал related_name='settings', что означает, что через объект пользователя (User) 
    # ты можешь напрямую получить доступ к связанному объекту UserSettings через settings.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    language = models.CharField(max_length=2, choices=LNG_CHOISES, default=lng_EN)
    age = models.IntegerField(null=True, blank=True)           # age не имеет NOT NULL, допускаем null
    ai_usage = models.IntegerField(default=0)                  # NOT NULL и DEFAULT 0
    page_size = models.IntegerField(default=12)                # NOT NULL и DEFAULT 15
    page_buttons = models.IntegerField(default=4)                # NOT NULL и DEFAULT 15
    model_name = models.CharField(max_length=255, default="")  # NOT NULL, поэтому default=""
    models_date = models.DateField(null=True, blank=True)
    model_temp = models.FloatField(null=True, blank=True)      # Поле с типом REAL, допускаем null
    model_top_p = models.FloatField(null=True, blank=True)     # Поле с типом REAL, допускаем null

    def __str__(self):
        return f"{self.user.username}"
    

class Mixtures(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mixtures')
    name = models.CharField(max_length=255)  # Название смеси

    class Meta:
        db_table = 'Mixtures'

# Модель MixtureList, связывающая Mixtures и Plants
class MixtureList(models.Model):
    mixture = models.ForeignKey(Mixtures, on_delete=models.CASCADE)  # Внешний ключ на Mixtures
    # plant = models.ForeignKey(models_bav.Plants, on_delete=models.DO_NOTHING)  # Внешний ключ на Plants из базы 'bav'
    plant_id = models.IntegerField(null=True, blank=True)  # Храним только идентификатор Plant
    selected = models.BooleanField(default=True)  # Поле булевого типа, по умолчанию True

    class Meta:
        db_table = 'MixtureList'
