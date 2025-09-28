from django.shortcuts import render,redirect
from . import forms,models
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect,HttpResponse
# from django.core.mail import send_mail
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from django.conf import settings
from django.db import transaction

from .ResumeParser.db_operations import *

#   Stripe imports
import stripe

#   PAYPAL imports
import uuid

#   Phonepe imports

import jsons
import base64
import requests
from cryptography.hazmat.primitives import hashes
from django.views.decorators.csrf import csrf_exempt
from cryptography.hazmat.backends import default_backend
from django.http import JsonResponse
import json
from functools import wraps
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
import secrets

# Payment validation decorator
def validated_payment_required(f):
    @wraps(f)
    def decorated(request, *args, **kwargs):
        validation_token = request.GET.get('validation_token')
        payment_type = request.GET.get('payment_type')
        
        if not validation_token or not payment_type:
            transaction_id = request.COOKIES.get('transaction_id', str(uuid.uuid4()))
            error_message = "Unauthorized access to payment success page - missing validation parameters"
            log_payment_error(transaction_id, payment_type or 'unknown', error_message, request)
            messages.error(request, "Invalid payment session. Please complete payment process properly.")
            return redirect('cart')
        
        try:
            payment_session = models.PaymentSession.objects.get(
                validation_token=validation_token,
                payment_type=payment_type
            )
            

            if payment_session.is_expired():
                payment_session.mark_as_failed("Session expired")
                error_message = "Payment session expired"
                log_payment_error(payment_session.transaction_id, payment_type, error_message, request)
                messages.error(request, "Payment session expired. Please try again.")
                return redirect('cart')
            

            if not payment_session.is_validated:
                error_message = "Payment not validated"
                log_payment_error(payment_session.transaction_id, payment_type, error_message, request)
                messages.error(request, "Payment validation failed. Please complete payment process.")
                return redirect('cart')
            

            if payment_session.status == 'COMPLETED':
                error_message = "Payment session already completed"
                log_payment_error(payment_session.transaction_id, payment_type, error_message, request)
                messages.warning(request, "This payment has already been processed.")
                return redirect('my-order')
            

            request.payment_session = payment_session
            
 
            response = f(request, *args, **kwargs)
            

            if hasattr(request, 'payment_session') and request.payment_session.status == 'VALIDATED':
                request.payment_session.mark_as_completed()
            
            return response
            
        except models.PaymentSession.DoesNotExist:

            error_message = "Invalid validation token for payment session"
            transaction_id = request.COOKIES.get('transaction_id', str(uuid.uuid4()))
            log_payment_error(transaction_id, payment_type, error_message, request)
            messages.error(request, "Invalid payment session. Please complete payment process properly.")
            return redirect('cart')
        
        except Exception as e:

            error_message = f"Payment validation error: {str(e)}"
            transaction_id = request.COOKIES.get('transaction_id', str(uuid.uuid4()))
            log_payment_error(transaction_id, payment_type, error_message, request)
            messages.error(request, "Payment validation failed. Please try again.")
            return redirect('cart')
    
    return decorated

def create_payment_session(transaction_id, payment_type, user_id, customer_email, amount, cart_data, shipping_details, expires_in_minutes=30):

    session_id = str(uuid.uuid4())
    validation_token = secrets.token_urlsafe(32)
    

    expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)
    

    payment_session = models.PaymentSession.objects.create(
        session_id=session_id,
        transaction_id=transaction_id,
        payment_type=payment_type,
        user_id=user_id,
        customer_email=customer_email,
        amount=amount,
        validation_token=validation_token,
        cart_data=cart_data,
        shipping_details=shipping_details,
        status='PENDING',
        expires_at=expires_at
    )
    
    return payment_session

stripe.api_key = settings.STRIPE_API
def home_view(request):
    products_list = models.Product.objects.all().order_by('id')

    # Pagination - 9 products per page
    paginator = Paginator(products_list, 9)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    if str(request.user) == "AnonymousUser" or is_admin(request.user):
        if 'product_ids' in request.COOKIES:
            product_ids = request.COOKIES['product_ids']
            counter=product_ids.split('|')
            product_count_in_cart=len(set(counter))
        else:
            product_count_in_cart=0
    else:
        cart_data = get_cart_context(request)
        product_count_in_cart = cart_data["product_count_in_cart"]
        
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'ecom/index.html',{'products':products,'product_count_in_cart':product_count_in_cart})


#for showing login button for admin
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

def is_admin(user):
    return user.is_staff or user.is_superuser



#---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,CUSTOMER
def afterlogin_view(request):
    if is_customer(request.user):
        sync_cookie_cart_to_db(request)
        return redirect('customer-home')
    elif is_admin(request.user):
        return redirect('admin-dashboard')
    
    return redirect('customerlogin')

#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def admin_dashboard_view(request):
    # for cards on dashboard
    customercount=models.Customer.objects.all().count()
    productcount=models.Product.objects.all().count()
    ordercount=models.Orders.objects.all().count()

    # for recent order tables
    orders = models.Orders.objects.all().order_by('-id')[:10]
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
@user_passes_test(is_admin , login_url='adminlogin')
def view_customer_view(request):
    customers=models.Customer.objects.all()
    
    # Pagination - 10 orders per page 
    paginator = Paginator(customers, 10) 
    page_number = request.GET.get('page') 
    customers = paginator.get_page(page_number)
    
    return render(request,'ecom/view_customer.html',{'customers':customers})

# admin delete customer
@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def delete_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('view-customer')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
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
@user_passes_test(is_admin , login_url='adminlogin')
def admin_products_view(request):
    products=models.Product.objects.all()
    
    # Pagination - 10 products per page
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    return render(request,'ecom/admin_products.html',{'products':products})


