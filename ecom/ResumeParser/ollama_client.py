import json
import logging
import time
from typing import Dict, Any
import datetime
import re

try:
    import ollama
except ImportError:
    ollama = None

# from config import OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_OPTIONS, CHUNK_SIZE
from django.conf import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaClient:

    def __init__(self, model: str = settings.OLLAMA_MODEL):
        if ollama is None:
            raise ImportError("ollama library is required. Install with: pip install ollama")

        self.model = model
        self.timeout = settings.OLLAMA_TIMEOUT
        self.options = settings.OLLAMA_OPTIONS.copy()

        # Test connection on initialization
        self._test_connection()

    def _get_client(self):
        return ollama

    def _test_connection(self) -> bool:
        try:
            client = self._get_client()
            models = client.list()

            if 'models' in models:
                model_names = [model['name'] for model in models['models']]

                if self.model not in model_names:
                    logger.warning(f"Model {self.model} not found. Available models: {model_names}")
                    logger.warning(f"Attempting to pull model {self.model}...")
                    try:
                        client.pull(self.model)
                        logger.info(f"Successfully pulled model {self.model}")
                    except Exception as e:
                        logger.error(f"Failed to pull model {self.model}: {str(e)}")
                        return False

                logger.info(f"Successfully connected to Ollama. Model {self.model} is available.")
                return True
            else:
                logger.error("Failed to get model list from Ollama")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {str(e)}")
            logger.error("Make sure Ollama is running: 'ollama serve'")
            return False
    
    def generate_response(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        
        try:
            client = self._get_client()

            # Prepare messages for chat format
            messages = []
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })

            messages.append({
                'role': 'user',
                'content': prompt
            })

            start_time = time.time()

            # Use chat API for better structured responses
            response = client.chat(
                model=self.model,
                messages=messages,
                options=self.options,
                stream=False
            )
            
            processing_time = time.time() - start_time
            
            # Extract the raw response content
            response_content = response.get('message', {}).get('content', '')

            # Log the raw response for debugging
            with open('test.txt' , 'a') as fp:
                fp.write("\n-----------------RAW LLM RESPONSE------------------\n")
                fp.write(response_content)
                fp.write("\n---------------------------------------------------\n")

            return {
                'success': True,
                'response': response_content,
                'processing_time': processing_time,
                'model': self.model,
                'prompt_tokens': len(prompt.split()),
                'error': None
            }

        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower():
                error_msg = "Could not connect to Ollama service. Is it running?"
            elif "timeout" in error_msg.lower():
                error_msg = f"Request timed out after {self.timeout} seconds"

            return {
                'success': False,
                'response': '',
                'error': error_msg,
                'processing_time': 0
            }
    
    def analyze_resume(self, resume_text: str, job_description: str) -> Dict[str, Any]:

        # Log the raw response for debugging
        with open('test.txt' , 'a') as fp:
            fp.write("\n-----------------Resume Text------------------\n")
            fp.write(resume_text)
            fp.write("\n---------------------------------------------------\n")

        
        total_processing_time = 0

        # Filter the resume to get only professional experience
        filter_prompt = f"""
        YOU ARE A WORK EXPERIENCE EXTRACTION ROBOT. FOLLOW THESE INSTRUCTIONS EXACTLY:

        TASK: Extract ONLY professional full-time work experience from the resume text below.

        WHAT TO EXTRACT:
        - Job Title
        - Company Name
        - Start Date (month/year)
        - End Date (month/year or "Present")
        - Brief job description (1-2 lines max)

        WHAT TO EXCLUDE:
        - Internships (unless explicitly mentioned as full-time)
        - Student projects
        - Part-time roles
        - Education details
        - Skills lists
        - Certifications
        - Personal projects
        - Volunteer work

        OUTPUT FORMAT:
        For each job, write exactly in this format:
        Job Title - Company Name (Start Date - End Date)
        Brief description of role

        EXAMPLE OUTPUT:
        Senior Software Developer - ABC Corp (Jan 2020 - Present)
        Developed Java applications and managed database systems

        Software Engineer - XYZ Ltd (Jun 2018 - Dec 2019)
        Built web applications using Spring Boot and React

        CRITICAL RULES:
        1. ONLY write "No professional experience found" if there are absolutely NO full-time jobs in the resume
        2. If you find ANY professional work experience, DO NOT include the "No professional experience found" text
        3. Extract ALL professional jobs you find - do not skip any
        4. Do not add explanatory text or commentary

        Resume Text:
        {resume_text}
        """
        
        filter_result = self.generate_response(filter_prompt, system_prompt=None)
        total_processing_time += filter_result.get('processing_time', 0)
        
        if not filter_result.get('success'):
            return {'success': False, 'error': f"Failed at filtering step: {filter_result.get('error', 'Unknown error')}"}

        cleaned_experience = filter_result.get('response', '').strip()

        # Clean up the response - remove "No professional experience found" if there's actual experience
        filtered_lines = cleaned_experience.split('\n')
        actual_experience_lines = []
        has_actual_experience = False

        for line in filtered_lines:
            line = line.strip()
            if not line:
                continue
            # Check if this line looks like actual job experience (contains company name and dates)
            if ' - ' in line and ('(' in line and ')' in line) and not line.startswith("No professional"):
                has_actual_experience = True
                actual_experience_lines.append(line)
            elif line != "No professional experience found" and not line.startswith("No professional"):
                # Include description lines that follow job titles
                actual_experience_lines.append(line)

        # If we found actual experience, use only the experience lines
        if has_actual_experience:
            cleaned_experience = '\n'.join(actual_experience_lines)

        # Log the cleaned experience for debugging
        with open('test.txt' , 'a') as fp:
            fp.write("\n-----------------Cleaned Experience------------------\n")
            fp.write(cleaned_experience)
            fp.write("\n---------------------------------------------------\n")

        job_history_data = {}
        job_history_result = {}

        # Extracting job history from the cleaned text
        if "No professional experience found" in cleaned_experience or not cleaned_experience.strip() or not has_actual_experience:
            job_history_data = {
                "fresher": True,
                "first_job_start_year": 0,
                "last_job_end_year": 0,
                "total_jobs_count": 0
            }
        else:
            current_year = datetime.datetime.now().year
            extraction_prompt = f"""
            YOU ARE A DATE EXTRACTION ROBOT. FOLLOW THESE INSTRUCTIONS EXACTLY.

            TASK: Extract job dates from the experience text below using this MANDATORY 4-STEP PROCESS:

            STEP 1: LIST ALL JOBS WITH THEIR EXACT DATES
            Read the experience text and write down each job with its exact date range.
            Format: Job Title - Company (Start Date - End Date)

            STEP 2: EXTRACT ALL YEARS FROM THE TEXT
            List every year number you see in the text. Include "Present" as {current_year}.
            Format: Years found: [list all years]

            STEP 3: FIND START AND END YEARS
            - Start years: [list all start years from Step 2]
            - End years: [list all end years from Step 2, convert Present to {current_year}]
            - SMALLEST start year = first_job_start_year
            - LARGEST end year = last_job_end_year

            STEP 4: COUNT JOBS
            Count the total number of jobs listed in Step 1.

            EXAMPLE WALKTHROUGH:
            If experience text contains:
            "Engineering Manager, Amazon (Jan 2022 - Present)"
            "Senior Software Engineer, Microsoft (Aug 2018 - Dec 2021)"
            "Software Engineer, Google (Jul 2016 - Jul 2018)"

            STEP 1: LIST JOBS
            - Engineering Manager - Amazon (Jan 2022 - Present)
            - Senior Software Engineer - Microsoft (Aug 2018 - Dec 2021)
            - Software Engineer - Google (Jul 2016 - Jul 2018)

            STEP 2: EXTRACT YEARS
            Years found: [2022, Present({current_year}), 2018, 2021, 2016, 2018]

            STEP 3: FIND START/END
            - Start years: [2022, 2018, 2016]
            - End years: [Present({current_year}), 2021, 2018] = [{current_year}, 2021, 2018]
            - SMALLEST start year = 2016
            - LARGEST end year = {current_year}

            STEP 4: COUNT JOBS
            Total jobs = 3

            RESULT: {{"first_job_start_year": 2016, "last_job_end_year": {current_year}, "total_jobs_count": 3}}

            CRITICAL RULES:
            - NEVER skip Step 1-4
            - ONLY use years that appear in the experience text
            - Present/Current = {current_year}
            - If no jobs found: {{"first_job_start_year": 0, "last_job_end_year": 0, "total_jobs_count": 0}}

            NOW APPLY THE 4-STEP PROCESS TO THE EXPERIENCE TEXT BELOW:

            Experience Text:
            {cleaned_experience}

            MANDATORY: Complete Steps 1-4 above, then respond with ONLY the JSON result.

            FORBIDDEN RESPONSES:
            - Do NOT explain your process
            - Do NOT show your work
            - Do NOT include any text except the JSON
            - Do NOT hallucinate years not in the text

            Experience Text:
            {cleaned_experience}

            STEP-BY-STEP PROCESS:
            1. Carefully read the experience text and list all jobs with their EXACT start and end dates
            2. Extract the ACTUAL years mentioned in the text (do not invent years)
            3. Find the job with the EARLIEST start date → this gives first_job_start_year
            4. Find the job with the LATEST end date (or "Present"/"Current" = {current_year}) → this gives last_job_end_year
            5. Count total number of jobs → this gives total_jobs_count
            6. Double-check that all years come from the actual text, not your assumptions

            CRITICAL: Respond ONLY with a valid JSON object. Do NOT include any explanations, text, or commentary outside the JSON.

            Required JSON format:
            {{
                "first_job_start_year": <year or 0 if fresher>,
                "last_job_end_year": <year or 0 if fresher>,
                "total_jobs_count": <number>
            }}

            WRONG RESPONSE EXAMPLES (do NOT do this):
            1. Text format: "Based on the provided experience text, I extracted..."
            2. Hallucinated dates: If text shows "Aug 2019 - Feb 2020" and "Mar 2020 - Present",
               do NOT return {{"first_job_start_year": 2014, "last_job_end_year": 2020, "total_jobs_count": 2}}

            CORRECT RESPONSE EXAMPLE:
            For "Aug 2019 - Feb 2020" and "Mar 2020 - Present":
            {{"first_job_start_year": 2019, "last_job_end_year": {current_year}, "total_jobs_count": 2}}
            """

            # Use a strict system prompt to enforce JSON format and accuracy
            json_system_prompt = f"""You are a DATE EXTRACTION ROBOT. You MUST:
                1. Follow the 4-step process exactly
                2. Only use years that appear in the experience text
                3. Convert Present/Current to {current_year}
                4. Return ONLY valid JSON - no explanations, no text, no commentary
                5. Double-check that first_job_start_year is the SMALLEST year in the text
                6. Double-check that last_job_end_year is the LARGEST year (or {current_year} for Present)"""

            job_history_result = self.generate_response(extraction_prompt, system_prompt=json_system_prompt)
            total_processing_time += job_history_result.get('processing_time', 0)
            
            if job_history_result.get('success'):
                try:
                    extracted_data = self._parse_json_from_string(job_history_result['response'])

                    # Handle fresher case - if all values are 0 or None the it's a fresher
                    first_year = extracted_data.get("first_job_start_year")
                    last_year = extracted_data.get("last_job_end_year")
                    job_count = extracted_data.get("total_jobs_count", 0)

                    # Convert None to 0 for consistency
                    if first_year is None:
                        first_year = 0
                    if last_year is None:
                        last_year = 0

                    # Validate the extracted data against the experience text
                    validated_data = self._validate_job_history_data(
                        first_year, last_year, job_count, cleaned_experience, current_year
                    )

                    # Determine if candidate is fresher
                    is_fresher = (validated_data['first_year'] == 0 and validated_data['last_year'] == 0 and validated_data['job_count'] == 0)

                    job_history_data = {
                        "fresher": is_fresher,
                        "first_job_start_year": validated_data['first_year'],
                        "last_job_end_year": validated_data['last_year'],
                        "total_jobs_count": validated_data['job_count']
                    }
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    logger.error(f"Failed to parse job history JSON: {e}")
                    logger.error(f"Raw LLM response was: {job_history_result['response'][:500]}...")
                    logger.error("This indicates the LLM did not return valid JSON format. Defaulting to fresher.")
                    job_history_data = {"fresher": True, "first_job_start_year": 0, "last_job_end_year": 0, "total_jobs_count": 0}
            else:
                 return {'success': False, 'error': f"Failed at job history extraction step: {job_history_result.get('error', 'Unknown error')}"}

        # --- STEP 3: Perform the main, detailed analysis ---
        main_system_prompt = f"""
        You are a resume analysis and scoring system. Your job is to extract factual, accurate data and scores from the resume and job description below.

        IMPORTANT SKILL MATCHING RULES:
        - Consider related skills and synonyms (e.g., GitHub implies Git knowledge, React implies JavaScript)
        - Django/Flask implies Python, Spring implies Java, etc.
        - Cloud platforms (AWS/Azure/GCP) are interchangeable for basic cloud skills
        - Version control tools (GitHub/GitLab/Bitbucket) all imply Git knowledge
        - Testing frameworks (pytest/junit/jest) imply testing skills
        - Be intelligent about skill relationships and don't penalize for using related technologies

        CRITICAL RULES - FOLLOW EXACTLY:
        1. You MUST return EXACTLY the JSON structure shown below - NO MODIFICATIONS ALLOWED
        2. Do NOT create your own JSON structure or add/remove/rename any fields
        3. Use ONLY the field names specified in the template below
        4. Do NOT add extra fields, nested objects, or change the structure
        5. Respond ONLY with valid JSON structure mentioned below. Do NOT include any explanation, commentary, or text outside the JSON.
        6. Extract skills ONLY if they are explicitly present in the resume text.
        7. List missing skills ONLY if they are required by the job and not found in the resume.
        8. All scores must be numerical, between 0 and 100, and based on actual evidence in the resume.
        9. For lists, include only relevant items found in the resume or required by the job.
        10. For recommendation, use EXACTLY "HIRE", "CONSIDER", or "REJECT" - no other values allowed.
        11. For salary_expectation_alignment, use EXACTLY "LOW", "MEDIUM", or "HIGH" - no other values allowed.
        12. If any field is missing, use a sensible default but keep the field name exactly as shown.
        13. For education scoring: Score based on education level only (higher education = higher score). Use this scale:
            - PhD/Doctorate: 90-100 points
            - Master's/Postgraduate: 75-85 points
            - Bachelor's/Undergraduate: 60-70 points
            - Diploma/Associate: 40-55 points
            - High School/Secondary: 20-35 points
            - No formal education mentioned: 10-20 points
        14. MANDATORY REJECTION RULE: If the candidate’s matching skills are LESS than 50% of the required job description skills, 
            the "recommendation" field MUST be "REJECT" regardless of other scores.

        MANDATORY JSON STRUCTURE - COPY THIS EXACTLY:
        You MUST return this EXACT structure with these EXACT field names.
        Do NOT modify, add, or remove any fields from this template:
        {{
            "candidate_name": "Extracted name from resume",
            "overall_score": <number 0-100>,
            "skills_match": <number 0-100>,
            "experience_relevance": <number 0-100>,
            "education": <number 0-100>,
            "keywords_match": <number 0-100>,
            "overall_fit": <number 0-100>,
            "matching_skills": ["Skills from resume that match job requirements"],
            "missing_skills": ["Skills from job requirements not in resume"],
            "matching_experience": ["Relevant experience from resume"],
            "experience_gaps": ["Required experience not found in resume"],
            "education_highlights": ["Education details from resume"],
            "strengths": ["Candidate's key strengths"],
            "weaknesses": ["Candidate's key weaknesses or gaps"],
            "growth_potential": <number 0-100>,
            "cultural_fit_indicators": ["Indicators of cultural fit"],
            "salary_expectation_alignment": "LOW|MEDIUM|HIGH",
            "recommendation": "HIRE|CONSIDER|REJECT",
            "recommendation_reason": "Brief reason for the recommendation",
            "summary": "A concise summary of the candidate's profile",
            "interview_focus_areas": ["Specific topics to focus on during an interview"],
            "matching_skills_count": <number>,
            "missing_skills_count": <number>,
            "relevant_experience_years": <number>,
            "education_level_code": <number>  e.g., 1: Diploma, 2: Bachelor, 3: Master, 4: PhD, 0: Other
        }}
        """


        main_user_prompt = f"""
        TASK: Analyze the candidate's resume against the job requirements.

        JOB REQUIREMENTS:
        {job_description}

        CANDIDATE'S RESUME TO ANALYZE:
        {resume_text}

        CRITICAL INSTRUCTIONS:
        1. Return EXACTLY the JSON structure defined in the system prompt
        2. Use ONLY the field names specified in the template - do NOT modify them
        3. Do NOT create your own JSON structure or add extra fields
        4. Do NOT include any explanation, comments, or text outside the JSON
        5. Do NOT use // comments inside the JSON as they break parsing
        6. Return only the exact JSON template with filled values

        RESPOND WITH THE EXACT JSON STRUCTURE ONLY:
        """

        main_analysis_result = self.generate_response(main_user_prompt, main_system_prompt)
        total_processing_time += main_analysis_result.get('processing_time', 0)

        if not main_analysis_result.get('success'):
            return {
                'success': False,
                'error': f"Failed at main analysis step: {main_analysis_result.get('error', 'Unknown error')}",
            }

        # --- STEP 4: Combine and validate the results ---
        try:
            final_analysis = self._parse_json_from_string(main_analysis_result['response'])

            # Check if LLM followed the exact structure
            if not self._validate_exact_structure(final_analysis):
                logger.warning("LLM did not follow exact JSON structure. Attempting retry with stricter prompt...")

                # Retry with even more explicit structure enforcement
                strict_retry_prompt = f"""
                CRITICAL ERROR: You did not follow the exact JSON structure.

                You MUST return EXACTLY this structure with NO modifications:

                {{
                    "candidate_name": "string",
                    "overall_score": number,
                    "skills_match": number,
                    "experience_relevance": number,
                    "education": number,
                    "keywords_match": number,
                    "overall_fit": number,
                    "matching_skills": ["array of strings"],
                    "missing_skills": ["array of strings"],
                    "matching_experience": ["array of strings"],
                    "experience_gaps": ["array of strings"],
                    "education_highlights": ["array of strings"],
                    "strengths": ["array of strings"],
                    "weaknesses": ["array of strings"],
                    "growth_potential": number,
                    "cultural_fit_indicators": ["array of strings"],
                    "salary_expectation_alignment": "LOW or MEDIUM or HIGH",
                    "recommendation": "HIRE or CONSIDER or REJECT",
                    "recommendation_reason": "string",
                    "summary": "string",
                    "interview_focus_areas": ["array of strings"],
                    "matching_skills_count": number,
                    "missing_skills_count": number,
                    "relevant_experience_years": number,
                    "education_level_code": number
                }}

                CANDIDATE'S RESUME:
                {resume_text}

                JOB REQUIREMENTS:
                {job_description}

                RESPOND WITH EXACTLY THE ABOVE JSON STRUCTURE - NO CHANGES ALLOWED:
                """

                retry_result = self.generate_response(strict_retry_prompt, "You MUST return the exact JSON structure specified. Do NOT modify field names or add extra fields.")
                if retry_result.get('success'):
                    try:
                        final_analysis = self._parse_json_from_string(retry_result['response'])
                        if not self._validate_exact_structure(final_analysis):
                            logger.error("LLM still not following exact structure after retry. Using fallback.")
                            final_analysis = self._create_fallback_analysis(retry_result['response'])
                    except Exception as e:
                        logger.error(f"Retry parsing failed: {e}. Using fallback.")
                        final_analysis = self._create_fallback_analysis(retry_result['response'])

            final_analysis.update(job_history_data)
            validated_analysis = self._validate_analysis(final_analysis)
            
            return {
                'success': True,
                'analysis': validated_analysis,
                'processing_time': total_processing_time,
                'model_used': self.model,
                'error': None
            }
        except Exception as e:
            logger.error(f"Error combining or parsing LLM responses: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to parse or combine final LLM response: {str(e)}',
            }

    def _validate_job_history_data(self, first_year: int, last_year: int, job_count: int,
                                   experience_text: str, current_year: int) -> Dict[str, int]:

        # Extract all years from the experience text
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        years_found = [int(year) for year in re.findall(year_pattern, experience_text)]

        # Check for "Present" or "Current" keywords
        has_present = any(keyword in experience_text.lower() for keyword in ['present', 'current'])

        if not years_found and not has_present:
            # No years found, likely a fresher
            return {'first_year': 0, 'last_year': 0, 'job_count': 0}

        if years_found:
            actual_first_year = min(years_found)
            actual_last_year = current_year if has_present else max(years_found)

            # Aggressive validation - always use the actual years found in text
            if first_year != actual_first_year:
                logger.warning(f"LLM error: first_job_start_year was {first_year}, correcting to actual minimum year: {actual_first_year}")
                first_year = actual_first_year

            if last_year != actual_last_year:
                logger.warning(f"LLM error: last_job_end_year was {last_year}, correcting to actual maximum year: {actual_last_year}")
                last_year = actual_last_year

            # Use the corrected values
            return {
                'first_year': first_year if first_year in years_found else actual_first_year,
                'last_year': actual_last_year if has_present or last_year not in years_found else last_year,
                'job_count': job_count
            }

        return {'first_year': first_year, 'last_year': last_year, 'job_count': job_count}

    def _parse_json_from_string(self, text: str) -> Dict[str, Any]:
        
        # Find the first '{' and the last '}' to extract the JSON object
        json_start = text.find('{')
        json_end = text.rfind('}') + 1

        if json_start != -1 and json_end != -1:
            json_str = text[json_start:json_end]

            # Remove JSON comments (// comments) that break parsing
            json_str = re.sub(r'//.*?(?=\n|$)', '', json_str, flags=re.MULTILINE)

            # Remove any trailing commas before closing braces/brackets
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed even after cleaning: {str(e)}")
                logger.error(f"Cleaned JSON string: {json_str[:500]}...")
                raise e
        else:
            raise json.JSONDecodeError("No JSON object found in the string.", text, 0)

    def _create_fallback_analysis(self, response: str) -> Dict[str, Any]:
        
        score_match = None
        score_patterns = [r'score[:\s]*(\d+)', r'rating[:\s]*(\d+)', r'(\d+)[/\s]*100', r'(\d+)%']

        for pattern in score_patterns:
            match = re.search(pattern, response.lower())
            if match:
                try:
                    score_match = int(match.group(1))
                    break
                except:
                    continue

        fallback_score = min(max(score_match or 50, 0), 100)

        return {
            "candidate_name": "Name not found",
            "overall_score": fallback_score, "skills_match": fallback_score,
            "experience_relevance": fallback_score, "education": fallback_score,
            "keywords_match": fallback_score, "overall_fit": fallback_score,
            "matching_skills": ["Unable to parse"], "missing_skills": ["Unable to parse"],
            "matching_experience": ["Unable to parse"], "experience_gaps": ["Unable to parse"],
            "education_highlights": ["Unable to parse"], "strengths": ["Analysis parsing failed"],
            "weaknesses": ["Manual review required"], "growth_potential": fallback_score,
            "cultural_fit_indicators": ["Unable to assess"], "salary_expectation_alignment": "MEDIUM",
            "recommendation": "CONSIDER", "recommendation_reason": "Analysis parsing failed - manual review required",
            "summary": "Analysis could not be parsed properly",
            "interview_focus_areas": ["Technical assessment", "Experience verification"]
        }
    
    def _validate_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize analysis results"""
        defaults = {
            "candidate_name": "Name not found", "overall_score": 50, "skills_match": 50,
            "experience_relevance": 50, "education": 50, "keywords_match": 50,
            "overall_fit": 50, "matching_skills": [], "missing_skills": [],
            "matching_experience": [], "experience_gaps": [], "education_highlights": [],
            "strengths": [], "weaknesses": [], "growth_potential": 50,
            "cultural_fit_indicators": [], "salary_expectation_alignment": "MEDIUM",
            "recommendation": "CONSIDER", "recommendation_reason": "Standard analysis completed",
            "summary": "Analysis completed", "interview_focus_areas": [],
            "fresher": True, "first_job_start_year": 0, "last_job_end_year": 0, "total_jobs_count": 0
        }

        for key, default_value in defaults.items():
            analysis.setdefault(key, default_value)

        score_fields = ["overall_score", "skills_match", "experience_relevance",
                        "education", "keywords_match", "overall_fit", "growth_potential"]
        for field in score_fields:
            try:
                score = float(analysis[field])
                analysis[field] = max(0, min(100, score))
            except (ValueError, TypeError):
                analysis[field] = 50

        if analysis.get("recommendation") not in ["HIRE", "CONSIDER", "REJECT"]:
            analysis["recommendation"] = "CONSIDER"
        if analysis.get("salary_expectation_alignment") not in ["LOW", "MEDIUM", "HIGH"]:
            analysis["salary_expectation_alignment"] = "MEDIUM"

        list_fields = ["matching_skills", "missing_skills", "matching_experience",
                       "experience_gaps", "education_highlights", "strengths",
                       "weaknesses", "cultural_fit_indicators", "interview_focus_areas"]
        for field in list_fields:
            if not isinstance(analysis.get(field), list):
                analysis[field] = [str(analysis[field])] if analysis.get(field) else []
        
        return analysis

    def _validate_exact_structure(self, analysis: Dict[str, Any]) -> bool:
        
        # Define the exact required fields from LLM
        required_llm_fields = [
            'candidate_name', 'overall_score', 'skills_match', 'experience_relevance',
            'education', 'keywords_match', 'overall_fit', 'matching_skills',
            'missing_skills', 'matching_experience', 'experience_gaps',
            'education_highlights', 'strengths', 'weaknesses', 'growth_potential',
            'cultural_fit_indicators', 'salary_expectation_alignment',
            'recommendation', 'recommendation_reason', 'summary',
            'interview_focus_areas', 'matching_skills_count', 'missing_skills_count',
            'relevant_experience_years', 'education_level_code'
        ]

        # Define fields that our code adds (these are allowed extra fields)
        allowed_extra_fields = [
            'fresher', 'first_job_start_year', 'last_job_end_year', 'total_jobs_count'
        ]

        # Check if all required fields are present
        missing_fields = [field for field in required_llm_fields if field not in analysis]

        if missing_fields:
            logger.warning(f"LLM response missing required fields: {missing_fields}")
            return False

        # Check for extra fields that shouldn't be there (excluding allowed ones)
        all_allowed_fields = required_llm_fields + allowed_extra_fields
        extra_fields = [field for field in analysis.keys() if field not in all_allowed_fields]

        if extra_fields:
            logger.warning(f"LLM response has unexpected extra fields: {extra_fields}")
            return False

        return True
