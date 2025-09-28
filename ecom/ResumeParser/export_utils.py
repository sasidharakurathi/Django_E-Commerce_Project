# import json
# import csv
# import logging
# from pathlib import Path
# from typing import Dict, List, Any, Optional
# from datetime import datetime

# import pandas as pd

# # from config import OUTPUT_DIR, OUTPUT_FORMATS, DEFAULT_OUTPUT_FORMAT, create_directories
# from django.conf import settings

# # Setup logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class ExportUtils:

#     def __init__(self,job_code):
#         # create_directories()
#         self.output_dir = Path(settings.OUTPUT_DIR) / job_code
#         # print("self.output_dir: " , self.output_dir)
#         self.supported_formats = settings.OUTPUT_FORMATS
    
#     def export_results(self, 
#                       results_data: Dict[str, Any], 
#                       output_format: str = settings.DEFAULT_OUTPUT_FORMAT,
#                       filename: Optional[str] = None) -> Dict[str, Any]:
        
#         if output_format not in self.supported_formats:
#             return {
#                 'success': False,
#                 'error': f'Unsupported format: {output_format}. Supported: {self.supported_formats}',
#                 'file_path': None
#             }
        
#         if not results_data.get('success', False):
#             return {
#                 'success': False,
#                 'error': 'Cannot export failed results',
#                 'file_path': None
#             }
        
#         try:
#             # Generate filename if not provided
#             if not filename:
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 filename = f"resume_scores_{timestamp}.{output_format}"
            
#             file_path = self.output_dir / filename
            
#             # Export based on format
#             if output_format == 'csv':
#                 success = self._export_to_csv(results_data, file_path)
#             elif output_format == 'json':
#                 success = self._export_to_json(results_data, file_path)
#             elif output_format == 'xlsx':
#                 success = self._export_to_excel(results_data, file_path)
#             else:
#                 return {
#                     'success': False,
#                     'error': f'Export method not implemented for {output_format}',
#                     'file_path': None
#                 }
            
#             if success:
#                 logger.info(f"Results exported successfully to {file_path}")
#                 return {
#                     'success': True,
#                     'file_path': str(file_path),
#                     'format': output_format,
#                     'records_exported': len(results_data.get('results', []))
#                 }
#             else:
#                 return {
#                     'success': False,
#                     'error': 'Export failed',
#                     'file_path': None
#                 }
                
#         except Exception as e:
#             logger.error(f"Error exporting results: {str(e)}")
#             return {
#                 'success': False,
#                 'error': str(e),
#                 'file_path': None
#             }

#     def export_web_json(self, results_data: Dict[str, Any], filename: str) -> Dict[str, Any]:

#         if not results_data.get('success', False):
#             return {
#                 'success': False,
#                 'error': 'Cannot export failed results',
#                 'file_path': None
#             }

#         try:
#             # Generate filename if not provided
#             # if not filename:
#             #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             #     filename = f"resume_analysis_web_{timestamp}.json"

#             file_path = self.output_dir / filename
            
#             print("filename: " , filename)

#             # Use the enhanced JSON export method
#             success = self._export_to_json(results_data, file_path)

#             if success:
#                 logger.info(f"Web-optimized JSON exported successfully to {file_path}")
#                 return {
#                     'success': True,
#                     'file_path': str(file_path),
#                     'format': 'json',
#                     'web_optimized': True,
#                     'records_exported': len(results_data.get('results', [])),
#                     'api_ready': True
#                 }
#             else:
#                 return {
#                     'success': False,
#                     'error': 'Web JSON export failed',
#                     'file_path': None
#                 }

#         except Exception as e:
#             logger.error(f"Error exporting web JSON: {str(e)}")
#             return {
#                 'success': False,
#                 'error': str(e),
#                 'file_path': None
#             }
    
#     def _export_to_csv(self, results_data: Dict[str, Any], file_path: Path) -> bool:
#         """Export results to CSV format"""
        
#         try:
#             results = results_data.get('results', [])
            
#             if not results:
#                 logger.warning("No results to export")
#                 return False
            
#             # Prepare CSV data
#             csv_data = []
#             for result in results:
#                 # Get analysis data if available
#                 analysis = result.get('analysis', {}) if result.get('success') else {}
#                 metadata = result.get('metadata', {})

