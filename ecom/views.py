from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.http import HttpResponseRedirect,HttpResponse
from django.core.mail import send_mail
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from django.conf import settings
import os

#   Stripe imports
import stripe

#   PAYPAL imports
from paypal.standard.forms import PayPalPaymentsForm
import uuid
from django.urls import reverse

#   Phonepe imports

import jsons
import base64
import requests
import shortuuid
from cryptography.hazmat.primitives import hashes
from django.views.decorators.csrf import csrf_exempt
from cryptography.hazmat.backends import default_backend
from django.http import JsonResponse
import datetime
import json

# Stripe configuration - use environment variable for security
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'your-stripe-secret-key-here')

def home_view(request):
    products=models.Product.objects.all()
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'ecom/index.html',{'products':products,'product_count_in_cart':product_count_in_cart})


#for showing login button for admin(by sumit)
def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return HttpResponseRedirect('adminlogin')


def customer_signup_view(request):
    userForm=forms.CustomerUserForm()
    customerForm=forms.CustomerForm()
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST)
        customerForm=forms.CustomerForm(request.POST,request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customer=customerForm.save(commit=False)
            customer.user=user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
            
            new_user = models.User.objects.get(username=user.get_username())
            print("----------------------------------")
            print("new :" ,new_user.id)
            # new_userid = new_user.id
            
            mydict = {
                'userid': new_user.id,
                'signup_success': True,
                'firstname':new_user.first_name,
            }
            
                        
            return render(request,'ecom/face_signup.html',context=mydict)
        return HttpResponseRedirect('customerlogin')
    # new_user = models.User.objects.get(username="abcd@gmail.com")
    # print("----------------------------------")
    # print("new :" ,new_user.id)
    return render(request,'ecom/customersignup.html',context=mydict)

#-----------for checking user iscustomer
def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()



#---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,CUSTOMER
def afterlogin_view(request):
    if is_customer(request.user):
        return redirect('customer-home')
    else:
        return redirect('admin-dashboard')

#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    # for cards on dashboard
    customercount=models.Customer.objects.all().count()
    productcount=models.Product.objects.all().count()
    ordercount=models.Orders.objects.all().count()

    # for recent order tables
    orders=models.Orders.objects.all()
    ordered_products=[]
    ordered_bys=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_by=models.Customer.objects.all().filter(id = order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)

    mydict={
    'customercount':customercount,
    'productcount':productcount,
    'ordercount':ordercount,
    'data':zip(ordered_products,ordered_bys,orders),
    }
    return render(request,'ecom/admin_dashboard.html',context=mydict)


# admin view customer table
@login_required(login_url='adminlogin')
def view_customer_view(request):
    customers=models.Customer.objects.all()
    return render(request,'ecom/view_customer.html',{'customers':customers})

# admin delete customer
@login_required(login_url='adminlogin')
def delete_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('view-customer')


@login_required(login_url='adminlogin')
def update_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(request.FILES,instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return redirect('view-customer')
    return render(request,'ecom/admin_update_customer.html',context=mydict)

# admin view the product
@login_required(login_url='adminlogin')
def admin_products_view(request):
    products=models.Product.objects.all()
    return render(request,'ecom/admin_products.html',{'products':products})


# admin add product by clicking on floating button
@login_required(login_url='adminlogin')
def admin_add_product_view(request):
    productForm=forms.ProductForm()
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST, request.FILES)
        if productForm.is_valid():
            productForm.save()
        return HttpResponseRedirect('admin-products')
    return render(request,'ecom/admin_add_products.html',{'productForm':productForm})


@login_required(login_url='adminlogin')
def delete_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    product.delete()
    return redirect('admin-products')


@login_required(login_url='adminlogin')
def update_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    productForm=forms.ProductForm(instance=product)
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST,request.FILES,instance=product)
        if productForm.is_valid():
            productForm.save()
            return redirect('admin-products')
    return render(request,'ecom/admin_update_product.html',{'productForm':productForm})


@login_required(login_url='adminlogin')
def admin_view_booking_view(request):
    orders=models.Orders.objects.all()
    ordered_products=[]
    ordered_bys=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_by=models.Customer.objects.all().filter(id = order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)
    return render(request,'ecom/admin_view_booking.html',{'data':zip(ordered_products,ordered_bys,orders)})


@login_required(login_url='adminlogin')
def delete_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    order.delete()
    return redirect('admin-view-booking')

# for changing status of order (pending,delivered...)
@login_required(login_url='adminlogin')
def update_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    orderForm=forms.OrderForm(instance=order)
    if request.method=='POST':
        orderForm=forms.OrderForm(request.POST,instance=order)
        if orderForm.is_valid():
            orderForm.save()
            return redirect('admin-view-booking')
    return render(request,'ecom/update_order.html',{'orderForm':orderForm})


