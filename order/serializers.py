from rest_framework import serializers
from .models import Order, OrderItem, OrderStatus, PaymentStatus, OrderStatusHistory
from product.models import Product
from decimal import Decimal

class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ['id', 'code', 'name', 'description', 'color', 'is_active']

class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentStatus
        fields = ['id', 'code', 'name', 'description', 'is_active']

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_slug', 
            'quantity', 'price', 'total'
        ]
        read_only_fields = ['id', 'total']

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
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request = self.context.get('request')
        
        # Calculate totals
        subtotal = 0
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            price = item_data.get('price', product.price)  # Use provided price or product price
            subtotal += quantity * price
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            subtotal=subtotal,
            tax_amount=subtotal * Decimal('0.10'), #10% tax
            shipping_cost= Decimal('10.00'),  # Example fixed shipping
            **validated_data
        )
        
        # Create order items
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            price = item_data.get('price', product.price)
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=price
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