# admin add product by clicking on floating button
@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def admin_add_product_view(request):
    productForm=forms.ProductForm()
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST, request.FILES)
        if productForm.is_valid():
            productForm.save()
        return HttpResponseRedirect('admin-products')
    return render(request,'ecom/admin_add_products.html',{'productForm':productForm})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def delete_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    product.delete()
    return redirect('admin-products')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
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
@user_passes_test(is_admin , login_url='adminlogin')
def admin_view_booking_view(request):
    orders = models.Orders.objects.all()[::-1]
    ordered_products = []
    ordered_bys = []

    for order in orders:
        ordered_product = models.Product.objects.filter(id=order.product.id)
        ordered_by = models.Customer.objects.filter(id=order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)

    # Pagination - 10 orders per page
    paginator = Paginator(list(zip(ordered_products, ordered_bys, orders)), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render( request,'ecom/admin_view_booking.html',{'data': page_obj})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def delete_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    order.delete()
    return redirect('admin-view-booking')

# for changing status of order (pending,delivered...)
@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def update_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    orderForm=forms.OrderForm(instance=order)
    if request.method=='POST':
        orderForm=forms.OrderForm(request.POST,instance=order)
        if orderForm.is_valid():
            orderForm.save()
            return redirect('admin-view-booking')
    return render(request,'ecom/update_order.html',{'orderForm':orderForm})

def admin_logs_view(request):
    mydict = dict()
    
    payment_logs_count = models.PaymentLogs.objects.all().count
    stripe_logs_count = models.StripeLogs.objects.all().count
    phonepe_logs_count = models.PhonepeLogs.objects.all().count
    gpay_logs_count = models.GooglepayLogs.objects.all().count
    payment_error_logs_count = models.PaymentErrorLogs.objects.all().count
    
    mydict["payment_logs_count"] = payment_logs_count
    mydict["stripe_logs_count"] = stripe_logs_count
    mydict["phonepe_logs_count"] = phonepe_logs_count
    mydict["gpay_logs_count"] = gpay_logs_count
    mydict["payment_error_logs_count"] = payment_error_logs_count
    
    return render(request , "ecom/admin_logs.html" , context=mydict)

def admin_payment_logs_view(request):
    mydict = dict()
    
    payment_logs = models.PaymentLogs.objects.all().order_by('id')
    
    # Pagination - 9 products per page
    paginator = Paginator(payment_logs, 10)
    page_number = request.GET.get('page')
    payment_logs = paginator.get_page(page_number)
    
    mydict["payment_logs"] = payment_logs
    return render(request , "ecom/admin_payment_logs.html" , context=mydict)

def admin_stripe_logs_view(request):
    
    mydict = dict()
    
    stripe_logs = models.StripeLogs.objects.all().order_by('id')
    
    # Pagination - 9 products per page
    paginator = Paginator(stripe_logs, 10)
    page_number = request.GET.get('page')
    stripe_logs = paginator.get_page(page_number)
    
    mydict["stripe_logs"] = stripe_logs
    
    return render(request , "ecom/admin_stripe_logs.html" , context=mydict)

def admin_phonepe_logs_view(request):
    
    mydict = dict()
    
    phonepe_logs = models.PhonepeLogs.objects.all().order_by('id')
    
    # Pagination - 9 products per page
    paginator = Paginator(phonepe_logs, 10)
    page_number = request.GET.get('page')
    phonepe_logs = paginator.get_page(page_number)
    
    mydict["phonepe_logs"] = phonepe_logs
    
    return render(request , "ecom/admin_phonepe_logs.html" , context=mydict)

def admin_gpay_logs_view(request):
    
    mydict = dict()
    
    gpay_logs = models.GooglepayLogs.objects.all().order_by('id')
    
    # Pagination - 9 products per page
    paginator = Paginator(gpay_logs, 10)
    page_number = request.GET.get('page')
    gpay_logs = paginator.get_page(page_number)
    
    mydict["gpay_logs"] = gpay_logs
    
    return render(request , "ecom/admin_gpay_logs.html" , context=mydict)

def admin_payment_error_logs_view(request):
    
    mydict = dict()
    
    payment_error_logs = models.PaymentErrorLogs.objects.all().order_by('id')
    
    # Pagination - 9 products per page
    paginator = Paginator(payment_error_logs, 10)
    page_number = request.GET.get('page')
    payment_error_logs = paginator.get_page(page_number)
    
    mydict["payment_error_logs"] = payment_error_logs
    
    return render(request , "ecom/admin_payment_error_logs.html" , context=mydict)



#---------------------------------------------------------------------------------
#------------------------ PUBLIC CUSTOMER RELATED VIEWS START ---------------------
#---------------------------------------------------------------------------------
def search_view(request):
    # whatever user write in search box we get in query
    query = request.GET['query']
    products_list = models.Product.objects.all().filter(name__icontains=query).order_by('id')

    # Pagination - 9 products per page
    paginator = Paginator(products_list, 9)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    if str(request.user) == "AnonymousUser":
        if 'product_ids' in request.COOKIES:
            product_ids = request.COOKIES['product_ids']
            counter=product_ids.split('|')
            product_count_in_cart=len(set(counter))
        else:
            product_count_in_cart=0
    else:
        cart_data = get_cart_context(request)
        product_count_in_cart = cart_data["product_count_in_cart"]

    # word variable will be shown in html when user click on search button
    word="Searched Result :"

    if request.user.is_authenticated:
        return render(request,'ecom/customer_home.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart,'query':query})
    return render(request,'ecom/index.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart,'query':query})


def get_cart_count(product_ids: str):
    counter = product_ids.split('|')
    return len(counter)

def get_cart_context(request):
    total = 0
    products_with_quantity = []

    if request.user.is_authenticated:
        customer = models.Customer.objects.get(user=request.user)
        cart_items = models.Cart.objects.filter(customer=customer)

        for item in cart_items:
            subtotal = item.product.price * item.quantity
            total += subtotal
            products_with_quantity.append({
                'product': item.product,
                'quantity': item.quantity,
                'subtotal': subtotal
            })

        return {
            'products_with_quantity': products_with_quantity,
            'total': total,
            'product_count_in_cart': cart_items.count(),
            'cart_source': 'db'
        }

    elif 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_dict = {
            int(pid): int(count)
            for pid, count in (pair.split(':') for pair in product_ids.split('|'))
        }

        products = models.Product.objects.filter(id__in=product_dict.keys())
        for p in products:
            quantity = product_dict.get(p.id, 1)
            subtotal = p.price * quantity
            total += subtotal
            products_with_quantity.append({
                'product': p,
                'quantity': quantity,
                'subtotal': subtotal
            })

        return {
            'products_with_quantity': products_with_quantity,
            'total': total,
            'product_count_in_cart': len(product_dict),
            'cart_source': 'cookie',
            'updated_cookie_value': '|'.join(f"{pid}:{count}" for pid, count in product_dict.items())
        }

    return {
        'products_with_quantity': [],
        'total': 0,
        'product_count_in_cart': 0,
        'cart_source': 'none'
    }


# any one can add product to cart, no need of signin
def add_to_cart_view(request, pk):
    pk = int(pk)

    if request.user.is_authenticated:
        customer = models.Customer.objects.get(user=request.user)
        product = models.Product.objects.get(id=pk)

        cart_item, created = models.Cart.objects.get_or_create(
            customer=customer,
            product=product,
            defaults={'quantity': 1, 'total_price': product.price}
        )
        if not created:
            cart_item.quantity += 1
            cart_item.total_price = cart_item.quantity * product.price
            cart_item.save()

    else:
        if 'product_ids' in request.COOKIES:
            product_ids = add_product_to_count(request.COOKIES['product_ids'], pk)
        else:
            product_ids = f"{pk}:1"

        response = redirect('')  # 👈 Redirect instead of render
        response.set_cookie('product_ids', product_ids)
        return response

    return redirect('')  # 👈 Redirect instead of render


def add_product_to_count(product_ids, new_product_id):
    print("product_ids:", product_ids)

    # Parse into dictionary
    product_dict = {
        int(pid): int(count)
        for pid, count in (pair.split(':') for pair in product_ids.split('|'))
    }

    print("Parsed dict:", product_dict)

    # Add or update the new product
    if new_product_id in product_dict:
        product_dict[new_product_id] += 1
    else:
        product_dict[new_product_id] = 1

    print("Updated dict:", product_dict)

    # Convert back to string format
    updated_string = '|'.join(f"{pid}:{count}" for pid, count in product_dict.items())
    print("Updated string:", updated_string)

    return updated_string
        
        

# for checkout of cart
def cart_view(request):
    context = get_cart_context(request)
    response = render(request, 'ecom/cart.html', context)

    # Optional: clear cookie if user is logged in
    if context['cart_source'] == 'cookie' and request.user.is_authenticated:
        response.delete_cookie('product_ids')

    return response

def remove_from_cart_view(request, pk):
    pk = int(pk)

    if request.user.is_authenticated:
        customer = models.Customer.objects.get(user=request.user)
        models.Cart.objects.filter(customer=customer, product_id=pk).delete()

    elif 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_dict = {
            int(pid): int(count)
            for pid, count in (pair.split(':') for pair in product_ids.split('|'))
        }
        if pk in product_dict:
            del product_dict[pk]
        updated_cookie_value = '|'.join(f"{pid}:{count}" for pid, count in product_dict.items())
    else:
        updated_cookie_value = None

    # context = get_cart_context(request)
    # response = render(request, 'ecom/cart.html', context)
    response = redirect('cart')

    if request.user.is_authenticated or not updated_cookie_value:
        response.delete_cookie('product_ids')
    elif updated_cookie_value:
        response.set_cookie('product_ids', updated_cookie_value)

    return response

def increment_cart_item_view(request, pk):
    pk = int(pk)

    if request.user.is_authenticated:
        customer = models.Customer.objects.get(user=request.user)
        cart_item, created = models.Cart.objects.get_or_create(
            customer=customer,
            product_id=pk,
            defaults={'quantity': 1, 'total_price': models.Product.objects.get(id=pk).price}
        )
        if not created:
            cart_item.quantity += 1
            cart_item.total_price = cart_item.quantity * cart_item.product.price
            cart_item.save()

    elif 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_dict = {
            int(pid): int(count)
            for pid, count in (pair.split(':') for pair in product_ids.split('|'))
        }
        product_dict[pk] = product_dict.get(pk, 0) + 1
        updated_cookie_value = '|'.join(f"{pid}:{count}" for pid, count in product_dict.items())
    else:
        updated_cookie_value = f"{pk}:1"

    # context = get_cart_context(request)
    # response = render(request, 'ecom/cart.html', context)
    response = redirect('cart')

    if request.user.is_authenticated:
        response.delete_cookie('product_ids')
    else:
        response.set_cookie('product_ids', updated_cookie_value)

    return response 


def decrement_cart_item_view(request, pk):
    pk = int(pk)

    if request.user.is_authenticated:
        customer = models.Customer.objects.get(user=request.user)
        try:
            cart_item = models.Cart.objects.get(customer=customer, product_id=pk)
            cart_item.quantity -= 1
            if cart_item.quantity <= 0:
                cart_item.delete()
            else:
                cart_item.total_price = cart_item.quantity * cart_item.product.price
                cart_item.save()
        except models.Cart.DoesNotExist:
            pass

    elif 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_dict = {
            int(pid): int(count)
            for pid, count in (pair.split(':') for pair in product_ids.split('|'))
        }
        if pk in product_dict:
            product_dict[pk] -= 1
            if product_dict[pk] <= 0:
                del product_dict[pk]
        updated_cookie_value = '|'.join(f"{pid}:{count}" for pid, count in product_dict.items())
    else:
        updated_cookie_value = None

    # context = get_cart_context(request)
    # response = render(request, 'ecom/cart.html', context)
    response = redirect('cart')

    if request.user.is_authenticated or not updated_cookie_value:
        response.delete_cookie('product_ids')
    elif updated_cookie_value:
        response.set_cookie('product_ids', updated_cookie_value)

    return response
    
def clear_cart_view(request):
    if str(request.user) != "AnonymousUser":
        customer = models.Customer.objects.get(user=request.user)
        models.Cart.objects.filter(customer=customer).delete()
        product_count_in_cart = 0
        return render(request, 'ecom/cart.html', {
            'products_with_quantity': [],
            'total': 0,
            'product_count_in_cart': product_count_in_cart
        })
    else:
        response = render(request, 'ecom/cart.html', {
            'products_with_quantity': [],
            'total': 0,
            'product_count_in_cart': 0
        })
        response.delete_cookie('product_ids')
        return response
    
def sync_cookie_cart_to_db(request):
    if 'product_ids' in request.COOKIES and str(request.user) != "AnonymousUser":
        product_ids = request.COOKIES['product_ids']
        product_dict = {
            int(pid): int(count)
            for pid, count in (pair.split(':') for pair in product_ids.split('|'))
        }

        customer = models.Customer.objects.get(user=request.user)

        for pid, count in product_dict.items():
            product = models.Product.objects.get(id=pid)

            cart_item, created = models.Cart.objects.get_or_create(
                customer=customer,
                product=product,
                defaults={'quantity': count, 'total_price': product.price * count}
            )

            if not created:
                cart_item.quantity = max(cart_item.quantity, count)  # or += count
                cart_item.total_price = cart_item.quantity * product.price
                cart_item.save()

        response = redirect('cart')  # or wherever you want to land post-login
        response.delete_cookie('product_ids')
        return response



#---------------------------------------------------------------------------------
#------------------------ CUSTOMER RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='customerlogin')
@user_passes_test(is_customer , login_url='customerlogin')
def customer_home_view(request):
    products_list = models.Product.objects.all().order_by('id')

    # Pagination - 9 products per page
    paginator = Paginator(products_list, 9)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    if str(request.user) == "AnonymousUser":
        if 'product_ids' in request.COOKIES:
            product_ids = request.COOKIES['product_ids']
            counter=product_ids.split('|')
            product_count_in_cart=len(set(counter))
        else:
            product_count_in_cart=0
    else:
        cart_data = get_cart_context(request)
        product_count_in_cart = cart_data["product_count_in_cart"]
    
    return render(request,'ecom/customer_home.html',{'products':products,'product_count_in_cart':product_count_in_cart})



# shipment address before placing order
@login_required(login_url='customerlogin')
def customer_address_view(request):
    cart_context = get_cart_context(request)
    product_in_cart = cart_context['product_count_in_cart'] > 0

    addressForm = forms.AddressForm()
    if request.method == 'POST':
        addressForm = forms.AddressForm(request.POST)
        if addressForm.is_valid() and product_in_cart:
            email = addressForm.cleaned_data['Email']
            mobile = addressForm.cleaned_data['Mobile']
            address = addressForm.cleaned_data['Address']

            transaction_id = str(uuid.uuid4())

            response = render(request, 'ecom/payment.html', {
                'total': cart_context['total'],
                'products_with_quantity': cart_context['products_with_quantity'],
                'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY
            })
            response.set_cookie('email', email)
            response.set_cookie('mobile', mobile)
            response.set_cookie('address', address)
            response.set_cookie('transaction_id', transaction_id)
            return response

    return render(request, 'ecom/customer_address.html', {
        'addressForm': addressForm,
        'product_in_cart': product_in_cart,
        'product_count_in_cart': cart_context['product_count_in_cart']
    })




@csrf_exempt
@validated_payment_required
def payment_success_view(request):
    customer = None
    if request.user.is_authenticated:
        try:
            customer = models.Customer.objects.get(user=request.user)
        except models.Customer.DoesNotExist:
            pass

    cart_context = get_cart_context(request)
    products_with_quantity = cart_context['products_with_quantity']

    email = request.COOKIES.get('email')
    mobile = request.COOKIES.get('mobile')
    address = request.COOKIES.get('address')
    transaction_id = request.COOKIES.get("transaction_id", str(uuid.uuid4()))
    order_id = str(uuid.uuid4())

    if not products_with_quantity:
        error_message = ErrorMessageManager.getErrorMessage(1006)
        log_payment_error(transaction_id, request.GET.get('payment_type', 'unknown'),
                          error_message, request)
        return render(request, 'ecom/payment_failed.html')

    try:
        with transaction.atomic():
            for item in products_with_quantity:
                product = item['product']
                quantity = item['quantity']

                models.Orders.objects.create(
                    customer=customer,
                    product=product,
                    status='Pending',
                    email=email,
                    mobile=mobile,
                    address=address,
                    order_id=order_id,
                    transaction_id=transaction_id,
                    quantity=quantity
                )

                models.Cart.objects.filter(customer=customer, product=product).delete()

        # Log payment transaction after all orders succeed
        PaymentTransactionManager.update_payment_transaction(
            request.COOKIES, request.GET, request.user.id, order_id
        )

    except Exception as e:
        error_message = ErrorMessageManager.getErrorMessage(1002)  # order creation failed
        log_payment_error(transaction_id, request.GET.get('payment_type', 'unknown'),
                          error_message, request, order_id=order_id)
        return render(request, 'ecom/payment_failed.html')

    # If everything succeeds → show success page
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
#     StripeLogger.log_stripe_transaction(data)

# def updatePhonepeLogs(data):
#     PhonepeLogger.log_phonepe_transaction(data)

# def updateGooglepayLogs(data):
#     GooglePayLogger.log_googlepay_transaction(data)

@login_required(login_url='customerlogin')
@user_passes_test(is_customer , login_url='customerlogin')
def my_order_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    orders=models.Orders.objects.all().filter(customer_id = customer)
    ordered_products=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_products.append(ordered_product)
        
    # Pagination - 9 orders per page
    paginator = Paginator(list(zip(ordered_products, orders))[::-1], 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if str(request.user) == "AnonymousUser":
        if 'product_ids' in request.COOKIES:
            product_ids = request.COOKIES['product_ids']
            counter=product_ids.split('|')
            product_count_in_cart=len(set(counter))
        else:
            product_count_in_cart=0
    else:
        cart_data = get_cart_context(request)
        product_count_in_cart = cart_data["product_count_in_cart"]

    return render(request,'ecom/my_order.html',{'data':page_obj , 'product_count_in_cart' : product_count_in_cart})




#--------------for bill (pdf) download and printing
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
@user_passes_test(is_customer , login_url='customerlogin')
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
@user_passes_test(is_customer , login_url='customerlogin')
def my_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    
    if str(request.user) == "AnonymousUser":
        if 'product_ids' in request.COOKIES:
            product_ids = request.COOKIES['product_ids']
            counter=product_ids.split('|')
            product_count_in_cart=len(set(counter))
        else:
            product_count_in_cart=0
    else:
        cart_data = get_cart_context(request)
        product_count_in_cart = cart_data["product_count_in_cart"]
    
    return render(request,'ecom/my_profile.html',{'customer':customer , 'product_count_in_cart' : product_count_in_cart})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer , login_url='customerlogin')
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




class PaymentProcessor:

    def __init__(self, request):
        self.request = request
        self.amount_data = self.calculate_checkout_price()
        self.amount = self.amount_data["total"]
        self.products_with_quantity = self.amount_data["products_with_quantity"]

    def calculate_checkout_price(self):
        cart_context = get_cart_context(self.request)
        return {
            'total': cart_context['total'],
            'products_with_quantity': cart_context['products_with_quantity']
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
    # import hashlib
    # return hashlib.sha256(input_string.encode('utf-8')).hexdigest()

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
            payment_session = create_payment_session(
                transaction_id=transaction_id,
                payment_type='stripe',
                user_id=self.request.user.id if self.request.user.is_authenticated else None,
                customer_email=customer_data['email'],
                amount=float(self.amount),
                cart_data={'products': [{'id': item['product'].id, 'quantity': item['quantity']} for item in self.products_with_quantity]},
                shipping_details=customer_data
            )
            payment_session.status = 'INITIATED'
            payment_session.save()

            stripe.Customer.create()
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                metadata={
                    'user_email': customer_data['email'],
                    'phone_number': customer_data['mobile'],
                    'address': customer_data['address'],
                    'transaction_id': transaction_id  # Include transaction_id in metadata
                },
                mode='payment',
                success_url=f"http://{settings.LOCALHOST_IP}:8000/validate-payment?stripe-session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f'http://{settings.LOCALHOST_IP}:8000/cart',
            )
            return redirect(checkout_session.url)

        except Exception as e:
            # error_message = f'Stripe payment failed: {str(e)}'
            error_message = ErrorMessageManager.getErrorMessage(1008)
            PaymentLogger.log_error(transaction_id,'stripe', error_message, self.request, amount=self.amount,customer_email=self.request.COOKIES.get('email', None))
            messages.error(self.request, f"Stripe payment failed: {str(e)}")
            return redirect('cart')

    def create_line_items(self):
        
        # products_with_quantity = models.Cart.objects.filter(customer_id = request.user)
        
        line_items = []
        for item in self.products_with_quantity:
            product = item['product']
            quantity = item['quantity']
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': product.price * 100,
                    'product_data': {
                        'name': product.name,
                        'description': product.description,
                    },
                },
                'quantity': quantity,
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

        customer_data = self.get_customer_data()
        
        try:
            payment_session = create_payment_session(
                transaction_id=transaction_id,
                payment_type='phonepe',
                user_id=self.request.user.id if self.request.user.is_authenticated else None,
                customer_email=customer_data['email'],
                amount=float(self.amount),
                cart_data={'products': [{'id': item['product'].id, 'quantity': item['quantity']} for item in self.products_with_quantity]},
                shipping_details=customer_data
            )
            payment_session.status = 'INITIATED'
            payment_session.save()
            
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
            # print(f"{responseData=}")
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

        customer_data = self.get_customer_data()
        
        try:
            payment_session = create_payment_session(
                transaction_id=transaction_id,
                payment_type='google-pay',
                user_id=self.request.user.id if self.request.user.is_authenticated else None,
                customer_email=customer_data['email'],
                amount=float(self.amount),
                cart_data={'products': [{'id': item['product'].id, 'quantity': item['quantity']} for item in self.products_with_quantity]},
                shipping_details=customer_data
            )
            payment_session.status = 'INITIATED'
            payment_session.save()
            
            payment_data = self.request.POST.get("paymentData")
            if not payment_data:
                error_message = ErrorMessageManager.getErrorMessage(1013)
                PaymentLogger.log_error(transaction_id,'google-pay', error_message, self.request,customer_email=customer_email)
                return JsonResponse({"error": "Missing payment data"}, status=400)

            if self.amount <= 0:
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
                url = PaymentRedirectManager.construct_redirect_url("google-pay", payment_json, settings.HOST+"payment-success", self.amount)
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
            # print("Stripe session: " , session)
            if session and session.get("payment_status" , None) == "paid":
                url = PaymentRedirectManager.construct_redirect_url("stripe", session, settings.HOST+"payment-success")
                return redirect(url)
            
            return redirect('cart')

        if request.POST.get('merchantId'):
            # print(f"{request.POST=}")
            if request.POST.get('code') == "PAYMENT_SUCCESS":
                url = PaymentRedirectManager.construct_redirect_url("phonepe", request.POST, settings.HOST+"payment-success")
            elif request.POST.get('code') in ['PAYMENT_ERROR' , 'PAYMENT_PENDING']:
                url = "payment-failed"
            return redirect(url)

@user_passes_test(is_customer,'customerlogin')
def payment_failed_view(request):
    return render(request , "ecom/payment_failed.html")


@csrf_exempt
def validate_payment(request):
    return PaymentValidator.validate_payment(request)

class PaymentRedirectManager:

    @staticmethod
    def construct_redirect_url(payment_type, data, redirect_url, gpay_amount=None):
        url = redirect_url
        
        transaction_id = None
        validation_token = None
        
        if payment_type == "stripe":
            transaction_id = data.get('metadata', {}).get('transaction_id') or str(uuid.uuid4())
        elif payment_type == "phonepe":

            phonepe_transaction_id = data.get('transactionId')
            
            try:
                from django.conf import settings
                merchant_id = data.get('merchantId', getattr(settings, 'PHONEPE_MERCHANT_ID', 'PGTESTPAYUAT86'))
                amount_from_response = data.get('amount', 0)
                
                from django.utils import timezone
                from datetime import timedelta
                recent_time = timezone.now() - timedelta(minutes=30)  # Looking for sessions in last 30 minutes
                
                print(f"Looking for PhonePe sessions with amount: {amount_from_response} (paisa)")
                
                potential_sessions = models.PaymentSession.objects.filter(
                    payment_type='phonepe',
                    status__in=['PENDING', 'INITIATED'],
                    created_at__gte=recent_time
                ).order_by('-created_at')
                
                print(f"Found {len(potential_sessions)} potential PhonePe sessions")
                
                for i, session in enumerate(potential_sessions[:5]):
                    print(f"  Session {i+1}: transaction_id={session.transaction_id}, amount={session.amount}, status={session.status}")
                
                expected_amount = float(amount_from_response) / 100 if amount_from_response else 0
                
                matching_session = None
                for session in potential_sessions:
                    if abs(float(session.amount) - expected_amount) < 0.01:
                        break
                
                if matching_session:
                    transaction_id = matching_session.transaction_id
                    print(f"Found matching PhonePe session: {transaction_id} for amount {expected_amount}")
                else:
                    print(f"No matching PhonePe session found for amount {expected_amount}")
                    transaction_id = phonepe_transaction_id
                    
            except Exception as e:
                print(f"Error finding PhonePe session: {e}")
                transaction_id = phonepe_transaction_id
        elif payment_type == "google-pay":
            try:
                from django.utils import timezone
                from datetime import timedelta
                recent_time = timezone.now() - timedelta(minutes=30)
                
                expected_amount = float(gpay_amount) if gpay_amount else 0
                
                print(f"Looking for Google Pay sessions with amount: {expected_amount}")
                
                potential_sessions = models.PaymentSession.objects.filter(
                    payment_type='google-pay',
                    status__in=['PENDING', 'INITIATED'],
                    created_at__gte=recent_time
                ).order_by('-created_at')
                
                print(f"Found {len(potential_sessions)} potential Google Pay sessions")
                
                matching_session = None
                for session in potential_sessions:
                    if abs(float(session.amount) - expected_amount) < 0.01:
                        matching_session = session
                        break
                
                if matching_session:
                    transaction_id = matching_session.transaction_id
                    print(f"Found matching Google Pay session: {transaction_id} for amount {expected_amount}")
                else:
                    print(f"No matching Google Pay session found for amount {expected_amount}")
                    transaction_id = str(uuid.uuid4())
                    
            except Exception as e:
                print(f"Error finding Google Pay session: {e}")
                transaction_id = str(uuid.uuid4())
        
        try:
            payment_session = models.PaymentSession.objects.get(transaction_id=transaction_id, payment_type=payment_type)
            print(f"Found payment session: {payment_session.session_id}, status: {payment_session.status}")
            
            if payment_session.can_be_validated():
                provider_response = dict(data) if isinstance(data, dict) else {}
                payment_session.mark_as_validated(provider_response)
                validation_token = payment_session.validation_token
                print(f"Session validated successfully, validation_token: {validation_token[:20]}...")
            else:
                validation_token = None
                print(f"Session cannot be validated - status: {payment_session.status}, expired: {payment_session.is_expired()}")
                
        except models.PaymentSession.DoesNotExist:
            validation_token = None
            print(f"No payment session found for transaction_id: {transaction_id}, payment_type: {payment_type}")

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
            from urllib.parse import quote
            code = data.get('code')
            merchantId = data.get('merchantId')
            transactionId = data.get('transactionId')
            amount = data.get('amount')
            providerReferenceId = data.get('providerReferenceId')
            checksum = data.get('checksum')

            checksum_encoded = quote(str(checksum), safe='') if checksum else checksum
            
            url += f"?payment_type={payment_type}&code={code}&merchantId={merchantId}&transactionId={transactionId}&amount={amount}&providerReferenceId={providerReferenceId}&checksum={checksum_encoded}"

        if validation_token:
            url += f"&validation_token={validation_token}"
            print(f"Final URL with validation token: {url}")
        else:
            print(f"Warning: No validation token found for payment session {transaction_id}")
            print(f"Final URL without validation token: {url}")

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
        self.fromMail = settings.EMAIL_HOST_USER
        self.appPassword = settings.EMAIL_APP_PASSWORD
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
import re
from html import unescape

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
                # print("-------------------------------------")
                # print(detected_user_entry)
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
 
from pathlib import Path
from .ResumeParser.main import process_resumes

def strip_html_tags(html_content):
    if not html_content:
        return ""

    # Replace block-level HTML tags with newlines to preserve structure
    block_tags = r'</?(div|p|br|h[1-6]|li|ul|ol|blockquote|pre)[^>]*>'
    clean_text = re.sub(block_tags, '\n', html_content, flags=re.IGNORECASE)

    # Remove all remaining HTML tags
    clean_text = re.sub(r'<[^>]+>', '', clean_text)

    # Unescape HTML entities (like &nbsp;, &amp;, etc.)
    clean_text = unescape(clean_text)

    # Clean up multiple consecutive newlines but preserve single newlines
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)

    # Remove extra spaces within lines but keep newlines
    clean_text = re.sub(r'[ \t]+', ' ', clean_text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in clean_text.split('\n')]
    clean_text = '\n'.join(line for line in lines if line)

    return clean_text.strip()

# Context processor for dynamic job navigation
def job_navigation_context(request):
    try:
        jobs = models.CreateJob.objects.all()
        return {'available_jobs': jobs}
    except:
        return {'available_jobs': []}
    
@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def create_new_job(request):
    
    if request.method == "POST":
        createjobform = forms.CreateJobForm(request.POST)
        print("createjobform.is_valid(): " , createjobform.is_valid())
        if createjobform.is_valid():
            job_description_html = createjobform.cleaned_data.get('job_description', '').strip()
            if not job_description_html:
                createjobform.add_error('job_description', 'This field is required.')
            else:
                # Strip HTML tags to get plain text for resume analysis
                job_description_plain = strip_html_tags(job_description_html)

                job = createjobform.save(commit=False)
                job.job_description = job_description_plain
                job.job_description_html = job_description_html
                job.save()
                
                new_job_resume_directory_path = settings.RESUMES_DIR / job.job_code
                new_job_resume_directory_path.mkdir(exist_ok=True)
            
            
            #   Create Boiler JSON for new JD
            # new_job_output_directory_path = settings.OUTPUT_DIR / job.job_code
            # new_job_output_directory_path.mkdir(exist_ok=True)
            # # filename = settings.OUTPUT_FILENAME + "_" +job_type + ".json"
            # output_file_path = new_job_output_directory_path / (settings.OUTPUT_FILENAME + "_" +job.job_code.lower()+".json")
            # try:
            #     with open(output_file_path , "w" , encoding="utf-8") as json_file:
            #         temp = json.loads(settings.JSON_BOILERPLATE)
            #         json.dump(temp , json_file, indent=2, ensure_ascii=False)
            # except (FileNotFoundError , json.JSONDecodeError):
            #     print(f"{output_file_path} is not found.")
            
            mydict = {"jobcreated" : True}
            return render(request , "resumeparser/jobcreated.html" , context=mydict)
        else:
            print("Form is invalid. Errors:", createjobform.errors)
            mydict = {"createjobform": createjobform, "form_errors": createjobform.errors}
            return render(request , "resumeparser/create-new-job.html" , context=mydict)
    createjobform = forms.CreateJobForm()
    mydict = {"createjobform": createjobform}
    return render(request , "resumeparser/create-new-job.html" , context=mydict)

@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def manage_jobs(request):
    
    job_list = models.CreateJob.objects.all().values()
    
    # print(list(job_list))
    mydict = {"job_list" : job_list}
    
    
    return render(request , "resumeparser/manage-jobs.html" , context=mydict)


def apply_job(request , job_code):

    # Get job details for the given job_code
    try:
        job_details = models.CreateJob.objects.get(job_code=job_code)
    except models.CreateJob.DoesNotExist:
        # Handle case where job doesn't exist
        return render(request, "resumeparser/job-not-found.html", {"job_code": job_code})

    if request.method == "POST":
        applyjobform = forms.ApplyJobForm(request.POST, request.FILES)
        if applyjobform.is_valid():
            job = applyjobform.save(commit=False)  # Don't save yet
            job.job_code = job_code  # 👈 Set it from URL or your logic
            # Get the actual filename and clean it to match the file system
            original_filename = str(job.resume).split("/")[-1]
            job.resume_filename = models.clean_filename(original_filename)
            job.save()
            mydict = {"jobformsubmitted": True}
            return render(request, "resumeparser/jobformsubmitted.html", context=mydict)
        else:
            print("👈",applyjobform.errors)  # 👈 Debug: shows why the form failed!
            mydict = {"jobformsubmitted": False}
            return render(request, "resumeparser/jobformsubmitted.html", context=mydict)



    applyjobform = forms.ApplyJobForm(initial={"job_code" : job_code})

    mydict = {
        "applyjobform" : applyjobform,
        "jobcode" : job_code,
        "job_details": job_details
    }
    return render(request , "resumeparser/apply-job-form.html" , context=mydict)

@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
def job_detail(request , job_code):
    # print(job_code)

    job_applications = models.ApplyJob.objects.all().filter(job_code = job_code)
    job_details = models.CreateJob.objects.get(job_code=job_code)
    
    total_applications = len(job_applications)
    
    # Pagination - 9 applications per page
    paginator = Paginator(job_applications, 9)
    page_number = request.GET.get('page')
    job_applications = paginator.get_page(page_number)
    
    
    # print(job_details.id)
    # print(job_details)
    # print(job_applications)
    mydict = {
        "job_applications" : job_applications,
        "applications_count": total_applications,
        "job_id": job_details.id,
        "job_code": job_code,
    }
    
    # print(job_applications[0].resume.url)
    return render(request , "resumeparser/job-detail.html" , context=mydict)

        
@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
@csrf_exempt
def view_analysis(request , job_code):
    mydict = {
        "job_code": job_code,
    }
    
    if request.method == "POST":
        data = json.loads(request.body)
        print("data: " , data)

        try:
            candidate_filename = data.pop("candidate_filename")
            print("candidate_filename: " , candidate_filename)

            apply_job = get_unique_apply_job_by_filename(candidate_filename, job_code)

            # print("apply_job: " , apply_job)

            if not apply_job:
                raise Exception(f"No unique ApplyJob found for candidate '{candidate_filename}' in job code '{job_code}'")

            # created = create_or_update_resume_attribute(apply_job, data, str(request.user))
            created = create_or_update_custom_attributes_db(candidate_filename, job_code , data , str(request.user))
            if not created:
                raise Exception("Something went wrong")

            print("Resume attributes saved successfully")
        except Exception as e:
            print("Unable to create resume attributes: " , e)
        
        
    
    job = models.CreateJob.objects.get(job_code = job_code)


    # filename = filename + ".json"
    # filepath = settings.OUTPUT_DIR / job_code / filename
    # print("filepath: ",filepath)
    # Path().read_text(encoding="utf-8")
    # try:
    #     file_content = json.loads(filepath.read_text(encoding="utf-8"))
    # except json.JSONDecodeError:
    #     file_content = json.loads(settings.JSON_BOILERPLATE)
    #     filepath.write_text(json.dumps(file_content ,indent=2, ensure_ascii=False) , encoding="utf-8")
    # # print(file_content["meta"])
    
    
    # ResumeAttributes SECTION
    
    # Get all resume attributes and organize them by candidate name
    resume_attributes = models.ResumeAttributes.objects.select_related('apply_resume').filter(apply_resume__job_code = job_code)
    # print("resume_attributes: " , resume_attributes)

    # Create a dictionary to map candidate names to their attributes
    attributes_by_candidate = {}
    for resume_attribute in resume_attributes:
        try:
            custom_attributes = json.loads(resume_attribute.custom_attributes)

            candidate_name = resume_attribute.apply_resume.name
            if candidate_name not in attributes_by_candidate:
                attributes_by_candidate[candidate_name] = []

            # Convert each key-value pair to individual attribute objects for JS compatibility
            for attr_name, attr_value in custom_attributes.items():
                attributes_by_candidate[candidate_name].append({
                    'attribute_name': attr_name,
                    'attribute_value': attr_value,
                })

        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing custom attributes for {resume_attribute.apply_resume.name}: {e}")
            continue
        
    
    

    # print("attributes_by_candidate: ", attributes_by_candidate)
    # ResumeAttributes SECTION
    
    analysis_data = get_results_by_job_code(job_code)
    # print("analysis_data: ", analysis_data)
    
    # with open("test.json" , "w" , encoding='utf-8') as fp:
    #     json.dump(analysis_data , fp , indent=2)
    
    # summary_statistics = calcuate_summary_statistics(analysis_data)
    
    unanalysed_data = get_unanalysed_data(job_code)
     
    file_content = {
        "candidates" : analysis_data,
        "job_description_html": job.job_description_html,
        # "summary_statistics" : summary_statistics,
        }

    mydict["job_title"] = job.job_title
    mydict["job_id"] = job.id
    # mydict["filepath"] = filepath
    mydict["file_content"] = file_content
    mydict["file_content_dump"] = json.dumps(file_content)
    # Removed resume_attributes QuerySet to prevent JSON serialization error
    mydict["attributes_by_candidate"] = json.dumps(attributes_by_candidate)
    mydict["unanalysed_data"] = json.dumps(unanalysed_data)
    mydict["resume_batch_size"] = settings.RESUME_BATCH_SIZE
    
    
    print(request.GET)
    if request.GET.get("startAnalysis"):
        print("Performing Analysis")
        mydict["analysis_started"] = True
        # return render(request , "resumeparser/view-analysis-file.html" , context=mydict)
    
    
    return render(request , "resumeparser/view-analysis.html" , context=mydict)

def calcuate_summary_statistics(analysis_data):
    
    
    summary_statistics = dict()
    
    success_count = 0
    score_sum = 0
    score_distribution = {
        "excellent" : 0,
        "good": 0,
        "average": 0,
        "below_average": 0
    }
    
    recommendations = {
        "HIRE": 0,
        "CONSIDER": 0,
        "REJECT": 0
    }
    
    try:
        for data in analysis_data:
            if data["success"] == True:
                success_count += 1
            
            score_sum += data.get("scores" , {}).get("final_score" , 0)
            
            if data['scores']['final_score'] >= 90:
                score_distribution["excellent"] += 1
            if 80 <= data['scores']['final_score'] < 90:
                score_distribution["good"] += 1
            if 60 <= data['scores']['final_score'] < 80:
                score_distribution["average"] += 1
            if data['scores']['final_score'] < 60:
                score_distribution["below_average"] += 1
                print(data['scores']['final_score'])
                
            recommendations[data["recommendation"]["decision"]] += 1
        
        summary_statistics["total_candidates"] = len(analysis_data)
        summary_statistics["successful_analyses"] = success_count
        summary_statistics["average_score"] = score_sum / len(analysis_data)
        summary_statistics["score_distribution"] = score_distribution
        summary_statistics["recommendations"] = recommendations
        
        
    except Exception as e:
        print(f"Unable to Calculate summary statistics: {e}")
            
    
    # print("score_distribution: ",score_distribution)
    
    return summary_statistics

from .batch_analyzer import *


@login_required(login_url='adminlogin')
@user_passes_test(is_admin , login_url='adminlogin')
@csrf_exempt
def analyse_batch(request):
    
    if request.method == "POST":
        data = json.loads(request.body)
        # print("request.body: ",json.loads(request.body))
        
        job_id = data["job_id"]
        job_code = data["job_code"]
        batch_id = data["batch_id"]
        resume_batch = data["batch"]
        total_batches = data["total_batches"]
        
        batch_analyzer = BatchResumeAnalyzer()

        responseData = batch_analyzer.analyse_resume_batch(
            job_id,
            job_code,
            batch_id,
            resume_batch,
            total_batches
        )
    
    
    return JsonResponse(responseData)



# @login_required(login_url='adminlogin')
# @user_passes_test(is_admin , login_url='adminlogin')
# @csrf_exempt
# def analyse_resumes(request):
#     mydict = {"analysisstarted" : True}

#     if request.method == "POST":
#         responseData = dict()
#         data = json.loads(request.body)
#         job = models.CreateJob.objects.get(id=data["job_id"])

#         responseData["job_code"] = job.job_code

#         job_description = job.job_description
#         resume_dir = str(settings.RESUMES_DIR / job.job_code)
#         output_dir = str(settings.OUTPUT_DIR / str(job.job_code))
#         print("OUTPUT_DIR: ",output_dir)
#         results = process_resumes(job_description , job.job_code)

#         responseData["results"] = results
#         responseData["analyseSuccess"] = True

#         print("Go to page")
#         return JsonResponse(responseData)

#     return render(request , "resumeparser/view-analysis.html" , context=mydict)



#             'message': f'Error clearing cache for job {job_code}: {str(e)}'
#         })



# def create_or_update_resume_attribute(apply_resume: models.ApplyJob , data: dict , created_by: str) -> bool:
#     try:
#         for key , value in data.items():
#             # Skip candidate_name as it's not an attribute to store
#             if key == "candidate_name":
#                 continue

#             resume_attribute, created = models.ResumeAttributes.objects.update_or_create(
#                 apply_resume=apply_resume,
#                 attribute_name=key,

#                 defaults={
#                     'attribute_value': str(value),
#                     'created_by': created_by
#                 }
#             )

#             log_created = create_resume_log(apply_resume, resume_attribute, key, value, created_by)

#             if not log_created:
#                 resume_attribute.delete()
#                 raise Exception("unable to create Resume Log")
        
#     except Exception as e:
#         print("Unable to create of update  resume attribute: " , e)
        
#         return False
    
#     return True

# def create_resume_log(apply_resume: models.ApplyJob , resume_attribute: models.ResumeAttributes , attribute_name: str , attribute_value: str , created_by: str) -> bool:
#     try:
#         models.ResumeLogs.objects.create(
#             apply_resume = apply_resume,
#             resume_attribute = resume_attribute,
#             attribute_name = attribute_name,
#             attribute_value = attribute_value,
#             created_by = created_by
#         )
#     except Exception as e:
#         print("Unable to create resume log: " , e)
#         return False
    
#     return True


### -------     Chatbot Implementation     ---------


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from.Chatbot.rag_pipeline import get_chatbot_response

# Initialize the RAG pipeline lazily to avoid startup issues
# The pipeline will be initialized on first request
# rag_initialized = False

class ChatbotAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # global rag_initialized

        # # Initialize RAG pipeline on first request if not already done
        # if not rag_initialized:
        #     try:
        #         initialize_rag_pipeline()
        #         rag_initialized = True
        #     except Exception as e:
        #         print(f"Error initializing RAG pipeline: {e}")
        #         return Response(
        #             {"status": "Chatbot is initializing, please try again in a moment."},
        #             status=status.HTTP_503_SERVICE_UNAVAILABLE
        #         )

        user_message = request.data.get('message')

        if not user_message:
            return Response(
                {"error": "Message field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bot_response = get_chatbot_response(user_message)
            return Response({"answer": bot_response}, status=status.HTTP_200_OK)
        except Exception as e:
            # Log the exception for debugging
            print(f"Error during RAG chain invocation: {e}")
            return Response(
                {"error": "An error occurred while processing your request. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



### -------     Implementation Testing     ---------

from .ResumeParser.resume_analyzer import ResumeAnalyzer


def test(request):
    mydict = {}

    return render(request , "ecom/logout.html" , context=mydict)
    # return render(request , "resumeparser/test.html" , context=mydict)

