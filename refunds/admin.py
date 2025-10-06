from django.contrib import admin

from .models import RefundRequest, RefundEvidence, RefundTransaction

admin.site.register(RefundRequest)
admin.site.register(RefundEvidence)
admin.site.register(RefundTransaction)
