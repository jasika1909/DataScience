📱 Mobile Price Predictor

An end-to-end Machine Learning application that predicts the fair market price of a smartphone based on its specifications and provides intelligent pricing insights. The project includes an interactive Streamlit dashboard, analytics visualizations, feature importance analysis, and a smart verdict system to help users evaluate mobile listings.

🚀 Features
📱 Mobile Price Prediction

Predict the estimated market price of a smartphone using a trained Machine Learning model.

💰 Smart Price Verdict

Compare a listed price against the predicted market value and classify it as:

✅ Underpriced
⚖️ Fairly Priced
❌ Overpriced
🎯 Recommendation Engine

Provides actionable recommendations such as:

Good Deal
Fair Value
Avoid / Negotiate
📊 Analytics Dashboard

Explore insights through:

Price Distribution Analysis
Brand-wise Price Comparison
Correlation Heatmap
Feature Importance Visualization
Mobile Specification Trends
📈 Model Evaluation

Displays important regression metrics:

R² Score
Mean Absolute Error (MAE)
Root Mean Squared Error (RMSE)
🧠 Machine Learning Workflow
Data Collection
Data Preprocessing
Feature Engineering
Exploratory Data Analysis (EDA)
Model Training
Model Evaluation
Streamlit Deployment

🛠️ Tech Stack
Programming Language
Python
Machine Learning
Scikit-Learn
Random Forest Regressor
Data Processing
Pandas
NumPy
Data Visualization
Matplotlib
Seaborn
Plotly
Web Framework
Streamlit
Model Persistence
Joblib

📂 Project Structure
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
⚙️ Installation & Setup
1. Clone Repository
git clone https://github.com/jasika1909/DataScience.git
2. Navigate to Project Directory
cd Mobile_price_predictor
3. Install Dependencies
pip install -r requirements.txt
4. Train the Model

Since GitHub has a file size limitation and the trained model files exceed the allowed size, the following files are not included in the repository:

model.pkl
encoder.pkl
metrics.pkl

Before running the application, generate these files by executing:

python train_model.py

This will automatically train the model and create all required artifacts.

5. Launch the Application
streamlit run app.py
📌 Important Note

⚠️ Due to GitHub file size restrictions, trained model files are not included in this repository.

Before running the application, you must execute:

python train_model.py

This generates:

model.pkl
encoder.pkl
metrics.pkl

Without these files, the application will not function correctly.

📸 Application Screenshots

Home Page

<img width="1917" height="881" alt="image" src="https://github.com/user-attachments/assets/6de5b4cb-1300-42e6-a746-5e848cbc93c1" />

<img width="1918" height="838" alt="image" src="https://github.com/user-attachments/assets/738a74ea-0db7-4739-82ba-a8bac702c53c" />


Analytics Dashboard

<img width="1915" height="868" alt="image" src="https://github.com/user-attachments/assets/10561223-51d3-4bc9-87ab-e7263d96aff0" />

<img width="1918" height="883" alt="image" src="https://github.com/user-attachments/assets/e11db1f0-0f58-4804-86be-8946031b1df1" />

<img width="1918" height="858" alt="image" src="https://github.com/user-attachments/assets/3fe0bcf6-f021-4919-9c1d-fc06043fba9c" />


Price Prediction Interface

<img width="1918" height="881" alt="image" src="https://github.com/user-attachments/assets/3b831521-bd45-4e52-8098-9b909cd14ae3" />


Feature Importance Analysis

<img width="806" height="456" alt="image" src="https://github.com/user-attachments/assets/e97e349c-2974-4e12-b6c6-d20155afbbee" />   <img width="782" height="652" alt="image" src="https://github.com/user-attachments/assets/7005d003-728f-4c1c-9f67-acbbf246633a" />


📈 Model Inputs

The prediction model uses mobile specifications such as:

Brand
RAM
Storage
Battery Capacity
Camera Specifications
Display Features
Connectivity Features
Additional Hardware Attributes
🎯 Business Value
For Consumers
Estimate fair smartphone prices
Identify overpriced listings
Make informed purchasing decisions
For Retailers
Assist in pricing strategy
Analyze market positioning
For Data Science Enthusiasts
Demonstrates an end-to-end Machine Learning pipeline
Covers preprocessing, model training, evaluation, and deployment
🔮 Future Enhancements
Deep Learning-Based Price Prediction
Real-Time Market Data Integration
Mobile Recommendation System
API Deployment
Cloud Deployment
Price Trend Forecasting
👩‍💻 Author
Jasika Awasthi

B.Tech – Computer Science Engineering (Data Science & Artificial Intelligence)

GitHub: https://github.com/jasika1909
LinkedIn: https://www.linkedin.com/in/jasika-awasthi-608037311/
⭐ Project Highlights
End-to-End Machine Learning Project
Mobile Price Prediction System
Interactive Streamlit Dashboard
Analytics & Visualization
Smart Pricing Verdict Engine
Model Evaluation & Insights
Real-Time User Predictions
