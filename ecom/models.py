from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.
class Customer(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    profile_pic= models.ImageField(upload_to='profile_pic/CustomerProfilePic/',null=True,blank=True)
    address = models.CharField(max_length=40)
    mobile = models.CharField(max_length=20,null=False)
    @property
    def get_name(self):
        return self.user.first_name+" "+self.user.last_name
    @property
    def get_id(self):
        return self.user.id
    def __str__(self):
        return self.user.first_name


class Product(models.Model):
    name=models.CharField(max_length=40)
    product_image= models.ImageField(upload_to='product_image/',null=True,blank=True)
    price = models.PositiveIntegerField()
    description=models.CharField(max_length=40)
    def __str__(self):
        return self.name


class Orders(models.Model):
    STATUS =(
        ('Pending','Pending'),
        ('Order Confirmed','Order Confirmed'),
        ('Out for Delivery','Out for Delivery'),
        ('Delivered','Delivered'),
    )
    customer=models.ForeignKey('Customer', on_delete=models.CASCADE,null=True)
    product=models.ForeignKey('Product',on_delete=models.CASCADE,null=True)
    email = models.CharField(max_length=50,null=True)
    address = models.CharField(max_length=500,null=True)
    mobile = models.CharField(max_length=20,null=True)
    order_date= models.DateField(auto_now_add=True,null=True)
    status=models.CharField(max_length=50,null=True,choices=STATUS)
    order_id=models.CharField(max_length=250)
    transaction_id = models.CharField(max_length=250)


class Feedback(models.Model):
    name=models.CharField(max_length=40)
    feedback=models.CharField(max_length=500)
    date= models.DateField(auto_now_add=True,null=True)
    def __str__(self):
        return self.name
    
    
class PaymentLogs(models.Model):
    transaction_id = models.CharField(max_length=250)
    payment_type = models.CharField(max_length=20)
    user_id = models.IntegerField()
    order_id=models.CharField(max_length=250)
    amount = models.DecimalField(max_digits=10 , decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    
class StripeLogs(models.Model):
    stripe_id = models.CharField(max_length=250 , unique=True)
    amount = models.DecimalField(max_digits=10 , decimal_places=2)
    name = models.CharField(max_length=250)
    email = models.CharField(max_length=250)
    transaction_id = models.CharField(max_length=250)
    # email = models.EmailField(max_length=250)

class GooglepayLogs(models.Model):
    transaction_id = models.CharField(max_length=250)
    token_id = models.CharField(max_length=250)
    card_last4 = models.CharField(max_length=250)
    address_city = models.CharField(max_length=250)
    address_country = models.CharField(max_length=250)
    address_state = models.CharField(max_length=250)
    address_zip = models.CharField(max_length=250)
    card_brand = models.CharField(max_length=250)
    amount = models.DecimalField(max_digits=10 , decimal_places=2)
    
class PhonepeLogs(models.Model):
    transaction_id = models.CharField(max_length=250)
    merchantId = models.CharField(max_length=250)
    payment_status = models.CharField(max_length=250)
    phonepeTransactionId = models.CharField(max_length=250)
    providerReferenceId = models.CharField(max_length=250)
    checksum = models.CharField(max_length=250)
    amount = models.DecimalField(max_digits=10 , decimal_places=2)
    
class PaymentErrorLogs(models.Model):
    payment_type = models.CharField(max_length=20, default='unknown')
    error_message = models.TextField()
    user_id = models.IntegerField(null=True, blank=True)
    order_id = models.CharField(max_length=250, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=250)

    class Meta:
        ordering = ['-timestamp']

class ErrorMessages(models.Model):
    error_id = models.IntegerField(unique=True)
    error_message = models.CharField(max_length=1000)
    # error_type = models.CharField(max_length=1000)
    
    def __str__(self):
        return f"Error ID: {self.error_id} \n Error Message: {self.error_message}"
