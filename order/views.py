from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem, OrderStatus, PaymentStatus, OrderStatusHistory
from .serializers import (
    OrderItemUpdateSerializer, OrderSerializer, OrderCreateSerializer, OrderUpdateSerializer,
    OrderStatusSerializer, PaymentStatusSerializer,
    OrderStatusHistorySerializer, OrderItemSerializer
)

class OrderListCreateAPIView(APIView):
    """
    GET: List all orders for current user
    POST: Create a new order
    """
    def get(self, request):
        orders = Order.objects.filter(user=request.user)
        serializer = OrderSerializer(orders, many=True)
        return Response({
            'count': orders.count(),
            'orders': serializer.data
        })
    
    def post(self, request):
        # Check if user has existing cart order
        cart_status = OrderStatus.objects.get(code='cart')
        existing_order = Order.objects.filter(user=request.user, status=cart_status).first()
        
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            if existing_order:
                # Add new items to existing cart
                items_data = serializer.validated_data.pop('items', [])
                for item_data in items_data:
                    product = item_data['product']
                    quantity = item_data['quantity']
                    price = item_data.get('price', product.price)
                    
                    # Check if item already exists in cart
                    order_item, created = OrderItem.objects.get_or_create(
                        order=existing_order, product=product,
                        defaults={'quantity': quantity, 'price': price}
                    )
                    if not created:
                        order_item.quantity += quantity
                        order_item.save()

                    subtotal = sum(item.price * item.quantity for item in existing_order.items.all())
                    existing_order.subtotal = subtotal
                    existing_order.tax_amount = subtotal * Decimal('0.1')  # example 10% tax
                    existing_order.shipping_cost = 10  # fixed or dynamic
                    existing_order.total = existing_order.subtotal + existing_order.tax_amount + existing_order.shipping_cost
                    existing_order.save()

                    return Response(OrderSerializer(existing_order).data)
            
            # Otherwise create new order
            order = serializer.save()

            subtotal = sum(Decimal(str(item.price)) * item.quantity for item in existing_order.items.all())
            order.subtotal = subtotal
            order.tax_amount = subtotal * Decimal('0.1')
            order.shipping_cost = 10
            order.total = order.subtotal + order.tax_amount + order.shipping_cost
            order.save()
            OrderStatusHistory.objects.create(
                order=order, status=order.status, note="Order created", created_by=request.user
            )
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderDetailAPIView(APIView):
    """
    GET: Get specific order details
    PATCH: Update order
    """
    def get_order(self, pk, user):
        return get_object_or_404(Order, pk=pk, user=user)
    
    def get(self, request, pk):
        order = self.get_order(pk, request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        order = self.get_order(pk, request.user)
        serializer = OrderUpdateSerializer(order, data=request.data, partial=True)
        
        if serializer.is_valid():
            old_status = order.status
            updated_order = serializer.save()
            
            # Create status history if status changed
            if 'status' in request.data and order.status != old_status:
                OrderStatusHistory.objects.create(
                    order=order,
                    status=order.status,
                    note=request.data.get('status_note', 'Status updated'),
                    created_by=request.user
                )
                
            
            return Response(OrderSerializer(updated_order).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderStatusListAPIView(APIView):
    """
    GET: List all order statuses
    """
    def get(self, request):
        statuses = OrderStatus.objects.filter(is_active=True)
        serializer = OrderStatusSerializer(statuses, many=True)
        return Response(serializer.data)

class PaymentStatusListAPIView(APIView):
    """
    GET: List all payment statuses
    """
    def get(self, request):
        statuses = PaymentStatus.objects.filter(is_active=True)
        serializer = PaymentStatusSerializer(statuses, many=True)
        return Response(serializer.data)

class OrderUpdateStatusAPIView(APIView):
    """
    POST: Update order status with note
    """
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        
        new_status_code = request.data.get('status_code')
        note = request.data.get('note', '')
        
        if not new_status_code:
            return Response(
                {'error': 'status_code is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_status = OrderStatus.objects.get(code=new_status_code, is_active=True)
        except OrderStatus.DoesNotExist:
            return Response(
                {'error': 'Invalid status code'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order status
        old_status = order.status
        order.status = new_status
        order.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            note=note,
            created_by=request.user
        )
        
        # Update timestamps based on status
        if new_status_code == 'paid' and not order.paid_at:
            order.paid_at = timezone.now()
            order.save()
        elif new_status_code == 'delivered' and not order.delivered_at:
            order.delivered_at = timezone.now()
            order.save()
        
        serializer = OrderSerializer(order)
        return Response({
            'message': f'Order status updated to {new_status.name}',
            'order': serializer.data
        })

class OrderCancelAPIView(APIView):
    """
    POST: Cancel an order
    """
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        
        # Check if order can be cancelled
        if order.status.code in ['cancelled', 'delivered', 'shipped']:
            return Response(
                {'error': f'Cannot cancel order with status {order.status.name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cancelled_status = OrderStatus.objects.get(code='cancelled')
        except OrderStatus.DoesNotExist:
            return Response(
                {'error': 'Cancelled status not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order status
        order.status = cancelled_status
        order.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            status=cancelled_status,
            note=request.data.get('note', 'Order cancelled by user'),
            created_by=request.user
        )
        
        serializer = OrderSerializer(order)
        return Response({
            'message': 'Order cancelled successfully',
            'order': serializer.data
        })


class OrderItemsListAPIView(APIView):
    """
    GET: List all items for a specific order
    """
    def get(self, request, order_pk):
        order = get_object_or_404(Order, pk=order_pk, user=request.user)
        items = order.items.all()
        serializer = OrderItemSerializer(items, many=True)
        return Response({
            'order_number': order.order_number,
            'order_status': order.status.name,
            'items_count': items.count(),
            'items': serializer.data
        })

class OrderStatusHistoryAPIView(APIView):
    """
    GET: Get status history for a specific order
    """
    def get(self, request, order_pk):
        order = get_object_or_404(Order, pk=order_pk, user=request.user)
        history = order.status_history.all().order_by('-created_at')
        serializer = OrderStatusHistorySerializer(history, many=True)
        return Response({
            'order_number': order.order_number,
            'history_count': history.count(),
            'history': serializer.data
        })
    


class CartItemUpdateDeleteAPIView(APIView):
    """
    PATCH: update quantity of an item in the cart
    DELETE: remove item from the cart
    """
    def get_object(self, item_id, user):
        cart_status = OrderStatus.objects.get(code='cart')
        return get_object_or_404(OrderItem, id=item_id, order__status=cart_status, order__user=user)

    def patch(self, request, item_id):
        item = self.get_object(item_id, request.user)
        quantity = request.data.get('quantity')
        if quantity is None or int(quantity) < 1:
            return Response({'error': 'Quantity must be >= 1'}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = int(quantity)
        item.save()

        # Update order totals
        order = item.order
        order.subtotal = sum(i.price * i.quantity for i in order.items.all())
        order.tax_amount = order.subtotal * 0.1
        order.total = order.subtotal + order.tax_amount + order.shipping_cost
        order.save()

        serializer = OrderItemUpdateSerializer(item)
        return Response(serializer.data)

    def delete(self, request, item_id):
        item = self.get_object(item_id, request.user)
        order = item.order
        item.delete()

        # Update order totals
        order.subtotal = sum(i.price * i.quantity for i in order.items.all())
        order.tax_amount = order.subtotal * 0.1
        order.total = order.subtotal + order.tax_amount + order.shipping_cost
        order.save()

        return Response({'message': 'Item removed from cart'}, status=status.HTTP_204_NO_CONTENT)