#                 row = {
#                     'filename': result.get('filename', ''),
#                     'candidate_name': metadata.get('candidate_name', 'Name not found'),
#                     'final_score': result.get('final_score', 0),
#                     'recommendation': result.get('recommendation', 'REJECT'),
#                     'recommendation_reason': analysis.get('recommendation_reason', ''),
#                     'skills_match_score': result.get('scores', {}).get('skills_match', 0),
#                     'experience_score': result.get('scores', {}).get('experience_relevance', 0),
#                     'education_score': result.get('scores', {}).get('education', 0),
#                     'keywords_match_score': result.get('scores', {}).get('keywords_match', 0),
#                     'overall_fit_score': result.get('scores', {}).get('overall_fit', 0),
#                     'growth_potential_score': analysis.get('growth_potential', 0),
#                     'matching_skills': '; '.join(analysis.get('matching_skills', [])),
#                     'missing_skills': '; '.join(analysis.get('missing_skills', [])),
#                     'required_skills_count': analysis.get('required_skills_count', 0),
#                     'matched_skills_count': analysis.get('matched_skills_count', 0),
#                     'skills_coverage_percentage': analysis.get('skills_coverage_percentage', 0),
#                     'meets_minimum_skills': analysis.get('meets_minimum_skills', False),
#                     'skills_coverage_level': analysis.get('skills_coverage_level', 'UNKNOWN'),
#                     'matching_experience': '; '.join(analysis.get('matching_experience', [])),
#                     'experience_gaps': '; '.join(analysis.get('experience_gaps', [])),
#                     'education_highlights': '; '.join(analysis.get('education_highlights', [])),
#                     'strengths': '; '.join(result.get('strengths', [])),
#                     'weaknesses': '; '.join(result.get('weaknesses', [])),
#                     'red_flags': '; '.join(analysis.get('red_flags', [])),
#                     'cultural_fit_indicators': '; '.join(analysis.get('cultural_fit_indicators', [])),
#                     'salary_expectation_alignment': analysis.get('salary_expectation_alignment', 'MEDIUM'),
#                     'interview_focus_areas': '; '.join(analysis.get('interview_focus_areas', [])),
#                     'summary': result.get('summary', ''),
#                     'processing_time': result.get('processing_time', 0),
#                     'success': result.get('success', False),
#                     'error': result.get('error', ''),
#                     'file_path': result.get('file_path', '')
#                 }
#                 csv_data.append(row)
            
#             # Write CSV file
#             with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
#                 fieldnames = csv_data[0].keys()
#                 writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#                 writer.writeheader()
#                 writer.writerows(csv_data)
            
#             return True
            
#         except Exception as e:
#             logger.error(f"Error exporting to CSV: {str(e)}")
#             return False
    
#     def _export_to_json(self, results_data: Dict[str, Any], file_path: Path) -> bool:
#         """Export results to JSON format optimized for web applications"""

        
#         try:
#             # Process results for web-friendly format
            
#             existing_json_data = None
#             processed_results = []
            
#             try:
#                 with open(file_path , "r" , encoding="utf-8") as json_file:
#                     existing_json_data = json.load(json_file)
#             except (FileNotFoundError , json.JSONDecodeError):
#                 print(f"{file_path} is not found.")
#                 existing_json_data = json.loads(settings.JSON_BOILERPLATE)
            
#             for result in results_data.get('results', []):
#                 analysis = result.get('analysis', {}) if result.get('success') else {}
#                 metadata = result.get('metadata', {})
                
#                 from .. import models
#                 job = models.ApplyJob.objects.filter(resume__contains=result.get('filename', ''))
                
#                 print("result: ",result)

