from rest_framework import serializers
from .models import Order, OrderItem, OrderStatus, PaymentStatus, OrderStatusHistory
from product.models import Product
from decimal import Decimal
from django.db import transaction
from product.serializers import ProductImageSerializer

class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ['id', 'code', 'name', 'description', 'color', 'is_active']

class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentStatus
        fields = ['id', 'code', 'name', 'description', 'is_active']

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    product_stock = serializers.IntegerField(source='product.stock_quantity', read_only=True)
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_slug', 
            'quantity', 'price', 'total', 'product_stock', 'primary_image'
        ]
        read_only_fields = ['id', 'total']

    def get_primary_image(self, obj):
        """
        Returns the product's primary image (or first image as fallback).
        """
        product = obj.product
        primary_image = product.images.filter(is_primary=True).first()

        # fallback if no primary image
        if not primary_image:
            primary_image = product.images.first()

        if primary_image:
            return ProductImageSerializer(primary_image).data
        return None

class OrderItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['quantity']

class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.name', read_only=True)
    status_code = serializers.CharField(source='status.code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'status', 'status_name', 'status_code', 
            'note', 'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at']

class OrderSerializer(serializers.ModelSerializer):
    # Related fields
    status_name = serializers.CharField(source='status.name', read_only=True)
    status_code = serializers.CharField(source='status.code', read_only=True)
    payment_status_name = serializers.CharField(source='payment_status.name', read_only=True)
    payment_status_code = serializers.CharField(source='payment_status.code', read_only=True)
    
    # Nested serializers
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    
    # User information
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            # Order Identification
            'id', 'order_number', 'user', 'user_email', 'user_username',
            
            # Status
            'status', 'status_name', 'status_code',
            'payment_status', 'payment_status_name', 'payment_status_code',
            
            # Pricing
            'subtotal', 'tax_amount', 'shipping_cost', 'total',
            
            # Shipping Information
            'shipping_address', 'shipping_city', 'shipping_state', 
            'shipping_zipcode', 'shipping_country',
            
            # Timestamps
            'created_at', 'updated_at', 'paid_at', 'delivered_at',
            
            # Additional
            'notes', 'tracking_number',
            
            # Nested objects
            'items', 'status_history'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at', 
            'total', 'paid_at', 'delivered_at'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)
    
    class Meta:
        model = Order
        fields = [
            'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_zipcode', 'shipping_country', 'notes', 'items'
        ]
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request = self.context.get('request')
        
        # Calculate totals
        subtotal = Decimal('0.00')
        for item_data in items_data:
            product = item_data['product']
            price = Decimal(str(item_data.get('price', product.price)))
            quantity = Decimal(str(item_data.get('quantity', 1)))
            subtotal += price * quantity
        
        # Tax and shipping calculation (could be dynamic later)
        tax_amount = subtotal * Decimal('0.10')  # 10% tax
        shipping_cost = Decimal('10.00')
        discount_amount = validated_data.get('discount_amount', Decimal('0.00'))

        # ✅ Compute total
        total = subtotal + tax_amount + shipping_cost - discount_amount

        # Default order status
        initial_status = OrderStatus.objects.filter(code='cart').first()
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_cost=shipping_cost,
            discount_amount=discount_amount,
            total=total,
            status=initial_status,
            **validated_data,
        )
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)

        OrderStatusHistory.objects.create(
            order=order,
            status=initial_status,
            note="Order created successfully",
            created_by=request.user
        )
        
        return order

class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'status', 'payment_status', 'tracking_number', 'notes',
            'paid_at', 'delivered_at'
        ]
        read_only_fields = ['order_number', 'user', 'subtotal', 'total']