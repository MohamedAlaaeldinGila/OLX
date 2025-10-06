# refunds/models.py
from django.db import models
from django.conf import settings
from order.models import Order, OrderItem

class RefundRequest(models.Model):
    REFUND_STATUS = [
        ('requested', 'Requested'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]
    
    REFUND_REASONS = [
        ('defective', 'Product Defective/Damaged'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_as_described', 'Not as Described'),
        ('changed_mind', 'Changed Mind'),
        ('late_delivery', 'Late Delivery'),
        ('missing_parts', 'Missing Parts'),
        ('other', 'Other'),
    ]
    
    # Basic info
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refund_requests')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Refund details
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='requested')
    reason = models.CharField(max_length=50, choices=REFUND_REASONS)
    description = models.TextField(help_text="Please describe the issue in detail")
    
    # Items to refund
    items = models.ManyToManyField(OrderItem, through='RefundItem')
    
    # Financial details
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Admin management
    admin_notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='reviewed_refunds')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Files/Evidence
    evidence_images = models.ManyToManyField('RefundEvidence', blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund #{self.id} - {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate requested amount if not set
        if not self.requested_amount and self.order:
            self.requested_amount = self.order.total
        super().save(*args, **kwargs)
    
    def can_be_processed(self):
        """Check if refund can be processed"""
        return self.status == 'approved' and self.approved_amount is not None
    
    def get_refundable_items(self):
        """Get items from the order that can be refunded"""
        return self.order.items.filter(product__is_active=True)

class RefundItem(models.Model):
    """Which specific items are being refunded"""
    refund_request = models.ForeignKey(RefundRequest, on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} x {self.order_item.product.number}"

class RefundEvidence(models.Model):
    """Evidence files for refund requests"""
    refund_request = models.ForeignKey(RefundRequest, on_delete=models.CASCADE, related_name='evidence_files')
    image = models.ImageField(upload_to='refund_evidence/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Evidence for Refund #{self.refund_request.id}"

class RefundTransaction(models.Model):
    """Track actual refund payments"""
    refund_request = models.OneToOneField(RefundRequest, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    processed_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"Refund TXN {self.transaction_id} - ${self.amount}"