#                 web_result = {
#                     # 'id': f"resume_{len(processed_results) + 1}",
#                     'filename': result.get('filename', ''),
#                     'candidate_name': metadata.get('candidate_name', 'Name not found'),
#                     'email': job[0].email if job else "No email found",
#                     'contact_number': job[0].contact_number if job else "No contact number found",
#                     'scores': {
#                         'final_score': result.get('final_score', 0),
#                         'skills_match': result.get('scores', {}).get('skills_match', 0),
#                         'experience_score': result.get('scores', {}).get('experience_relevance', 0),
#                         'education_score': result.get('scores', {}).get('education', 0),
#                         'keywords_match': result.get('scores', {}).get('keywords_match', 0),
#                         'overall_fit': result.get('scores', {}).get('overall_fit', 0),
#                         'growth_potential': analysis.get('growth_potential', 0)
#                     },
#                     'recommendation': {
#                         'decision': result.get('recommendation', 'REJECT'),
#                         'reason': analysis.get('recommendation_reason', ''),
#                         'confidence': 'HIGH' if result.get('final_score', 0) > 80 else 'MEDIUM' if result.get('final_score', 0) > 60 else 'LOW'
#                     },
#                     'skills_analysis': {
#                         'matching_skills': analysis.get('matching_skills', []),
#                         'missing_skills': analysis.get('missing_skills', []),
#                         'skill_match_percentage': round((len(analysis.get('matching_skills', [])) / max(len(analysis.get('matching_skills', [])) + len(analysis.get('missing_skills', [])), 1)) * 100, 1)
#                     },
#                     'experience_analysis': {
#                         'matching_experience': analysis.get('matching_experience', []),
#                         'experience_gaps': analysis.get('experience_gaps', []),
#                         'experience_level': 'SENIOR' if result.get('scores', {}).get('experience_relevance', 0) > 80 else 'MID' if result.get('scores', {}).get('experience_relevance', 0) > 60 else 'JUNIOR'
#                     },
#                     'education_analysis': {
#                         'education_highlights': analysis.get('education_highlights', []),
#                         'education_level': 'ADVANCED' if result.get('scores', {}).get('education', 0) > 80 else 'STANDARD' if result.get('scores', {}).get('education', 0) > 60 else 'BASIC'
#                     },
#                     'job_analysis': {
#                         "fresher": analysis.get('fresher', 'true'),
#                         "first_job_start_year": analysis.get('first_job_start_year', 'null') if analysis.get('fresher', True) == False else 0,
#                         "last_job_end_year": analysis.get('last_job_end_year', 'null') if analysis.get('fresher', True) == False else 0,
#                         "total_jobs_count": analysis.get('total_jobs_count', 'null') if analysis.get('fresher', True) == False else 0,
#                         "average_job_change": self.getAverageJobChange(analysis.get('fresher', 'true'),analysis.get('first_job_start_year', 'null'),analysis.get('last_job_end_year', 'null'),analysis.get('total_jobs_count', 'null')),
#                     },
#                     'assessment': {
#                         'strengths': result.get('strengths', []),
#                         'weaknesses': result.get('weaknesses', []),
#                         'red_flags': analysis.get('red_flags', []),
#                         'cultural_fit_indicators': analysis.get('cultural_fit_indicators', [])
#                     },
#                     'hiring_insights': {
#                         'salary_expectation_alignment': analysis.get('salary_expectation_alignment', 'MEDIUM'),
#                         'interview_focus_areas': analysis.get('interview_focus_areas', []),
#                         'onboarding_priority': 'HIGH' if result.get('recommendation') == 'HIRE' else 'MEDIUM' if result.get('recommendation') == 'CONSIDER' else 'LOW'
#                     },
#                     'metadata': {
#                         'processing_time': result.get('processing_time', 0),
#                         'processed_at': result.get('timestamp', datetime.now().isoformat()),
#                         'file_path': str(result.get('file_path', '')),
#                         'file_size': metadata.get('file_size', 0),
#                         'word_count': metadata.get('word_count', 0),
#                         'success': result.get('success', False),
#                         'error': result.get('error', '') if not result.get('success', False) else None
#                     },
#                     'summary': result.get('summary', '')
#                 }
#                 existing_json_data["candidates"].append(web_result)
#                 # processed_results.append(web_result)

#             # Create web-optimized JSON structure
#             export_data = {
#                 'meta': {
#                     # 'version': '1.0',
#                     # 'exported_at': datetime.now().isoformat(),
#                     'total_candidates': len(existing_json_data["candidates"]),
#                     'successful_analyses': len([r for r in existing_json_data["candidates"] if r['metadata']['success']]),
#                     'failed_analyses': len([r for r in existing_json_data["candidates"] if not r['metadata']['success']]),
#                     'job_description': results_data.get('job_description', ''),
#                     'processed_at': results_data.get('processed_at', '')
#                 },
#                 'summary_statistics': {
#                     'average_score': results_data.get('statistics', {}).get('average_score', self.find_average(existing_json_data["candidates"])),
#                     'score_distribution': {
#                         'excellent': len([r for r in existing_json_data["candidates"] if r['scores']['final_score'] >= 90]),
#                         'good': len([r for r in existing_json_data["candidates"] if 80 <= r['scores']['final_score'] < 90]),
#                         'average': len([r for r in existing_json_data["candidates"] if 60 <= r['scores']['final_score'] < 80]),
#                         'below_average': len([r for r in existing_json_data["candidates"] if r['scores']['final_score'] < 60])
#                     },
#                     'recommendations': results_data.get('statistics', {}).get('recommendations', {}),
#                     'processing_time': results_data.get('statistics', {}).get('processing_time', 0)
#                 },
#                 'candidates': existing_json_data["candidates"],
#                 'top_candidates': sorted(
#                     [r for r in existing_json_data["candidates"] if r['metadata']['success']],
#                     key=lambda x: x['scores']['final_score'],
#                     reverse=True
#                 )[ : 10 if len(existing_json_data["candidates"]) >= 10 else len(existing_json_data["candidates"])],  # Top 10 candidates
#                 'boiler_plate': 0
#             }

