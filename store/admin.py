from django.contrib import admin
from .models import Category, Product

admin.site.site_header = "Vijaya Lakshmi Agro Agencies"
admin.site.site_title = "Agro Agencies Admin"
admin.site.index_title = "Manage your store"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_type", "sort_order")
    list_editable = ("sort_order",)
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "price", "stock_quantity", "is_active", "featured")
    list_filter = ("category", "is_active", "featured", "brand")
    list_search = ("name", "brand", "description")
    list_editable = ("price", "stock_quantity", "is_active", "featured")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
