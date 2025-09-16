from django.contrib import admin

from apps.catalog.models import MasterCategory, SubCategory, ArticleType


@admin.register(MasterCategory)
class MasterCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'subcategories_count')
    list_filter = ('name',)
    search_fields = ('name', 'slug')
    readonly_fields = ('slug',)
    ordering = ('name',)

    def subcategories_count(self, obj):
        return obj.sub_categories.count()

    subcategories_count.short_description = 'Sub Categories'


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'master_category', 'slug', 'article_types_count')
    list_filter = ('master_category',)
    search_fields = ('name', 'slug', 'master_category__name')
    readonly_fields = ('slug',)
    ordering = ('master_category__name', 'name')

    def article_types_count(self, obj):
        return obj.article_types.count()

    article_types_count.short_description = 'Article Types'


@admin.register(ArticleType)
class ArticleTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'sub_category', 'master_category_name', 'slug', 'products_count')
    list_filter = ('sub_category__master_category', 'sub_category')
    search_fields = ('name', 'slug', 'sub_category__name', 'sub_category__master_category__name')
    readonly_fields = ('slug',)
    ordering = ('sub_category__master_category__name', 'sub_category__name', 'name')

    def master_category_name(self, obj):
        return obj.sub_category.master_category.name

    master_category_name.short_description = 'Master Category'

    def products_count(self, obj):
        return obj.products.count()

    products_count.short_description = 'Products'
