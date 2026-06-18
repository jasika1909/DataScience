import numpy as np
import pandas as pd
import pickle
import logging
from typing import Tuple, Dict, Any, List

from sklearn.ensemble import (
    RandomForestRegressor, GradientBoostingRegressor,
    StackingRegressor, ExtraTreesRegressor
)
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error,
    r2_score, mean_absolute_percentage_error
)
from sklearn.model_selection import cross_val_score, KFold

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SalaryFeatureBuilder:
    """Build features specifically for salary prediction"""

    JOB_LEVEL_MAP = {
        'internship': 0, 'entry level': 1, 'associate': 2,
        'mid-senior level': 3, 'director': 4, 'executive': 5, 'not applicable': 2
    }

    EDU_LEVEL_MAP = {
        'high school or equivalent': 0, 'some college(s)': 1,
        "bachelor's degree": 2, "master's degree": 3,
        'professional': 4, 'doctorate': 4, 'unspecified': 2
    }

    HIGH_PAY_INDUSTRIES = [
        'technology', 'finance', 'healthcare', 'consulting',
        'aerospace', 'energy', 'pharmaceutical'
    ]

    HIGH_PAY_SKILLS = [
        'machine learning', 'deep learning', 'tensorflow', 'pytorch',
        'cloud', 'aws', 'azure', 'kubernetes', 'blockchain',
        'data science', 'ai', 'nlp', 'computer vision'
    ]

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Experience level encoding
        df['experience_level_num'] = df.get('required_experience', pd.Series([''] * len(df)))\
            .str.lower().fillna('not applicable').map(self.JOB_LEVEL_MAP).fillna(2)

        # Education encoding
        df['education_level_num'] = df.get('required_education', pd.Series([''] * len(df)))\
            .str.lower().fillna('unspecified').map(self.EDU_LEVEL_MAP).fillna(2)

        # Is high-pay industry?
        industry = df.get('industry', pd.Series([''] * len(df))).fillna('').str.lower()
        df['is_high_pay_industry'] = industry.apply(
            lambda x: int(any(h in x for h in self.HIGH_PAY_INDUSTRIES))
        )

        # Is remote?
        location = df.get('location', pd.Series([''] * len(df))).fillna('').str.lower()
        df['is_remote'] = location.apply(lambda x: int('remote' in x)).astype(int)

        # Is US-based?
        df['is_us_based'] = location.apply(
            lambda x: int(any(us in x for us in ['new york', 'california', 'san francisco',
                                                   'seattle', 'boston', 'austin', 'chicago']))
        )

        # High-pay skills in description
        desc = df.get('description', pd.Series([''] * len(df))).fillna('').str.lower()
        df['high_pay_skill_count'] = desc.apply(
            lambda x: sum(1 for s in self.HIGH_PAY_SKILLS if s in x)
        )

        # Full-time employment
        emp_type = df.get('employment_type', pd.Series([''] * len(df))).fillna('').str.lower()
        df['is_fulltime'] = emp_type.apply(lambda x: int('full-time' in x or 'full time' in x))

        # Company trust signals
        df['has_logo'] = df.get('has_company_logo', pd.Series([0] * len(df))).fillna(0).astype(int)
        df['has_questions'] = df.get('has_questions', pd.Series([0] * len(df))).fillna(0).astype(int)

        # Title-based seniority
        title = df.get('title', pd.Series([''] * len(df))).fillna('').str.lower()
        df['is_senior'] = title.apply(lambda x: int('senior' in x or 'lead' in x or 'staff' in x))
        df['is_manager'] = title.apply(lambda x: int('manager' in x or 'director' in x or 'head of' in x))
        df['is_junior'] = title.apply(lambda x: int('junior' in x or 'intern' in x or 'entry' in x))

        return df

    def get_feature_cols(self) -> List[str]:
        return [
            'experience_level_num', 'education_level_num', 'is_high_pay_industry',
            'is_remote', 'is_us_based', 'high_pay_skill_count', 'is_fulltime',
            'has_logo', 'has_questions', 'is_senior', 'is_manager', 'is_junior',
            'telecommuting', 'total_skills_mentioned', 'text_length', 'word_count'
        ]


