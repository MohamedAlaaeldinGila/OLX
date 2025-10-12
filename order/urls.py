from django.urls import path, include
from .views import (
    # Order views
    OrderListCreateAPIView,
    OrderDetailAPIView,
    OrderUpdateStatusAPIView,
    OrderCancelAPIView,
    
    # Status views
    OrderStatusListAPIView,
    PaymentStatusListAPIView,
    
    # Order Items views
    OrderItemsListAPIView,
    
    # Order History views
    OrderStatusHistoryAPIView
)

urlpatterns = [
    
    # List all orders & create new order
    path('', OrderListCreateAPIView.as_view(), name='order-list-create'),
    
    # Get, update, or delete specific order
    path('<int:pk>/', OrderDetailAPIView.as_view(), name='order-detail'),
    
    # Update order status
    path('<int:pk>/update-status/', OrderUpdateStatusAPIView.as_view(), name='order-update-status'),
    
    # Cancel order
    path('<int:pk>/cancel/', OrderCancelAPIView.as_view(), name='order-cancel'),
    
    # Get all order statuses (for dropdowns)
    path('order-statuses/', OrderStatusListAPIView.as_view(), name='order-status-list'),
    
    # Get all payment statuses (for dropdowns)
    path('payment-statuses/', PaymentStatusListAPIView.as_view(), name='payment-status-list'),
    
    # Get all items for a specific order
    path('<int:order_pk>/items/', OrderItemsListAPIView.as_view(), name='order-items'),
    # Get status history for a specific order
    path('<int:order_pk>/status-history/', OrderStatusHistoryAPIView.as_view(), name='order-status-history'),
]