#             # Write JSON file
#             with open(file_path, 'w', encoding='utf-8') as jsonfile:
#                 json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)

#             # Automatically save to database after JSON export
#             try:
#                 from .resume_analysis_service import ResumeAnalysisService

#                 # Extract job code from filename (e.g., resume_analysis_web_py.json -> PY)
#                 filename = file_path.name
#                 job_code = None
#                 if '_' in filename:
#                     parts = filename.replace('.json', '').split('_')
#                     if len(parts) > 2:
#                         job_code = parts[-1].upper()
                
#                 logger.info(f"\nAuto-saving analysis data to database for job code: {job_code}\n")
#                 # summary = ResumeAnalysisService.save_analysis_to_database(str(file_path), job_code)
#                 # logger.info(f"\nDatabase save summary: {summary}\n")

#             except Exception as e:
#                 logger.warning(f"\nFailed to auto-save to database: {str(e)}\n")
#                 # Don't fail the JSON export if database save fails

#             return True

#         except Exception as e:
#             logger.error(f"Error exporting to JSON: {str(e)}")
#             return False
    
#     def getAverageJobChange(self, fresher, first_job_start_year, last_job_end_year, total_jobs_count):
#         if fresher:
#             return "No job changes"
#         else:
#             # Validate input data
#             if (first_job_start_year != 'null' and last_job_end_year != 'null' and
#                 total_jobs_count != 'null' and total_jobs_count > 0):

#                 try:
#                     # Convert to integers if they're strings
#                     start_year = int(first_job_start_year)
#                     end_year = int(last_job_end_year)
#                     job_count = int(total_jobs_count)

#                     # If only one job, no job changes
#                     if job_count <= 1:
#                         return "No job changes"

#                     # Calculate total career duration in years
#                     total_career_years = max(1, end_year - start_year)

#                     # Calculate average time per job (not between job changes)
#                     # This represents how long someone typically stays in each job
#                     average_time_per_job = total_career_years / job_count

#                     # Convert to years and months
#                     years = int(average_time_per_job)
#                     months = int((average_time_per_job - years) * 12)

#                     # Format the output
#                     if years == 0 and months == 0:
#                         return "Less than 1 month"
#                     elif years == 0:
#                         return f"{months} month{'s' if months != 1 else ''}"
#                     elif months == 0:
#                         return f"{years} year{'s' if years != 1 else ''}"
#                     else:
#                         return f"{years} year{'s' if years != 1 else ''} {months} month{'s' if months != 1 else ''}"

#                 except (ValueError, TypeError):
#                     # Handle conversion errors
#                     return "No job changes"
#             else:
#                 return "No job changes"
    
#     def _export_to_excel(self, results_data: Dict[str, Any], file_path: Path) -> bool:
#         """Export results to Excel format with multiple sheets"""
        
#         try:
#             results = results_data.get('results', [])
#             statistics = results_data.get('statistics', {})
            
#             if not results:
#                 logger.warning("No results to export")
#                 return False
            
#             # Create Excel writer
#             with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                
#                 # Main results sheet
#                 main_data = []
#                 for result in results:
#                     # Get analysis data if available
#                     analysis = result.get('analysis', {}) if result.get('success') else {}
#                     metadata = result.get('metadata', {})

