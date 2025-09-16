from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.catalog.models import Product
from apps.favorites.models import FavoriteItem
from apps.ratings.models import Rating, Dislike, Like
from .filters import StockStatusFilter, YearFilter, RatingFilter


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'product_thumbnail',
        'product_display_name_short',
        'product_id',
        'gender_badge',
        'year',
        'category_hierarchy',
        'stock_status_badge',
        'price_display',
        'popularity_stats',
        'created_at_short',
    )

    list_filter = (
        StockStatusFilter,
        'gender',
        YearFilter,
        RatingFilter,
        'article_type__sub_category__master_category',
        'article_type__sub_category',
        'base_colour',
        'season',
        'usage_type',
        'created_at',
    )

    search_fields = (
        'product_display_name',
        'product_id',
        'slug',
        'article_type__name',
        'article_type__sub_category__name',
        'article_type__sub_category__master_category__name',
        'base_colour__name',
    )

    readonly_fields = (
        'slug',
        'product_id',
        'created_at',
        'updated_at',
        'product_image_preview',
        'full_category_path',
        'inventory_details',
        'rating_summary',
        'engagement_stats',
        'favorites_info',
        'view_on_site_link',
    )

    list_per_page = 25
    list_max_show_all = 100

    ordering = ['-year', '-updated_at']

    date_hierarchy = 'created_at'

    actions = ['mark_as_featured', 'bulk_update_season', 'export_selected_products']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'product_image_preview',
                'product_display_name',
                'product_id',
                'slug',
                'image_url',
                'gender',
                'year',
            ),
            'classes': ('wide',),
        }),
        ('Categorization', {
            'fields': (
                'full_category_path',
                'article_type',
                'base_colour',
                'season',
                'usage_type',
            ),
            'classes': ('collapse',),
        }),
        ('Inventory & Pricing', {
            'fields': ('inventory_details',),
            'classes': ('collapse',),
        }),
        ('Engagement & Social', {
            'fields': (
                'rating_summary',
                'engagement_stats',
                'favorites_info',
            ),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
                'view_on_site_link',
            ),
            'classes': ('collapse',),
        }),
    )

    def _get_optimized_queryset(self):
        return (
            Product.objects
            .select_related(
                'article_type',
                'article_type__sub_category',
                'article_type__sub_category__master_category',
                'base_colour',
                'season',
                'usage_type',
                'inventory',
                'inventory__currency',
            )
            .prefetch_related(
                Prefetch(
                    'ratings',
                    queryset=Rating.objects.only('score', 'product_id', 'user_id'),
                    to_attr='ratings_list'
                ),
                Prefetch(
                    'likes',
                    queryset=Like.objects.only('product_id', 'user_id'),
                    to_attr='likes_list'
                ),
                Prefetch(
                    'dislikes',
                    queryset=Dislike.objects.only('product_id', 'user_id'),
                    to_attr='dislikes_list'
                ),
                Prefetch(
                    'favorite_items',
                    queryset=FavoriteItem.objects.select_related('collection__user'),
                    to_attr='favorites_list'
                )
            )
        )

    def get_queryset(self, request):
        return self._get_optimized_queryset()

    def get_object(self, request, object_id, from_field=None):
        queryset = self._get_optimized_queryset()
        model = queryset.model
        field = (
            model._meta.pk if from_field is None else model._meta.get_field(from_field)
        )
        try:
            object_id = field.to_python(object_id)
            return queryset.get(**{field.name: object_id})
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

    @admin.display(description='Image')
    def product_thumbnail(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" title="{}">',
                obj.image_url,
                obj.product_display_name
            )
        return mark_safe(
            '<div style="width: 50px; height: 50px; background: #f0f0f0; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #999;">No Image</div>')

    @admin.display(description='Product Name', ordering='product_display_name')
    def product_display_name_short(self, obj):
        name = obj.product_display_name
        if len(name) > 40:
            return format_html(
                '<span title="{}">{}&hellip;</span>',
                name,
                name[:40]
            )
        return name

    @admin.display(description='Gender', ordering='gender')
    def gender_badge(self, obj):
        colors = {
            'Men': '#2196F3',
            'Women': '#E91E63',
            'Boys': '#4CAF50',
            'Girls': '#FF9800',
            'Unisex': '#9C27B0',
        }
        color = colors.get(obj.gender, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.gender
        )

    @admin.display(description='Category')
    def category_hierarchy(self, obj):
        return format_html(
            '<div style="font-size: 11px; line-height: 1.3;"><strong>{}</strong><br><span style="color: #666;">{} → {}</span></div>',
            obj.article_type.sub_category.master_category.name,
            obj.article_type.sub_category.name,
            obj.article_type.name
        )

    @admin.display(description='Stock')
    def stock_status_badge(self, obj):
        if hasattr(obj, 'inventory') and obj.inventory:
            inv = obj.inventory
            if not inv.is_active:
                return mark_safe('<span style="color: #757575;">Inactive</span>')
            elif inv.stock_quantity == 0:
                return mark_safe('<span style="color: #f44336; font-weight: bold;">Out of Stock</span>')
            elif inv.stock_quantity < 10:
                return format_html('<span style="color: #ff9800; font-weight: bold;">Low ({} left)</span>',
                                   inv.stock_quantity)
            else:
                return format_html('<span style="color: #4caf50; font-weight: bold;">In Stock ({})</span>',
                                   inv.stock_quantity)
        return mark_safe('<span style="color: #757575;">No Inventory</span>')

    @admin.display(description='Price')
    def price_display(self, obj):
        if hasattr(obj, 'inventory') and obj.inventory:
            inv = obj.inventory
            if inv.sale_price:
                return format_html(
                    '<div style="font-size: 11px;"><span style="color: #f44336; font-weight: bold;">${}</span><br><span style="text-decoration: line-through; color: #999;">${}</span></div>',
                    inv.sale_price,
                    inv.base_price
                )
            else:
                return format_html('<strong>${}</strong>', inv.base_price)
        return mark_safe('<span style="color: #757575;">N/A</span>')

    @admin.display(description='Engagement')
    def popularity_stats(self, obj):
        likes = obj.get_likes_count()
        dislikes = obj.get_dislikes_count()
        ratings = obj.get_rating_stats()
        rating_display = f"{ratings['avg_rating']:.1f}" if ratings['ratings_count'] > 0 else "N/A"

        return format_html(
            '<div style="font-size: 10px; line-height: 1.2;"><span style="color: #4caf50;">👍 {}</span> <span style="color: #f44336;">👎 {}</span><br><span style="color: #ff9800;">⭐ {} ({})</span></div>',
            likes,
            dislikes,
            rating_display,
            ratings['ratings_count']
        )

    @admin.display(description='Created', ordering='created_at')
    def created_at_short(self, obj):
        return obj.created_at.strftime('%m/%d/%y')

    @admin.display(description='Product Image')
    def product_image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<div style="text-align: center;"><img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" alt="{}"><br><small style="color: #666; margin-top: 10px; display: inline-block;">Product Image</small></div>',
                obj.image_url,
                obj.product_display_name
            )
        return mark_safe('<p style="color: #999; font-style: italic;">No image available</p>')

    @admin.display(description='Category Path')
    def full_category_path(self, obj):
        return format_html(
            '<div style="font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 4px;">{} → {} → {}</div>',
            obj.article_type.sub_category.master_category.name,
            obj.article_type.sub_category.name,
            obj.article_type.name
        )

    @admin.display(description='Inventory Information')
    def inventory_details(self, obj):
        if hasattr(obj, 'inventory') and obj.inventory:
            inv = obj.inventory
            status_color = '#4caf50' if inv.is_active else '#f44336'
            stock_color = '#4caf50' if inv.stock_quantity > 10 else '#ff9800' if inv.stock_quantity > 0 else '#f44336'
            status_text = 'Active' if inv.is_active else 'Inactive'
            sale_price_text = f'${inv.sale_price}' if inv.sale_price else 'None'

            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid {};"><h4 style="margin: 0 0 10px 0; color: {};">Inventory Status: {}</h4><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;"><div><strong>Base Price:</strong> ${}<br><strong>Sale Price:</strong> {}<br><strong>Currency:</strong> {}</div><div><strong style="color: {};">Stock:</strong> <span style="color: {};">{} units</span><br><strong>Reserved:</strong> {} units<br><strong>Available:</strong> {} units</div></div></div>',
                status_color,
                status_color,
                status_text,
                inv.base_price,
                sale_price_text,
                inv.currency.code,
                stock_color,
                stock_color,
                inv.stock_quantity,
                inv.reserved_quantity,
                inv.available_quantity
            )
        return mark_safe('<p style="color: #999; font-style: italic;">No inventory record found</p>')

    @admin.display(description='Rating Summary')
    def rating_summary(self, obj):
        stats = obj.get_rating_stats()
        if stats['ratings_count'] > 0:
            stars = '⭐' * int(stats['avg_rating'])
            avg_rating_formatted = f"{stats['avg_rating']:.1f}"
            return format_html(
                '<div style="background: #fff3e0; padding: 12px; border-radius: 6px; border-left: 4px solid #ff9800;"><div style="font-size: 16px; margin-bottom: 8px;">{} <strong>{}</strong></div><div style="color: #666; font-size: 14px;">{} ratings total</div></div>',
                stars,
                avg_rating_formatted,
                stats['ratings_count']
            )
        return mark_safe('<p style="color: #999; font-style: italic;">No ratings yet</p>')

    @admin.display(description='Like/Dislike Stats')
    def engagement_stats(self, obj):
        likes = obj.get_likes_count()
        dislikes = obj.get_dislikes_count()
        total_engagement = likes + dislikes

        if total_engagement > 0:
            like_percent = (likes / total_engagement) * 100
            like_percent_formatted = f"{like_percent:.1f}"
            return format_html(
                '<div style="background: #f3e5f5; padding: 12px; border-radius: 6px; border-left: 4px solid #9c27b0;"><div style="display: flex; justify-content: space-between; margin-bottom: 8px;"><span style="color: #4caf50;">👍 {} likes</span><span style="color: #f44336;">👎 {} dislikes</span></div><div style="background: #e0e0e0; height: 6px; border-radius: 3px; overflow: hidden;"><div style="background: #4caf50; height: 100%; width: {}%; transition: width 0.3s;"></div></div><div style="font-size: 12px; color: #666; margin-top: 4px; text-align: center;">{}% positive</div></div>',
                likes,
                dislikes,
                like_percent,
                like_percent_formatted
            )
        return mark_safe('<p style="color: #999; font-style: italic;">No engagement yet</p>')


    @admin.display(description='Favorites')
    def favorites_info(self, obj):
        count = obj.get_favorites_count()
        if count > 0:
            return format_html(
                '<div style="background: #e8f5e8; padding: 10px; border-radius: 4px; text-align: center;"><span style="font-size: 18px;">❤️</span><br><strong style="color: #2e7d32;">{} users</strong><br><small style="color: #666;">added to favorites</small></div>',
                count
            )
        return mark_safe('<p style="color: #999; font-style: italic;">Not in any favorites yet</p>')

    @admin.display(description='External Link')
    def view_on_site_link(self, obj):
        if obj.pk:
            url = obj.get_absolute_url()
            return format_html(
                '<a href="{}" target="_blank" style="background: #2196F3; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block;">🔗 View on Site</a>',
                url
            )
        return mark_safe('<span style="color: #999;">Save to view on site</span>')

    def mark_as_featured(self, request, queryset):
        count = queryset.count()
        self.message_user(request, format_html("Would mark {} products as featured", count))

    mark_as_featured.short_description = "Mark selected products as featured"

    def bulk_update_season(self, request, queryset):
        count = queryset.count()
        self.message_user(request, format_html("Would bulk update season for {} products", count))

    bulk_update_season.short_description = "Bulk update season"

    def export_selected_products(self, request, queryset):
        count = queryset.count()
        self.message_user(request, format_html("Would export {} products", count))

    export_selected_products.short_description = "Export selected products"
