from django.contrib import admin
from .models import (
    Customer, Product, Orders, Cart, PaymentLogs, StripeLogs, PhonepeLogs,
    GooglepayLogs, PaymentErrorLogs, ErrorMessages, CreateJob, ApplyJob,
    ResumeAnalysis
)
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
admin.site.register(Cart)


admin.site.register(PaymentLogs)
admin.site.register(StripeLogs)
admin.site.register(PhonepeLogs)
admin.site.register(GooglepayLogs)
admin.site.register(PaymentErrorLogs)
admin.site.register(ErrorMessages)
admin.site.register(CreateJob)


# Resume Analysis Admin - Single Table Design
@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'candidate_name', 'email', 'final_score', 'recommendation_decision',
        'experience_level', 'is_fresher', 'get_matching_skills_count',
        'get_strengths_count', 'processed_at'
    ]
    list_filter = [
        'recommendation_decision', 'experience_level', 'is_fresher',
        'education_level', 'salary_expectation_alignment', 'onboarding_priority'
    ]
    search_fields = ['candidate_name', 'email', 'application__name']
    readonly_fields = [
        'candidate_name', 'email', 'contact_number', 'final_score',
        'skills_match', 'experience_score', 'education_score',
        'keywords_match', 'overall_fit', 'growth_potential',
        'recommendation_decision', 'recommendation_reason',
        'recommendation_confidence', 'skill_match_percentage',
        'experience_level', 'education_level', 'is_fresher',
        'first_job_start_year', 'last_job_end_year', 'total_jobs_count',
        'average_job_change', 'salary_expectation_alignment',
        'onboarding_priority', 'processing_time', 'processed_at',
        'file_path', 'file_size', 'word_count', 'success', 'error_message',
        'matching_skills', 'missing_skills', 'matching_experience',
        'experience_gaps', 'education_highlights', 'strengths',
        'weaknesses', 'red_flags', 'cultural_fit_indicators',
        'interview_focus_areas'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('application', 'candidate_name', 'email', 'contact_number')
        }),
        ('Scores', {
            'fields': (
                'final_score', 'skills_match', 'experience_score',
                'education_score', 'keywords_match', 'overall_fit',
                'growth_potential'
            )
        }),
        ('Recommendation', {
            'fields': (
                'recommendation_decision', 'recommendation_reason',
                'recommendation_confidence'
            )
        }),
        ('Skills Analysis', {
            'fields': (
                'skill_match_percentage', 'matching_skills', 'missing_skills'
            )
        }),
        ('Experience Analysis', {
            'fields': (
                'experience_level', 'matching_experience', 'experience_gaps'
            )
        }),
        ('Education Analysis', {
            'fields': (
                'education_level', 'education_highlights'
            )
        }),
        ('Job History', {
            'fields': (
                'is_fresher', 'first_job_start_year', 'last_job_end_year',
                'total_jobs_count', 'average_job_change'
            )
        }),
        ('Assessment', {
            'fields': (
                'strengths', 'weaknesses', 'red_flags', 'cultural_fit_indicators'
            )
        }),
        ('Hiring Insights', {
            'fields': (
                'salary_expectation_alignment', 'onboarding_priority',
                'interview_focus_areas'
            )
        }),
        ('Metadata', {
            'fields': (
                'processing_time', 'processed_at', 'file_path', 'file_size',
                'word_count', 'success', 'error_message'
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(ApplyJob)
class ApplyJobAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'job_code', 'analysed', 'dob', 'has_analysis']
    list_filter = ['job_code', 'analysed', 'gender']
    search_fields = ['name', 'email']

    def has_analysis(self, obj):
        return hasattr(obj, 'analysis')
    has_analysis.boolean = True
    has_analysis.short_description = 'Has Analysis'