# admin view the feedback
@login_required(login_url='adminlogin')
def view_feedback_view(request):
    feedbacks=models.Feedback.objects.all().order_by('-id')
    return render(request,'ecom/view_feedback.html',{'feedbacks':feedbacks})



#---------------------------------------------------------------------------------
#------------------------ PUBLIC CUSTOMER RELATED VIEWS START ---------------------
#---------------------------------------------------------------------------------
def search_view(request):
    # whatever user write in search box we get in query
    query = request.GET['query']
    products=models.Product.objects.all().filter(name__icontains=query)
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # word variable will be shown in html when user click on search button
    word="Searched Result :"

    if request.user.is_authenticated:
        return render(request,'ecom/customer_home.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart})
    return render(request,'ecom/index.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart})


# any one can add product to cart, no need of signin
def add_to_cart_view(request,pk):
    products=models.Product.objects.all()

    #for cart counter, fetching products ids added by customer from cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=1

    response = render(request, 'ecom/index.html',{'products':products,'product_count_in_cart':product_count_in_cart})

    #adding product id to cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids=="":
            product_ids=str(pk)
        else:
            product_ids=product_ids+"|"+str(pk)
        response.set_cookie('product_ids', product_ids)
    else:
        response.set_cookie('product_ids', pk)

    product=models.Product.objects.get(id=pk)
    messages.info(request, product.name + ' added to cart successfully!')

    return response



# for checkout of cart
def cart_view(request):
    #for cart counter
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # fetching product details from db whose id is present in cookie
    products=None
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_id_in_cart=product_ids.split('|')
            products=models.Product.objects.all().filter(id__in = product_id_in_cart)

            #for total price shown in cart
            for p in products:
                total=total+p.price
    return render(request,'ecom/cart.html',{'products':products,'total':total,'product_count_in_cart':product_count_in_cart})


def remove_from_cart_view(request,pk):
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # removing product id from cookie
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_id_in_cart=product_ids.split('|')
        product_id_in_cart=list(set(product_id_in_cart))
        product_id_in_cart.remove(str(pk))
        products=models.Product.objects.all().filter(id__in = product_id_in_cart)
        #for total price shown in cart after removing product
        for p in products:
            total=total+p.price

        #  for update coookie value after removing product id in cart
        value=""
        for i in range(len(product_id_in_cart)):
            if i==0:
                value=value+product_id_in_cart[0]
            else:
                value=value+"|"+product_id_in_cart[i]
        response = render(request, 'ecom/cart.html',{'products':products,'total':total,'product_count_in_cart':product_count_in_cart})
        if value=="":
            response.delete_cookie('product_ids')
        response.set_cookie('product_ids',value)
        return response


def send_feedback_view(request):
    feedbackForm=forms.FeedbackForm()
    if request.method == 'POST':
        feedbackForm = forms.FeedbackForm(request.POST)
        if feedbackForm.is_valid():
            feedbackForm.save()
            return render(request, 'ecom/feedback_sent.html')
    return render(request, 'ecom/send_feedback.html', {'feedbackForm':feedbackForm})


#---------------------------------------------------------------------------------
#------------------------ CUSTOMER RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_home_view(request):
    products=models.Product.objects.all()
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0
    return render(request,'ecom/customer_home.html',{'products':products,'product_count_in_cart':product_count_in_cart})



# shipment address before placing order
@login_required(login_url='customerlogin')
def customer_address_view(request):
    # this is for checking whether product is present in cart or not
    # if there is no product in cart we will not show address form
    product_in_cart=False
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_in_cart=True
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    addressForm = forms.AddressForm()
    if request.method == 'POST':
        addressForm = forms.AddressForm(request.POST)
        if addressForm.is_valid():
            # here we are taking address, email, mobile at time of order placement
            # we are not taking it from customer account table because
            # these thing can be changes
            email = addressForm.cleaned_data['Email']
            mobile=addressForm.cleaned_data['Mobile']
            address = addressForm.cleaned_data['Address']
            #for showing total price on payment page.....accessing id from cookies then fetching  price of product from db
            
            priceDetails = calculateCheckOutPrice(request)
            
            total = priceDetails["total"]
            products = priceDetails["products"]
                
            line_items = []        
            for product in products:
                line_items.append({
                    'price_data': {
                        'currency': 'inr',
                        'unit_amount': product.price * 100,
                        'product_data': {
                            'name': product.name,
                            'description':product.description,
                        },
                    },
                    'quantity': 1,
                })
                
            transaction_id = str(uuid.uuid4())
            
            context = {
                'total': total,
                'stripe_publishable_key': os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_your_stripe_publishable_key')
            }
            response = render(request, 'ecom/payment.html', context)
            response.set_cookie('email', email)
            response.set_cookie('mobile', mobile)
            response.set_cookie('address', address)
            response.set_cookie('transaction_id' , transaction_id)
            return response
    return render(request,'ecom/customer_address.html',{'addressForm':addressForm,'product_in_cart':product_in_cart,'product_count_in_cart':product_count_in_cart})




# here we are just directing to this view...actually we have to check whther payment is successful or not
#then only this view should be accessed
@csrf_exempt
def payment_success_view(request):
    # Here we will place order | after successful payment
    # we will fetch customer  mobile, address, Email
    # we will fetch product id from cookies then respective details from db
    # then we will create order objects and store in db
    # after that we will delete cookies because after order placed...cart should be empty
    
    print("Payment Success - GET params:", request.GET)
    print("Payment Success - POST params:", request.POST)

    customer = None
    if request.user.is_authenticated:
        try:
            customer = models.Customer.objects.get(user_id=request.user.id)
            print("got customer id: " ,request.user.id)
        except models.Customer.DoesNotExist:
            pass

    products = None
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_id_in_cart = product_ids.split('|')
            products = models.Product.objects.all().filter(id__in=product_id_in_cart)

    email = request.COOKIES.get('email', None)
    mobile = request.COOKIES.get('mobile', None)
    address = request.COOKIES.get('address', None)

    # For Stripe payments, try to get data from session metadata
    # session_id = request.GET.get('stripe-session_id')
    # print("session id: " , session_id)
    # if request.GET.get('stripe-session_id'):
    #     try:
    #         session_id = request.GET.get('stripe-session_id')
    #         print("session id: " , session_id)
    #         session = stripe.checkout.Session.retrieve(session_id)
    #         if session.metadata:
    #             print(session.metadata)
    #             email = session.metadata.get('user_email')
    #             mobile = session.metadata.get('phone_number')
    #             address = session.metadata.get('address')
    #     except Exception as e:
    #         print(f"Error retrieving Stripe session: {e}")

    order_id = None
    if products:
        order_id = str(uuid.uuid4())
        transaction_id = request.COOKIES.get("transaction_id" , str(uuid.uuid4()))
        if request.GET.get('code') == "PAYMENT_ERROR":
            # error_message = "payment failed"
            error_message = ErrorMessageManager.getErrorMessage(1001)
            PaymentLogger.log_error(transaction_id,request.GET.get('payment_type', 'unknown'), error_message, request , order_id=order_id , customer_email=request.COOKIES.get('email', None))
    
        for product in products:
            try:
                models.Orders.objects.get_or_create(
                    customer=customer,
                    product=product,
                    status='Pending',
                    email=email,
                    mobile=mobile,
                    address=address,
                    order_id=order_id,
                    transaction_id=transaction_id, 
                )
                print(f"Order created for product: {product.name}")
            except Exception as e:
                # error_message = f'Order creation failed for {product.name}: {str(e)}'
                error_message = ErrorMessageManager.getErrorMessage(1002)
                log_payment_error(transaction_id,request.GET.get('payment_type', 'unknown'),
                                error_message,
                                request, order_id=order_id)
    else:
        # error_message = 'No products in cart'
        error_message = ErrorMessageManager.getErrorMessage(1006)
        log_payment_error(transaction_id,request.GET.get('payment_type', 'unknown'),
                         error_message, request)

    # if request.GET.get('payment_type') == "stripe":
        # id = request.GET.get('id')
        # amount = request.GET.get('amount')
        # name = request.GET.get('name')
        # email = request.GET.get('email')
        
        # data = {
        #     "stripe_id": id,
        #     "amount": float(amount)/100,
        #     "name": name,
        #     "email": email
        # }
        
    print("Updating Payments")
    # updatePaymentTransaction(request.GET , request.user.id , order_id)
    PaymentTransactionManager.update_payment_transaction(request.COOKIES ,request.GET , request.user.id , order_id)
    

    res = render(request, 'ecom/payment_success.html')
    res.delete_cookie('product_ids')
    res.delete_cookie('email')
    res.delete_cookie('mobile')
    res.delete_cookie('address')
    
    return res


class PaymentTransactionManager:

    @staticmethod
    def update_payment_transaction(cookies , query_params, user_id, order_id , request=None):
        payment_type = query_params.get('payment_type')
        amount = query_params.get('amount')
        transaction_id = cookies.get("transaction_id" , str(uuid.uuid4()))
        amount = amount if payment_type == "google-pay" else float(amount)/100
        customer_email = cookies.get('email')

        try:
            PaymentLogger.log_payment_transaction(transaction_id,payment_type, user_id, order_id, amount,cookies.get('email', None))

            if payment_type == "stripe":
                StripeLogger.log_stripe_transaction({
                    "stripe_id": query_params.get('id'),
                    "amount": amount,
                    "name": query_params.get('name'),
                    "email": query_params.get('email'),
                    "transaction_id": transaction_id
                })
            elif payment_type == "phonepe":
                
                PhonepeLogger.log_phonepe_transaction({
                    "merchantId": query_params.get('merchantId'),
                    "payment_status": query_params.get('code'),
                    "phonepeTransactionId": query_params.get('transactionId'),
                    "providerReferenceId": query_params.get('providerReferenceId'),
                    "checksum": query_params.get('checksum'),
                    "amount": amount,
                    "transaction_id": transaction_id
                } , customer_email)
            elif payment_type == "google-pay":
                GooglePayLogger.log_googlepay_transaction({
                    "token_id": query_params.get('token_id'),
                    "card_last4": query_params.get('card_last4'),
                    "address_city": query_params.get('address_city'),
                    "address_country": query_params.get('address_country'),
                    "address_state": query_params.get('address_state'),
                    "address_zip": query_params.get('address_zip'),
                    "card_brand": query_params.get('card_brand'),
                    "amount": amount,
                    "transaction_id": transaction_id
                }, customer_email)

            print("Payment updated")

        except Exception as e:
            # error_message = f'Payment transaction update failed: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1004)
            PaymentLogger.log_error(transaction_id,payment_type, error_message,
                                  user_id=user_id, order_id=order_id, amount=amount,customer_email=request.COOKIES.get('email', None))
            print(f"Error updating payment transaction: {str(e)}")


# def updatePaymentTransaction(queryParams, userId, order_id):
#     PaymentTransactionManager.update_payment_transaction(queryParams, userId, order_id)

# def updateStripeLogs(data):
#     """Wrapper function to maintain compatibility"""
#     StripeLogger.log_stripe_transaction(data)

# def updatePhonepeLogs(data):
#     """Wrapper function to maintain compatibility"""
#     PhonepeLogger.log_phonepe_transaction(data)

# def updateGooglepayLogs(data):
#     """Wrapper function to maintain compatibility"""
#     GooglePayLogger.log_googlepay_transaction(data)

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_order_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    orders=models.Orders.objects.all().filter(customer_id = customer)
    ordered_products=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_products.append(ordered_product)

    return render(request,'ecom/my_order.html',{'data':zip(ordered_products,orders)})




#--------------for discharge patient bill (pdf) download and printing
import io
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.http import HttpResponse


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def download_invoice_view(request,orderID,productID):
    order=models.Orders.objects.get(id=orderID)
    product=models.Product.objects.get(id=productID)
    mydict={
        'orderDate':order.order_date,
        'customerName':request.user,
        'customerEmail':order.email,
        'customerMobile':order.mobile,
        'shipmentAddress':order.address,
        'orderStatus':order.status,

        'productName':product.name,
        'productImage':product.product_image,
        'productPrice':product.price,
        'productDescription':product.description,


    }
    return render_to_pdf('ecom/download_invoice.html',mydict)






@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    return render(request,'ecom/my_profile.html',{'customer':customer})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def edit_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(request.FILES,instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return HttpResponseRedirect('my-profile')
    return render(request,'ecom/edit_profile.html',context=mydict)



#---------------------------------------------------------------------------------
#------------------------ ABOUT US AND CONTACT US VIEWS START --------------------
#---------------------------------------------------------------------------------
def aboutus_view(request):
    return render(request,'ecom/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name=sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name)+' || '+str(email),message, settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently = False)
            return render(request, 'ecom/contactussuccess.html')
    return render(request, 'ecom/contactus.html', {'form':sub})


class PaymentProcessor:

    def __init__(self, request):
        self.request = request
        self.amount_data = self.calculate_checkout_price()
        self.amount = self.amount_data["total"]
        self.products = self.amount_data["products"]

    def calculate_checkout_price(self):
        total = 0
        products = None
        if 'product_ids' in self.request.COOKIES:
            product_ids = self.request.COOKIES['product_ids']
            if product_ids != "":
                product_id_in_cart = product_ids.split('|')
                products = models.Product.objects.all().filter(id__in=product_id_in_cart)
                for p in products:
                    total = total + p.price

        return {
            'total': total,
            'products': products,
        }

    def validate_cart(self):
        if self.amount <= 0:
            return False, f"Your {ErrorMessageManager.getErrorMessage(1006)}. Please add products to cart before making payment."
        return True, None

    def validate_customer_info(self):
        email = self.request.COOKIES.get('email', None)
        mobile = self.request.COOKIES.get('mobile', None)
        address = self.request.COOKIES.get('address', None)

        if not email or not mobile or not address:
            return False, f"{ErrorMessageManager.getErrorMessage(1007)}. Please fill address form again."
        return True, None

    def get_customer_data(self):
        return {
            'email': self.request.COOKIES.get('email', None),
            'mobile': self.request.COOKIES.get('mobile', None),
            'address': self.request.COOKIES.get('address', None)
        }

class PaymentLogger:

    @staticmethod
    def log_payment_transaction(transaction_id,payment_type, user_id, order_id, amount,customer_email):
        try:
            models.PaymentLogs.objects.create(
                transaction_id=transaction_id,
                payment_type=payment_type,
                user_id=user_id,
                order_id=order_id,
                amount=amount
            )
            print("Payment transaction logged")
        except Exception as e:
            # error_message = f'Payment transaction logging failed: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1005)
            PaymentLogger.log_error(transaction_id,payment_type, error_message,
                                  user_id=user_id, order_id=order_id, amount=amount,customer_email=customer_email)

    @staticmethod
    def log_error(transaction_id,payment_type, error_message, request=None, **kwargs):
        try:
            
            customer_email=request.COOKIES.get('email') if request else kwargs.get('customer_email')
            
            models.PaymentErrorLogs.objects.create(
                transaction_id=transaction_id,
                payment_type=payment_type,
                error_message=error_message,
                user_id=request.user.id if request and request.user.is_authenticated else kwargs.get('user_id'),
                order_id=kwargs.get('order_id'),
                amount=kwargs.get('amount'),
                customer_email=customer_email
            )
            print(f"Payment error logged: {payment_type} - {error_message}")
            
            EmailService(customer_email).sendErrorMessage(error_message)
            
        except Exception as e:
            print(f"Failed to log error: {e}")


def calculateCheckOutPrice(request):
    processor = PaymentProcessor(request)
    return processor.calculate_checkout_price()

def calculate_sha256_string(input_string):
    sha256 = hashes.Hash(hashes.SHA256(), backend=default_backend())
    sha256.update(input_string.encode('utf-8'))
    return sha256.finalize().hex()

def base64_encode(input_dict):
    json_data = jsons.dumps(input_dict)
    data_bytes = json_data.encode('utf-8')
    return base64.b64encode(data_bytes).decode('utf-8')

class StripePaymentProcessor(PaymentProcessor):

    def process_payment(self):
        # validate cart
        is_valid, error_msg = self.validate_cart()
        transaction_id = self.request.COOKIES.get("transaction_id" , str(uuid.uuid4()))
        if not is_valid:
            # error_message = 'Cart is empty'
            error_message = ErrorMessageManager.getErrorMessage(1006)
            PaymentLogger.log_error(transaction_id,'stripe', error_message, self.request, amount=self.amount ,customer_email=self.request.COOKIES.get('email', None))
            messages.error(self.request, error_msg)
            return redirect('cart')

        # validate customer info
        is_valid, error_msg = self.validate_customer_info()
        if not is_valid:
            # error_message = 'Customer information missing'
            error_message = ErrorMessageManager.getErrorMessage(1007)
            PaymentLogger.log_error(transaction_id,'stripe', error_message, self.request, amount=self.amount,customer_email=self.request.COOKIES.get('email', None))
            messages.error(self.request, error_msg)
            return redirect('customer-address')

        customer_data = self.get_customer_data()
        line_items = self.create_line_items()

        try:
            stripe.Customer.create()
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                metadata={
                    'user_email': customer_data['email'],
                    'phone_number': customer_data['mobile'],
                    'address': customer_data['address']
                },
                mode='payment',
                success_url="http://127.0.0.1:8000/validate-payment?stripe-session_id={CHECKOUT_SESSION_ID}",
                cancel_url='http://127.0.0.1:8000/cart',
            )
            return redirect(checkout_session.url)

        except Exception as e:
            # error_message = f'Stripe payment failed: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1008)
            PaymentLogger.log_error(transaction_id,'stripe', error_message, self.request, amount=self.amount,customer_email=self.request.COOKIES.get('email', None))
            messages.error(self.request, f"Stripe payment failed: {str(e)}")
            return redirect('cart')

    def create_line_items(self):
        line_items = []
        for product in self.products:
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': product.price * 100,
                    'product_data': {
                        'name': product.name,
                        'description': product.description,
                    },
                },
                'quantity': 1,
            })
        return line_items

