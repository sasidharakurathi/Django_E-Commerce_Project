import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from .ollama_client import OllamaClient
# from config import (
#     SCORING_WEIGHTS, MAX_SCORE, MIN_SCORE, PASSING_SCORE,
#     CRITICAL_SKILLS_THRESHOLD, MINIMUM_SKILLS_PERCENTAGE, SKILLS_VETO_THRESHOLD,
#     EXPERIENCE_COMPENSATION_LIMIT
# )

from django.conf import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScoringEngine:
    

    def __init__(self):
        self.ollama_client = OllamaClient()
        self.weights = settings.SCORING_WEIGHTS
        self.max_score = settings.MAX_SCORE
        self.min_score = settings.MIN_SCORE
        self.passing_score = settings.PASSING_SCORE
    
    def score_resume(self, resume_data: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        
        
        if not resume_data.get('success', False):
            return {
                'success': False,
                'error': resume_data.get('error', 'Resume parsing failed'),
                'filename': resume_data.get('filename', 'unknown'),
                'scores': {},
                'recommendation': 'REJECT'
            }
        
        try:
            # Get LLM analysis
            llm_result = self.ollama_client.analyze_resume(
                resume_data['text'], 
                job_description
            )
            
            if not llm_result['success']:
                logger.error(f"LLM analysis failed: {llm_result['error']}")
                return {
                    'success': False,
                    'error': f"LLM analysis failed: {llm_result['error']}",
                    'filename': resume_data['filename'],
                    'scores': {},
                    'recommendation': 'REJECT'
                }
            
            # Improve skill matching accuracy
            improved_analysis = self._improve_skill_matching(
                llm_result['analysis'],
                resume_data['text'],
                job_description
            )

            # Validate skills requirements
            improved_analysis = self._validate_skills_requirements(improved_analysis)

            # Combine LLM analysis with rule-based scoring
            combined_scores = self._combine_scores(
                improved_analysis,
                resume_data,
                job_description
            )
            
            # Apply skills-first scoring logic
            final_score, recommendation = self._calculate_skills_first_score(combined_scores)

            # Get the best candidate name (LLM extracted or parser extracted)
            llm_name = improved_analysis.get('candidate_name', '')
            parser_name = resume_data.get('metadata', {}).get('candidate_name', 'Name not found')

            # Use LLM name if it's valid, otherwise use parser name
            best_name = llm_name if (llm_name and llm_name != "Name not found" and len(llm_name.split()) >= 2) else parser_name

            # Update metadata with best name
            updated_metadata = resume_data.get('metadata', {}).copy()
            updated_metadata['candidate_name'] = best_name

            # Prepare detailed results
            result = {
                'success': True,
                'filename': resume_data['filename'],
                'final_score': round(final_score, 2),
                'scores': combined_scores,
                'recommendation': recommendation,
                'analysis': improved_analysis,  # Use improved analysis
                'strengths': improved_analysis.get('strengths', []),
                'weaknesses': improved_analysis.get('weaknesses', []),
                'summary': improved_analysis.get('summary', ''),
                'processing_time': llm_result.get('processing_time', 0),
                'metadata': updated_metadata,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error scoring resume {resume_data.get('filename', 'unknown')}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'filename': resume_data.get('filename', 'unknown'),
                'scores': {},
                'recommendation': 'REJECT'
            }
    
    def _combine_scores(self, llm_analysis: Dict[str, Any], resume_data: Dict[str, Any], 
                       job_description: str) -> Dict[str, float]:
        
        
        # Start with LLM scores
        combined_scores = {
            'skills_match': llm_analysis.get('skills_match', 50),
            'experience_relevance': llm_analysis.get('experience_relevance', 50),
            'education': llm_analysis.get('education', 50),
            'keywords_match': llm_analysis.get('keywords_match', 50),
            'overall_fit': llm_analysis.get('overall_fit', 50)
        }
        
        # Apply rule-based adjustments
        adjustments = self._calculate_rule_based_adjustments(resume_data, job_description)
        
        # Combine scores with adjustments
        for criterion, base_score in combined_scores.items():
            adjustment = adjustments.get(criterion, 0)
            adjusted_score = base_score + adjustment
            combined_scores[criterion] = max(self.min_score, min(self.max_score, adjusted_score))
        
        return combined_scores
    
    def _calculate_rule_based_adjustments(self, resume_data: Dict[str, Any], 
                                        job_description: str) -> Dict[str, float]:
        
        
        adjustments = {
            'skills_match': 0,
            'experience_relevance': 0,
            'education': 0,
            'keywords_match': 0,
            'overall_fit': 0
        }
        
        resume_text = resume_data.get('text', '').lower()
        job_desc_lower = job_description.lower()
        metadata = resume_data.get('metadata', {})
        
        # Keywords matching adjustment
        job_keywords = self._extract_keywords(job_desc_lower)
        keyword_matches = sum(1 for keyword in job_keywords if keyword in resume_text)
        if job_keywords:
            keyword_match_ratio = keyword_matches / len(job_keywords)
            adjustments['keywords_match'] += (keyword_match_ratio - 0.5) * 20  # ±10 points
        
        # Contact information bonus
        if metadata.get('has_email') and metadata.get('has_phone'):
            adjustments['overall_fit'] += 5
        
        # Professional profiles bonus
        if metadata.get('has_linkedin'):
            adjustments['overall_fit'] += 3
        if metadata.get('has_github'):
            adjustments['skills_match'] += 5
        
        # Resume length considerations
        word_count = metadata.get('word_count', 0)
        if word_count < 100:  # Too short
            adjustments['overall_fit'] -= 10
        elif word_count > 2000:  # Too long
            adjustments['overall_fit'] -= 5
        
        # Experience indicators
        experience_indicators = ['years', 'experience', 'worked', 'developed', 'managed', 'led']
        experience_count = sum(1 for indicator in experience_indicators if indicator in resume_text)
        if experience_count >= 3:
            adjustments['experience_relevance'] += 5

        # Education level adjustments (higher education = higher score)
        education_adjustments = 0
        if any(keyword in resume_text for keyword in ['phd', 'ph.d', 'doctorate', 'doctoral']):
            education_adjustments = 40  # PhD gets highest boost
        elif any(keyword in resume_text for keyword in ['master', 'msc', 'm.sc', 'mba', 'm.b.a', 'mtech', 'm.tech', 'postgraduate']):
            education_adjustments = 25  # Master's gets good boost
        elif any(keyword in resume_text for keyword in ['bachelor', 'bsc', 'b.sc', 'btech', 'b.tech', 'be', 'b.e', 'undergraduate']):
            education_adjustments = 15  # Bachelor's gets moderate boost
        elif any(keyword in resume_text for keyword in ['diploma', 'associate', 'polytechnic']):
            education_adjustments = 5   # Diploma gets small boost
        elif any(keyword in resume_text for keyword in ['high school', 'secondary', '12th', 'intermediate']):
            education_adjustments = -10  # High school gets penalty

        adjustments['education'] += education_adjustments

        return adjustments
    
    def _extract_keywords(self, text: str) -> List[str]:
        
        
        # Common technical and professional keywords
        common_keywords = [
            'python', 'java', 'javascript', 'react', 'node', 'sql', 'database',
            'aws', 'docker', 'kubernetes', 'git', 'agile', 'scrum', 'api',
            'machine learning', 'data science', 'analytics', 'cloud', 'devops',
            'frontend', 'backend', 'fullstack', 'mobile', 'web development',
            'project management', 'leadership', 'team', 'communication'
        ]
        
        # Extract keywords that appear in the job description
        found_keywords = []
        for keyword in common_keywords:
            if keyword in text:
                found_keywords.append(keyword)
        
        # Also extract words that appear multiple times (likely important)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        word_freq = {}
        for word in words:
            if word not in ['the', 'and', 'for', 'with', 'you', 'will', 'are', 'have']:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Add frequently mentioned words
        frequent_words = [word for word, freq in word_freq.items() if freq >= 2]
        found_keywords.extend(frequent_words[:10])  # Top 10 frequent words
        
        return list(set(found_keywords))  # Remove duplicates
    
    def _calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        
        
        weighted_sum = 0
        total_weight = 0
        
        for criterion, score in scores.items():
            weight = self.weights.get(criterion, 0)
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 50  # Default score if no weights
        
        return weighted_sum / total_weight
    
    def _generate_recommendation(self, final_score: float, scores: Dict[str, float]) -> str:
        
        
        if final_score >= 80:
            return "HIRE"
        elif final_score >= self.passing_score:
            # Check if any critical area is too low
            critical_areas = ['skills_match', 'experience_relevance']
            critical_scores = [scores.get(area, 0) for area in critical_areas]
            
            if any(score < 40 for score in critical_scores):
                return "CONSIDER"
            else:
                return "HIRE"
        elif final_score >= 40:
            return "CONSIDER"
        else:
            return "REJECT"
    
    def batch_score_resumes(self, resume_list: List[Dict[str, Any]], 
                           job_description: str) -> List[Dict[str, Any]]:
        
        
        results = []
        total_resumes = len(resume_list)
        
        logger.info(f"Starting batch scoring of {total_resumes} resumes")
        
        for i, resume_data in enumerate(resume_list, 1):
            logger.info(f"Processing resume {i}/{total_resumes}: {resume_data.get('filename', 'unknown')}")
            
            result = self.score_resume(resume_data, job_description)
            results.append(result)
            
            # Log progress
            if result['success']:
                logger.info(f"Scored: {result['filename']} - Score: {result['final_score']} - {result['recommendation']}")
            else:
                logger.error(f"Failed: {result['filename']} - {result['error']}")
        
        logger.info(f"Batch scoring completed. {len([r for r in results if r['success']])} successful, {len([r for r in results if not r['success']])} failed")

        return results



    def _improve_skill_matching(self, llm_analysis: Dict[str, Any], resume_text: str, job_description: str) -> Dict[str, Any]:
        
        # Create a copy of the analysis to modify
        improved_analysis = llm_analysis.copy()

        # Extract skills from job description
        job_skills = self._extract_skills_from_text(job_description)

        # Extract skills from resume
        resume_skills = self._extract_skills_from_text(resume_text)

        # Find actual matching skills using intelligent matching
        actual_matching_skills = []
        matched_job_skills = set()  # Track which job skills have been matched
        implied_skills_satisfied = set()  # Track skills satisfied through "implies" relationships

        for job_skill in job_skills:
            matched_skill = self._find_matching_skill(job_skill, resume_skills, resume_text)
            if matched_skill and job_skill.lower() not in matched_job_skills:
                actual_matching_skills.append(matched_skill)
                matched_job_skills.add(job_skill.lower())

                # Check if this match implies other skills and mark them as satisfied
                implied_skills = self._extract_implied_skills(matched_skill)
                implied_skills_satisfied.update(implied_skills)

        # Add implied skills to matched_job_skills so they don't appear in missing skills
        matched_job_skills.update(implied_skills_satisfied)

        # Find actual missing skills (accounting for intelligent matching and implies relationships)
        actual_missing_skills = []
        for job_skill in job_skills:
            # Check if this job skill was matched (including through "implies" relationships)
            if job_skill.lower() not in matched_job_skills:
                actual_missing_skills.append(job_skill)

        # Update the analysis with accurate skill matching
        improved_analysis['matching_skills'] = actual_matching_skills
        improved_analysis['missing_skills'] = actual_missing_skills

        # Recalculate skills match score based on actual matching
        if job_skills:
            skills_match_percentage = len(actual_matching_skills) / len(job_skills) * 100
            improved_analysis['skills_match'] = min(100, max(0, skills_match_percentage))

            # Add critical skills analysis
            improved_analysis['required_skills_count'] = len(job_skills)
            improved_analysis['matched_skills_count'] = len(actual_matching_skills)
            improved_analysis['skills_coverage_percentage'] = skills_match_percentage

        return improved_analysis

    def _extract_skills_from_text(self, text: str) -> List[str]:
        
        # Comprehensive skill database
        skill_database = [
            # Programming Languages
            'Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust', 'Swift',
            'Kotlin', 'TypeScript', 'Scala', 'R', 'MATLAB', 'Perl', 'Shell', 'Bash', 'PowerShell',

            # Web Technologies
            'HTML', 'HTML5', 'CSS', 'CSS3', 'React', 'Angular', 'Vue.js', 'Node.js', 'Express',
            'Django', 'Flask', 'Spring', 'Laravel', 'Rails', 'ASP.NET', 'jQuery', 'Bootstrap',
            'Sass', 'Less', 'Webpack', 'Vite', 'Next.js', 'Nuxt.js', 'Svelte',

            # Databases
            'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'SQLite', 'Oracle', 'SQL Server',
            'Cassandra', 'DynamoDB', 'Elasticsearch', 'Neo4j', 'InfluxDB', 'Database',

            # Cloud & DevOps
            'AWS', 'Azure', 'Google Cloud', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'GitLab CI',
            'GitHub Actions', 'Terraform', 'Ansible', 'Chef', 'Puppet', 'Vagrant', 'Helm',
            'GitHub', 'GitLab', 'Bitbucket', 'CI/CD', 'DevOps', 'Cloud',

            # Data Science & ML
            'TensorFlow', 'PyTorch', 'Keras', 'scikit-learn', 'Pandas', 'NumPy', 'Matplotlib',
            'Seaborn', 'Plotly', 'Jupyter', 'Apache Spark', 'Hadoop', 'Tableau', 'Power BI',

            # Mobile Development
            'React Native', 'Flutter', 'Xamarin', 'Ionic', 'Cordova', 'Android', 'iOS',

            # Testing
            'Testing', 'Unit Testing', 'Integration Testing', 'Test Automation', 'QA',
            'Selenium', 'Jest', 'Mocha', 'PyTest', 'JUnit', 'TestNG', 'Cypress',

            # Tools & Others
            'Git', 'SVN', 'JIRA', 'Confluence', 'Slack', 'VS Code', 'IntelliJ', 'Eclipse',
            'Postman', 'Swagger', 'REST', 'GraphQL', 'SOAP', 'Microservices', 'API',
            'Agile', 'Scrum', 'Kanban', 'TDD', 'BDD', 'Maven', 'Gradle'
        ]

        # Convert text to lowercase for matching
        text_lower = text.lower()

        # Find skills that appear in the text
        found_skills = []
        for skill in skill_database:
            # Check for exact word match (case-insensitive)
            import re
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)

        return found_skills

    def _find_matching_skill(self, job_skill: str, resume_skills: List[str], resume_text: str) -> str:
        
        job_skill_lower = job_skill.lower().strip()

        # 1. Exact match (case-insensitive)
        for resume_skill in resume_skills:
            if job_skill_lower == resume_skill.lower().strip():
                return resume_skill

        # 2. Check skill synonyms and related skills
        skill_mappings = self._get_skill_mappings()

        # Check if job skill has synonyms in resume
        if job_skill_lower in skill_mappings:
            synonyms = skill_mappings[job_skill_lower]
            for synonym in synonyms:
                for resume_skill in resume_skills:
                    if synonym.lower() == resume_skill.lower().strip():
                        return f"{resume_skill} (implies {job_skill})"

                # Also check in full resume text for context
                import re
                pattern = r'\b' + re.escape(synonym.lower()) + r'\b'
                if re.search(pattern, resume_text.lower()):
                    return f"{synonym} (implies {job_skill})"

        # 3. Check reverse mapping (if resume skill implies job skill)
        for resume_skill in resume_skills:
            resume_skill_lower = resume_skill.lower().strip()
            if resume_skill_lower in skill_mappings:
                if job_skill_lower in [s.lower() for s in skill_mappings[resume_skill_lower]]:
                    return f"{resume_skill} (implies {job_skill})"

        # 4. Partial matching for compound skills
        if self._is_partial_match(job_skill_lower, resume_skills):
            return self._get_partial_match(job_skill_lower, resume_skills)

        return None

    def _extract_implied_skills(self, matched_skill: str) -> set:
        
        implied_skills = set()

        # Check if the matched skill contains "implies"
        if "(implies " in matched_skill:
            # Extract the implied skill from the parentheses
            import re
            pattern = r'\(implies ([^)]+)\)'
            match = re.search(pattern, matched_skill)
            if match:
                implied_skill = match.group(1).strip()
                implied_skills.add(implied_skill.lower())

        return implied_skills

    def _get_skill_mappings(self) -> Dict[str, List[str]]:
        
        return {
            # Version Control & Git
            'git': ['github', 'gitlab', 'bitbucket', 'version control', 'source control', 'git version control'],
            'github': ['git', 'version control', 'source control'],
            'gitlab': ['git', 'version control', 'source control'],
            'bitbucket': ['git', 'version control', 'source control'],
            'version control': ['git', 'github', 'gitlab', 'bitbucket', 'svn'],

            # Programming Languages
            'javascript': ['js', 'node.js', 'nodejs', 'react', 'vue', 'angular', 'jquery'],
            'js': ['javascript', 'node.js', 'nodejs'],
            'python': ['django', 'flask', 'fastapi', 'pandas', 'numpy', 'scikit-learn'],
            'java': ['spring', 'spring boot', 'hibernate', 'maven', 'gradle'],
            'c#': ['csharp', '.net', 'dotnet', 'asp.net'],
            'typescript': ['ts', 'javascript', 'js', 'angular', 'react'],

            # Web Technologies
            'html': ['html5', 'web development', 'frontend'],
            'css': ['css3', 'sass', 'scss', 'less', 'web development', 'frontend'],
            'react': ['javascript', 'jsx', 'redux', 'frontend'],
            'angular': ['typescript', 'javascript', 'frontend'],
            'vue': ['javascript', 'frontend'],
            'node.js': ['nodejs', 'javascript', 'backend'],
            'express': ['node.js', 'nodejs', 'javascript'],

            # Databases
            'sql': ['mysql', 'postgresql', 'sqlite', 'sql server', 'oracle'],
            'mysql': ['sql', 'database'],
            'postgresql': ['postgres', 'sql', 'database'],
            'mongodb': ['nosql', 'database'],
            'redis': ['cache', 'database', 'nosql'],

            # Cloud & DevOps
            'aws': ['amazon web services', 'ec2', 's3', 'lambda', 'cloud'],
            'azure': ['microsoft azure', 'cloud'],
            'gcp': ['google cloud', 'google cloud platform', 'cloud'],
            'docker': ['containerization', 'containers', 'devops'],
            'kubernetes': ['k8s', 'container orchestration', 'devops'],
            'jenkins': ['ci/cd', 'continuous integration', 'devops'],

            # Frameworks
            'django': ['django'],
            'flask': ['flask'],
            'spring': ['spring'],
            'laravel': ['laravel'],
            'rails': ['rails', 'ruby on rails'],

            # Testing
            'testing': ['unit testing', 'integration testing', 'pytest', 'junit', 'jest'],
            'pytest': ['pytest'],
            'junit': ['junit'],
            'jest': ['jest'],

            # Project Management
            'agile': ['scrum', 'kanban', 'project management'],
            'scrum': ['agile', 'project management'],
            'jira': ['project management', 'issue tracking'],

            # Data Science & ML
            'machine learning': ['ml', 'ai', 'artificial intelligence', 'data science'],
            'data science': ['machine learning', 'python', 'pandas', 'numpy'],
            'pandas': ['pandas'],
            'numpy': ['numpy'],
            'tensorflow': ['tensorflow'],
            'pytorch': ['pytorch'],
        }

    def _is_partial_match(self, job_skill: str, resume_skills: List[str]) -> bool:
        
        job_words = set(job_skill.lower().split())

        for resume_skill in resume_skills:
            resume_words = set(resume_skill.lower().split())
            # If job skill words are subset of resume skill words
            if job_words.issubset(resume_words) or resume_words.issubset(job_words):
                return True
        return False

    def _get_partial_match(self, job_skill: str, resume_skills: List[str]) -> str:
        
        job_words = set(job_skill.lower().split())

        for resume_skill in resume_skills:
            resume_words = set(resume_skill.lower().split())
            if job_words.issubset(resume_words) or resume_words.issubset(job_words):
                return f"{resume_skill} (partial match for {job_skill})"
        return None

    def _calculate_skills_first_score(self, scores: Dict[str, float]) -> tuple:
        

        skills_score = scores.get('skills_match', 0)
        experience_score = scores.get('experience_relevance', 0)

        # CRITICAL: Skills veto - if skills are too low, automatic reject
        if skills_score < settings.SKILLS_VETO_THRESHOLD:
            return 0, "REJECT"

        # Skills-first calculation
        if skills_score >= settings.CRITICAL_SKILLS_THRESHOLD:
            # Good skills - calculate normally with high skills weight
            final_score = self._calculate_weighted_score(scores)

        elif skills_score >= settings.MINIMUM_SKILLS_PERCENTAGE:
            # Marginal skills - limit experience compensation
            base_score = self._calculate_weighted_score(scores)

            # Cap the benefit from high experience if skills are marginal
            if experience_score > 80 and skills_score < 50:
                # Reduce experience contribution
                experience_penalty = (80 - skills_score) * 0.5
                final_score = max(base_score - experience_penalty, skills_score)
            else:
                final_score = base_score

        else:
            # Poor skills - heavily penalized regardless of experience
            final_score = skills_score * 0.8  # Maximum 80% of skills score

        # Ensure final score doesn't exceed 100 or go below 0
        final_score = max(0, min(100, final_score))

        # Generate skills-based recommendation
        recommendation = self._generate_skills_based_recommendation(final_score, skills_score, scores)

        return round(final_score, 2), recommendation

    def _generate_skills_based_recommendation(self, final_score: float, skills_score: float,
                                            scores: Dict[str, float]) -> str:
        

        experience_score = scores.get('experience_relevance', 0)
        education_score = scores.get('education', 0)

        # Skills veto rules
        if skills_score < settings.SKILLS_VETO_THRESHOLD:
            return "REJECT"

        # High skills threshold
        if skills_score >= 80:
            if final_score >= 85:
                return "HIRE"
            elif final_score >= 70:
                return "HIRE" if experience_score >= 60 else "CONSIDER"
            else:
                return "CONSIDER"

        # Good skills threshold
        elif skills_score >= settings.CRITICAL_SKILLS_THRESHOLD:
            if final_score >= 80 and experience_score >= 70:
                return "HIRE"
            elif final_score >= 70:
                return "CONSIDER"
            else:
                return "REJECT"

        # Marginal skills threshold
        elif skills_score >= settings.MINIMUM_SKILLS_PERCENTAGE:
            # Even with high experience, marginal skills = CONSIDER at best
            if final_score >= 75 and experience_score >= 85:
                return "CONSIDER"
            else:
                return "REJECT"

        # Poor skills
        else:
            return "REJECT"

    def _validate_skills_requirements(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        

        required_skills_count = analysis.get('required_skills_count', 0)
        matched_skills_count = analysis.get('matched_skills_count', 0)

        if required_skills_count == 0:
            return analysis

        # Calculate skills coverage
        coverage_percentage = (matched_skills_count / required_skills_count) * 100

        # Add validation flags
        analysis['meets_minimum_skills'] = coverage_percentage >= settings.MINIMUM_SKILLS_PERCENTAGE
        analysis['skills_coverage_level'] = (
            'EXCELLENT' if coverage_percentage >= 80 else
            'GOOD' if coverage_percentage >= 60 else
            'MARGINAL' if coverage_percentage >= 40 else
            'POOR'
        )

        return analysis


# def test_scoring_engine():
    
#     # Sample resume data
#     sample_resume = {
#         'success': True,
#         'filename': 'john_doe.txt',
#         'text': """John Doe
#         Software Developer
#         john.doe@email.com
#         (555) 123-4567
#         LinkedIn: linkedin.com/in/johndoe
#         GitHub: github.com/johndoe
        
#         Experience:
#         - 3 years Python development
#         - React and JavaScript experience
#         - SQL database management
#         - AWS cloud services
#         - Agile development
        
#         Education:
#         Bachelor's in Computer Science
#         """,
#         'metadata': {
#             'word_count': 50,
#             'has_email': True,
#             'has_phone': True,
#             'has_linkedin': True,
#             'has_github': True
#         }
#     }
    
#     sample_job_desc = """
#     Software Developer Position
#     Required Skills: Python, JavaScript, React, SQL, AWS
#     Experience: 2-5 years in software development
#     Education: Bachelor's degree in Computer Science preferred
#     Must have experience with Agile methodologies
#     """
    
#     # Test scoring
#     engine = ScoringEngine()
#     result = engine.score_resume(sample_resume, sample_job_desc)
    
#     print("Scoring Test Result:")
#     print(f"Final Score: {result.get('final_score', 'N/A')}")
#     print(f"Recommendation: {result.get('recommendation', 'N/A')}")
#     print(f"Success: {result.get('success', False)}")


# if __name__ == "__main__":
#     test_scoring_engine()
