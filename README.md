# Smart Student Performance Prediction System

This project is a complete web-based student performance prediction platform built with Flask and Scikit-learn.

## Features

- Instructor registration, login, and session-based access control
- CSV upload and validation for academic data
- Automated preprocessing (missing value imputation + Min-Max scaling)
- ML training with:
  - Decision Tree
  - Random Forest
  - Logistic Regression
- Automatic best-model selection by accuracy
- Prediction dashboard with:
  - Bar chart
  - Pie chart
  - Highlighted "At-Risk" students
- Report export:
  - CSV
  - PDF

## Required CSV Columns

- `student_id` (recommended for prediction reports)
- `attendance_percentage`
- `assignment_avg`
- `quiz_avg`
- `midterm_score`
- `performance_level` (optional for training upload; if absent it is auto-derived)

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

Default admin account (created automatically):

- username: `admin`
- password: `admin123`

You can override with environment variables:

- `APP_ADMIN_USERNAME`
- `APP_ADMIN_PASSWORD`
- `DATABASE_URL` (set to MySQL URI for production)

## Notes

- Default database is SQLite for easy setup.
- You can switch to MySQL by setting:
  `DATABASE_URL=mysql+pymysql://user:password@localhost/db_name`