#                     row = {
#                         'Filename': result.get('filename', ''),
#                         'Candidate Name': metadata.get('candidate_name', 'Name not found'),
#                         'Final Score': result.get('final_score', 0),
#                         'Recommendation': result.get('recommendation', 'REJECT'),
#                         'Recommendation Reason': analysis.get('recommendation_reason', ''),
#                         'Skills Match Score': result.get('scores', {}).get('skills_match', 0),
#                         'Experience Score': result.get('scores', {}).get('experience_relevance', 0),
#                         'Education Score': result.get('scores', {}).get('education', 0),
#                         'Keywords Match Score': result.get('scores', {}).get('keywords_match', 0),
#                         'Overall Fit Score': result.get('scores', {}).get('overall_fit', 0),
#                         'Growth Potential Score': analysis.get('growth_potential', 0),
#                         'Matching Skills': '; '.join(analysis.get('matching_skills', [])),
#                         'Missing Skills': '; '.join(analysis.get('missing_skills', [])),
#                         'Required Skills Count': analysis.get('required_skills_count', 0),
#                         'Matched Skills Count': analysis.get('matched_skills_count', 0),
#                         'Skills Coverage %': analysis.get('skills_coverage_percentage', 0),
#                         'Meets Minimum Skills': analysis.get('meets_minimum_skills', False),
#                         'Skills Coverage Level': analysis.get('skills_coverage_level', 'UNKNOWN'),
#                         'Matching Experience': '; '.join(analysis.get('matching_experience', [])),
#                         'Experience Gaps': '; '.join(analysis.get('experience_gaps', [])),
#                         'Education Highlights': '; '.join(analysis.get('education_highlights', [])),
#                         'Strengths': '; '.join(result.get('strengths', [])),
#                         'Weaknesses': '; '.join(result.get('weaknesses', [])),
#                         'Red Flags': '; '.join(analysis.get('red_flags', [])),
#                         'Cultural Fit Indicators': '; '.join(analysis.get('cultural_fit_indicators', [])),
#                         'Salary Expectation Alignment': analysis.get('salary_expectation_alignment', 'MEDIUM'),
#                         'Interview Focus Areas': '; '.join(analysis.get('interview_focus_areas', [])),
#                         'Summary': result.get('summary', ''),
#                         'Processing Time (s)': result.get('processing_time', 0),
#                         'Success': result.get('success', False),
#                         'Error': result.get('error', ''),
#                         'File Path': result.get('file_path', '')
#                     }
#                     main_data.append(row)
                
#                 df_main = pd.DataFrame(main_data)
#                 df_main.to_excel(writer, sheet_name='Resume Scores', index=False)
                
#                 # Statistics sheet
#                 stats_data = [
#                     ['Metric', 'Value'],
#                     ['Total Resumes', statistics.get('total_resumes', 0)],
#                     ['Successful', statistics.get('successful', 0)],
#                     ['Failed', statistics.get('failed', 0)],
#                     ['Average Score', statistics.get('average_score', 0)],
#                     ['Max Score', statistics.get('max_score', 0)],
#                     ['Min Score', statistics.get('min_score', 0)],
#                     ['Processing Time (s)', statistics.get('processing_time', 0)],
#                     ['Avg Time per Resume (s)', statistics.get('average_processing_time_per_resume', 0)],
#                     ['', ''],
#                     ['Recommendations', ''],
#                     ['HIRE', statistics.get('recommendations', {}).get('HIRE', 0)],
#                     ['CONSIDER', statistics.get('recommendations', {}).get('CONSIDER', 0)],
#                     ['REJECT', statistics.get('recommendations', {}).get('REJECT', 0)]
#                 ]
                
#                 df_stats = pd.DataFrame(stats_data)
#                 df_stats.to_excel(writer, sheet_name='Statistics', index=False, header=False)
                
#                 # Top candidates sheet
#                 top_candidates = statistics.get('top_candidates', [])
#                 if top_candidates:
#                     df_top = pd.DataFrame(top_candidates)
#                     df_top.to_excel(writer, sheet_name='Top Candidates', index=False)
                
#                 # Job description sheet
#                 job_desc_data = [
#                     ['Job Description'],
#                     [results_data.get('job_description', '')],
#                     [''],
#                     ['Processed At'],
#                     [results_data.get('processed_at', '')]
#                 ]
                
#                 df_job = pd.DataFrame(job_desc_data)
#                 df_job.to_excel(writer, sheet_name='Job Description', index=False, header=False)
            
#             return True
            
#         except Exception as e:
#             logger.error(f"Error exporting to Excel: {str(e)}")
#             return False
    
#     def export_summary_report(self, results_data: Dict[str, Any], filename: Optional[str] = None) -> Dict[str, Any]:
#         """Export a summary report in text format"""
        
#         try:
#             if not filename:
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 filename = f"resume_summary_{timestamp}.txt"
            
#             file_path = self.output_dir / filename
            
