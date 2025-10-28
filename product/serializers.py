from rest_framework import serializers
from .models import Product, ProductImage, Review, Category, Discount, PriceHistory, DiscountUsage
from django.conf import settings

User = settings.AUTH_USER_MODEL

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent', 'image', 'is_active', 'order']
        read_only_fields = ['id', 'slug']

class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'is_active', 'order', 'children']
    
    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategoryTreeSerializer(children, many=True).data

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'alt_text', 'is_primary', 'order']
        read_only_fields = ['id']
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'product', 'user', 'user_name', 'user_email', 
            'rating', 'title', 'comment', 'is_verified', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'is_verified', 'created_at', 'updated_at']
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def create(self, validated_data):
        # Set the current user as the review author
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    categories = CategorySerializer(many=True, read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'price', 'primary_image', 'average_rating',
            'review_count', 'categories', 'stock_quantity', 'is_in_stock',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return ProductImageSerializer(primary_image).data
        return None
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0
    
    def get_review_count(self, obj):
        return obj.reviews.count()

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.get_full_name', read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 'price', 'categories',
            'stock_quantity', 'is_active', 'is_in_stock', 'vendor',
            'vendor_name', 'images', 'reviews', 'average_rating',
            'review_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews:
            return round(sum(review.rating for review in reviews) / len(reviews), 1)
        return 0
    
    def get_review_count(self, obj):
        return obj.reviews.count()

class ProductCreateSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        many=True,
        required=False
    )
    
    class Meta:
        model = Product
        fields = [
            'title', 'description', 'price', 'categories',
            'stock_quantity', 'is_active'
        ]
    
    def create(self, validated_data):
        categories = validated_data.pop('categories', [])
        product = Product.objects.create(**validated_data)
        product.categories.set(categories)
        return product
    
    def update(self, instance, validated_data):
        categories = validated_data.pop('categories', None)
        product = super().update(instance, validated_data)
        
        if categories is not None:
            product.categories.set(categories)
        
        return product

class ProductImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_primary', 'order', 'product']
        read_only_fields = ['product']
    
    def create(self, validated_data):
        validated_data['product'] = self.context['product']
        return super().create(validated_data)

#----------------------DIscount and Price History Serializers----------------------#

class DiscountSerializer(serializers.ModelSerializer):
    is_currently_active = serializers.BooleanField(read_only=True)
    discount_display = serializers.CharField(read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Discount
        fields = [
            'id', 'name', 'description', 'discount_type', 'percentage', 'fixed_amount',
            'buy_quantity', 'get_quantity', 'start_date', 'end_date', 'products',
            'categories', 'apply_to_all_products', 'usage_limit', 'usage_count',
            'min_order_amount', 'max_discount_amount', 'status', 'is_active',
            'is_currently_active', 'discount_display', 'products_count',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['usage_count', 'status', 'created_by']
    
    def get_products_count(self, obj):
        if obj.apply_to_all_products:
            return "All Products"
        return obj.products.count()
    
    def validate(self, data):
        # Custom validation for discount types
        discount_type = data.get('discount_type')
        
        if discount_type == 'percentage' and not data.get('percentage'):
            raise serializers.ValidationError({"percentage": "Percentage is required for percentage discounts."})
        
        if discount_type == 'fixed' and not data.get('fixed_amount'):
            raise serializers.ValidationError({"fixed_amount": "Fixed amount is required for fixed amount discounts."})
        
        if discount_type == 'buy_x_get_y':
            if not data.get('buy_quantity') or not data.get('get_quantity'):
                raise serializers.ValidationError({
                    "buy_quantity": "Buy quantity is required for Buy X Get Y discounts.",
                    "get_quantity": "Get quantity is required for Buy X Get Y discounts."
                })
        
        # Validate dates
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})
        
        return data

class PriceHistorySerializer(serializers.ModelSerializer):
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    discount_name = serializers.CharField(source='discount.name', read_only=True)
    
    class Meta:
        model = PriceHistory
        fields = [
            'id', 'product', 'original_price', 'discounted_price', 'discount',
            'discount_name', 'discount_amount', 'discount_percentage',
            'start_date', 'end_date', 'is_current', 'created_at'
        ]
        read_only_fields = ['created_at']

class DiscountUsageSerializer(serializers.ModelSerializer):
    discount_name = serializers.CharField(source='discount.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = DiscountUsage
        fields = [
            'id', 'discount', 'discount_name', 'order', 'order_number',
            'user', 'user_name', 'product', 'product_title',
            'original_price', 'discount_amount', 'final_price', 'used_at'
        ]
        read_only_fields = ['used_at']