class StripeLogger(PaymentLogger):

    @staticmethod
    def log_stripe_transaction(data):
        try:
            models.StripeLogs.objects.create(**data)
            print("Stripe Log created")
        except Exception as e:
            transaction_id = data.get("transaction_id" , str(uuid.uuid4()))
            # error_message = f'Stripe log creation failed: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1009)
            PaymentLogger.log_error(transaction_id,'stripe', error_message, amount=data.get('amount') , customer_email=data.get('email'))
            print(f"Error creating Stripe log: {str(e)}")


def stripe_payment(request):
    processor = StripePaymentProcessor(request)
    return processor.process_payment()


class PhonepePaymentProcessor(PaymentProcessor):

    def process_payment(self):
        # validate cart
        is_valid, error_msg = self.validate_cart()
        transaction_id = self.request.COOKIES.get("transaction_id" , str(uuid.uuid4()))
        customer_email=self.request.COOKIES.get('email', None)
        if not is_valid:
            # error_message = 'Cart is empty'
            error_message = ErrorMessageManager.getErrorMessage(1006)
            PaymentLogger.log_error(transaction_id,'phonepe', error_message, self.request, amount=self.amount,customer_email=customer_email)
            messages.error(self.request, error_msg)
            return redirect('cart')

        # validate customer info
        is_valid, error_msg = self.validate_customer_info()
        if not is_valid:
            # error_message = 'Customer information missing'
            error_message = ErrorMessageManager.getErrorMessage(1007)
            PaymentLogger.log_error(transaction_id,'phonepe', error_message, self.request, amount=self.amount,customer_email=customer_email)
            messages.error(self.request, error_msg)
            return redirect('customer-address')

        try:
            # transaction_id = shortuuid.uuid()
            payload = self.create_payment_payload(transaction_id)

            base64String = base64_encode(payload)
            mainString = base64String + "/pg/v1/pay" + "96434309-7796-489d-8924-ab56988a6076"
            sha256Val = calculate_sha256_string(mainString)
            checkSum = sha256Val + '###1'

            response = requests.post(
                'https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/pay',
                headers={'Content-Type': 'application/json', 'X-VERIFY': checkSum, 'accept': 'application/json'},
                json={'request': base64String},
                timeout=30
            )

            responseData = response.json()
            if responseData.get('success') and 'data' in responseData and 'instrumentResponse' in responseData['data']:
                return redirect(responseData['data']['instrumentResponse']['redirectInfo']['url'])
            else:
                error_msg = f'{ErrorMessageManager.getErrorMessage(1016)}: {responseData.get("message", "Unknown error")}'
                PaymentLogger.log_error(transaction_id,'phonepe', error_msg, self.request, amount=self.amount,customer_email=customer_email)
                messages.error(self.request, "PhonePe payment initiation failed. Please try again.")
                return redirect('cart')

        except Exception as e:
            # error_message = f'PhonePe payment error: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1010)
            PaymentLogger.log_error(transaction_id,'phonepe', error_message, self.request, amount=self.amount,customer_email=customer_email)
            messages.error(self.request, "Failed to initialize payment. Please try again.")
            return redirect('cart')

    def create_payment_payload(self, transaction_id):
        return {
            "merchantId": "PGTESTPAYUAT86",
            "merchantTransactionId": transaction_id,
            "merchantUserId": f"MUID{self.request.user.id if self.request.user.is_authenticated else 'GUEST'}",
            "amount": int(self.amount * 100),
            "redirectUrl": self.request.build_absolute_uri('/validate-payment/'),
            "redirectMode": "POST",
            "callbackUrl": self.request.build_absolute_uri('/cart'),
            "mobileNumber": "9999999999",
            "paymentInstrument": {"type": "PAY_PAGE"}
        }

