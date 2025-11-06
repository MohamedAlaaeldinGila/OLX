from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from .models import Product, ProductImage, Review, Category
from .serializers import *
from rest_framework import generics
from django.utils import timezone
from django.db import models

class CategoryListView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        categories = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

class CategoryDetailView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk, is_active=True)
        serializer = CategorySerializer(category)
        return Response(serializer.data)

class CategoryTreeView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        root_categories = Category.objects.filter(parent__isnull=True, is_active=True)
        serializer = CategoryTreeSerializer(root_categories, many=True)
        return Response(serializer.data)

class ProductListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Start with base queryset
        queryset = Product.objects.filter(is_active=True)
        
        # Apply filters from query parameters
        category_slug = request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        in_stock = request.query_params.get('in_stock')
        if in_stock and in_stock.lower() == 'true':
            queryset = queryset.filter(stock_quantity__gt=0)
        
        # Apply search
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(categories__name__icontains=search_query)
            )
        
        # Apply ordering
        ordering = request.query_params.get('ordering', '-created_at')
        if ordering in ['price', '-price', 'created_at', '-created_at']:
            queryset = queryset.order_by(ordering)
        
        # Annotate with ratings
        queryset = queryset.annotate(
            average_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        
        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)

class ProductDetailView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, id):
        product = get_object_or_404(Product, id=id, is_active=True)
        serializer = ProductDetailSerializer(product)
        return Response(serializer.data)

class ProductCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user

        # Check if the user is a vendor
        if not user.is_vendor:
            return Response(
                {"detail": "Only vendors can add products."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Save the product with the vendor as the current user
            product = serializer.save(vendor=user)
            return Response(ProductDetailSerializer(product).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ProductUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, id):
        # Users can only update their own products
        return get_object_or_404(Product, id=id, vendor=self.request.user)
    
    def put(self, request, id):
        product = self.get_object(id)
        serializer = ProductCreateSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, id):
        product = self.get_object(id)
        serializer = ProductCreateSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, id):
        # Users can only delete their own products
        return get_object_or_404(Product, id=id, vendor=self.request.user)
    
    def delete(self, request, id):
        product = self.get_object(id)
        # Soft delete
        product.is_active = False
        product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ProductImageCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, product_id):
        # Check if product exists and user owns it
        product = get_object_or_404(Product, id=product_id, vendor=request.user)
        
        serializer = ProductImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductImageDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, id):
        # Users can only delete images from their own products
        return get_object_or_404(ProductImage, id=id, product__vendor=self.request.user)
    
    def delete(self, request, pk):
        product_image = self.get_object(pk)
        product_image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ReviewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        
        # Check if user already reviewed this product
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response(
                {"error": "You have already reviewed this product."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReviewUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk):
        # Users can only update their own reviews
        return get_object_or_404(Review, id=pk, user=self.request.user)
    
    def put(self, request, pk):
        review = self.get_object(pk)
        serializer = ReviewSerializer(review, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        review = self.get_object(pk)
        serializer = ReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReviewDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk):
        # Users can only delete their own reviews
        return get_object_or_404(Review, id=pk, user=self.request.user)
    
    def delete(self, request, pk):
        review = self.get_object(pk)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class VendorProductListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        products = Product.objects.filter(vendor=request.user, is_active=True)
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

class ProductSearchView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        products = Product.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(categories__name__icontains=query),
            is_active=True
        ).distinct()
        
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

