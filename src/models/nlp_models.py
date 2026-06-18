import numpy as np
import pandas as pd
import re
import pickle
import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter

import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold

import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import (
    Dense, Embedding, LSTM, Bidirectional, Dropout,
    GlobalMaxPooling1D, Input, Conv1D, Concatenate
)
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# JOB CATEGORY CLASSIFIER
# ─────────────────────────────────────────────

class JobCategoryClassifier:
    """
    Multi-class job category classification using TF-IDF + Logistic Regression
    + Deep BiLSTM for comparison
    """

    JOB_CATEGORIES = [
        'Data Science & AI', 'Software Engineering', 'Product Management',
        'Marketing & Sales', 'Finance & Accounting', 'Human Resources',
        'Healthcare & Medical', 'Operations & Supply Chain',
        'Design & Creative', 'Customer Support', 'Legal & Compliance',
        'Education & Research'
    ]

    # Keyword seeds per category for zero-shot / rule-based fallback
    CATEGORY_KEYWORDS = {
        'Data Science & AI': ['data scientist', 'machine learning', 'deep learning', 'ai',
                               'nlp', 'tensorflow', 'pytorch', 'model', 'analytics', 'pandas'],
        'Software Engineering': ['software engineer', 'developer', 'backend', 'frontend',
                                  'fullstack', 'java', 'javascript', 'python', 'api', 'microservices'],
        'Product Management': ['product manager', 'roadmap', 'stakeholder', 'agile', 'sprint',
                                'kpi', 'user story', 'backlog', 'go-to-market', 'product strategy'],
        'Marketing & Sales': ['marketing', 'sales', 'seo', 'campaign', 'lead generation',
                               'crm', 'brand', 'content', 'conversion', 'pipeline'],
        'Finance & Accounting': ['finance', 'accounting', 'cfa', 'cpa', 'audit', 'budget',
                                  'financial model', 'valuation', 'tax', 'compliance'],
        'Human Resources': ['hr', 'human resources', 'recruitment', 'talent', 'payroll',
                             'onboarding', 'performance review', 'employee', 'compensation'],
        'Healthcare & Medical': ['doctor', 'nurse', 'clinical', 'medical', 'patient',
                                  'health', 'pharmaceutical', 'diagnosis', 'hospital', 'care'],
        'Operations & Supply Chain': ['operations', 'supply chain', 'logistics', 'inventory',
                                       'procurement', 'warehouse', 'vendor', 'shipping', 'erp'],
        'Design & Creative': ['designer', 'ux', 'ui', 'figma', 'sketch', 'adobe', 'creative',
                               'branding', 'illustration', 'motion graphics'],
        'Customer Support': ['customer service', 'support', 'help desk', 'ticketing', 'zendesk',
                              'live chat', 'escalation', 'client', 'satisfaction'],
        'Legal & Compliance': ['lawyer', 'attorney', 'legal', 'compliance', 'regulatory',
                                'contract', 'litigation', 'paralegal', 'intellectual property'],
        'Education & Research': ['teacher', 'professor', 'researcher', 'academic', 'curriculum',
                                  'phd', 'lecturer', 'tutoring', 'publication', 'grant']
    }

    def __init__(self):
        self.tfidf = TfidfVectorizer(max_features=10000, ngram_range=(1, 2),
                                      sublinear_tf=True, min_df=2)
        self.label_encoder = LabelEncoder()
        self.classifier = LogisticRegression(
            C=5.0, solver='saga', multi_class='multinomial',
            max_iter=1000, n_jobs=-1, random_state=42
        )
        self.is_fitted = False

    def rule_based_classify(self, text: str) -> str:
        """Fast rule-based classification as fallback"""
        text_lower = text.lower()
        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            scores[category] = sum(1 for kw in keywords if kw in text_lower)
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'Software Engineering'

    def fit(self, X_texts: pd.Series, y_labels: pd.Series):
        """Train the classifier"""
        logger.info(f"Training on {len(X_texts)} samples, {y_labels.nunique()} categories")
        X_tfidf = self.tfidf.fit_transform(X_texts.fillna(""))
        y_encoded = self.label_encoder.fit_transform(y_labels)
        self.classifier.fit(X_tfidf, y_encoded)
        self.is_fitted = True
        logger.info("Job category classifier trained!")

    def predict(self, texts: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """Predict categories and confidence"""
        X_tfidf = self.tfidf.transform(texts.fillna(""))
        y_pred_enc = self.classifier.predict(X_tfidf)
        y_prob = self.classifier.predict_proba(X_tfidf)
        y_pred = self.label_encoder.inverse_transform(y_pred_enc)
        return y_pred, y_prob

    def predict_single(self, text: str) -> Dict:
        """Predict category for a single job posting"""
        if not self.is_fitted:
            # Fall back to rule-based
            category = self.rule_based_classify(text)
            return {'category': category, 'confidence': 0.75, 'top_5': [(category, 0.75)]}

        X = self.tfidf.transform([text])
        pred_enc = self.classifier.predict(X)[0]
        probs = self.classifier.predict_proba(X)[0]
        categories = self.label_encoder.classes_

        top_5 = sorted(zip(categories, probs), key=lambda x: x[1], reverse=True)[:5]
        return {
            'category': self.label_encoder.inverse_transform([pred_enc])[0],
            'confidence': float(probs.max()),
            'top_5': [(self.label_encoder.inverse_transform([i])[0], float(p))
                       for i, p in enumerate(probs)]
        }

    def evaluate(self, X_test: pd.Series, y_test: pd.Series) -> Dict:
        """Evaluate classifier"""
        y_pred, _ = self.predict(X_test)
        return {
            'accuracy': accuracy_score(y_test, y_pred),
            'f1_macro': f1_score(y_test, y_pred, average='macro', zero_division=0),
            'f1_weighted': f1_score(y_test, y_pred, average='weighted', zero_division=0),
            'report': classification_report(y_test, y_pred, zero_division=0)
        }


# ─────────────────────────────────────────────
# SKILL GAP ANALYZER
# ─────────────────────────────────────────────

class SkillGapAnalyzer:
    """
    Analyzes the gap between a candidate's skills and job market requirements.
    Provides personalized skill recommendations and learning paths.
    """

    SKILL_TAXONOMY = {
        'Programming Languages': {
            'python': {'aliases': ['python3'], 'level': 'foundational', 'popularity': 95},
            'r': {'aliases': ['r-lang', 'r language'], 'level': 'foundational', 'popularity': 65},
            'sql': {'aliases': ['mysql', 'postgresql', 'sqlite'], 'level': 'foundational', 'popularity': 90},
            'java': {'aliases': ['java8', 'java11'], 'level': 'intermediate', 'popularity': 72},
            'scala': {'aliases': [], 'level': 'advanced', 'popularity': 45},
            'julia': {'aliases': [], 'level': 'advanced', 'popularity': 20},
            'javascript': {'aliases': ['js', 'nodejs', 'typescript'], 'level': 'intermediate', 'popularity': 70}
        },
        'ML & AI Frameworks': {
            'tensorflow': {'aliases': ['tf', 'keras'], 'level': 'intermediate', 'popularity': 82},
            'pytorch': {'aliases': ['torch'], 'level': 'intermediate', 'popularity': 78},
            'scikit-learn': {'aliases': ['sklearn'], 'level': 'foundational', 'popularity': 88},
            'xgboost': {'aliases': ['xgb'], 'level': 'intermediate', 'popularity': 72},
            'lightgbm': {'aliases': ['lgbm'], 'level': 'intermediate', 'popularity': 65},
            'hugging face': {'aliases': ['transformers', 'huggingface'], 'level': 'advanced', 'popularity': 70},
            'langchain': {'aliases': [], 'level': 'advanced', 'popularity': 60}
        },
        'Data Engineering': {
            'apache spark': {'aliases': ['pyspark', 'spark'], 'level': 'advanced', 'popularity': 68},
            'hadoop': {'aliases': [], 'level': 'advanced', 'popularity': 50},
            'kafka': {'aliases': ['apache kafka'], 'level': 'advanced', 'popularity': 55},
            'airflow': {'aliases': ['apache airflow'], 'level': 'intermediate', 'popularity': 60},
            'dbt': {'aliases': [], 'level': 'intermediate', 'popularity': 55},
            'databricks': {'aliases': [], 'level': 'intermediate', 'popularity': 62}
        },
        'Cloud & MLOps': {
            'aws': {'aliases': ['amazon web services', 'sagemaker', 'ec2', 's3'], 'level': 'intermediate', 'popularity': 80},
            'azure': {'aliases': ['microsoft azure', 'azure ml'], 'level': 'intermediate', 'popularity': 70},
            'gcp': {'aliases': ['google cloud', 'vertex ai', 'bigquery'], 'level': 'intermediate', 'popularity': 65},
            'docker': {'aliases': ['dockerfile', 'docker-compose'], 'level': 'intermediate', 'popularity': 75},
            'kubernetes': {'aliases': ['k8s'], 'level': 'advanced', 'popularity': 60},
            'mlflow': {'aliases': [], 'level': 'intermediate', 'popularity': 55},
            'git': {'aliases': ['github', 'gitlab'], 'level': 'foundational', 'popularity': 92}
        },
        'Visualization & BI': {
            'tableau': {'aliases': [], 'level': 'intermediate', 'popularity': 72},
            'power bi': {'aliases': ['powerbi'], 'level': 'intermediate', 'popularity': 70},
            'matplotlib': {'aliases': [], 'level': 'foundational', 'popularity': 85},
            'seaborn': {'aliases': [], 'level': 'foundational', 'popularity': 75},
            'plotly': {'aliases': ['dash', 'plotly dash'], 'level': 'intermediate', 'popularity': 65},
            'looker': {'aliases': [], 'level': 'intermediate', 'popularity': 55},
            'streamlit': {'aliases': [], 'level': 'foundational', 'popularity': 65}
        },
        'NLP & Computer Vision': {
            'nltk': {'aliases': [], 'level': 'foundational', 'popularity': 70},
            'spacy': {'aliases': [], 'level': 'intermediate', 'popularity': 68},
            'bert': {'aliases': ['roberta', 'distilbert', 'gpt'], 'level': 'advanced', 'popularity': 72},
            'opencv': {'aliases': ['cv2'], 'level': 'intermediate', 'popularity': 60},
            'yolo': {'aliases': ['yolov8'], 'level': 'advanced', 'popularity': 55},
            'llm': {'aliases': ['large language model', 'chatgpt api', 'openai'], 'level': 'advanced', 'popularity': 75}
        }
    }

    LEARNING_RESOURCES = {
        'python': ['Python.org Official Tutorial', 'Kaggle Python Course (Free)', 'CS50P Harvard (Free)'],
        'sql': ['Mode SQL Tutorial (Free)', 'SQLZoo (Free)', 'LeetCode SQL'],
        'tensorflow': ['TensorFlow Official Docs', 'DeepLearning.AI TF Specialization (Coursera)', 'Fast.ai'],
        'pytorch': ['PyTorch Official Tutorial', 'Fast.ai Practical DL', 'Udacity DL Nanodegree'],
        'scikit-learn': ['Scikit-learn User Guide (Free)', 'Kaggle ML Course', 'Hands-on ML Book'],
        'apache spark': ['Databricks Academy (Free)', 'Spark Official Docs', 'Udemy Spark & Scala'],
        'aws': ['AWS Training (Free Tier)', 'AWS Certified ML Specialty', 'A Cloud Guru'],
        'docker': ['Docker Official Get Started (Free)', 'Docker & Kubernetes Udemy', 'KodeKloud'],
        'tableau': ['Tableau Public (Free)', 'Tableau Official Training', 'Coursera Tableau Specialization'],
        'power bi': ['Microsoft Learn Power BI (Free)', 'SQLBI', 'Udemy Power BI A-Z'],
        'bert': ['HuggingFace Course (Free)', 'Stanford CS224N (Free)', 'Illustrated Transformer Blog'],
        'mlflow': ['MLflow Official Docs', 'Databricks MLflow Tutorial', 'Coursera MLOps Specialization']
    }

    def extract_skills_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract required skills from job description"""
        text_lower = text.lower()
        found_skills = {}

        for category, skills in self.SKILL_TAXONOMY.items():
            found_in_category = []
            for skill, info in skills.items():
                # Check main skill name and aliases
                all_names = [skill] + info['aliases']
                for name in all_names:
                    pattern = r'\b' + re.escape(name) + r'\b'
                    if re.search(pattern, text_lower):
                        found_in_category.append(skill)
                        break
            if found_in_category:
                found_skills[category] = found_in_category

        return found_skills

    def parse_candidate_skills(self, skills_text: str) -> List[str]:
        """Parse skills from a comma/newline separated string"""
        skills = re.split(r'[,\n;]', skills_text.lower())
        parsed = []
        for s in skills:
            s = s.strip()
            if s:
                # Match against taxonomy
                for category, skill_dict in self.SKILL_TAXONOMY.items():
                    for skill, info in skill_dict.items():
                        if s == skill or s in info['aliases']:
                            parsed.append(skill)
                            break
                else:
                    if len(s) > 1:  # Keep it even if not in taxonomy
                        parsed.append(s)
        return list(set(parsed))

    def analyze_gap(self, candidate_skills: List[str],
                    job_description: str,
                    job_title: str = "") -> Dict:
        """
        Main gap analysis function.
        Returns match score, missing skills, matching skills, and learning paths.
        """
        required_skills_by_cat = self.extract_skills_from_text(job_description)
        all_required = []
        for skills in required_skills_by_cat.values():
            all_required.extend(skills)
        all_required = list(set(all_required))

        candidate_set = set(s.lower() for s in candidate_skills)
        required_set = set(all_required)

        # Matching and missing
        matching = [s for s in required_set if s in candidate_set or
                    any(s in skill or skill in s for skill in candidate_set)]
        missing = [s for s in required_set if s not in matching]

        # Match score
        match_score = len(matching) / max(len(required_set), 1)

        # Prioritize missing skills by market popularity
        def get_popularity(skill_name):
            for cat_skills in self.SKILL_TAXONOMY.values():
                if skill_name in cat_skills:
                    return cat_skills[skill_name]['popularity']
            return 50

        missing_prioritized = sorted(missing, key=get_popularity, reverse=True)

        # Build learning paths
        learning_paths = {}
        for skill in missing_prioritized[:5]:  # Top 5 missing skills
            resources = self.LEARNING_RESOURCES.get(skill, [
                f"Search '{skill} tutorial' on Coursera/Udemy",
                f"Official {skill.title()} documentation",
                f"YouTube: '{skill} crash course'"
            ])
            level = "foundational"
            for cat_skills in self.SKILL_TAXONOMY.values():
                if skill in cat_skills:
                    level = cat_skills[skill]['level']
                    break
            learning_paths[skill] = {
                'level': level,
                'estimated_time': {'foundational': '2-4 weeks',
                                   'intermediate': '1-3 months',
                                   'advanced': '3-6 months'}.get(level, '4-8 weeks'),
                'resources': resources
            }

        return {
            'match_score': round(match_score * 100, 1),
            'total_required': len(required_set),
            'matching_skills': matching,
            'missing_skills': missing_prioritized,
            'required_by_category': required_skills_by_cat,
            'learning_paths': learning_paths,
            'recommendation': self._get_recommendation(match_score),
            'readiness_label': self._readiness_label(match_score)
        }

    def _get_recommendation(self, score: float) -> str:
        if score >= 0.8:
            return "Strong match! You're well-qualified. Focus on polishing your portfolio and preparing for interviews."
        elif score >= 0.6:
            return "Good match! Address 2–3 key skill gaps to maximize your interview chances."
        elif score >= 0.4:
            return "Moderate match. Upskill in the top missing areas over the next 1–2 months."
        else:
            return "Significant skill gap. Consider building foundational skills before applying, or target entry-level roles."

    def _readiness_label(self, score: float) -> str:
        if score >= 0.8: return "🟢 Ready to Apply"
        elif score >= 0.6: return "🟡 Minor Gaps"
        elif score >= 0.4: return "🟠 Moderate Gaps"
        else: return "🔴 Significant Gaps"

    def market_skill_frequency(self, job_descriptions: pd.Series,
                               top_n: int = 20) -> pd.DataFrame:
        """Analyze skill frequency across job postings"""
        skill_counts = Counter()
        for desc in job_descriptions.fillna(""):
            found = self.extract_skills_from_text(desc)
            for skills in found.values():
                skill_counts.update(skills)

        df = pd.DataFrame(skill_counts.most_common(top_n),
                          columns=['skill', 'frequency'])
        df['percentage'] = (df['frequency'] / len(job_descriptions) * 100).round(1)
        return df