class PhonepeLogger(PaymentLogger):

    @staticmethod
    def log_phonepe_transaction(data , customer_email):
        try:
            models.PhonepeLogs.objects.create(**data)
            print("PhonePe Log created")
        except Exception as e:
            transaction_id = data.get("transaction_id" , str(uuid.uuid4()))
            # error_message = f'PhonePe log creation failed: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1011)
            PaymentLogger.log_error(transaction_id,'phonepe', error_message, amount=data.get('amount'),customer_email=customer_email)
            print(f"Error creating PhonePe log: {str(e)}")


def phonepe_payment(request):
    processor = PhonepePaymentProcessor(request)
    return processor.process_payment()


class GooglePayPaymentProcessor(PaymentProcessor):

    def process_payment(self):
        transaction_id = self.request.COOKIES.get("transaction_id" , str(uuid.uuid4()))
        customer_email=self.request.COOKIES.get('email', None)
        if self.request.method != "POST":
            # error_message = 'Invalid request method'
            error_message = ErrorMessageManager.getErrorMessage(1012)
            PaymentLogger.log_error(transaction_id,'google-pay', error_message, self.request,customer_email=customer_email)
            return JsonResponse({"error": "Invalid request method"}, status=400)

        try:
            payment_data = self.request.POST.get("paymentData")
            if not payment_data:
                # error_message = 'Missing payment data'
                error_message = ErrorMessageManager.getErrorMessage(1013)
                PaymentLogger.log_error(transaction_id,'google-pay', error_message, self.request,customer_email=customer_email)
                return JsonResponse({"error": "Missing payment data"}, status=400)

            if self.amount <= 0:
                # error_message = 'Cart is empty'
                error_message = ErrorMessageManager.getErrorMessage(1006)
                PaymentLogger.log_error(transaction_id,'google-pay', error_message, self.request, amount=self.amount,customer_email=customer_email)
                return JsonResponse({"error": "Invalid amount"}, status=400)

            payment_json = jsons.loads(payment_data)
            token_json = jsons.loads(payment_json['paymentMethodData']['tokenizationData']['token'])
            stripe_token = token_json['id']

            charge = stripe.Charge.create(
                amount=int(self.amount * 100),
                currency='inr',
                description='Google Pay Demo Payment',
                source=stripe_token
            )

            if charge.status == "succeeded":
                url = self.construct_redirect_url("google-pay", payment_json, settings.HOST+"payment-success", self.amount)
                return redirect(url)
            else:
                # error_message = f'Payment failed with status: {charge.status}'
                error_message = ErrorMessageManager.getErrorMessage(1001)
                PaymentLogger.log_error(transaction_id,'google-pay', error_message,
                                      self.request, amount=self.amount,customer_email=customer_email)
                return JsonResponse({"error": "Payment failed."}, status=400)

        except Exception as e:
            # error_message = f'Google Pay error: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1014)
            PaymentLogger.log_error(transaction_id,'google-pay', error_message, self.request,customer_email=customer_email)
            return JsonResponse({"error": str(e)}, status=400)

    def construct_redirect_url(self, payment_type, data, redirect_url, gpay_amount):
        url = redirect_url
        tokenizationData = jsons.loads(data['paymentMethodData']['tokenizationData']['token'])
        token_id = tokenizationData['id']
        card_last4 = tokenizationData['card']['dynamic_last4']
        address_city = tokenizationData['card']['address_city']
        address_country = tokenizationData['card']['address_country']
        address_state = tokenizationData['card']['address_state']
        address_zip = tokenizationData['card']['address_zip']
        card_brand = tokenizationData['card']['brand']

        url += f"?payment_type={payment_type}&amount={gpay_amount}&token_id={token_id}&card_last4={card_last4}&address_city={address_city}&address_country={address_country}&address_state={address_state}&address_zip={address_zip}&card_brand={card_brand}"

        return url

