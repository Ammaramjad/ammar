import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.tree import DecisionTreeClassifier

REQUIRED_FEATURE_COLUMNS = [
    "attendance_percentage",
    "assignment_avg",
    "quiz_avg",
    "midterm_score",
]


@dataclass
class TrainingResult:
    selected_model_name: str
    selected_metrics: Dict[str, float]
    all_metrics: Dict[str, Dict[str, float]]


def normalize_label(value: str) -> str:
    normalized = str(value).strip().lower()
    mapping = {
        "excellent": "Excellent",
        "average": "Average",
        "at-risk": "At-Risk",
        "atrisk": "At-Risk",
        "at_risk": "At-Risk",
    }
    return mapping.get(normalized, "Average")


def validate_columns(dataframe: pd.DataFrame, include_target: bool = False) -> List[str]:
    expected = list(REQUIRED_FEATURE_COLUMNS)
    if include_target:
        expected.append("performance_level")
    return [column for column in expected if column not in dataframe.columns]


def preprocess_training_data(dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, Dict]:
    frame = dataframe.copy()
    log_steps = []

    if "performance_level" not in frame.columns:
        score = (
            0.3 * frame["attendance_percentage"]
            + 0.25 * frame["assignment_avg"]
            + 0.2 * frame["quiz_avg"]
            + 0.25 * frame["midterm_score"]
        )
        frame["performance_level"] = np.select(
            [score >= 80, score >= 60],
            ["Excellent", "Average"],
            default="At-Risk",
        )
        log_steps.append("Derived performance_level from weighted academic score.")

    numeric_frame = frame[REQUIRED_FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    means = numeric_frame.mean().to_dict()
    numeric_frame = numeric_frame.fillna(means)
    log_steps.append("Imputed missing numerical values with column means.")

    scaler = MinMaxScaler()
    transformed = scaler.fit_transform(numeric_frame)
    x_data = pd.DataFrame(transformed, columns=REQUIRED_FEATURE_COLUMNS)
    log_steps.append("Normalized feature columns with Min-Max scaling.")

    y_data = frame["performance_level"].apply(normalize_label)
    return x_data, y_data, {"feature_means": means, "preprocessing_log": log_steps, "scaler": scaler}


def preprocess_prediction_data(dataframe: pd.DataFrame, feature_means: Dict[str, float], scaler: MinMaxScaler) -> pd.DataFrame:
    numeric_frame = dataframe[REQUIRED_FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    numeric_frame = numeric_frame.fillna(feature_means)
    transformed = scaler.transform(numeric_frame)
    return pd.DataFrame(transformed, columns=REQUIRED_FEATURE_COLUMNS)


def train_models(x_data: pd.DataFrame, y_data: pd.Series) -> Tuple[TrainingResult, Dict[str, object]]:
    stratify_labels = y_data if len(y_data.unique()) > 1 else None
    try:
        x_train, x_test, y_train, y_test = train_test_split(
            x_data,
            y_data,
            test_size=0.2,
            random_state=42,
            stratify=stratify_labels,
        )
    except ValueError:
        # Fall back to non-stratified split for very small datasets.
        x_train, x_test, y_train, y_test = train_test_split(
            x_data,
            y_data,
            test_size=0.2,
            random_state=42,
            stratify=None,
        )

    models = {
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(random_state=42, n_estimators=200),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    }

    all_metrics: Dict[str, Dict[str, float]] = {}
    trained_models: Dict[str, object] = {}

    for name, model in models.items():
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        accuracy = accuracy_score(y_test, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, predictions, average="weighted", zero_division=0
        )
        all_metrics[name] = {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
        }
        trained_models[name] = model

    selected_model_name = max(all_metrics, key=lambda item: all_metrics[item]["accuracy"])
    selected_metrics = all_metrics[selected_model_name]

    return (
        TrainingResult(
            selected_model_name=selected_model_name,
            selected_metrics=selected_metrics,
            all_metrics=all_metrics,
        ),
        trained_models,
    )


def save_model_artifact(path: str, artifact: Dict[str, object]) -> None:
    joblib.dump(artifact, path)


def load_model_artifact(path: str) -> Dict[str, object]:
    return joblib.load(path)


def serialize_log(log_steps: List[str]) -> str:
    return json.dumps(log_steps)