class SalaryPredictor:
    """Ensemble salary predictor using stacking"""

    def __init__(self):
        self.feature_builder = SalaryFeatureBuilder()
        self.scaler = StandardScaler()
        self.model = None
        self.feature_cols = None

        # Base models for stacking
        base_models = [
            ('rf', RandomForestRegressor(n_estimators=200, max_depth=12,
                                          random_state=42, n_jobs=-1)),
            ('gbm', GradientBoostingRegressor(n_estimators=150, max_depth=5,
                                               learning_rate=0.05, random_state=42)),
            ('et', ExtraTreesRegressor(n_estimators=200, random_state=42, n_jobs=-1)),
            ('ridge', Ridge(alpha=10.0))
        ]
        meta_model = GradientBoostingRegressor(
            n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42
        )
        self.stacking_model = StackingRegressor(
            estimators=base_models,
            final_estimator=meta_model,
            cv=5, n_jobs=-1
        )

    def prepare_features(self, df: pd.DataFrame,
                         fit_scaler: bool = True) -> Tuple[np.ndarray, List[str]]:
        """Build and scale features"""
        df = self.feature_builder.build_features(df)
        feature_cols = [c for c in self.feature_builder.get_feature_cols()
                        if c in df.columns]
        X = df[feature_cols].fillna(0).values
        if fit_scaler:
            X = self.scaler.fit_transform(X)
        else:
            X = self.scaler.transform(X)
        self.feature_cols = feature_cols
        return X, feature_cols

    def train(self, df_train: pd.DataFrame,
              y_train: np.ndarray) -> Dict[str, float]:
        """Train stacking ensemble"""
        logger.info("Training salary prediction model...")
        X_train, _ = self.prepare_features(df_train, fit_scaler=True)

        logger.info("Fitting stacking ensemble...")
        self.stacking_model.fit(X_train, y_train)

        # Cross-validation
        cv_scores = cross_val_score(
            self.stacking_model, X_train, y_train,
            cv=KFold(n_splits=5, shuffle=True, random_state=42),
            scoring='r2'
        )

        train_pred = self.stacking_model.predict(X_train)
        metrics = {
            'train_r2': r2_score(y_train, train_pred),
            'train_mae': mean_absolute_error(y_train, train_pred),
            'train_rmse': np.sqrt(mean_squared_error(y_train, train_pred)),
            'cv_r2_mean': cv_scores.mean(),
            'cv_r2_std': cv_scores.std()
        }
        logger.info(f"Train R²: {metrics['train_r2']:.4f}, CV R²: {metrics['cv_r2_mean']:.4f}")
        return metrics

    def evaluate(self, df_test: pd.DataFrame,
                 y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate on test set"""
        X_test, _ = self.prepare_features(df_test, fit_scaler=False)
        y_pred = self.stacking_model.predict(X_test)

        # Clip negative predictions
        y_pred = np.maximum(y_pred, 0)

        return {
            'r2': r2_score(y_test, y_pred),
            'mae': mean_absolute_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mape': mean_absolute_percentage_error(y_test, y_pred) * 100,
            'y_pred': y_pred,
            'y_test': y_test
        }

    def predict(self, job_features: dict) -> Dict[str, float]:
        """Predict salary for a single job"""
        df = pd.DataFrame([job_features])
        X, _ = self.prepare_features(df, fit_scaler=False)
        salary = float(np.maximum(self.stacking_model.predict(X)[0], 0))

        # Estimate confidence interval (±15%)
        return {
            'predicted_salary': salary,
            'lower_bound': salary * 0.85,
            'upper_bound': salary * 1.15,
            'salary_formatted': f"${salary:,.0f}",
            'range_formatted': f"${salary * 0.85:,.0f} – ${salary * 1.15:,.0f}"
        }

    def save(self, path: str = "data/models/salary_predictor.pkl"):
        import os, pickle
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.stacking_model,
                'scaler': self.scaler,
                'feature_cols': self.feature_cols
            }, f)
        logger.info(f"Saved to {path}")

    @classmethod
    def load(cls, path: str) -> 'SalaryPredictor':
        import pickle
        predictor = cls()
        with open(path, 'rb') as f:
            data = pickle.load(f)
        predictor.stacking_model = data['model']
        predictor.scaler = data['scaler']
        predictor.feature_cols = data['feature_cols']
        return predictor


class DeepSalaryPredictor:
    """Neural Network salary predictor for learning non-linear patterns"""

    def __init__(self):
        self.scaler = StandardScaler()
        self.model = None
        self.feature_builder = SalaryFeatureBuilder()

    def _build_model(self, input_dim: int) -> Sequential:
        model = Sequential([
            Dense(512, activation='relu', input_dim=input_dim),
            BatchNormalization(),
            Dropout(0.3),
            Dense(256, activation='relu'),
            BatchNormalization(),
            Dropout(0.3),
            Dense(128, activation='relu'),
            Dropout(0.2),
            Dense(64, activation='relu'),
            Dense(1, activation='linear')
        ])
        model.compile(
            optimizer=Adam(learning_rate=1e-3),
            loss='huber',
            metrics=['mae']
        )
        return model

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: np.ndarray, y_val: np.ndarray,
              epochs: int = 100, batch_size: int = 64):
        self.model = self._build_model(X_train.shape[1])
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5)
        ]
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs, batch_size=batch_size,
            callbacks=callbacks, verbose=0
        )
        return history.history

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.maximum(self.model.predict(X, verbose=0).flatten(), 0)