class GooglePayLogger(PaymentLogger):

    @staticmethod
    def log_googlepay_transaction(data, customer_email):
        try:
            models.GooglepayLogs.objects.create(**data)
            print("Google Pay Log created")
        except Exception as e:
            transaction_id = data.get("transaction_id" , str(uuid.uuid4()))
            # error_message = f'Google Pay log creation failed: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1015)
            PaymentLogger.log_error(transaction_id,'google-pay', error_message, amount=data.get('amount'),customer_email=customer_email)
            print(f"Error creating Google Pay log: {str(e)}")


@csrf_exempt
def gpay_payment(request):
    processor = GooglePayPaymentProcessor(request)
    return processor.process_payment()
    

class PaymentValidator:

    @staticmethod
    def validate_payment(request):
        print("Validate GET params:", request.GET)
        print("Validate POST params:", request.POST)

        if request.GET.get('stripe-session_id'):
            session_id = request.GET.get('stripe-session_id')
            session = stripe.checkout.Session.retrieve(session_id)
            url = PaymentRedirectManager.construct_redirect_url("stripe", session, settings.HOST+"payment-success")
            return redirect(url)

        if request.POST.get('merchantId'):
            url = PaymentRedirectManager.construct_redirect_url("phonepe", request.POST, settings.HOST+"payment-success")
            return redirect(url)


