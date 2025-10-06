from django.db import models
from django.conf import settings
import random
import string

from product.models import Product
from .constants import DEFAULT_OrderStatus, DEFAULT_PaymentStatus

class OrderStatus(models.Model):
    """Configurable order statuses"""
    id = models.PositiveSmallIntegerField(primary_key=True)  # Single-digit ID
    code = models.CharField(max_length=20, unique=True)      # 'pending', 'shipped'
    name = models.CharField(max_length=50)                   # 'Pending', 'Shipped'
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)                   # For sorting in admin
    color = models.CharField(max_length=7, default='#000000') # For UI display
    
    class Meta:
        verbose_name_plural = "Order Statuses"
        ordering = ['order', 'code']
    
    def __str__(self):
        return self.name

class PaymentStatus(models.Model):
    """Configurable payment statuses"""
    id = models.PositiveSmallIntegerField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Payment Statuses"
        ordering = ['order', 'code']
    
    def __str__(self):
        return self.name


class Order(models.Model):
    """ORDER_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]"""
    
    # Order Identification
    order_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    
    # Order Status
    status = models.ForeignKey(
        OrderStatus, 
        on_delete=models.PROTECT,
        related_name='orders',
        default= DEFAULT_OrderStatus.PENDING
    )
    payment_status = models.ForeignKey(
        PaymentStatus,
        on_delete=models.PROTECT,
        related_name='orders',
        default= DEFAULT_PaymentStatus.PENDING
    )
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    #discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Shipping Information
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_zipcode = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)
    
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Additional
    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    #coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        self.total = self.subtotal + self.tax_amount + self.shipping_cost #- self.discount_amount
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        return f"ORD{''.join(random.choices(string.digits, k=10))}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of purchase
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.total = self.quantity * self.price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.ForeignKey(OrderStatus, on_delete=models.PROTECT)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status}"