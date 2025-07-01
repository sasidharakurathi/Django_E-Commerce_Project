from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from ecom.models import Customer, Product, Orders
import json


class EcommerceTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create user and customer
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User',
            email='test@example.com'
        )

        # Create customer group
        customer_group, _ = Group.objects.get_or_create(name='CUSTOMER')
        customer_group.user_set.add(self.user)

        # Create customer
        self.customer = Customer.objects.create(
            user=self.user,
            address='123 Test Street',
            mobile='1234567890'
        )

        # Create test products
        self.product1 = Product.objects.create(
            name='Test Product 1',
            price=100,
            description='Test Description 1'
        )

        self.product2 = Product.objects.create(
            name='Test Product 2',
            price=200,
            description='Test Description 2'
        )

        self.client = Client()

    def test_add_to_cart(self):
        """Test adding products to cart"""
        response = self.client.get(f'/add-to-cart/{self.product1.id}')
        self.assertEqual(response.status_code, 200)

        # Check if product is in cookies
        self.assertIn('product_ids', response.cookies)
        self.assertEqual(response.cookies['product_ids'].value, str(self.product1.id))

    def test_cart_view(self):
        """Test cart view functionality"""
        # Add product to cart first
        self.client.get(f'/add-to-cart/{self.product1.id}')

        # View cart
        response = self.client.get('/cart')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product1.name)

    def test_remove_from_cart(self):
        """Test removing products from cart"""
        # Add product to cart first
        self.client.get(f'/add-to-cart/{self.product1.id}')

        # Remove from cart
        response = self.client.get(f'/remove-from-cart/{self.product1.id}')
        self.assertEqual(response.status_code, 200)

    def test_customer_address_view_authenticated(self):
        """Test customer address view for authenticated users"""
        # Login user
        self.client.login(username='testuser', password='testpass123')

        # Add product to cart
        self.client.get(f'/add-to-cart/{self.product1.id}')

        # Access customer address view
        response = self.client.get('/customer-address')
        self.assertEqual(response.status_code, 200)

        # Test POST with address form
        response = self.client.post('/customer-address', {
            'Email': 'test@example.com',
            'Mobile': 1234567890,
            'Address': '123 Test Street'
        })
        self.assertEqual(response.status_code, 200)
        # Should render payment page
        self.assertContains(response, 'Pay with Stripe')
        self.assertContains(response, 'PhonePe')

    def test_payment_success_view_creates_orders(self):
        """Test that payment success view creates orders"""
        # Login user
        self.client.login(username='testuser', password='testpass123')

        # Set up cart cookies
        self.client.cookies['product_ids'] = f'{self.product1.id}|{self.product2.id}'
        self.client.cookies['email'] = 'test@example.com'
        self.client.cookies['mobile'] = '1234567890'
        self.client.cookies['address'] = '123 Test Street'

        # Call payment success view
        response = self.client.get('/payment-success')

        self.assertEqual(response.status_code, 200)

        # Check if orders were created
        orders = Orders.objects.filter(customer=self.customer)
        self.assertEqual(orders.count(), 2)

        # Verify order details
        order1 = orders.filter(product=self.product1).first()
        self.assertIsNotNone(order1)
        self.assertEqual(order1.email, 'test@example.com')
        self.assertEqual(order1.mobile, '1234567890')
        self.assertEqual(order1.address, '123 Test Street')
        self.assertEqual(order1.status, 'Pending')

    def test_my_order_view(self):
        """Test my orders view"""
        # Login user
        self.client.login(username='testuser', password='testpass123')

        # Create test order
        Orders.objects.create(
            customer=self.customer,
            product=self.product1,
            email='test@example.com',
            mobile='1234567890',
            address='123 Test Street',
            status='Pending'
        )

        # Access my orders view
        response = self.client.get('/my-order')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product1.name)

    def test_download_invoice_view(self):
        """Test invoice download functionality"""
        # Login user
        self.client.login(username='testuser', password='testpass123')

        # Create test order
        order = Orders.objects.create(
            customer=self.customer,
            product=self.product1,
            email='test@example.com',
            mobile='1234567890',
            address='123 Test Street',
            status='Delivered'
        )

        # Download invoice
        response = self.client.get(f'/download-invoice/{order.id}/{self.product1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_stripe_payment_view(self):
        """Test Stripe payment initiation"""
        # Add product to cart
        self.client.get(f'/add-to-cart/{self.product1.id}')

        # Set customer data cookies
        self.client.cookies['email'] = 'test@example.com'
        self.client.cookies['mobile'] = '1234567890'
        self.client.cookies['address'] = '123 Test Street'

        # This test would require mocking Stripe API
        # For now, just test that the view exists and handles missing data
        response = self.client.get('/stripe-payment')
        # Should redirect to customer-address if no cookies
        self.assertEqual(response.status_code, 302)

    def test_phonepe_payment_view(self):
        """Test PhonePe payment initiation"""
        # Add product to cart
        self.client.get(f'/add-to-cart/{self.product1.id}')

        # Test without customer data - should redirect
        response = self.client.get('/phonepe-payment')
        self.assertEqual(response.status_code, 302)

    def test_gpay_payment_view(self):
        """Test GPay payment processing"""
        # Add product to cart
        self.client.get(f'/add-to-cart/{self.product1.id}')

        # Set customer data cookies
        self.client.cookies['email'] = 'test@example.com'
        self.client.cookies['mobile'] = '1234567890'
        self.client.cookies['address'] = '123 Test Street'

        # Test POST request (would need mock payment data)
        response = self.client.post('/gpay-payment/', {})
        # Should return error for invalid request
        self.assertEqual(response.status_code, 400)
