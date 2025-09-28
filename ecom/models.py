from django.db import models
from django.contrib.auth.models import User

from django.conf import settings

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
    name=models.CharField(max_length=250)
    product_image= models.ImageField(upload_to='product_image/',null=True,blank=True , max_length=250)
    price = models.PositiveIntegerField()
    description=models.CharField(max_length=250)

    def __str__(self):
        return self.name

    @property
    def get_image_url(self):
        """
        Returns the appropriate image URL for both local files and external URLs
        """
        if not self.product_image:
            return None

        # Convert to string to handle both file paths and URLs
        image_str = str(self.product_image)

        # Check if it's an external URL (starts with http:// or https://)
        if image_str.startswith(('http://', 'https://')):
            return image_str
        else:
            # It's a local file, return the media URL
            try:
                return self.product_image.url
            except ValueError:
                # Handle case where file doesn't exist
                return None
    
class Cart(models.Model):
    customer = models.ForeignKey('Customer' , on_delete=models.CASCADE)
    product = models.ForeignKey('Product' , on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=10 , decimal_places=2)

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
    quantity = models.IntegerField(default=1)


    
    
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

class PaymentSession(models.Model):

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('INITIATED', 'Initiated'),
        ('VALIDATED', 'Validated'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('EXPIRED', 'Expired'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('stripe', 'Stripe'),
        ('phonepe', 'PhonePe'),
        ('google-pay', 'Google Pay'),
    ]
    
    session_id = models.CharField(max_length=100, unique=True)
    transaction_id = models.CharField(max_length=250, unique=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    user_id = models.IntegerField(null=True, blank=True)
    customer_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    provider_payment_id = models.CharField(max_length=250, null=True, blank=True) 
    provider_response = models.JSONField(default=dict, blank=True) 
    
    # Session management
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    is_validated = models.BooleanField(default=False)
    validation_token = models.CharField(max_length=100, unique=True)
    
    # Cart data
    cart_data = models.JSONField(default=dict)
    shipping_details = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['validation_token']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Payment Session {self.session_id} - {self.status}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def can_be_validated(self):
        return (
            not self.is_expired() and 
            self.status in ['INITIATED', 'PENDING'] and 
            not self.is_validated
        )
    
    def mark_as_validated(self, provider_response=None):
        from django.utils import timezone
        
        self.status = 'VALIDATED'
        self.is_validated = True
        self.validated_at = timezone.now()
        
        if provider_response:
            self.provider_response = provider_response
        
        self.save()
    
    def mark_as_completed(self):
        self.status = 'COMPLETED'
        self.save()
    
    def mark_as_failed(self, error_reason=None):
        self.status = 'FAILED'
        if error_reason:
            self.provider_response['error'] = error_reason
        self.save()

class ErrorMessages(models.Model):
    error_id = models.IntegerField(unique=True)
    error_message = models.CharField(max_length=1000)
    # error_type = models.CharField(max_length=1000)
    
    def __str__(self):
        return f"Error ID: {self.error_id} \n Error Message: {self.error_message}"

class CreateJob(models.Model):
    job_code = models.CharField(max_length=10, unique=True)
    job_title = models.CharField(max_length=100)
    job_description = models.TextField()
    job_description_html = models.TextField()

    def __str__(self):
        return self.job_title

    # def clean(self):
    #     """Validate job code format"""
    #     from django.core.exceptions import ValidationError
    #     if self.job_code:
    #         self.job_code = self.job_code.upper().strip()
    #         if not self.job_code.replace('_', '').replace('-', '').isalnum():
    #             raise ValidationError({'job_code': 'Job code must contain only letters, numbers, hyphens, and underscores.'})

    # def save(self, *args, **kwargs):
    #     self.clean()
    #     super().save(*args, **kwargs)

class Gender(models.TextChoices):
    NOT_SELECTED = '', 'Gender'
    MALE = 'M' , 'Male'
    FEMALE = 'F' , 'Female'
    OTHERS = 'O' , 'Others'
    
# Removed static JobTypes choices - now using dynamic job codes from CreateJob model
    
class AnalysedChoices(models.IntegerChoices):
    UNANALYZED = 0 , "Unanalyzed"
    ANALYZED = 1 , "Analyzed"


def clean_filename(filename):

    return filename.replace(' ', '_')

def resume_upload_path(instance , filename):
    job_code = instance.job_code
    # Remove spaces from filename to prevent mismatch between file system and database
    cleaned_filename = clean_filename(filename)
    # return f'resumes/{job_code}/{cleaned_filename}'
    return f'ResumeParser/resumes/{job_code}/{cleaned_filename}'

class ApplyJob(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    contact_number = models.CharField(max_length=15)
    # gender = models.CharField(max_length=1 , choices=Gender.choices, default="Gender")
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.NOT_SELECTED, blank=True)
    dob = models.DateField()
    job_code = models.CharField(max_length=10)  # Increased max_length to accommodate dynamic job codes
    resume = models.FileField(upload_to=resume_upload_path)
    resume_filename = models.CharField(max_length=100 , default="")
    analysed = models.IntegerField(choices=AnalysedChoices.choices , default=AnalysedChoices.UNANALYZED)
    #custom_attributes = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return self.name

    def get_job_title(self):
        """Get the job title from the CreateJob model based on job_code"""
        try:
            job = CreateJob.objects.get(job_code=self.job_code)
            return job.job_title
        except CreateJob.DoesNotExist:
            return f"Job {self.job_code}"


class ResumeAttributes(models.Model):

    apply_resume = models.ForeignKey(ApplyJob , on_delete=models.CASCADE , to_field="id" , related_name="resume_attributes")
    analysis_json = models.TextField()
    custom_attributes = models.TextField(default='{}')
    analysis_success = models.BooleanField()
    # created_by = models.CharField(max_length=50)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)


class ResumeLogs(models.Model):

    apply_resume = models.ForeignKey(ApplyJob , on_delete=models.CASCADE , to_field="id" , related_name="resume_logs")
    resume_attribute = models.ForeignKey(ResumeAttributes , on_delete=models.CASCADE , to_field="id" , related_name="attribute_logs")
    custom_attributes = models.TextField()
    created_by = models.CharField(max_length=50)
    created_date = models.DateTimeField(auto_now_add=True)



# Resume Analysis Model - Single Table Design
class ResumeAnalysis(models.Model):
    
    # Link to the job application
    application = models.OneToOneField(ApplyJob, on_delete=models.CASCADE,to_field="id", related_name='analysis')

    # Basic candidate info
    candidate_name = models.CharField(max_length=150)
    email = models.EmailField()
    contact_number = models.CharField(max_length=15)

    # Scores
    final_score = models.FloatField()
    skills_match = models.FloatField()
    experience_score = models.FloatField()
    education_score = models.FloatField()
    keywords_match = models.FloatField()
    overall_fit = models.FloatField()
    growth_potential = models.FloatField()

    # Recommendation
    recommendation_decision = models.CharField(max_length=20)  # HIRE, CONSIDER, REJECT
    recommendation_reason = models.TextField()
    recommendation_confidence = models.CharField(max_length=20)  # HIGH, MEDIUM, LOW

    # Skills analysis - stored as JSON
    skill_match_percentage = models.FloatField()
    matching_skills = models.JSONField(default=list, blank=True)  # List of matching skills
    missing_skills = models.JSONField(default=list, blank=True)   # List of missing skills

    # Experience analysis - stored as JSON
    experience_level = models.CharField(max_length=20)  # SENIOR, MID, JUNIOR, ENTRY
    matching_experience = models.JSONField(default=list, blank=True)  # List of relevant experience
    experience_gaps = models.JSONField(default=list, blank=True)      # List of experience gaps

    # Education analysis - stored as JSON
    education_level = models.CharField(max_length=20)  # ADVANCED, INTERMEDIATE, BASIC
    education_highlights = models.JSONField(default=list, blank=True)  # List of education highlights

    # Job analysis
    is_fresher = models.BooleanField(default=True)
    first_job_start_year = models.IntegerField(null=True, blank=True)
    last_job_end_year = models.IntegerField(null=True, blank=True)
    total_jobs_count = models.IntegerField(default=0)
    average_job_change = models.CharField(max_length=50, null=True, blank=True)

    # Assessment - stored as JSON
    strengths = models.JSONField(default=list, blank=True)           # List of strengths
    weaknesses = models.JSONField(default=list, blank=True)          # List of weaknesses
    red_flags = models.JSONField(default=list, blank=True)           # List of red flags
    cultural_fit_indicators = models.JSONField(default=list, blank=True)  # List of cultural fit indicators

    # Hiring insights - stored as JSON
    salary_expectation_alignment = models.CharField(max_length=20)  # HIGH, MEDIUM, LOW
    onboarding_priority = models.CharField(max_length=20)  # HIGH, MEDIUM, LOW
    interview_focus_areas = models.JSONField(default=list, blank=True)  # List of interview focus areas

    # Metadata
    processing_time = models.FloatField()
    processed_at = models.DateTimeField()
    file_path = models.TextField()
    file_size = models.BigIntegerField()
    word_count = models.IntegerField()
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.candidate_name} - {self.final_score}%"

    class Meta:
        ordering = ['-created_at']

    # Helper methods to get data in a structured way
    def get_matching_skills_count(self):
        return len(self.matching_skills) if self.matching_skills else 0

    def get_missing_skills_count(self):
        return len(self.missing_skills) if self.missing_skills else 0

    def get_strengths_count(self):
        return len(self.strengths) if self.strengths else 0

    def get_weaknesses_count(self):
        return len(self.weaknesses) if self.weaknesses else 0

    def get_red_flags_count(self):
        return len(self.red_flags) if self.red_flags else 0

    def get_interview_focus_count(self):
        return len(self.interview_focus_areas) if self.interview_focus_areas else 0