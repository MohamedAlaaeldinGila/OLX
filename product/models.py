from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Product(models.Model):

    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    #category
    categories = models.ManyToManyField('Category')

    #availability
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    #timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    #addistional fields
    vendor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='products',
        limit_choices_to={'user_type': 'vendor'},  # Only vendor users can have products
    )

    def is_in_stock(self):
        return self.stock_quantity > 0
    
    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    title = models.CharField(max_length=255)
    comment = models.TextField()
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'user'] 


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)  
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Discount(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('buy_x_get_y', 'Buy X Get Y'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percentage')
    
    # Discount Values
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # 10.00 for 10%
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Buy X Get Y Fields
    buy_quantity = models.PositiveIntegerField(null=True, blank=True)  # Buy X
    get_quantity = models.PositiveIntegerField(null=True, blank=True)  # Get Y free
    
    # Scheduling
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Scope
    products = models.ManyToManyField('Product', related_name='discounts', blank=True)
    categories = models.ManyToManyField('Category', related_name='discounts', blank=True)
    apply_to_all_products = models.BooleanField(default=False)
    
    # Limits
    usage_limit = models.PositiveIntegerField(null=True, blank=True)  # Total usage limit
    usage_count = models.PositiveIntegerField(default=0)  # Current usage count
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_discounts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_discount_type_display()})"
    
    def clean(self):
        """Validate discount data"""
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")
        
        if self.discount_type == 'percentage' and not self.percentage:
            raise ValidationError("Percentage is required for percentage discounts")
        
        if self.discount_type == 'fixed' and not self.fixed_amount:
            raise ValidationError("Fixed amount is required for fixed amount discounts")
        
        if self.discount_type == 'buy_x_get_y':
            if not self.buy_quantity or not self.get_quantity:
                raise ValidationError("Buy quantity and get quantity are required for Buy X Get Y discounts")
    
    def save(self, *args, **kwargs):
        # Update status based on dates
        now = timezone.now()
        if self.start_date <= now <= self.end_date and self.is_active:
            self.status = 'active'
        elif now > self.end_date:
            self.status = 'expired'
        elif now < self.start_date:
            self.status = 'scheduled'
        
        # Validate before saving
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_currently_active(self):
        """Check if discount is currently active"""
        now = timezone.now()
        return (self.is_active and 
                self.start_date <= now <= self.end_date and 
                self.status == 'active' and
                (self.usage_limit is None or self.usage_count < self.usage_limit))
    
    def calculate_discount_amount(self, product_price, quantity=1):
        """Calculate discount amount for a product"""
        if not self.is_currently_active:
            return 0
        
        if self.discount_type == 'percentage':
            discount_amount = (product_price * self.percentage) / 100
            if self.max_discount_amount:
                discount_amount = min(discount_amount, self.max_discount_amount)
            return discount_amount
        
        elif self.discount_type == 'fixed':
            return min(self.fixed_amount, product_price)
        
        elif self.discount_type == 'buy_x_get_y':
            # For Buy X Get Y, we calculate the effective discount per item
            if quantity >= self.buy_quantity + self.get_quantity:
                free_items = (quantity // (self.buy_quantity + self.get_quantity)) * self.get_quantity
                return free_items * product_price
            return 0
        
        return 0
    
    def get_discount_display(self):
        """Get human-readable discount description"""
        if self.discount_type == 'percentage':
            return f"{self.percentage}% OFF"
        elif self.discount_type == 'fixed':
            return f"${self.fixed_amount} OFF"
        elif self.discount_type == 'buy_x_get_y':
            return f"Buy {self.buy_quantity} Get {self.get_quantity} Free"
        return "No Discount"

class PriceHistory(models.Model):
    """Track price changes and discounts for products"""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='price_history')
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.ForeignKey(Discount, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Effective period for this price
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name_plural = "Price Histories"
    
    def __str__(self):
        return f"{self.product.title} - {self.original_price} ({self.start_date})"
    
    @property
    def discount_amount(self):
        if self.discounted_price and self.original_price:
            return self.original_price - self.discounted_price
        return 0
    
    @property
    def discount_percentage(self):
        if self.discounted_price and self.original_price and self.original_price > 0:
            return ((self.original_price - self.discounted_price) / self.original_price) * 100
        return 0
    
    @property
    def is_current(self):
        """Check if this price is currently active"""
        now = timezone.now()
        return (self.start_date <= now and 
                (self.end_date is None or self.end_date >= now))

class DiscountUsage(models.Model):
    """Track usage of discounts"""
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='usages')
    order = models.ForeignKey('order.Order', on_delete=models.CASCADE, related_name='discount_usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, null=True, blank=True)
    
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-used_at']
        unique_together = ['discount', 'order', 'product']
    
    def __str__(self):
        return f"{self.discount.name} - {self.user.username} - ${self.discount_amount}"

