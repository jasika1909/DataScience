# TalentLens AI: Recruitment Intelligence Platform 🚀

## Project Overview

TalentLens AI is an end-to-end Recruitment Intelligence Platform designed to assist recruiters, job seekers, and organizations in making data-driven hiring decisions.

The platform leverages Machine Learning, Natural Language Processing (NLP), and Data Analytics to provide insights into job postings, salary trends, hiring patterns, skill gaps, and fraudulent recruitment activities through an interactive dashboard.

---

## Key Features

### 🔍 Fake Job Detection

Detect fraudulent job postings using Machine Learning and NLP techniques to protect job seekers from recruitment scams.

### 💰 Salary Prediction

Predict expected salary ranges based on job-related attributes and historical hiring data.

### 📈 Hiring Trends Analysis

Analyze recruitment trends, demand patterns, and employment opportunities across different industries and roles.

### 🏷️ Job Classification

Automatically categorize job postings into relevant job domains using machine learning classification techniques.

### 🎯 Skills Gap Analysis

Identify skill mismatches between market requirements and candidate capabilities to support career planning and workforce development.

### 📊 Interactive Dashboard

Visualize recruitment insights using dynamic charts, KPIs, and analytics dashboards.

---

## Objectives

* Detect fake job advertisements.
* Analyze hiring market trends.
* Predict salary expectations.
* Classify job postings automatically.
* Identify emerging skill requirements.
* Support data-driven recruitment decisions.

---

## Technology Stack

### Programming Language

* Python

### Machine Learning & NLP

* Scikit-Learn
* NLTK
* TF-IDF Vectorization
* Classification Models
* Regression Models

### Data Processing

* Pandas
* NumPy

### Data Visualization

* Plotly
* Matplotlib
* Seaborn

### Web Application

* Streamlit

### Development Tools

* Jupyter Notebook
* VS Code
* Git & GitHub

---

## Project Architecture

```text
TalentLens AI
│
├── src
│   │
│   ├── app.py
│   │
│   ├── models
│   │   ├── fake_job_model.py
│   │   ├── hiring_trends_model.py
│   │   ├── nlp_models.py
│   │   └── salary_model.py
│   │
│   ├── pages
│   │   ├── home.py
│   │   ├── dashboard.py
│   │   ├── fake_job_detection.py
│   │   ├── hiring_trends.py
│   │   ├── job_classification.py
│   │   ├── salary_prediction.py
│   │   └── skills_gap_analysis.py
│   │
│   └── utils
│       └── data_pipeline.py
│
└── README.md
```

---

## Workflow

### Step 1: Data Collection

Collect recruitment-related datasets containing job descriptions, salary information, hiring patterns, and industry data.

### Step 2: Data Preprocessing

* Missing value treatment
* Data cleaning
* Text preprocessing
* Feature engineering

### Step 3: NLP Processing

* Tokenization
* Stopword Removal
* Text Vectorization
* Feature Extraction

### Step 4: Model Development

Build machine learning models for:

* Fake Job Detection
* Salary Prediction
* Job Classification
* Hiring Trend Analysis

### Step 5: Dashboard Development

Integrate predictive models into a user-friendly Streamlit dashboard.

### Step 6: Insights Generation

Generate actionable insights for recruiters and job seekers.

---

## Dashboard Modules

### 🏠 Home

Introduction and project overview.

### 📊 Dashboard

High-level recruitment analytics and KPIs.

### 🔍 Fake Job Detection

Predict whether a job posting is genuine or fraudulent.

### 💰 Salary Prediction

Estimate salary ranges using job-related features.

### 📈 Hiring Trends Analysis

Explore industry-wise and role-wise hiring trends.

### 🏷️ Job Classification

Automatically classify jobs into predefined categories.

### 🎯 Skills Gap Analysis

Compare required skills against available skill sets.

---

## Screenshots

### Home Page

