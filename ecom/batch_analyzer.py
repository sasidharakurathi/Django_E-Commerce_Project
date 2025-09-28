import json
import logging
from . import models
from .ResumeParser.main import process_resumes

# Setup logging for single-user analysis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchResumeAnalyzer:
    

    def analyse_resume_batch(self, job_id, job_code, batch_id, resume_batch, total_batches):
        
        logger.info(f"Starting batch analysis for job {job_code}, batch {batch_id}/{total_batches}")



        try:
            logger.info(f"Processing batch {batch_id}/{total_batches} with {len(resume_batch)} resume IDs: {resume_batch}")

            responseData = self._analyse_resumes(job_id, resume_batch, batch_id, total_batches)
            logger.info(f"Completed batch {batch_id}/{total_batches} analysis")

            return responseData

        except Exception as e:
            logger.error(f"Analysis failed for job {job_code}: {str(e)}", exc_info=True)
            return {
                "job_code": job_code,
                "batch_no": batch_id,
                "total_batches": total_batches,
                "batch_analyse_success": False,
                "error": str(e)
            }
            
            
            
    def _analyse_resumes(self, job_id, resume_ids, batch_no, total_batches):
        """
        Simplified single-user resume analysis
        resume_ids: List of ApplyJob IDs that need to be converted to file paths
        """
        logger.info(f"Starting resume analysis - Job ID: {job_id}, Batch: {batch_no}/{total_batches}, Resume IDs: {len(resume_ids)}")

        responseData = dict()

        job = models.CreateJob.objects.get(id=job_id)
        job_description = job.job_description
        logger.debug(f"Retrieved job details for {job.job_code}")

        # Convert ApplyJob IDs to actual file paths
        resume_files = []
        for resume_id in resume_ids:
            try:
                apply_job = models.ApplyJob.objects.get(id=resume_id)
                # Get the full file path from the resume field
                from django.conf import settings
                file_path = settings.PROJECT_ROOT / str(apply_job.resume)
                resume_files.append(str(file_path))
                logger.debug(f"Converted ID {resume_id} to path: {file_path}")
            except models.ApplyJob.DoesNotExist:
                logger.error(f"ApplyJob with ID {resume_id} not found")
                continue

        logger.info(f"Processing {len(resume_files)} resumes with LLM")
        results = process_resumes(job_description, job.job_code, resume_files=resume_files)
        logger.info(f"LLM processing completed for batch {batch_no}")

        responseData["job_code"] = job.job_code
        responseData["results"] = results
        responseData["batch_no"] = batch_no
        responseData["total_batches"] = total_batches
        responseData["batch_analyse_success"] = True

        logger.info(f"Batch {batch_no} analysis completed successfully")
        return responseData
        
