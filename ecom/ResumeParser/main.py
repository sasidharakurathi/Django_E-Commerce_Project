"""
Resume Parser and Scoring System - Simple Interface
Parse and score resumes using Ollama LLM
"""

import logging
from pathlib import Path
from typing import Dict, Any

from .resume_analyzer import ResumeAnalyzer
# from config import RESUMES_DIR, OUTPUT_DIR, create_directories
from django.conf import settings
from ..models import ApplyJob
from ..models import AnalysedChoices
from .db_operations import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_resumes(job_description: str, job_code: str,resume_files: list = [], min_score: float = 0,verbose: bool = False) -> Dict[str, Any]:

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate inputs
    if not job_description.strip():
        raise ValueError("Job description cannot be empty")


    logger.info(f"🚀 Starting resume processing...")
    # logger.info(f"📁 Resumes directory: {resumes_dir}")
    logger.info(f"📄 Job description: {job_description[:100]}...")
    logger.info(f"🔄 Processing: Sequential")

    # Progress callback
    def progress_callback(current: int, total: int, result: dict):
        filename = result.get('filename', 'unknown')
        score = result.get('final_score', 0)
        recommendation = result.get('recommendation', 'UNKNOWN')

        if result.get('success', False):
            logger.info(f"✅ [{current}/{total}] {filename} - Score: {score:.1f} - {recommendation}")
            update_analysis_in_db(filename , job_code)
        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"❌ [{current}/{total}] {filename} - Error: {error}")

    # Process resumes using ResumeAnalyzer
    analyzer = ResumeAnalyzer(job_code)

    # Find all resume files
    if not resume_files:
        # resume_files = []
        
        # Get Resume Files from Database for specific job code
        job_applicants = ApplyJob.objects.filter(
            analysed=AnalysedChoices.UNANALYZED,
            job_code=job_code
        )
        print(f"Found {job_applicants.count()} unanalyzed resumes for job code: {job_code}")

        for job_applicant in job_applicants:
            print("job_applicant.resume: ",job_applicant.resume)
            file_path = settings.PROJECT_ROOT / str(job_applicant.resume)
            resume_files.append(str(file_path))  # Convert Path to string
    
    
    # Process resumes
    results = analyzer.analyze_multiple_resumes(resume_files, job_description, progress_callback)

    if not results['success']:
        raise RuntimeError(f"Processing failed: {results.get('error', 'Unknown error')}")

    # Filter results by minimum score
    if min_score > 0:
        original_count = len(results['results'])
        results['results'] = [
            r for r in results['results']
            if r.get('final_score', 0) >= min_score
        ]
        filtered_count = len(results['results'])
        logger.info(f"🔍 Filtered results: {filtered_count}/{original_count} resumes with score >= {min_score}")

    # Export results to JSON (using analyzer's built-in export)
    # export_result = analyzer.export_results_to_json(results , job_code)
    export_result = get_results_by_job_code(job_code)

    # if export_result['success']:
    #     logger.info(f"💾 Results exported to: {export_result['file_path']}")
    # else:
    #     logger.error(f"❌ Export failed: {export_result['error']}")

    # Display summary
    stats = results['statistics']
    logger.info("\n📈 PROCESSING SUMMARY:")
    logger.info(f"   Total resumes: {stats['total_resumes']}")
    logger.info(f"   Successful: {stats['successful']}")
    logger.info(f"   Failed: {stats['failed']}")
    logger.info(f"   Average score: {stats['average_score']:.2f}")

    logger.info("\n🎯 RECOMMENDATIONS:")
    recs = stats['recommendations']
    logger.info(f"   HIRE: {recs['HIRE']}")
    logger.info(f"   CONSIDER: {recs['CONSIDER']}")
    logger.info(f"   REJECT: {recs['REJECT']}")

    logger.info("\n✅ Processing completed successfully!")

    return results