#             statistics = results_data.get('statistics', {})
#             results = results_data.get('results', [])
            
#             with open(file_path, 'w', encoding='utf-8') as f:
#                 f.write("RESUME SCORING SUMMARY REPORT\n")
#                 f.write("=" * 50 + "\n\n")
                
#                 f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
#                 f.write(f"Job Description: {results_data.get('job_description', 'N/A')[:100]}...\n\n")
                
#                 f.write("STATISTICS:\n")
#                 f.write("-" * 20 + "\n")
#                 f.write(f"Total Resumes Processed: {statistics.get('total_resumes', 0)}\n")
#                 f.write(f"Successful: {statistics.get('successful', 0)}\n")
#                 f.write(f"Failed: {statistics.get('failed', 0)}\n")
#                 f.write(f"Average Score: {statistics.get('average_score', 0):.2f}\n")
#                 f.write(f"Processing Time: {statistics.get('processing_time', 0):.2f} seconds\n\n")
                
#                 f.write("RECOMMENDATIONS:\n")
#                 f.write("-" * 20 + "\n")
#                 recommendations = statistics.get('recommendations', {})
#                 f.write(f"HIRE: {recommendations.get('HIRE', 0)}\n")
#                 f.write(f"CONSIDER: {recommendations.get('CONSIDER', 0)}\n")
#                 f.write(f"REJECT: {recommendations.get('REJECT', 0)}\n\n")
                
#                 f.write("TOP CANDIDATES:\n")
#                 f.write("-" * 20 + "\n")
#                 top_candidates = statistics.get('top_candidates', [])
#                 for i, candidate in enumerate(top_candidates, 1):
#                     f.write(f"{i}. {candidate.get('filename', 'N/A')} - "
#                            f"Score: {candidate.get('score', 0):.2f} - "
#                            f"{candidate.get('recommendation', 'N/A')}\n")
            
#             return {
#                 'success': True,
#                 'file_path': str(file_path),
#                 'format': 'txt'
#             }
            
#         except Exception as e:
#             logger.error(f"Error creating summary report: {str(e)}")
#             return {
#                 'success': False,
#                 'error': str(e),
#                 'file_path': None
#             }
    
#     def find_average(self,candidates):
#         candidates_count = len(candidates)
#         average_score = 0
#         for candidate in candidates:
#             average_score += candidate.get("scores" , {}).get("final_score" , 0)
        
#         return average_score / candidates_count


# def test_export_utils():
#     """Test function for export utilities"""
    
#     # Sample results data
#     sample_results = {
#         'success': True,
#         'job_description': 'Software Developer with Python and React experience',
#         'processed_at': datetime.now().isoformat(),
#         'results': [
#             {
#                 'filename': 'john_doe.pdf',
#                 'final_score': 85.5,
#                 'recommendation': 'HIRE',
#                 'scores': {
#                     'skills_match': 90,
#                     'experience_relevance': 85,
#                     'education': 80,
#                     'keywords_match': 88,
#                     'overall_fit': 82
#                 },
#                 'strengths': ['Strong Python skills', 'React experience'],
#                 'weaknesses': ['Limited cloud experience'],
#                 'summary': 'Excellent candidate with strong technical skills',
#                 'processing_time': 2.5,
#                 'success': True,
#                 'error': '',
#                 'file_path': '/path/to/john_doe.pdf'
#             }
#         ],
#         'statistics': {
#             'total_resumes': 1,
#             'successful': 1,
#             'failed': 0,
#             'average_score': 85.5,
#             'max_score': 85.5,
#             'min_score': 85.5,
#             'processing_time': 2.5,
#             'recommendations': {'HIRE': 1, 'CONSIDER': 0, 'REJECT': 0},
#             'top_candidates': [
#                 {'filename': 'john_doe.pdf', 'score': 85.5, 'recommendation': 'HIRE'}
#             ]
#         }
#     }
    
#     # Test exports
#     exporter = ExportUtils()
    
#     # Test CSV export
#     csv_result = exporter.export_results(sample_results, 'csv', 'test_results.csv')
#     print(f"CSV Export: {csv_result}")
    
#     # Test JSON export
#     json_result = exporter.export_results(sample_results, 'json', 'test_results.json')
#     print(f"JSON Export: {json_result}")
    
#     # Test summary report
#     summary_result = exporter.export_summary_report(sample_results, 'test_summary.txt')
#     print(f"Summary Export: {summary_result}")


# if __name__ == "__main__":
#     test_export_utils()
