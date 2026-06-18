import numpy as np
import pandas as pd
import pickle
import os
import logging
from typing import Tuple, Dict, Any, Optional

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, accuracy_score, f1_score,
    precision_score, recall_score, roc_curve
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

import tensorflow as tf
from tensorflow.keras.models import Model, Sequential, load_model
from tensorflow.keras.layers import (
    Dense, LSTM, Embedding, Dropout, Bidirectional,
    GlobalMaxPooling1D, Conv1D, Input, Concatenate,
    BatchNormalization, Flatten
)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.optimizers import Adam

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CLASSICAL ML MODELS
# ─────────────────────────────────────────────

class ClassicalFraudDetector:
    """Ensemble of classical ML models for fraud detection"""

    def __init__(self):
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=300, max_depth=15, min_samples_leaf=2,
                class_weight='balanced', random_state=42, n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=200, max_depth=5, learning_rate=0.05,
                random_state=42, subsample=0.8
            ),
            'logistic_regression': LogisticRegression(
                C=1.0, class_weight='balanced', solver='saga',
                max_iter=1000, random_state=42
            )
        }
        self.best_model = None
        self.best_model_name = None
        self.feature_names = None
        self.scaler = StandardScaler()
        self.smote = SMOTE(random_state=42, k_neighbors=5)

    def _get_feature_matrix(self, df: pd.DataFrame, tfidf_matrix) -> np.ndarray:
        """Combine structured + TF-IDF features"""
        structured_cols = [c for c in df.columns if any(
            c.startswith(p) for p in ['skill_', 'fraud_', 'text_', 'salary_', 'has_']
        ) and c in df.columns]

        # Boolean/binary columns
        binary_cols = ['telecommuting', 'has_company_logo', 'has_questions']
        binary_cols = [c for c in binary_cols if c in df.columns]

        structured = df[structured_cols + binary_cols].fillna(0).values

        # Combine with TF-IDF (dense representation)
        if hasattr(tfidf_matrix, 'toarray'):
            tfidf_dense = tfidf_matrix.toarray()
        else:
            tfidf_dense = tfidf_matrix

        # Reduce TF-IDF to top 200 features for memory
        from sklearn.decomposition import TruncatedSVD
        if tfidf_dense.shape[1] > 200:
            svd = TruncatedSVD(n_components=200, random_state=42)
            tfidf_reduced = svd.fit_transform(tfidf_matrix)
        else:
            tfidf_reduced = tfidf_dense

        X = np.hstack([structured, tfidf_reduced])
        self.feature_names = structured_cols + binary_cols + [f'tfidf_{i}' for i in range(tfidf_reduced.shape[1])]
        return X

    def train(self, df_train: pd.DataFrame, tfidf_train,
              y_train: np.ndarray) -> Dict[str, Dict]:
        """Train all models and select the best"""
        logger.info("Training classical ML models...")
        X_train = self._get_feature_matrix(df_train, tfidf_train)

        # Handle class imbalance with SMOTE
        logger.info(f"Class distribution before SMOTE: {np.bincount(y_train)}")
        X_resampled, y_resampled = self.smote.fit_resample(X_train, y_train)
        logger.info(f"Class distribution after SMOTE: {np.bincount(y_resampled)}")

        X_scaled = self.scaler.fit_transform(X_resampled)

        results = {}
        best_f1 = 0

        for name, model in self.models.items():
            logger.info(f"Training {name}...")
            cv_scores = cross_val_score(
                model, X_scaled, y_resampled,
                cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
                scoring='f1'
            )
            model.fit(X_scaled, y_resampled)
            y_pred = model.predict(self.scaler.transform(X_train))
            f1 = f1_score(y_train, y_pred)

            results[name] = {
                'cv_f1_mean': cv_scores.mean(),
                'cv_f1_std': cv_scores.std(),
                'train_f1': f1,
                'model': model
            }
            logger.info(f"{name}: CV F1 = {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

            if cv_scores.mean() > best_f1:
                best_f1 = cv_scores.mean()
                self.best_model = model
                self.best_model_name = name

        logger.info(f"Best model: {self.best_model_name} (F1={best_f1:.4f})")
        return results

    def evaluate(self, df_test: pd.DataFrame, tfidf_test,
                 y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate the best model on test set"""
        X_test = self._get_feature_matrix(df_test, tfidf_test)
        X_test_scaled = self.scaler.transform(X_test)

        y_pred = self.best_model.predict(X_test_scaled)
        y_prob = self.best_model.predict_proba(X_test_scaled)[:, 1]

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_prob),
            'confusion_matrix': confusion_matrix(y_test, y_pred),
            'classification_report': classification_report(y_test, y_pred),
            'y_pred': y_pred,
            'y_prob': y_prob,
            'roc_curve': roc_curve(y_test, y_prob)
        }

        if hasattr(self.best_model, 'feature_importances_'):
            fi = self.best_model.feature_importances_
            if self.feature_names:
                metrics['feature_importance'] = dict(
                    sorted(zip(self.feature_names, fi), key=lambda x: x[1], reverse=True)[:20]
                )
        return metrics

    def predict(self, df: pd.DataFrame, tfidf_matrix) -> Tuple[np.ndarray, np.ndarray]:
        """Predict on new data"""
        X = self._get_feature_matrix(df, tfidf_matrix)
        X_scaled = self.scaler.transform(X)
        y_pred = self.best_model.predict(X_scaled)
        y_prob = self.best_model.predict_proba(X_scaled)[:, 1]
        return y_pred, y_prob

    def save(self, path: str = "data/models/classical_fraud_detector.pkl"):
        """Save model to disk"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump({
                'models': self.models,
                'best_model': self.best_model,
                'best_model_name': self.best_model_name,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }, f)
        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str) -> 'ClassicalFraudDetector':
        """Load model from disk"""
        detector = cls()
        with open(path, 'rb') as f:
            data = pickle.load(f)
        detector.models = data['models']
        detector.best_model = data['best_model']
        detector.best_model_name = data['best_model_name']
        detector.scaler = data['scaler']
        detector.feature_names = data['feature_names']
        return detector


