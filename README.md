# 🛒 Django E-Commerce Platform with Face Recognition

A comprehensive e-commerce platform built with Django featuring face recognition authentication, multiple payment gateways, and a complete admin dashboard.

## ✨ Features

### 🔐 Authentication System
- **Traditional Login/Signup** - Email and password authentication
- **Face Recognition Login** - Advanced facial recognition for secure access
- **Role-based Access Control** - Customer and Admin roles
- **Session Management** - Secure session handling

### 🛍️ E-Commerce Functionality
- **Product Catalog** - Browse and search products
- **Shopping Cart** - Add/remove items, quantity management
- **Order Management** - Complete order processing workflow
- **Invoice Generation** - PDF invoice generation
- **Customer Profiles** - User profile management

### 💳 Payment Integration
- **PayPal Integration** - Secure PayPal payments
- **Stripe Support** - Credit card processing
- **PhonePe Integration** - Indian payment gateway
- **Google Pay Support** - Digital wallet integration
- **Multiple Payment Options** - Flexible payment methods

### 👨‍💼 Admin Dashboard
- **Product Management** - Add, edit, delete products
- **Order Management** - Track and update orders
- **Customer Management** - View and manage customers
- **Analytics Dashboard** - Sales and performance metrics
- **Feedback System** - Customer feedback management

### 🎯 Face Recognition Features
- **Face Enrollment** - Register faces for authentication
- **Live Recognition** - Real-time face detection and recognition
- **Secure Storage** - Encrypted face encoding storage
- **Performance Optimized** - Fast recognition with caching

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Git
- Webcam (for face recognition features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sasidharakurathi/Django_E-Commerce_Project.git
   cd Django_E-Commerce_Project
   ```

2. **Create virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```


3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   # Copy environment template
   cp .env.example .env
   # Edit .env with your credentials (see .env.example for all options)
   ```

5. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the application**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## ⚙️ Configuration

### Environment Variables

All sensitive credentials (API keys, DB passwords, email, payment gateway keys, etc.) are loaded from a `.env` file. See `.env.example` for all required variables. **Never commit your real `.env` to a public repo.**

### Requirements

All dependencies are listed in `requirements.txt`. Install with:
```bash
pip install -r requirements.txt
```

### Security

- All secrets and API keys must be set via environment variables.
- `.env` and database files are excluded from git via `.gitignore`.
- See `SECURITY_CHECKLIST.md` for more.

### Email Setup (Gmail)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. **Update .env file** with your email and app password

### Payment Gateway Setup

#### PayPal
1. Create PayPal Developer account
2. Create sandbox/live application
3. Update `PAYPAL_RECEIVER_EMAIL` in `.env`

#### Stripe (Optional)
1. Create Stripe account
2. Get API keys from dashboard
3. Add to `.env` file

## 📁 Project Structure

```
django-ecommerce-face-recognition/
├── ecommerce/              # Main Django project
│   ├── settings.py         # Project settings
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py            # WSGI configuration
├── ecom/                  # Main application
│   ├── models.py          # Database models
│   ├── views.py           # View functions
│   ├── forms.py           # Django forms
│   ├── admin.py           # Admin configuration
│   └── FaceRecognition/   # Face recognition module
│       ├── capture_images.py
│       ├── encode_faces.py
│       └── live_recognition.py
├── templates/ecom/        # HTML templates
├── static/               # Static files (CSS, JS, images)
├── media/                # User uploaded files
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
└── README.md           # This file
```

## 🎭 Face Recognition Setup

### Initial Setup

1. **Install face recognition dependencies**
   ```bash
   # For Windows users, you might need to install dlib separately
   pip install cmake
   pip install dlib
   pip install face-recognition
   ```

2. **Prepare face data**
   - Navigate to `ecom/FaceRecognition/`
   - Create user folders in `dataset/` directory
   - Add face images for each user

3. **Generate face encodings**
   ```bash
   cd ecom/FaceRecognition
   python encode_faces.py
   ```

### Adding New Users for Face Recognition

1. **Create user folder**
   ```bash
   mkdir ecom/FaceRecognition/dataset/username
   ```

2. **Add face images**
   - Add 5-10 clear face images
   - Images should be well-lit and front-facing
   - Supported formats: JPG, PNG

3. **Re-generate encodings**
   ```bash
   cd ecom/FaceRecognition
   python encode_faces.py
   ```

## 🔧 Troubleshooting

### Common Issues

#### Face Recognition Installation
```bash
# If dlib installation fails on Windows
pip install dlib-binary

# If OpenCV issues occur
pip uninstall opencv-python
pip install opencv-python-headless
```

#### Database Issues
```bash
# Reset database
python manage.py flush
python manage.py makemigrations
python manage.py migrate
```

#### Static Files Issues
```bash
# Collect static files
python manage.py collectstatic
```

### Performance Optimization

#### Face Recognition
- Use smaller image sizes (640px max)
- Limit face dataset to 10 images per person
- Enable caching for better performance

#### Database
- Use PostgreSQL for production
- Enable database indexing
- Optimize queries in views

## 🚀 Deployment

### Production Checklist

1. **Security Settings**
   ```python
   DEBUG = False
   ALLOWED_HOSTS = ['yourdomain.com']
   SECRET_KEY = 'your-production-secret-key'
   ```

2. **Database Configuration**
   - Use PostgreSQL or MySQL
   - Configure database backups
   - Set up connection pooling

3. **Static Files**
   ```bash
   python manage.py collectstatic
   ```

4. **Environment Variables**
   - Set all production environment variables
   - Use secure secret keys
   - Configure production email settings

### Deployment Platforms

#### Heroku
1. Install Heroku CLI
2. Create Procfile
3. Configure buildpacks for Python and OpenCV
4. Set environment variables

#### DigitalOcean/AWS
1. Set up virtual server
2. Install dependencies
3. Configure Nginx/Apache
4. Set up SSL certificates

## 📊 API Documentation

### Face Recognition Endpoints

#### Capture Face Images
```python
POST /face-signup/
# Captures face images for new user registration
```

#### Face Login
```python
POST /face-login/
# Authenticates user using face recognition
```

### E-commerce Endpoints

#### Product Management
```python
GET /api/products/          # List all products
POST /api/products/         # Create new product
PUT /api/products/{id}/     # Update product
DELETE /api/products/{id}/  # Delete product
```

#### Order Management
```python
GET /api/orders/           # List user orders
POST /api/orders/          # Create new order
GET /api/orders/{id}/      # Get order details
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
4. **Push to branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open Pull Request**

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Akurathi Sasidhar**
- GitHub: [@sasidharakurathi](https://github.com/sasidharakurathi)
- Email: 22kt1a0595@gmail.com

## 🙏 Acknowledgments

- Django community for the excellent framework
- OpenCV and face_recognition libraries
- Bootstrap for responsive UI components
- All contributors and testers

## 📞 Support

If you encounter any issues or have questions:

1. **Check the troubleshooting section** above
2. **Search existing issues** on GitHub
3. **Create a new issue** with detailed description
4. **Contact the author** via email

---

⭐ **Star this repository** if you find it helpful!

🐛 **Report bugs** by creating an issue

💡 **Suggest features** by opening a feature request
