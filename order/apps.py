from django.apps import AppConfig


class OrderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "order"

    def ready(self):
        """Run when app is ready - creates default order and payment statuses"""
        try:
            self.create_default_order_statuses()
            self.create_default_payment_statuses()
        except (ProgrammingError, OperationalError):
            # Database tables might not be created yet during initial migration
            pass
    
    def create_default_order_statuses(self):
        from .models import OrderStatus
        
        DEFAULT_ORDER_STATUSES = [
            {
                'id': 1,
                'code': 'pending',
                'name': 'Pending',
                'description': 'Order has been placed but not confirmed',
                'color': '#FFA500',  # Orange
                'order': 1,
                'is_active': True
            },
            {
                'id': 2,
                'code': 'confirmed', 
                'name': 'Confirmed',
                'description': 'Order has been confirmed and is being processed',
                'color': '#007BFF',  # Blue
                'order': 2,
                'is_active': True
            },
            {
                'id': 3,
                'code': 'processing', 
                'name': 'Processing',
                'description': 'Order is being prepared for shipment',
                'color': '#17A2B8',  # Teal
                'order': 3,
                'is_active': True
            },
            {
                'id': 4,
                'code': 'shipped',
                'name': 'Shipped', 
                'description': 'Order has been shipped to customer',
                'color': '#6F42C1',  # Purple
                'order': 4,
                'is_active': True
            },
            {
                'id': 5,
                'code': 'delivered',
                'name': 'Delivered',
                'description': 'Order has been delivered to customer',
                'color': '#28A745',  # Green
                'order': 5,
                'is_active': True
            },
            {
                'id': 6,
                'code': 'cancelled',
                'name': 'Cancelled',
                'description': 'Order has been cancelled',
                'color': '#DC3545',  # Red
                'order': 6,
                'is_active': True
            },
            {
                'id': 7,
                'code': 'refunded',
                'name': 'Refunded',
                'description': 'Order has been refunded',
                'color': '#6C757D',  # Gray
                'order': 7,
                'is_active': True
            }
        ]
        
        for status_data in DEFAULT_ORDER_STATUSES:
            OrderStatus.objects.get_or_create(
                id=status_data['id'],
                defaults=status_data
            )
        print("✅ Default order statuses created/verified")
    
    def create_default_payment_statuses(self):
        from .models import PaymentStatus
        
        DEFAULT_PAYMENT_STATUSES = [
            {
                'id': 1,
                'code': 'pending',
                'name': 'Pending',
                'description': 'Payment is pending',
                'order': 1,
                'is_active': True
            },
            {
                'id': 2,
                'code': 'paid',
                'name': 'Paid',
                'description': 'Payment has been successfully processed',
                'order': 2,
                'is_active': True
            },
            {
                'id': 3,
                'code': 'failed',
                'name': 'Failed',
                'description': 'Payment has failed',
                'order': 3,
                'is_active': True
            },
            {
                'id': 4,
                'code': 'refunded',
                'name': 'Refunded',
                'description': 'Payment has been refunded',
                'order': 4,
                'is_active': True
            },
            {
                'id': 5,
                'code': 'partially_refunded',
                'name': 'Partially Refunded',
                'description': 'Payment has been partially refunded',
                'order': 5,
                'is_active': True
            }
        ]
        
        for status_data in DEFAULT_PAYMENT_STATUSES:
            PaymentStatus.objects.get_or_create(
                id=status_data['id'],
                defaults=status_data
            )
        print("✅ Default payment statuses created/verified")


