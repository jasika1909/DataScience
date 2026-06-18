import pandas as pd
import numpy as np
import re
import string
import logging
from typing import Tuple, List, Optional

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import spacy

from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.impute import SimpleImputer

# Download NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextPreprocessor:
    """NLP Text Preprocessing for job descriptions and titles"""

    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        # Load spacy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
            self.nlp = None

    def clean_text(self, text: str) -> str:
        """Basic text cleaning"""
        if pd.isna(text) or text == "":
            return ""
        text = str(text).lower()
        text = re.sub(r'http\S+|www\S+|https\S+', '', text)     # Remove URLs
        text = re.sub(r'<.*?>', '', text)                         # Remove HTML tags
        text = re.sub(r'\$[\d,]+(?:\.\d+)?(?:k|K)?', 'SALARY', text)  # Normalize salaries
        text = re.sub(r'\b\d+\+?\s*(?:years?|yrs?)\b', 'EXPERIENCE', text, flags=re.I)
        text = re.sub(r'[^\w\s]', ' ', text)                     # Remove punctuation
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def tokenize_and_lemmatize(self, text: str) -> List[str]:
        """Tokenize, remove stopwords, and lemmatize"""
        if not text:
            return []
        tokens = word_tokenize(text)
        tokens = [
            self.lemmatizer.lemmatize(token)
            for token in tokens
            if token.isalpha() and token not in self.stop_words and len(token) > 2
        ]
        return tokens

    def extract_entities(self, text: str) -> dict:
        """Extract Named Entities using spaCy"""
        entities = {"skills": [], "organizations": [], "locations": []}
        if self.nlp is None or not text:
            return entities
        doc = self.nlp(text[:512])  # Limit for performance
        for ent in doc.ents:
            if ent.label_ == "ORG":
                entities["organizations"].append(ent.text)
            elif ent.label_ in ["GPE", "LOC"]:
                entities["locations"].append(ent.text)
        return entities

    def preprocess_pipeline(self, text: str) -> str:
        """Full preprocessing pipeline: clean → tokenize → lemmatize → rejoin"""
        cleaned = self.clean_text(text)
        tokens = self.tokenize_and_lemmatize(cleaned)
        return " ".join(tokens)

    def batch_preprocess(self, texts: pd.Series, verbose: bool = True) -> pd.Series:
        """Process a full Pandas Series"""
        if verbose:
            logger.info(f"Preprocessing {len(texts)} texts...")
        return texts.fillna("").apply(self.preprocess_pipeline)


