from django.contrib import admin
from .models import Customer,Product,Orders,Feedback,PaymentLogs,StripeLogs,PhonepeLogs,GooglepayLogs,PaymentErrorLogs
# Register your models here.
class CustomerAdmin(admin.ModelAdmin):
    pass
admin.site.register(Customer, CustomerAdmin)

class ProductAdmin(admin.ModelAdmin):
    pass
admin.site.register(Product, ProductAdmin)

class OrderAdmin(admin.ModelAdmin):
    pass
admin.site.register(Orders, OrderAdmin)

class FeedbackAdmin(admin.ModelAdmin):
    pass
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(PaymentLogs)
admin.site.register(StripeLogs)
admin.site.register(PhonepeLogs)
admin.site.register(GooglepayLogs)
admin.site.register(PaymentErrorLogs)
# Register your models here.
