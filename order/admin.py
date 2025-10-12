from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory, OrderStatus, PaymentStatus

admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderStatusHistory)
admin.site.register(OrderStatus)
admin.site.register(PaymentStatus)
