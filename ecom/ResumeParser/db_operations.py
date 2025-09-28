from .. import models
import json


def create_or_update_json_analysis_db(filename , job_code , result , analysis_success):
    apply_job = get_unique_apply_job_by_filename(filename , job_code)

    if not apply_job:
        print(f"❌ ERROR: Could not find ApplyJob record for candidate '{filename}' in job code '{job_code}'")
        print(f"   This means the resume analysis cannot be saved to database.")
        print(f"   Please check if the candidate name matches exactly with the application record.")
        return None

    resume_attribute , created = models.ResumeAttributes.objects.update_or_create(
        apply_resume = apply_job,

        defaults= {
            "analysis_json" : json.dumps(result),
            # "custom_attributes" : json.dumps({"CTC":20 , "LPA":15}),
            "analysis_success" : analysis_success,
        }
    )

    print("✅ Entry created") if created else print("✅ Entry updated")
    
    

    return resume_attribute

def create_or_update_custom_attributes_db(filename , job_code , data , created_by):
    apply_job = get_unique_apply_job_by_filename(filename , job_code)
    
    if not apply_job:
        print(f"❌ ERROR: Could not find ApplyJob record for candidate '{filename}' in job code '{job_code}'")
        print(f"   This means the resume analysis cannot be saved to database.")
        print(f"   Please check if the candidate name matches exactly with the application record.")
        return None
    
    resume_attribute = models.ResumeAttributes.objects.get(apply_resume = apply_job)
    
    existing_custom_attributes = json.loads(resume_attribute.custom_attributes)
    
    
    print("existing_custom_attributes: ",existing_custom_attributes)
    
    
    for key , value in data.items():
        existing_custom_attributes[key] = value
    
    

    resume_attribute, created = models.ResumeAttributes.objects.update_or_create(
        apply_resume=apply_job,

        defaults={
            "custom_attributes" : json.dumps(existing_custom_attributes)
        }
    )
        
        

    log_created = create_resume_log_db(apply_job, resume_attribute, existing_custom_attributes, created_by)

    if not log_created:
        resume_attribute.delete()
        return False


    print("Custom Attribute Added")
    
    return True

def create_resume_log_db(apply_job , resume_attribute , custom_attributes , created_by):
    try:
        resume_log = models.ResumeLogs.objects.create(
            apply_resume = apply_job,
            resume_attribute = resume_attribute,
            custom_attributes = custom_attributes,
            created_by = created_by
        )
        
        if resume_log:
            return True
    
    except Exception as e:
        print(f"Unable to create ResumeLog object: {e}")
    
    return False
    
def update_analysis_in_db(filename, job_code=None):

    try:
        if job_code:
            # Try with job_code for better uniqueness
            apply_jobs = models.ApplyJob.objects.filter(resume_filename=filename, job_code=job_code)
        else:
            apply_jobs = models.ApplyJob.objects.filter(resume_filename=filename)

        if apply_jobs.count() == 1:
            apply_job = apply_jobs.first()
            apply_job.analysed = models.AnalysedChoices.ANALYZED
            apply_job.save()
            print(f"Updated analysis status for {filename} in {job_code or 'any job code'}")
        elif apply_jobs.count() > 1:
            print(f"Warning: Multiple ApplyJob records found for {filename}. Updating all {apply_jobs.count()} records.")
            for job in apply_jobs:
                job.analysed = models.AnalysedChoices.ANALYZED
                job.save()
        else:
            print(f"Warning: No ApplyJob record found for {filename}")

    except Exception as e:
        print(f"Error updating analysis status for {filename}: {e}")
    


def fetch_analysis_from_db(filename , job_code):
    apply_job = get_unique_apply_job_by_filename(filename , job_code)
    resume_attribute = models.ResumeAttributes.objects.get(apply_resume = apply_job)
    return json.loads(resume_attribute.analysis_json)

def get_unique_apply_job_by_candidate_name(candidate_name, job_code):
 
    print(f"🔍 Searching for ApplyJob: candidate='{candidate_name}', job_code='{job_code}'")

    # Strategy 1: Exact name and job_code match
    try:
        apply_job = models.ApplyJob.objects.get(
            name=candidate_name,
            job_code=job_code
        )
        print(f"✅ Strategy 1 SUCCESS: Exact match found for '{candidate_name}' with job_code '{job_code}'")
        return apply_job
    except models.ApplyJob.DoesNotExist:
        print(f"⚠️  Strategy 1 FAILED: No exact match for '{candidate_name}' with job_code '{job_code}'")
    except models.ApplyJob.MultipleObjectsReturned:
        print(f"⚠️  Strategy 1 PARTIAL: Multiple exact matches for '{candidate_name}' in '{job_code}', returning first")
        return models.ApplyJob.objects.filter(name=candidate_name, job_code=job_code).first()

def get_unique_apply_job_by_filename(filename, job_code):
 
    print(f"🔍 Searching for ApplyJob: candidate='{filename}', job_code='{job_code}'")

    # Strategy 1: Exact name and job_code match
    try:
        apply_job = models.ApplyJob.objects.get(
            resume_filename=filename,
            job_code=job_code
        )
        print(f"✅ Strategy 1 SUCCESS: Exact match found for '{filename}' with job_code '{job_code}'")
        return apply_job
    except models.ApplyJob.DoesNotExist:
        print(f"⚠️  Strategy 1 FAILED: No exact match for '{filename}' with job_code '{job_code}'")
    except models.ApplyJob.MultipleObjectsReturned:
        print(f"⚠️  Strategy 1 PARTIAL: Multiple exact matches for '{filename}' in '{job_code}', returning first")
        return models.ApplyJob.objects.filter(name=filename, job_code=job_code).first()

def get_results_by_job_code(job_code):
        
    results = []
    
    resume_attributes = models.ResumeAttributes.objects.filter(analysis_success = True , apply_resume__job_code=job_code)
    
    for resume_attribute in resume_attributes:
        result = json.loads(resume_attribute.analysis_json) 
        results.append(result)
    
    return results
    

def get_unanalysed_data(job_code):
    
    unanalysed_data_queryset = models.ApplyJob.objects.filter(analysed = models.AnalysedChoices.UNANALYZED , job_code=job_code)
    # print("unanalysed_data: " , unanalysed_data)
    
    unanalysed_data = []
    
    for apply_job in unanalysed_data_queryset:
            unanalysed_data.append({
                'id': apply_job.id,
                'name': apply_job.name,
                'email': apply_job.email,
                'contact_number': apply_job.contact_number,
                'resume_filename': apply_job.resume_filename,
                'job_code': apply_job.job_code,
                'analysed': apply_job.analysed
            })
    
    return (unanalysed_data if unanalysed_data else None)
    
    
    