# ─────────────────────────────────────────────
# DEEP LEARNING: Bi-LSTM MODEL
# ─────────────────────────────────────────────

class DeepFraudDetector:
    """
    Deep Learning model for fake job detection.
    Architecture: Bidirectional LSTM + CNN hybrid with attention
    """

    def __init__(self, max_vocab: int = 20000, max_len: int = 256,
                 embed_dim: int = 128):
        self.max_vocab = max_vocab
        self.max_len = max_len
        self.embed_dim = embed_dim
        self.tokenizer = Tokenizer(num_words=max_vocab, oov_token='<OOV>')
        self.model = None
        self.history = None

    def _build_model(self) -> Model:
        """
        Hybrid CNN-BiLSTM architecture:
        - Embedding → Conv1D (local n-gram features) → BiLSTM (sequential context)
        - Dense head with dropout for regularization
        """
        inp = Input(shape=(self.max_len,), name='text_input')

        # Embedding layer
        x = Embedding(self.max_vocab, self.embed_dim,
                       input_length=self.max_len, name='embedding')(inp)
        x = Dropout(0.3)(x)

        # CNN branch (local patterns)
        conv = Conv1D(128, kernel_size=3, activation='relu', padding='same')(x)
        conv = Conv1D(64, kernel_size=2, activation='relu', padding='same')(conv)

        # BiLSTM branch (sequential patterns)
        lstm = Bidirectional(LSTM(128, return_sequences=True, dropout=0.2))(x)
        lstm = Bidirectional(LSTM(64, dropout=0.2))(lstm)

        # Global pooling on CNN branch
        conv_pool = GlobalMaxPooling1D()(conv)

        # Concatenate branches
        merged = Concatenate()([conv_pool, lstm])
        merged = BatchNormalization()(merged)

        # Dense classification head
        out = Dense(256, activation='relu')(merged)
        out = Dropout(0.4)(out)
        out = Dense(128, activation='relu')(out)
        out = Dropout(0.3)(out)
        out = Dense(1, activation='sigmoid', name='fraud_probability')(out)

        model = Model(inputs=inp, outputs=out)
        model.compile(
            optimizer=Adam(learning_rate=1e-3),
            loss='binary_crossentropy',
            metrics=['accuracy', tf.keras.metrics.AUC(name='auc'),
                     tf.keras.metrics.Precision(name='precision'),
                     tf.keras.metrics.Recall(name='recall')]
        )
        return model

    def prepare_sequences(self, texts: pd.Series, fit: bool = True) -> np.ndarray:
        """Convert texts to padded sequences"""
        texts = texts.fillna("").astype(str).tolist()
        if fit:
            self.tokenizer.fit_on_texts(texts)
        sequences = self.tokenizer.texts_to_sequences(texts)
        padded = pad_sequences(sequences, maxlen=self.max_len,
                               padding='post', truncating='post')
        return padded

    def train(self, X_train_text: pd.Series, y_train: np.ndarray,
              X_val_text: pd.Series, y_val: np.ndarray,
              epochs: int = 20, batch_size: int = 64) -> dict:
        """Train the deep learning model"""
        logger.info("Preparing sequences for deep learning...")
        X_train_seq = self.prepare_sequences(X_train_text, fit=True)
        X_val_seq = self.prepare_sequences(X_val_text, fit=False)

        logger.info(f"Train shape: {X_train_seq.shape}, Val shape: {X_val_seq.shape}")

        self.model = self._build_model()
        logger.info(f"Model parameters: {self.model.count_params():,}")

        # Callbacks
        callbacks = [
            EarlyStopping(monitor='val_auc', patience=5, restore_best_weights=True, mode='max'),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-6),
            ModelCheckpoint('data/models/bilstm_best.h5', monitor='val_auc',
                            save_best_only=True, mode='max')
        ]

        # Class weights for imbalanced data
        n_neg = np.sum(y_train == 0)
        n_pos = np.sum(y_train == 1)
        class_weight = {0: 1.0, 1: n_neg / n_pos}

        self.history = self.model.fit(
            X_train_seq, y_train,
            validation_data=(X_val_seq, y_val),
            epochs=epochs,
            batch_size=batch_size,
            class_weight=class_weight,
            callbacks=callbacks,
            verbose=1
        )
        return self.history.history

    def evaluate(self, X_test_text: pd.Series,
                 y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate model on test set"""
        X_test_seq = self.prepare_sequences(X_test_text, fit=False)
        y_prob = self.model.predict(X_test_seq, verbose=0).flatten()
        y_pred = (y_prob > 0.5).astype(int)

        return {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_prob),
            'confusion_matrix': confusion_matrix(y_test, y_pred),
            'classification_report': classification_report(y_test, y_pred),
            'y_pred': y_pred,
            'y_prob': y_prob
        }

    def predict_single(self, text: str) -> Tuple[int, float]:
        """Predict fraud probability for a single job posting"""
        seq = self.prepare_sequences(pd.Series([text]), fit=False)
        prob = float(self.model.predict(seq, verbose=0)[0][0])
        return int(prob > 0.5), prob

    def save(self, model_path: str = "data/models/bilstm_fraud.h5",
             tokenizer_path: str = "data/models/tokenizer.pkl"):
        """Save model and tokenizer"""
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        self.model.save(model_path)
        with open(tokenizer_path, 'wb') as f:
            pickle.dump(self.tokenizer, f)
        logger.info(f"Deep model saved to {model_path}")

    @classmethod
    def load(cls, model_path: str, tokenizer_path: str) -> 'DeepFraudDetector':
        """Load saved model and tokenizer"""
        detector = cls()
        detector.model = load_model(model_path)
        with open(tokenizer_path, 'rb') as f:
            detector.tokenizer = pickle.load(f)
        return detector


# ─────────────────────────────────────────────
# ENSEMBLE PREDICTOR
# ─────────────────────────────────────────────

class EnsembleFraudDetector:
    """
    Weighted ensemble combining classical ML + Deep Learning
    for maximum accuracy
    """

    def __init__(self, classical_weight: float = 0.4, deep_weight: float = 0.6):
        self.classical_weight = classical_weight
        self.deep_weight = deep_weight
        self.classical_model: Optional[ClassicalFraudDetector] = None
        self.deep_model: Optional[DeepFraudDetector] = None
        self.threshold = 0.5

    def set_models(self, classical: ClassicalFraudDetector,
                   deep: DeepFraudDetector):
        self.classical_model = classical
        self.deep_model = deep

    def predict(self, df: pd.DataFrame, tfidf_matrix,
                text_col: str = 'combined_text') -> Tuple[np.ndarray, np.ndarray]:
        """Ensemble prediction"""
        _, classical_prob = self.classical_model.predict(df, tfidf_matrix)
        deep_seq = self.deep_model.prepare_sequences(df[text_col], fit=False)
        deep_prob = self.deep_model.model.predict(deep_seq, verbose=0).flatten()

        ensemble_prob = (self.classical_weight * classical_prob +
                         self.deep_weight * deep_prob)
        ensemble_pred = (ensemble_prob > self.threshold).astype(int)
        return ensemble_pred, ensemble_prob

    def find_optimal_threshold(self, y_true: np.ndarray,
                               y_prob: np.ndarray) -> float:
        """Find threshold that maximizes F1 score"""
        thresholds = np.arange(0.1, 0.9, 0.05)
        best_f1, best_thresh = 0, 0.5
        for thresh in thresholds:
            y_pred = (y_prob > thresh).astype(int)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_thresh = thresh
        self.threshold = best_thresh
        logger.info(f"Optimal threshold: {best_thresh:.2f} (F1={best_f1:.4f})")
        return best_thresh