class FeatureEngineer:
    """Feature Engineering for recruitment data"""

    TECH_SKILLS = [
        'python', 'sql', 'java', 'javascript', 'r', 'scala', 'spark',
        'tensorflow', 'pytorch', 'keras', 'scikit', 'pandas', 'numpy',
        'tableau', 'power bi', 'excel', 'aws', 'azure', 'gcp', 'docker',
        'kubernetes', 'git', 'linux', 'hadoop', 'kafka', 'mongodb',
        'react', 'node', 'django', 'flask', 'nlp', 'deep learning',
        'machine learning', 'data science', 'computer vision'
    ]

    FRAUD_SIGNALS = [
        'work from home', 'no experience needed', 'earn from home',
        'daily payment', 'weekly payment', 'be your own boss',
        'unlimited income', 'guaranteed income', 'easy money',
        'no degree required', 'immediate start', 'apply now',
        'bitcoin', 'cryptocurrency', 'mlm', 'multi-level',
        'wire transfer', 'gift card', 'money order', 'western union'
    ]

    def extract_salary_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse and engineer salary-related features"""
        df = df.copy()

        def parse_salary(salary_str):
            if pd.isna(salary_str) or salary_str == "":
                return np.nan, np.nan
            nums = re.findall(r'[\d,]+', str(salary_str))
            nums = [int(n.replace(',', '')) for n in nums if n.replace(',', '').isdigit()]
            if len(nums) >= 2:
                return min(nums), max(nums)
            elif len(nums) == 1:
                return nums[0], nums[0]
            return np.nan, np.nan

        if 'salary_range' in df.columns:
            salary_parsed = df['salary_range'].apply(parse_salary)
            df['salary_min'] = salary_parsed.apply(lambda x: x[0])
            df['salary_max'] = salary_parsed.apply(lambda x: x[1])
            df['salary_avg'] = (df['salary_min'] + df['salary_max']) / 2
            df['salary_spread'] = df['salary_max'] - df['salary_min']
            df['has_salary'] = (~df['salary_avg'].isna()).astype(int)
        return df

    def extract_text_features(self, df: pd.DataFrame, text_col: str = 'description') -> pd.DataFrame:
        """Extract statistical text features"""
        df = df.copy()
        text = df[text_col].fillna("")
        df['text_length'] = text.apply(len)
        df['word_count'] = text.apply(lambda x: len(x.split()))
        df['avg_word_length'] = text.apply(
            lambda x: np.mean([len(w) for w in x.split()]) if x.split() else 0
        )
        df['exclamation_count'] = text.apply(lambda x: x.count('!'))
        df['question_count'] = text.apply(lambda x: x.count('?'))
        df['uppercase_ratio'] = text.apply(
            lambda x: sum(1 for c in x if c.isupper()) / max(len(x), 1)
        )
        df['num_sentences'] = text.apply(lambda x: len(re.split(r'[.!?]+', x)))
        return df

    def extract_skill_features(self, df: pd.DataFrame, text_col: str = 'description') -> pd.DataFrame:
        """Extract skill presence features"""
        df = df.copy()
        text = df[text_col].fillna("").str.lower()
        for skill in self.TECH_SKILLS:
            col_name = 'skill_' + re.sub(r'\s+', '_', skill)
            df[col_name] = text.apply(lambda x: int(skill in x))
        df['total_skills_mentioned'] = df[
            [c for c in df.columns if c.startswith('skill_')]
        ].sum(axis=1)
        return df

    def extract_fraud_signals(self, df: pd.DataFrame, text_col: str = 'description') -> pd.DataFrame:
        """Extract fraud red-flag signals"""
        df = df.copy()
        text = df[text_col].fillna("").str.lower()
        for signal in self.FRAUD_SIGNALS:
            col_name = 'fraud_' + re.sub(r'[\s-]+', '_', signal)
            df[col_name] = text.apply(lambda x: int(signal in x))
        df['fraud_signal_count'] = df[
            [c for c in df.columns if c.startswith('fraud_')]
        ].sum(axis=1)
        return df

    def encode_categoricals(self, df: pd.DataFrame, cat_cols: List[str]) -> Tuple[pd.DataFrame, dict]:
        """Label encode categorical columns"""
        df = df.copy()
        encoders = {}
        for col in cat_cols:
            if col in df.columns:
                le = LabelEncoder()
                df[col + '_encoded'] = le.fit_transform(df[col].fillna('Unknown').astype(str))
                encoders[col] = le
        return df, encoders

    def scale_features(self, X_train: np.ndarray, X_test: np.ndarray,
                       method: str = 'standard') -> Tuple[np.ndarray, np.ndarray, object]:
        """Scale numerical features"""
        scaler = StandardScaler() if method == 'standard' else MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        return X_train_scaled, X_test_scaled, scaler


class DataLoader:
    """Load and validate raw datasets"""

    REQUIRED_COLS_FAKE_JOB = [
        'job_id', 'title', 'location', 'department', 'salary_range',
        'company_profile', 'description', 'requirements', 'benefits',
        'telecommuting', 'has_company_logo', 'has_questions',
        'employment_type', 'required_experience', 'required_education',
        'industry', 'function', 'fraudulent'
    ]

    def load_fake_job_dataset(self, path: str) -> pd.DataFrame:
        """Load EMSCAD Fake Job Postings dataset"""
        df = pd.read_csv(path)
        logger.info(f"Loaded Fake Job dataset: {df.shape}")
        logger.info(f"Fraud rate: {df['fraudulent'].mean():.2%}")
        return df

    def load_linkedin_jobs(self, path: str) -> pd.DataFrame:
        """Load LinkedIn Job Postings dataset"""
        df = pd.read_csv(path)
        logger.info(f"Loaded LinkedIn dataset: {df.shape}")
        return df

    def load_glassdoor_salaries(self, path: str) -> pd.DataFrame:
        """Load Glassdoor salary dataset"""
        df = pd.read_csv(path)
        logger.info(f"Loaded Glassdoor dataset: {df.shape}")
        return df

    def validate_dataframe(self, df: pd.DataFrame, required_cols: List[str]) -> bool:
        """Validate that required columns exist"""
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            logger.warning(f"Missing columns: {missing}")
            return False
        return True

    def generate_sample_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """Generate synthetic data for demo/testing"""
        np.random.seed(42)
        titles = ['Data Scientist', 'ML Engineer', 'Data Analyst', 'Software Engineer',
                  'AI Researcher', 'Business Analyst', 'DevOps Engineer', 'Product Manager',
                  'Work From Home Agent', 'Easy Income Opportunity']
        industries = ['Technology', 'Finance', 'Healthcare', 'Education', 'Retail', 'Marketing']
        locations = ['Remote', 'New York, NY', 'San Francisco, CA', 'Austin, TX',
                     'Seattle, WA', 'Chicago, IL', 'Boston, MA', 'Unknown']
        experience = ['Entry level', 'Mid-Senior level', 'Associate', 'Director',
                      'Executive', 'Internship', 'Not Applicable']
        education = ["Bachelor's Degree", "Master's Degree", 'High School or equivalent',
                     'Some College(s)', 'Professional', 'Doctorate', 'Unspecified']

        legit_descriptions = [
            "We are seeking a skilled data scientist with strong Python and ML experience. "
            "Responsibilities include building predictive models, analyzing large datasets, "
            "and collaborating with engineering teams. Requires 3+ years experience.",
            "Join our analytics team to drive data-driven decisions. You will work with "
            "SQL, Tableau, and Python to extract insights from complex datasets.",
            "Exciting opportunity for an ML Engineer to develop and deploy production-grade "
            "machine learning models using TensorFlow and PyTorch."
        ]
        fraud_descriptions = [
            "EASY MONEY! Work from home, no experience needed! Earn $500/day guaranteed! "
            "Daily payment! Be your own boss! Apply now! Unlimited income potential!!!",
            "Make money fast from home! No degree required! Immediate start! "
            "Send $50 registration fee via Western Union to get started today!",
            "Online data entry jobs - earn $1000 weekly! No skills required! "
            "Bitcoin payments available. Guaranteed income working just 2 hours daily!!!"
        ]

        data = []
        for i in range(n_samples):
            is_fraud = np.random.choice([0, 1], p=[0.83, 0.17])
            title = np.random.choice(titles[-2:] if is_fraud else titles[:-2])
            desc = np.random.choice(fraud_descriptions if is_fraud else legit_descriptions)
            salary_min = np.random.choice([np.nan, 30000, 50000, 70000, 90000, 120000])
            salary_max = salary_min * np.random.uniform(1.1, 1.5) if not np.isnan(salary_min) else np.nan
            salary_str = f"${int(salary_min)}-${int(salary_max)}" if not np.isnan(salary_min) else ""

            data.append({
                'job_id': i + 1,
                'title': title,
                'location': np.random.choice(locations),
                'department': np.random.choice(['Engineering', 'Data', 'Marketing', 'Sales', 'HR']),
                'salary_range': salary_str,
                'company_profile': "" if is_fraud else "Established company with great culture.",
                'description': desc,
                'requirements': "" if is_fraud else "BS in CS or related field. 2+ years exp.",
                'benefits': "" if is_fraud else "Health insurance, 401k, remote options.",
                'telecommuting': int(is_fraud) if np.random.random() > 0.5 else 0,
                'has_company_logo': 0 if is_fraud else np.random.choice([0, 1], p=[0.2, 0.8]),
                'has_questions': np.random.choice([0, 1]),
                'employment_type': 'Full-time' if not is_fraud else np.random.choice(['Contract', 'Other', '']),
                'required_experience': np.random.choice(experience),
                'required_education': np.random.choice(education),
                'industry': np.random.choice(industries),
                'function': np.random.choice(['Engineering', 'Information Technology', 'Sales', 'Marketing']),
                'fraudulent': is_fraud
            })

        df = pd.DataFrame(data)
        logger.info(f"Generated {n_samples} samples (fraud rate: {df['fraudulent'].mean():.2%})")
        return df


class FullPreprocessingPipeline:
    """End-to-end preprocessing pipeline"""

    def __init__(self):
        self.text_preprocessor = TextPreprocessor()
        self.feature_engineer = FeatureEngineer()
        self.tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=2)
        self.is_fitted = False

    def fit_transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """Fit and transform the full dataset"""
        logger.info("Starting full preprocessing pipeline...")

        # 1. Text preprocessing
        logger.info("Step 1: Text preprocessing...")
        df['description_clean'] = self.text_preprocessor.batch_preprocess(df['description'])
        df['title_clean'] = self.text_preprocessor.batch_preprocess(df['title'])
        df['combined_text'] = df['title_clean'] + ' ' + df['description_clean']

        # 2. Feature engineering
        logger.info("Step 2: Feature engineering...")
        df = self.feature_engineer.extract_salary_features(df)
        df = self.feature_engineer.extract_text_features(df, 'description')
        df = self.feature_engineer.extract_skill_features(df, 'description')
        df = self.feature_engineer.extract_fraud_signals(df, 'description')

        # 3. TF-IDF
        logger.info("Step 3: TF-IDF vectorization...")
        tfidf_matrix = self.tfidf.fit_transform(df['combined_text'])

        self.is_fitted = True
        logger.info("Pipeline complete!")
        return df, tfidf_matrix

    def transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
        """Transform new data using fitted pipeline"""
        if not self.is_fitted:
            raise RuntimeError("Pipeline must be fit before transforming.")

        df['description_clean'] = self.text_preprocessor.batch_preprocess(df['description'])
        df['title_clean'] = self.text_preprocessor.batch_preprocess(df['title'])
        df['combined_text'] = df['title_clean'] + ' ' + df['description_clean']
        df = self.feature_engineer.extract_salary_features(df)
        df = self.feature_engineer.extract_text_features(df, 'description')
        df = self.feature_engineer.extract_skill_features(df, 'description')
        df = self.feature_engineer.extract_fraud_signals(df, 'description')
        tfidf_matrix = self.tfidf.transform(df['combined_text'])
        return df, tfidf_matrix