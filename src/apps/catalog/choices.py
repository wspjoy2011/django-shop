from django.db import models


class GenderChoices(models.TextChoices):
    """
    Enumeration of gender options used for classifying products
    by their intended audience.
    """

    MEN = 'Men', 'Men'
    WOMEN = 'Women', 'Women'
    BOYS = 'Boys', 'Boys'
    GIRLS = 'Girls', 'Girls'
    UNISEX = 'Unisex', 'Unisex'


class SeasonChoices(models.TextChoices):
    """
    Enumeration of seasonal options representing the intended
    season of use for a product.
    """

    SUMMER = 'Summer', 'Summer'
    WINTER = 'Winter', 'Winter'
    SPRING = 'Spring', 'Spring'
    FALL = 'Fall', 'Fall'