<img width="1918" height="867" alt="image" src="https://github.com/user-attachments/assets/c1a8e328-b1ac-4fdd-8dcf-d126555835e2" />


### Fake Job Detection

<img width="1600" height="725" alt="image" src="https://github.com/user-attachments/assets/d34f7388-78ce-409d-a3b6-ce1ee931079f" />

<img width="1600" height="718" alt="image" src="https://github.com/user-attachments/assets/f1b76689-b00e-45ff-9245-e2169c80115f" />


### Salary Prediction

<img width="1600" height="725" alt="image" src="https://github.com/user-attachments/assets/5ffd05fb-f4e0-440e-bfe0-6934144c123c" />

<img width="1600" height="725" alt="image" src="https://github.com/user-attachments/assets/1a7ea0f5-602b-44fc-8417-5b52bf0d5ebb" />


### Skill Gap Analysis

<img width="1600" height="725" alt="image" src="https://github.com/user-attachments/assets/57eb82d8-eb65-43bd-88ad-13557b98dab1" />

<img width="1600" height="725" alt="image" src="https://github.com/user-attachments/assets/b4620104-5e00-40be-ac45-49d16b77ba9f" />

<img width="1512" height="517" alt="image" src="https://github.com/user-attachments/assets/1be2fd7c-dac2-4dae-8bb3-c0f6e387eea1" />


### Job Classification

<img width="1600" height="737" alt="image" src="https://github.com/user-attachments/assets/a22f292d-bc0c-48b2-a23e-49abb60b2e49" />

<img width="1600" height="737" alt="image" src="https://github.com/user-attachments/assets/bb1a874d-0865-4cdd-a40d-7760d6ef13dd" />


### Hiring Trends Analysis

<img width="1600" height="740" alt="image" src="https://github.com/user-attachments/assets/11da4a92-f7db-4608-9816-21093af3c3bf" />

<img width="1600" height="739" alt="image" src="https://github.com/user-attachments/assets/6ac440ec-cc29-4618-865e-ada66be62303" />

<img width="1473" height="757" alt="image" src="https://github.com/user-attachments/assets/de792c3a-066e-402a-bb39-82a59cfc8c23" />


### Dashboard

<img width="1511" height="547" alt="image" src="https://github.com/user-attachments/assets/0e95d131-eb87-4037-bfd0-3cd9bd9e201c" />

<img width="1907" height="846" alt="image" src="https://github.com/user-attachments/assets/11f4d406-8b42-47bc-b9b6-907e50e3f1ff" />

---

## Installation

### Clone Repository

```bash
git clone https://github.com/jasika1909/DataScience.git
```

### Navigate to Project Directory

```bash
cd Fake_Job_Detection
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
streamlit run src/app.py
```

---

## Business Value

This platform helps:

### Recruiters

* Detect fake job postings
* Analyze hiring trends
* Improve recruitment quality

### Job Seekers

* Identify fraudulent opportunities
* Understand salary expectations
* Discover skill gaps

### Organizations

* Optimize hiring strategies
* Improve workforce planning
* Generate data-driven insights

---

## Future Enhancements

* Deep Learning Models
* BERT-Based NLP Pipeline
* Resume Screening System
* Recommendation Engine
* Real-Time Job Market Analytics
* Cloud Deployment
* MLOps Integration
* AI-Powered Career Guidance

---

## Learning Outcomes

This project demonstrates practical experience in:

* Machine Learning
* Natural Language Processing
* Data Analytics
* Dashboard Development
* Streamlit Application Development
* Predictive Modeling
* Feature Engineering
* Data Visualization

---

## Author

### Jasika Awasthi

B.Tech CSE (Data Science & Artificial Intelligence)

Aspiring Data Scientist | Data Analyst | AI Enthusiast

GitHub: https://github.com/jasika1909

LinkedIn: https://www.linkedin.com/in/jasika-awasthi-608037311/
