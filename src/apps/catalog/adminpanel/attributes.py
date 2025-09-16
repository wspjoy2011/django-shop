from django.contrib import admin

from apps.catalog.models import BaseColour, Season, UsageType


@admin.register(BaseColour)
class BaseColourAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'products_count')
    search_fields = ('name', 'slug')
    readonly_fields = ('slug',)
    ordering = ('name',)

    def products_count(self, obj):
        return obj.products.count()

    products_count.short_description = 'Products'


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'products_count')
    list_filter = ('name',)
    search_fields = ('name', 'slug')
    readonly_fields = ('slug',)
    ordering = ('name',)

    def products_count(self, obj):
        return obj.products.count()

    products_count.short_description = 'Products'


@admin.register(UsageType)
class UsageTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'products_count')
    search_fields = ('name', 'slug')
    readonly_fields = ('slug',)
    ordering = ('name',)

    def products_count(self, obj):
        return obj.products.count()

    products_count.short_description = 'Products'
