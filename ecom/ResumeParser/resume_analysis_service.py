import logging
from datetime import datetime
from django.utils.dateparse import parse_datetime
from django.db import transaction
from ecom.models import ApplyJob, ResumeAnalysis

logger = logging.getLogger(__name__)


class ResumeAnalysisService:

    @staticmethod
    def save_analysis_to_database(data, job_code=None):
        
        try:
            # with open(json_file_path, 'r', encoding='utf-8') as file:
            #     data = json.load(file)

            # summary = {
            #     'total_candidates': 0,
            #     'saved_successfully': 0,
            #     'updated_existing': 0,
            #     'errors': []
            # }

            # candidates = data.get('candidates', [])
            # summary['total_candidates'] = len(candidates)
            result = ResumeAnalysisService._save_single_candidate(data, job_code)
            # for candidate_data in candidates:
            #     try:
            #         with transaction.atomic():
            #             result = ResumeAnalysisService._save_single_candidate(candidate_data, job_code)
            #             if result['updated']:
            #                 summary['updated_existing'] += 1
            #             else:
            #                 summary['saved_successfully'] += 1

            #     except Exception as e:
            #         error_msg = f"Error saving {candidate_data.get('candidate_name', 'Unknown')}: {str(e)}"
            #         logger.error(error_msg)
            #         summary['errors'].append(error_msg)

            logger.info(f"Resume analysis save summary: {result}")
            return result

        except Exception as e:
            logger.error(f"Error saved analysis to database: {str(e)}")
            raise
    
    @staticmethod
    def _save_single_candidate(candidate_data, job_code=None):
        
        candidate_name = candidate_data.get('candidate_name', '')
        email = candidate_data.get('email', '')

        # Find the corresponding ApplyJob record
        application = ResumeAnalysisService._find_application(candidate_name, email, job_code)

        if not application:
            raise ValueError(f"No matching application found for {candidate_name} ({email})")

        # Prepare all analysis data including JSON fields
        analysis_data = ResumeAnalysisService._prepare_analysis_data(candidate_data, application)

        # Check if analysis already exists
        analysis, created = ResumeAnalysis.objects.get_or_create(
            application=application,
            defaults=analysis_data
        )

        if not created:
            # Update existing analysis with all data
            for key, value in analysis_data.items():
                setattr(analysis, key, value)
            analysis.save()

        # Update the application status to analyzed
        application.analysed = 1
        application.save()

        return {'updated': not created, 'analysis': analysis}
    
    @staticmethod
    def _find_application(candidate_name, email, job_code=None):
        
        try:
            # Strategy 1: Exact match with name, email, and job_code
            if job_code:
                exact_query = ApplyJob.objects.filter(
                    name=candidate_name,
                    email=email,
                    job_code=job_code
                )
                if exact_query.exists():
                    if exact_query.count() == 1:
                        return exact_query.first()
                    else:
                        print(f"Warning: Multiple exact matches for {candidate_name} ({email}) in {job_code}")
                        return exact_query.first()  # Return first match

            # Strategy 2: Exact match with name and email (any job type)
            exact_query = ApplyJob.objects.filter(
                name=candidate_name,
                email=email
            )
            if exact_query.exists():
                if job_code:
                    # Prefer the job_code match if available
                    job_specific = exact_query.filter(job_code=job_code).first()
                    if job_specific:
                        return job_specific

                if exact_query.count() == 1:
                    return exact_query.first()
                else:
                    print(f"Warning: Multiple matches for {candidate_name} ({email}), returning first match")
                    return exact_query.first()

            # Strategy 3: Partial name matching with email
            first_name = candidate_name.split()[0] if candidate_name else ""
            if first_name:
                partial_query = ApplyJob.objects.filter(
                    name__icontains=first_name,
                    email=email
                )

                if job_code:
                    partial_query = partial_query.filter(job_code=job_code)

                if partial_query.exists():
                    return partial_query.first()

            # Strategy 4: Email-only matching (last resort)
            email_query = ApplyJob.objects.filter(email=email)
            if job_code:
                email_query = email_query.filter(job_code=job_code)

            if email_query.exists():
                print(f"Warning: Using email-only match for {candidate_name} ({email})")
                return email_query.first()

            print(f"No matching application found for {candidate_name} ({email}) in {job_code or 'any job type'}")
            return None

        except Exception as e:
            print(f"Error finding application for {candidate_name}: {e}")
            return None
    
    @staticmethod
    def _prepare_analysis_data(candidate_data, application):
        
        scores = candidate_data.get('scores', {})
        recommendation = candidate_data.get('recommendation', {})
        skills_analysis = candidate_data.get('skills_analysis', {})
        experience_analysis = candidate_data.get('experience_analysis', {})
        education_analysis = candidate_data.get('education_analysis', {})
        job_analysis = candidate_data.get('job_analysis', {})
        assessment = candidate_data.get('assessment', {})
        hiring_insights = candidate_data.get('hiring_insights', {})
        metadata = candidate_data.get('metadata', {})

        # Parse processed_at datetime
        processed_at = metadata.get('processed_at')
        if processed_at:
            try:
                processed_at = parse_datetime(processed_at)
            except:
                processed_at = datetime.now()
        else:
            processed_at = datetime.now()

        return {
            'candidate_name': candidate_data.get('candidate_name', ''),
            'email': candidate_data.get('email', ''),
            'contact_number': candidate_data.get('contact_number', ''),

            # Scores
            'final_score': scores.get('final_score', 0),
            'skills_match': scores.get('skills_match', 0),
            'experience_score': scores.get('experience_score', 0),
            'education_score': scores.get('education', 0),
            'keywords_match': scores.get('keywords_match', 0),
            'overall_fit': scores.get('overall_fit', 0),
            'growth_potential': scores.get('growth_potential', 0),

            # Recommendation
            'recommendation_decision': recommendation.get('decision', ''),
            'recommendation_reason': recommendation.get('reason', ''),
            'recommendation_confidence': recommendation.get('confidence', ''),

            # Skills analysis - JSON fields
            'skill_match_percentage': skills_analysis.get('skill_match_percentage', 0),
            'matching_skills': skills_analysis.get('matching_skills', []),
            'missing_skills': skills_analysis.get('missing_skills', []),

            # Experience analysis - JSON fields
            'experience_level': experience_analysis.get('experience_level', ''),
            'matching_experience': experience_analysis.get('matching_experience', []),
            'experience_gaps': experience_analysis.get('experience_gaps', []),

            # Education analysis - JSON fields
            'education_level': education_analysis.get('education_level', ''),
            'education_highlights': education_analysis.get('education_highlights', []),

            # Job analysis
            'is_fresher': job_analysis.get('fresher', True),
            'first_job_start_year': job_analysis.get('first_job_start_year'),
            'last_job_end_year': job_analysis.get('last_job_end_year'),
            'total_jobs_count': job_analysis.get('total_jobs_count', 0),
            'average_job_change': job_analysis.get('average_job_change'),

            # Assessment - JSON fields
            'strengths': assessment.get('strengths', []),
            'weaknesses': assessment.get('weaknesses', []),
            'red_flags': assessment.get('red_flags', []),
            'cultural_fit_indicators': assessment.get('cultural_fit_indicators', []),

            # Hiring insights - JSON fields
            'salary_expectation_alignment': hiring_insights.get('salary_expectation_alignment', ''),
            'onboarding_priority': hiring_insights.get('onboarding_priority', ''),
            'interview_focus_areas': hiring_insights.get('interview_focus_areas', []),

            # Metadata
            'processing_time': metadata.get('processing_time', 0),
            'processed_at': processed_at,
            'file_path': metadata.get('file_path', ''),
            'file_size': metadata.get('file_size', 0),
            'word_count': metadata.get('word_count', 0),
            'success': metadata.get('success', True),
            'error_message': metadata.get('error'),
        }
    
