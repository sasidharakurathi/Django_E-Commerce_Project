from django import forms
from django.contrib.auth.models import User
from . import models


class CustomerUserForm(forms.ModelForm):
    class Meta:
        model=User
        fields=['first_name','last_name','username','password']
        widgets = {
        'password': forms.PasswordInput()
        }
        
class CustomerForm(forms.ModelForm):
    class Meta:
        model=models.Customer
        fields=['address','mobile','profile_pic']

class ProductForm(forms.ModelForm):
    class Meta:
        model=models.Product
        fields=['name','price','description','product_image']

#address of shipment
class AddressForm(forms.Form):
    Email = forms.EmailField()
    Mobile= forms.IntegerField()
    Address = forms.CharField(max_length=500)

#for updating status of order
class OrderForm(forms.ModelForm):
    class Meta:
        model=models.Orders
        fields=['status']
        
class CreateJobForm(forms.ModelForm):
    class Meta:
        model = models.CreateJob
        fields = ["job_code","job_title","job_description"]
        widgets = {
            'job_description': forms.Textarea(attrs={
                'required': False,  # Remove HTML5 required validation to prevent focus issues with TinyMCE
            })
        }
        

class ApplyJobForm(forms.ModelForm):
    
    class Meta:
        model = models.ApplyJob
        fields = ["name" , "email" , "contact_number" , "gender" , "dob", "resume"]
        widgets = {
            "email" : forms.EmailInput(),
            "gender": forms.Select(),
            "dob": forms.DateInput(attrs={'placeholder': 'Date Of Birth', 'type': 'date'}),
            "resume": forms.FileInput(),
        }
        labels = {
            "name": "Name",
            "email": "Email",
            "contact_number": "Contact Number",
            "gender": "Gender",
            "dob": "Date Of Birth",
            "resume": "Resume",
        }
        


