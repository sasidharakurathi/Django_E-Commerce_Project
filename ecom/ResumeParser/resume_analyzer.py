import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .resume_parser import ResumeParser
from .scoring_engine import ScoringEngine
# from .export_utils import ExportUtils
from .db_operations import *
from .resume_analysis_service import ResumeAnalysisService
from django.conf import settings


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResumeAnalyzer:

    def __init__(self , job_code):
        
        self.resume_parser = ResumeParser()
        self.scoring_engine = ScoringEngine()
        # self.export_utils = ExportUtils(job_code)
        self.job_code = job_code

    def analyze_single_resume(self, resume_file_path: str, job_description: str) -> Dict[str, Any]:
        
        try:
            # Parse the resume
            parsed_resume = self.resume_parser.parse_resume(resume_file_path)
            
            if not parsed_resume['success']:
                return {
                    'success': False,
                    'error': parsed_resume['error'],
                    'filename': Path(resume_file_path).name,
                    'final_score': 0,
                    'recommendation': 'REJECT'
                }
            
            # Score the resume
            scoring_result = self.scoring_engine.score_resume(parsed_resume, job_description)
            
            # Add file path information
            scoring_result['file_path'] = resume_file_path
            
            return scoring_result
            
        except Exception as e:
            logger.error(f"Error analyzing resume {resume_file_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'filename': Path(resume_file_path).name,
                'final_score': 0,
                'recommendation': 'REJECT',
                'file_path': resume_file_path
            }

    def analyze_multiple_resumes(self, resume_files: List[str], job_description: str,
                               progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        
        results = []
        total_files = len(resume_files)
        
        logger.info(f"Analyzing {total_files} resumes sequentially")
        
        for i, file_path in enumerate(resume_files):
            result = self.analyze_single_resume(file_path, job_description)
            # self.writeResultToTextFile(result)
            
            #   --- Creating Entry in DB ---
            # candidate_name = result['analysis']['candidate_name']
            filename = result['filename']
            success = result['success']
            web_json_data = self.structure_web_json(result)
            resume_attribute = create_or_update_json_analysis_db(filename , self.job_code , web_json_data , success)
            summary = ResumeAnalysisService.save_analysis_to_database(json.loads(resume_attribute.analysis_json), self.job_code)
            logger.info(f"\nDatabase save summary: {summary}\n")
            if resume_attribute:
                result_web_data = json.loads(resume_attribute.analysis_json)
                results.append(result_web_data)
            else:
                print(f"⚠️  WARNING: Could not save analysis for '{filename}' to database")
                print(f"   Analysis will be skipped for this candidate")
                # Still add the result to maintain processing flow, but mark it as unsaved
                web_json_data['database_saved'] = False
                web_json_data['error'] = f"Could not find matching ApplyJob record for '{filename}'"
                results.append(web_json_data)
            
            if progress_callback:
                progress_callback(i + 1, total_files, result)

            logger.info(f"Processed {i + 1}/{total_files}: {Path(file_path).name}")
        
        # Calculate statistics
        statistics = self._calculate_statistics(results)
        
        return {
            'success': True,
            'results': results,
            'statistics': statistics,
            'job_description': job_description
        }

    # def export_results_to_json(self, results: Dict[str, Any] , job_code: str) -> Dict[str, Any]:
    #     """
    #     Export analysis results to JSON format

    #     Args:
    #         results (Dict): Analysis results
    #         output_path (str): Optional output file path

    #     Returns:
    #         Dict containing export status and file path
    #     """
    #     try:
    #         filename = settings.OUTPUT_FILENAME + "_" +job_code + ".json"
    #         return self.export_utils.export_web_json(results , filename)
    #     except Exception as e:
    #         logger.error(f"Error exporting results: {str(e)}")
    #         return {
    #             'success': False,
    #             'error': str(e)
    #         }

    def _extract_basic_metadata(self, text: str) -> Dict[str, Any]:
        
        import re
        
        metadata = {
            'word_count': len(text.split()),
            'has_email': bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
            'has_phone': bool(re.search(r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)),
            'has_linkedin': 'linkedin' in text.lower(),
            'has_github': 'github' in text.lower(),
            'candidate_name': self._extract_name(text)
        }
        
        return metadata

    def _extract_name(self, text: str) -> str:
        
        lines = text.strip().split('\n')
        if lines:
            # Usually the first line contains the name
            first_line = lines[0].strip()
            if len(first_line.split()) >= 2 and len(first_line) < 50:
                return first_line
        return "Name not found"

    def _calculate_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        
        
        # print("results:2 " , results)
        
        total_resumes = len(results)
        successful_results = [r for r in results if r.get('success', False)]
        failed_results = [r for r in results if not r.get('success', False)]
        
        print(len(failed_results))
        print("!!!!!!!!!!!!!!!!!!!!!!!")
        # [print(r) for r in results]
        
        if not successful_results:
            return {
                'total_resumes': total_resumes,
                'successful': 0,
                'failed': len(failed_results),
                'average_score': 0,
                'recommendations': {'HIRE': 0, 'CONSIDER': 0, 'REJECT': total_resumes}
            }
        
        # Score statistics
        scores = [r.get('final_score', 0) for r in successful_results]
        average_score = sum(scores) / len(scores) if scores else 0
        
        # Recommendation statistics
        recommendations = {'HIRE': 0, 'CONSIDER': 0, 'REJECT': 0}
        for result in results:
            rec = result.get('recommendation', 'REJECT').get('decision' , 'REJECT')
            # print("-----------------")
            # print(rec)
            # print(recommendations.get(rec, 0))
            recommendations[rec] = recommendations.get(rec, 0) + 1
        
        return {
            'total_resumes': total_resumes,
            'successful': len(successful_results),
            'failed': len(failed_results),
            'average_score': round(average_score, 2),
            'recommendations': recommendations
        }

    def structure_web_json(self,result):
        
        # Get analysis data if available
        analysis = result.get('analysis', {}) if result.get('success') else {}
        metadata = result.get('metadata', {})
        
        job = models.ApplyJob.objects.filter(resume__contains=result.get('filename', ''))
        
        
        web_result = {
            # 'id': f"resume_{len(processed_results) + 1}",
            'success': True,
            'filename': result.get('filename', ''),
            'candidate_name': job[0].name if job else "No name found",
            'email': job[0].email if job else "No email found",
            'contact_number': job[0].contact_number if job else "No contact number found",
            'scores': {
                'final_score': result.get('final_score', 0),
                'skills_match': result.get('scores', {}).get('skills_match', 0),
                'experience_score': result.get('scores', {}).get('experience_relevance', 0),
                'education_score': result.get('scores', {}).get('education', 0),
                'keywords_match': result.get('scores', {}).get('keywords_match', 0),
                'overall_fit': result.get('scores', {}).get('overall_fit', 0),
                'growth_potential': analysis.get('growth_potential', 0)
            },
            'recommendation': {
                'decision': result.get('recommendation', 'REJECT'),
                'reason': analysis.get('recommendation_reason', ''),
                'confidence': 'HIGH' if result.get('final_score', 0) > 80 else 'MEDIUM' if result.get('final_score', 0) > 60 else 'LOW'
            },
            'skills_analysis': {
                'matching_skills': analysis.get('matching_skills', []),
                'missing_skills': analysis.get('missing_skills', []),
                'skill_match_percentage': round((len(analysis.get('matching_skills', [])) / max(len(analysis.get('matching_skills', [])) + len(analysis.get('missing_skills', [])), 1)) * 100, 1)
            },
            'experience_analysis': {
                'matching_experience': analysis.get('matching_experience', []),
                'experience_gaps': analysis.get('experience_gaps', []),
                'experience_level': ( 'Experienced' if result.get('scores', {}).get('experience_relevance', 0) > 80 else 'Intermediate' if result.get('scores', {}).get('experience_relevance', 0) > 60 else 'Beginner' )},
            'education_analysis': {
                'education_highlights': analysis.get('education_highlights', []),
                'education_level': 'ADVANCED' if result.get('scores', {}).get('education', 0) > 80 else 'STANDARD' if result.get('scores', {}).get('education', 0) > 60 else 'BASIC'
            },
            'job_analysis': {
                "fresher": analysis.get('fresher', 'true'),
                "first_job_start_year": analysis.get('first_job_start_year', 'null') if analysis.get('fresher', True) == False else 0,
                "last_job_end_year": analysis.get('last_job_end_year', 'null') if analysis.get('fresher', True) == False else 0,
                "total_jobs_count": analysis.get('total_jobs_count', 'null') if analysis.get('fresher', True) == False else 0,
                "average_job_change": self.getAverageJobChange(analysis.get('fresher', 'true'),analysis.get('first_job_start_year', 'null'),analysis.get('last_job_end_year', 'null'),analysis.get('total_jobs_count', 'null')),
            },
            'assessment': {
                'strengths': result.get('strengths', []),
                'weaknesses': result.get('weaknesses', []),
                'red_flags': analysis.get('red_flags', []),
                'cultural_fit_indicators': analysis.get('cultural_fit_indicators', [])
            },
            'hiring_insights': {
                'salary_expectation_alignment': analysis.get('salary_expectation_alignment', 'MEDIUM'),
                'interview_focus_areas': analysis.get('interview_focus_areas', []),
                'onboarding_priority': 'HIGH' if result.get('recommendation') == 'HIRE' else 'MEDIUM' if result.get('recommendation') == 'CONSIDER' else 'LOW'
            },
            'metadata': {
                'processing_time': result.get('processing_time', 0),
                'processed_at': result.get('timestamp', datetime.now().isoformat()),
                'file_path': str(result.get('file_path', '')),
                'file_size': metadata.get('file_size', 0),
                'word_count': metadata.get('word_count', 0),
                'success': result.get('success', False),
                'error': result.get('error', '') if not result.get('success', False) else None
            },
            'summary': result.get('summary', '')
        }
        
        return web_result
        
    def getAverageJobChange(self, fresher, first_job_start_year, last_job_end_year, total_jobs_count):
        if fresher:
            return "No job changes"
        else:
            # Validate input data
            if (first_job_start_year != 'null' and last_job_end_year != 'null' and
                total_jobs_count != 'null' and total_jobs_count > 0):

                try:
                    # Convert to integers if they're strings
                    start_year = int(first_job_start_year)
                    end_year = int(last_job_end_year)
                    job_count = int(total_jobs_count)

                    # If only one job, no job changes
                    if job_count <= 1:
                        return "No job changes"

                    # Calculate total career duration in years
                    total_career_years = max(1, end_year - start_year)

                    # Calculate average time per job (not between job changes)
                    # This represents how long someone typically stays in each job
                    average_time_per_job = total_career_years / job_count

                    # Convert to years and months
                    years = int(average_time_per_job)
                    months = int((average_time_per_job - years) * 12)

                    # Format the output
                    if years == 0 and months == 0:
                        return "Less than 1 month"
                    elif years == 0:
                        return f"{months} month{'s' if months != 1 else ''}"
                    elif months == 0:
                        return f"{years} year{'s' if years != 1 else ''}"
                    else:
                        return f"{years} year{'s' if years != 1 else ''} {months} month{'s' if months != 1 else ''}"

                except (ValueError, TypeError):
                    # Handle conversion errors
                    return "No job changes"
            else:
                return "No job changes"
            
    def writeResultToTextFile(self , result):
        with open("test.txt" , "w") as fp:
            fp.write(json.dumps(result , indent=2))