from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    
    # Products
    path('', views.ProductListView.as_view(), name='product-list'),
    path('create/', views.ProductCreateView.as_view(), name='product-create'),
    path('<int:id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('<int:id>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    path('<int:id>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    
    # Vendor products
    path('vendor/my-products/', views.VendorProductListView.as_view(), name='vendor-product-list'),
    path('all-products/', views.AllProductsView.as_view(), name='all-products'),
    
    # Product images
    path('<int:product_id>/images/', views.ProductImageCreateView.as_view(), name='product-image-create'),
    path('images/<int:pk>/delete/', views.ProductImageDeleteView.as_view(), name='product-image-delete'),
    
    # Reviews
    path('discounts/', views.DiscountListView.as_view(), name='discount-list'),
    path('discounts/<int:pk>/', views.DiscountDetailView.as_view(), name='discount-detail'),
    
    # Public discount endpoints
    path('discounts/active/', views.ActiveDiscountsView.as_view(), name='active-discounts'),
    path('products/<int:product_id>/discounts/', views.ProductDiscountsView.as_view(), name='product-discounts'),
    path('calculate-discount/', views.CalculateDiscountView.as_view(), name='calculate-discount'),
    
    # Vendor-specific endpoints
    path('vendor/products/<int:product_id>/discounts/', views.VendorProductDiscountsView.as_view(), name='vendor-product-discounts'),
    path('vendor/discounts/stats/', views.VendorDiscountStatsView.as_view(), name='vendor-discount-stats'),
    path('vendor/discount-products/', views.VendorDiscountProductsView.as_view(), name='vendor-discount-products'),
    
    # Utility endpoints
    path('products/<int:product_id>/price-history/', views.PriceHistoryView.as_view(), name='price-history'),
    path('discount-usage/', views.DiscountUsageView.as_view(), name='discount-usage'),
    path('flash-sales/', views.FlashSaleProductsView.as_view(), name='flash-sales'),

]