@csrf_exempt
def validate_payment(request):
    return PaymentValidator.validate_payment(request)

class PaymentRedirectManager:

    @staticmethod
    def construct_redirect_url(payment_type, data, redirect_url, gpay_amount=None):
        url = redirect_url

        if payment_type == "google-pay":
            tokenizationData = jsons.loads(data['paymentMethodData']['tokenizationData']['token'])
            token_id = tokenizationData['id']
            card_last4 = tokenizationData['card']['dynamic_last4']
            address_city = tokenizationData['card']['address_city']
            address_country = tokenizationData['card']['address_country']
            address_state = tokenizationData['card']['address_state']
            address_zip = tokenizationData['card']['address_zip']
            card_brand = tokenizationData['card']['brand']

            url += f"?payment_type={payment_type}&amount={gpay_amount}&token_id={token_id}&card_last4={card_last4}&address_city={address_city}&address_country={address_country}&address_state={address_state}&address_zip={address_zip}&card_brand={card_brand}"

        elif payment_type == "stripe":
            id = data['id']
            amount = data['amount_total']
            name = data['customer_details']['name']
            email = data['customer_details']['email']

            url += f"?payment_type={payment_type}&id={id}&amount={amount}&email={email}&name={name}"

        elif payment_type == "phonepe":
            code = data.get('code')
            merchantId = data.get('merchantId')
            transactionId = data.get('transactionId')
            amount = data.get('amount')
            providerReferenceId = data.get('providerReferenceId')
            checksum = data.get('checksum')

            url += f"?payment_type={payment_type}&code={code}&merchantId={merchantId}&transactionId={transactionId}&amount={amount}&providerReferenceId={providerReferenceId}&checksum={checksum}"

        return url


