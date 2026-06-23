# 📱 Mobile Price Predictor

An end-to-end Machine Learning application that predicts the fair market price of a smartphone based on its specifications and provides intelligent pricing insights. The project features an interactive Streamlit dashboard, analytics visualizations, feature importance analysis, and a smart verdict system to help users evaluate mobile listings before making purchasing decisions.

---

## 🚀 Features

### 📱 Mobile Price Prediction
Predict the estimated market price of a smartphone using Machine Learning based on its specifications.

### 💰 Smart Price Verdict
Compare the entered price with the predicted market value and classify it as:

- ✅ Underpriced
- ⚖️ Fairly Priced
- ❌ Overpriced

### 🎯 Recommendation System
Provides actionable recommendations such as:

- Good Deal
- Fair Value
- Avoid / Negotiate

### 📊 Analytics Dashboard

Explore insights through:

- Price Distribution Analysis
- Brand-wise Price Comparison
- Correlation Heatmap
- Feature Importance Analysis
- Mobile Specification Trends

### 📈 Model Performance Metrics

Evaluate model performance using:

- R² Score
- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)

---

## 🎯 Project Objectives

- Predict smartphone prices using Machine Learning.
- Analyze the impact of mobile specifications on pricing.
- Provide real-time price estimation through a web application.
- Help users evaluate device value before purchase.
- Demonstrate an end-to-end Machine Learning workflow.

---

## 🧠 Machine Learning Workflow

1. Data Collection
2. Data Preprocessing
3. Feature Engineering
4. Exploratory Data Analysis (EDA)
5. Model Training
6. Model Evaluation
7. Streamlit Deployment

---

## 🛠️ Technology Stack

### Programming Language
- Python

### Machine Learning
- Scikit-Learn
- Random Forest Regressor

### Data Processing
- Pandas
- NumPy

### Data Visualization
- Matplotlib
- Seaborn
- Plotly

### Web Application
- Streamlit

### Model Persistence
- Joblib

---

## 📂 Project Structure

```text
Mobile_price_predictor/
│
├── app.py
├── preprocess.py
├── train_model.py
├── requirements.txt
│
├── data/
│   ├── mobile_data.csv
│   └── feature_importance.csv
│
├── pages/
│   ├── analytics.py
│   └── predictor.py
│
└── utils/
    └── helper.py
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/jasika1909/DataScience.git
```

### 2️⃣ Navigate to the Project Directory

```bash
cd Mobile_price_predictor
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Train the Model

> **Important:** Due to GitHub file size limitations, trained model files are not included in the repository.

Before running the application, execute:

```bash
python train_model.py
```

This command generates the required model artifacts:

```text
model.pkl
encoder.pkl
metrics.pkl
```

### 5️⃣ Launch the Application

```bash
streamlit run app.py
```

---

## ⚠️ Important Note

GitHub does not allow uploading large model files in this repository. Therefore, the following files are excluded:

```text
model.pkl
encoder.pkl
metrics.pkl
```

To run the project successfully, first execute:

```bash
python train_model.py
```

This will automatically train the model and generate all required files.

---

## 📸 Application Screenshots

### 🏠 Home Page

<img width="1917" height="881" alt="image" src="https://github.com/user-attachments/assets/6de5b4cb-1300-42e6-a746-5e848cbc93c1" />

<img width="1918" height="838" alt="image" src="https://github.com/user-attachments/assets/738a74ea-0db7-4739-82ba-a8bac702c53c" />


### 📱 Price Prediction Interface

<img width="1915" height="868" alt="image" src="https://github.com/user-attachments/assets/10561223-51d3-4bc9-87ab-e7263d96aff0" />

<img width="1918" height="883" alt="image" src="https://github.com/user-attachments/assets/e11db1f0-0f58-4804-86be-8946031b1df1" />

<img width="1918" height="858" alt="image" src="https://github.com/user-attachments/assets/3fe0bcf6-f021-4919-9c1d-fc06043fba9c" />


### 📊 Analytics Dashboard

<img width="1918" height="881" alt="image" src="https://github.com/user-attachments/assets/3b831521-bd45-4e52-8098-9b909cd14ae3" />


### 📈 Feature Importance Analysis

<img width="806" height="456" alt="image" src="https://github.com/user-attachments/assets/e97e349c-2974-4e12-b6c6-d20155afbbee" />   
<img width="782" height="652" alt="image" src="https://github.com/user-attachments/assets/7005d003-728f-4c1c-9f67-acbbf246633a" />


---

## 📊 Model Inputs

The prediction model considers several smartphone specifications, including:

- Brand
- RAM
- Storage
- Battery Capacity
- Camera Specifications
- Display Features
- Connectivity Features
- Additional Hardware Attributes

---

## 📈 Model Evaluation Metrics

| Metric | Description |
|----------|-------------|
| R² Score | Measures model accuracy |
| MAE | Average prediction error |
| RMSE | Root Mean Squared Error |

---

## 💼 Business Value

### For Consumers

- Estimate fair smartphone prices
- Identify overpriced listings
- Make informed purchasing decisions

### For Retailers

- Support pricing strategies
- Analyze market positioning

### For Data Science Enthusiasts

- Demonstrates a complete Machine Learning pipeline
- Covers preprocessing, training, evaluation, and deployment

---

## 🔮 Future Enhancements

- Deep Learning-Based Price Prediction
- Real-Time Market Data Integration
- Mobile Recommendation System
- API Deployment
- Cloud Deployment
- Price Trend Forecasting
- Mobile Brand Comparison

---

## 🎓 Learning Outcomes

This project demonstrates practical experience in:

- Machine Learning
- Regression Modeling
- Feature Engineering
- Exploratory Data Analysis
- Streamlit Development
- Model Deployment
- Data Visualization
- End-to-End ML Workflow

---

## 👩‍💻 Author

### Jasika Awasthi

**B.Tech – Computer Science Engineering (Data Science & Artificial Intelligence)**

📧 Email: jasikaawasthi@gmail.com

🔗 LinkedIn: https://www.linkedin.com/in/jasika-awasthi-608037311/

💻 GitHub: https://github.com/jasika1909

---

## ⭐ Project Highlights

- End-to-End Machine Learning Project
- Mobile Price Prediction System
- Interactive Streamlit Dashboard
- Analytics & Visualization
- Smart Pricing Verdict Engine
- Feature Importance Analysis
- Model Evaluation & Insights
- Real-Time User Predictions

---

### 🌟 If you found this project useful, consider giving it a star on GitHub!
