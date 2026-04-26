# 📱 Google Play Store Data Analysis Project

## 📌 Project Overview

This project focuses on analyzing the Google Play Store dataset to extract meaningful insights about mobile applications, user ratings, installs, categories, and trends. The goal of this project is to perform data cleaning, exploratory data analysis (EDA), and visualization to understand the factors that influence app popularity and user engagement.

This project demonstrates practical skills in **data preprocessing, visualization, and exploratory data analysis**, which are essential for Data Science workflows.

---

## 🎯 Objectives

- Clean and preprocess raw Google Play Store data
- Handle missing and inconsistent values
- Convert data types into proper formats
- Perform Exploratory Data Analysis (EDA)
- Identify trends in app ratings and installs
- Analyze category-wise performance
- Visualize relationships between key features
- Generate insights useful for business decisions

---

## 📂 Dataset Information

The dataset used in this project contains information about mobile applications available on the Google Play Store.

### Dataset Features:

- **App** — Name of the application
- **Category** — App category
- **Rating** — User rating (0–5)
- **Reviews** — Number of user reviews
- **Size** — App size
- **Installs** — Number of downloads
- **Type** — Free or Paid
- **Price** — App price
- **Content Rating** — Target audience
- **Genres** — App genre
- **Last Updated** — Last update date
- **Current Version** — App version
- **Android Version** — Minimum Android version required

---

## 🛠️ Technologies Used

- **Programming Language:** Python 🐍  
- **Libraries Used:**
  - NumPy
  - Pandas
  - Matplotlib
  - Seaborn

---

## 📊 Project Workflow

### Step 1: Import Libraries
Essential Python libraries are imported for data manipulation and visualization.
'''python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

### Step 2: Load Dataset
The dataset is loaded using Pandas.
df = pd.read_csv("googleplaystore.csv")

### Step 3: Data Cleaning
Key preprocessing steps performed:
- Removing duplicate records
- Handling missing values
- Converting installs into numeric format
- Cleaning price column
- Fixing rating inconsistencies
- Formatting size values

### Step 4: Exploratory Data Analysis (EDA)
Various visualizations are created to understand the data.
Examples:
- Category distribution
- Rating distribution
- Install trends
- Price vs Rating
- Reviews vs Rating
- Free vs Paid app comparison

### Step 5: Data Visualization
Visualization techniques used:
- Bar Charts
- Histograms
- Scatter Plots
- Heatmaps
- Countplots
These visualizations help in identifying patterns and trends in the dataset.

### Key Insights

Some important insights discovered during analysis:
- Most apps available on the Play Store are Free apps
- Certain categories dominate the platform (e.g., Family, Games, Tools)
- Apps with more installs tend to have more reviews
- Paid apps are fewer compared to free apps
- Higher-rated apps generally receive more downloads

📌 Skills Demonstrated
This project showcases the following Data Science skills:
- Data Cleaning
- Data Preprocessing
- Exploratory Data Analysis (EDA)
- Data Visualization
- Feature Understanding
- Insight Generation