# def construct_redirect_url(payment_type, data, redirect_url, gpay_amount=None):
#     return PaymentRedirectManager.construct_redirect_url(payment_type, data, redirect_url, gpay_amount)

def log_payment_error(transaction_id,payment_type, error_message, request=None, **kwargs):
    PaymentLogger.log_error(transaction_id,payment_type, error_message, request, **kwargs , customer_email=request.COOKIES.get('email', None))
    
    
class ErrorMessageManager:
    
    @staticmethod
    def getErrorMessage(error_id):
        error_msg_object = models.ErrorMessages.objects.get(error_id=error_id)
        # print(error_msg_object.error_message)
        return error_msg_object.error_message

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class EmailService:
    
    def __init__(self , mail):
        self.fromMail = 'spmproject66@gmail.com' 
        self.appPassword = 'mqot ougz ojjl vwcl'
        self.toMail = mail
    
        
    def sendErrorMessage(self , error_message):
        server = smtplib.SMTP('smtp.gmail.com' , 587)
        server.starttls()
        
        server.login(self.fromMail, self.appPassword)
        
        html_content = f"""
        <html>
        <body>
            <p style="font-size:20px; font-weight: bold;">Order Purchase Failed!</p>
            <p style="font-size:16px; font-weight: bold;">Error: {error_message}</p>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = "Order Purchase Failed"
        msg['From'] = self.fromMail
        msg['To'] = self.toMail
        msg.attach(MIMEText(html_content, 'html'))
        
        server.sendmail(self.fromMail, self.toMail, msg.as_string())
        server.quit()
        print("Email Sent")


def face_login(request):
    return render(request , 'ecom/face_login.html')


import cv2
import numpy as np
from .FaceRecognition import live_recognition , capture_images , encode_faces
from django.contrib.auth import login
import time

@csrf_exempt
def get_res(request):
    if request.method == "POST":
        data = json.loads(request.body)
        image_data = data["image"]
        header, base64_data = image_data.split(",", 1)
        image_bytes = base64.b64decode(base64_data)
        image_cv = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        processed_image , detected_userid = live_recognition.live_face_recognition(image_cv)
        # _ , buffer = cv2.imencode('.jpg' , processed_image)
        # jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        # resData = {
        #     'res': 'Image received and saved',
        #     'parsed_image': jpg_as_text,
        # }
        
        resData = None
        
        if detected_userid.lower() == "uknown":
            resData = {
                'user_id': 'unknown',
                'username': 'unknown',
                'isloggedin':False,
            }
            return JsonResponse(resData) 
        
        users = models.User.objects.all().values('id', 'first_name')
        for user in users:
            if str(user['id']) == detected_userid:
                detected_userid = int(detected_userid)
                detected_username = user['first_name']
                detected_user_entry = models.User.objects.get(id=detected_userid)
                login(request, detected_user_entry)
                print("-------------------------------------")
                print(detected_user_entry)
                resData = {
                    'user_id': detected_userid,
                    'username': detected_username,
                    'isloggedin':True,
                }
                break
            else:
                resData = {
                    'user_id': 'unknown',
                    'username': 'unknown',
                    'isloggedin':False,
                }
        # print(users)
        # print("Detected User: " + detected_userid)
        
        
        return JsonResponse(resData)
    return JsonResponse({"res": "hello"})

@csrf_exempt
def save_frame(request):
    
    
    resData = {
        'user_id': 'data["userid"]',
        'isFrameSaved':False,
    }
    
    if request.method == "POST":
        data = json.loads(request.body)
        image_data = data["image"]
        header, base64_data = image_data.split(",", 1)
        image_bytes = base64.b64decode(base64_data)
        image_cv = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        # processed_image , detected_userid = live_recognition.live_face_recognition(image_cv)
        capture_images.save_frame(image_cv , data["userid"] , data["count"])
        resData = {
            'user_id': 'data["userid"]',
            'isFrameSaved':True,
        }
        time.sleep(1)
        
        if(data["count"]+1 == 5):
            encode_faces.encode_faces()
        
        return JsonResponse(resData)
    time.sleep(1)
    return JsonResponse(resData)
    # return JsonResponse({"res": "hello"})