#--------------------Discount and Price History Views----------------------#
class DiscountListView(APIView):
    serializer_class = DiscountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # If user is vendor, show only their discounts
        if request.user.is_vendor:
            queryset = Discount.objects.filter(created_by=request.user)
        else:
            # For admin users, show all discounts ___________will be changed later.....
            queryset = Discount.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by active discounts
        """active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            )"""
        
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            discount = serializer.save(created_by=self.request.user)
            
            # If user is vendor, validate product ownership
            if request.user.is_vendor:
                products = request.data.get('products', [])
                if products:
                    vendor_products = Product.objects.filter(
                        id__in=products, 
                        vendor=request.user
                    )
                    if vendor_products.count() != len(products):
                        discount.delete()  # Rollback creation
                        return Response(
                            {"error": "You can only assign discounts to your own products"},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    discount.products.set(vendor_products)
                
                # Validate categories if specified
                categories = request.data.get('categories', [])
                if categories:
                    vendor_categories = Category.objects.filter(
                        id__in=categories,
                        products__vendor=request.user
                    ).distinct()
                    if vendor_categories.count() != len(categories):
                        discount.delete()  # Rollback creation
                        return Response(
                            {"error": "You can only assign discounts to categories containing your products"},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    discount.categories.set(vendor_categories)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DiscountDetailView(APIView):
    serializer_class = DiscountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get discount object and verify ownership for vendors"""
        discount = get_object_or_404(Discount, pk=pk)
        if user.is_vendor and discount.created_by != user:
            raise PermissionDenied("You don't have permission to access this discount")
        return discount
    
    def get(self, request, pk):
        discount = self.get_object(pk, request.user)
        serializer = self.serializer_class(discount)
        return Response(serializer.data)
    
    def put(self, request, pk):
        discount = self.get_object(pk, request.user)
        
        # Validate product ownership for vendors
        if request.user.is_vendor and 'products' in request.data:
            products = request.data.get('products', [])
            if products:
                vendor_products = Product.objects.filter(
                    id__in=products, 
                    vendor=request.user
                )
                if vendor_products.count() != len(products):
                    return Response(
                        {"error": "You can only assign discounts to your own products"},
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        serializer = self.serializer_class(discount, data=request.data)
        if serializer.is_valid():
            updated_discount = serializer.save()
            
            # Update products if provided (for vendors, already validated above)
            if 'products' in request.data:
                products = request.data.get('products', [])
                if request.user.is_vendor:
                    vendor_products = Product.objects.filter(
                        id__in=products, 
                        vendor=request.user
                    )
                    updated_discount.products.set(vendor_products)
                else:
                    updated_discount.products.set(products)
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        discount = self.get_object(pk, request.user)
        
        # Validate product ownership for vendors
        if request.user.is_vendor and 'products' in request.data:
            products = request.data.get('products', [])
            vendor_products = Product.objects.filter(
                id__in=products, 
                vendor=request.user
            )
            if vendor_products.count() != len(products):
                return Response(
                    {"error": "You can only assign discounts to your own products"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.serializer_class(discount, data=request.data, partial=True)
        if serializer.is_valid():
            updated_discount = serializer.save()
            
            # Update products if provided
            if 'products' in request.data:
                products = request.data.get('products', [])
                if request.user.is_vendor:
                    vendor_products = Product.objects.filter(
                        id__in=products, 
                        vendor=request.user
                    )
                    updated_discount.products.set(vendor_products)
                else:
                    updated_discount.products.set(products)
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        discount = self.get_object(pk, request.user)
        discount.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ActiveDiscountsView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        now = timezone.now()
        active_discounts = Discount.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
            status='active'
        ).exclude(
            Q(usage_limit__isnull=False) & Q(usage_count__gte=models.F('usage_limit'))
        )
        
        serializer = DiscountSerializer(active_discounts, many=True)
        return Response(serializer.data)

class ProductDiscountsView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        now = timezone.now()
        
        # Get discounts that apply to this product
        discounts = Discount.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
            status='active'
        ).filter(
            Q(products=product) | 
            Q(categories__in=product.categories.all()) |
            Q(apply_to_all_products=True)
        ).distinct()
        
        serializer = DiscountSerializer(discounts, many=True)
        return Response(serializer.data)

class VendorProductDiscountsView(APIView):
    """Get all discounts for a vendor's specific product"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, product_id):
        if not request.user.is_vendor:
            return Response(
                {"error": "Only vendors can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify the product belongs to the vendor
        product = get_object_or_404(Product, id=product_id, vendor=request.user)
        
        # Get discounts that apply to this product and are created by the vendor
        discounts = Discount.objects.filter(
            created_by=request.user
        ).filter(
            Q(products=product) | 
            Q(categories__in=product.categories.all()) |
            Q(apply_to_all_products=True)
        ).distinct()
        
        serializer = DiscountSerializer(discounts, many=True)
        return Response(serializer.data)

class CalculateDiscountView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        product_id = request.data.get('product_id')
        discount_id = request.data.get('discount_id')
        quantity = request.data.get('quantity', 1)
        
        product = get_object_or_404(Product, id=product_id)
        discount = get_object_or_404(Discount, id=discount_id)
        
        if not discount.is_currently_active:
            return Response(
                {"error": "Discount is not currently active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        discount_amount = discount.calculate_discount_amount(
            float(product.price), 
            quantity
        )
        
        final_price = float(product.price) - float(discount_amount)
        
        return Response({
            'original_price': product.price,
            'discount_amount': discount_amount,
            'final_price': final_price,
            'discount_percentage': (float(discount_amount) / float(product.price)) * 100 if product.price > 0 else 0
        })

class PriceHistoryView(APIView):
    serializer_class = PriceHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        
        # If user is vendor, verify product ownership
        if request.user.is_vendor and product.vendor != request.user:
            return Response(
                {"error": "You can only view price history for your own products"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        price_history = PriceHistory.objects.filter(product=product)
        serializer = self.serializer_class(price_history, many=True)
        return Response(serializer.data)

class DiscountUsageView(APIView):
    serializer_class = DiscountUsageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # If user is vendor, show only usage for their discounts
        if request.user.is_vendor:
            discount_usage = DiscountUsage.objects.filter(discount__created_by=request.user)
        else:
            # For admin users, show all discount usage
            discount_usage = DiscountUsage.objects.all()
        
        serializer = self.serializer_class(discount_usage, many=True)
        return Response(serializer.data)

class VendorDiscountStatsView(APIView):
    """Get statistics for vendor's discounts"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_vendor:
            return Response(
                {"error": "Only vendors can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        now = timezone.now()
        vendor_discounts = Discount.objects.filter(created_by=request.user)
        
        stats = {
            'total_discounts': vendor_discounts.count(),
            'active_discounts': vendor_discounts.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now,
                status='active'
            ).count(),
            'upcoming_discounts': vendor_discounts.filter(
                start_date__gt=now,
                status='active'
            ).count(),
            'expired_discounts': vendor_discounts.filter(
                end_date__lt=now
            ).count(),
            'total_usage': vendor_discounts.aggregate(
                total_usage=models.Sum('usage_count')
            )['total_usage'] or 0,
            'most_popular_discount': self.get_most_popular_discount(vendor_discounts),
        }
        
        return Response(stats)
    
    def get_most_popular_discount(self, discounts):
        """Get the most used discount"""
        most_popular = discounts.order_by('-usage_count').first()
        if most_popular:
            return {
                'id': most_popular.id,
                'name': most_popular.name,
                'usage_count': most_popular.usage_count
            }
        return None

class VendorDiscountProductsView(APIView):
    """Get all products that can have discounts applied (vendor's products)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_vendor:
            return Response(
                {"error": "Only vendors can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor_products = Product.objects.filter(vendor=request.user, is_active=True)
        serializer = ProductSerializer(vendor_products, many=True)
        return Response(serializer.data)
    

class FlashSaleProductsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        now = timezone.now()
        # Define "flash sale" as discounts ending within the next 24 hours
        upcoming_threshold = now + timezone.timedelta(hours=24)

        # Filter discounts that are active and expiring soon
        flash_discounts = Discount.objects.filter(
            is_active=True,
            status='active',
            end_date__lte=upcoming_threshold,
            end_date__gte=now
        ).prefetch_related('products')

        products = Product.objects.filter(
            discounts__in=flash_discounts,
            is_active=True
        ).annotate(
            average_rating=models.Avg('reviews__rating'),
            review_count=models.Count('reviews')
        ).distinct()

        serializer = ProductListSerializer(products, many=True)
        return Response({
            "flash_sales": serializer.data,
            "current_time": now,
        })

class AllProductsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        queryset = Product.objects.filter(is_active=True)

        # Optional: handle filters (like search, category, etc.)
        category_slug = request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)

        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(categories__name__icontains=search_query)
            )

        # Annotate ratings
        queryset = queryset.annotate(
            average_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )

        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)
