from django.contrib import admin
from .models import Category, Product, ProductImage, Review, Discount, PriceHistory, DiscountUsage

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Review)
admin.site.register(Discount)
admin.site.register(PriceHistory)
admin.site.register(DiscountUsage)
