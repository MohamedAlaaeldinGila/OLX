from django.apps import AppConfig
from django.db.utils import ProgrammingError, OperationalError


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        """Run when app is ready - creates default notification types"""
        try:
            from .models import NotificationType
            self.create_default_notification_types()
        except (ProgrammingError, OperationalError):
            # Database tables might not be created yet during initial migration
            pass
    
    def create_default_notification_types(self):
        from .models import NotificationType
        
        DEFAULT_TYPES = [
            {
                'id': 1,
                'code': 'order',
                'name': 'Order Update',
                'description': 'Order related notifications',
                'icon': 'shopping_cart'
            },
            {
                'id': 2, 
                'code': 'promotion',
                'name': 'Promotion',
                'description': 'Promotional offers and discounts',
                'icon': 'local_offer'
            },
            {
                'id': 3,
                'code': 'security', 
                'name': 'Security Alert',
                'description': 'Security and account related alerts',
                'icon': 'security'
            },
            {
                'id': 4,
                'code': 'system',
                'name': 'System Notification', 
                'description': 'System maintenance and updates',
                'icon': 'notifications'
            },
            {
                'id': 5,
                'code': 'product',
                'name': 'Product Update',
                'description': 'Product updates and new features',
                'icon': 'update'
            }
        ]
        
        for type_data in DEFAULT_TYPES:
            NotificationType.objects.get_or_create(
                id=type_data['id'],
                defaults=type_data
            )
    
        
