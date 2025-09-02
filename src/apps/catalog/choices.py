from django.db import models


class GenderChoices(models.TextChoices):
    MEN = 'Men', 'Men'
    WOMEN = 'Women', 'Women'
    BOYS = 'Boys', 'Boys'
    GIRLS = 'Girls', 'Girls'
    UNISEX = 'Unisex', 'Unisex'


class SeasonChoices(models.TextChoices):
    SUMMER = 'Summer', 'Summer'
    WINTER = 'Winter', 'Winter'
    SPRING = 'Spring', 'Spring'
    FALL = 'Fall', 'Fall'
