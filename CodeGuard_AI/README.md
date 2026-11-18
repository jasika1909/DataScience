# 🛡️ AI-Based Code Plagiarism Detector | CodeGuard AI

\<p align="center">   \<strong>Intelligent Code Similarity & Plagiarism Analysis Platform\</strong> \</p>

\<p align="center">   Detect code similarities, identify matching code blocks, and analyze potential plagiarism across multiple programming languages. \</p>

\<p align="center">   \<a href="[https://datascience-codeguardai.streamlit.app/](https://datascience-codeguardai.streamlit.app/)">🚀 Live Demo\</a> •   \<a href="[https://github.com/jasika1909/DataScience/tree/main/CodeGuard_AI](https://github.com/jasika1909/DataScience/tree/main/CodeGuard_AI)">📂 GitHub Repository\</a> \</p>

---

## 📌 Project Overview

**CodeGuard AI** is a Python and Streamlit-based code plagiarism detection platform designed to identify similarities between source-code submissions. It uses multiple code comparison techniques, including token-based matching, TF-IDF similarity, syntax-tree analysis, and semantic logic comparison.

The platform supports individual and batch code analysis, highlights matching code sections, explains similarity scores, and generates downloadable PDF and CSV reports. It also provides classroom-oriented features such as teacher and student accounts, assignment management, and submission analysis.

## 🎯 Objectives

- Detect potential code plagiarism across programming assignments.
- Identify similarities despite variable renaming and code reformatting.
- Analyze structural and logical similarities between programs.
- Support batch comparison of multiple code submissions.
- Provide similarity scores and detailed comparison reports.
- Simplify code evaluation through an interactive dashboard.

## ✨ Key Features

- **Multi-Language Support:** Analyze Python, Java, C, C++, and JavaScript source code.
- **Multiple Similarity Techniques:** Combines seven signals, including exact-line matching, token n-grams, TF-IDF cosine similarity, sequence matching, block coverage, AST analysis, and semantic similarity.
- **Semantic Similarity Detection:** Identifies similar programming logic even when variable names, loop styles, or programming languages differ.
- **Code Highlighting:** Displays matching code blocks with color-coded highlights and line numbers.
- **Batch Analysis:** Compare multiple submissions simultaneously and identify highly similar pairs.
- **Similarity Heatmap:** Visualize similarity relationships between submitted programs.
- **Detailed Analysis:** View similarity scores, risk levels, matched blocks, unique code sections, and explanations.
- **Report Generation:** Export analysis results in PDF and CSV formats.
- **Classroom Management:** Teacher and student accounts, assignment creation, submission management, and role-based access.
- **Comparison History:** Access previous analysis results and reports.

## 🛠️ Technologies Used

| Category             | Technologies                                 |
| -------------------- | -------------------------------------------- |
| Programming Language | Python                                       |
| Frontend / UI        | Streamlit                                    |
| Data Processing      | Pandas                                       |
| Visualization        | Plotly                                       |
| Code Analysis        | Python AST, Tokenization                     |
| Similarity Analysis  | TF-IDF, Cosine Similarity, Sequence Matching |
| Code Comparison      | Greedy String Tiling, Semantic Analysis      |
| Database             | SQLite                                       |
| Report Generation    | ReportLab, CSV                               |
| Testing              | Python Unittest                              |

## 🖥️ Application Screenshots

### 1. Code Comparison Workspace

Upload source-code files, paste code snippets, or load sample programs to begin similarity analysis.



### 2. Semantic Similarity Analysis

Identify similar programming logic even when code is written using different styles or programming languages.



### 3. Batch Analysis

Analyze multiple submissions, rank similar code pairs, and visualize relationships through a similarity heatmap.



### 4. Detailed PDF Report

Generate detailed reports containing similarity scores, analysis explanations, visualizations, and matched code snippets.



### 5. PDF Report Summary

View a summarized representation of the code comparison results.



## ⚙️ How It Works

1. **Upload Code:** Upload source files, ZIP archives, paste code snippets, or use sample submissions.
2. **Select Comparisons:** Choose individual file pairs or analyze all available pairs.
3. **Analyze Similarity:** The system applies multiple comparison techniques to identify matching patterns.
4. **Review Results:** Explore similarity scores, risk levels, highlighted code blocks, and explanations.
5. **Generate Reports:** Download detailed comparison results in PDF or CSV format.

## 📂 Project Structure

```text
CodeGuard_AI/
│
├── app.py
├── config.py
├── reset_password.py
├── requirements.txt
│
├── assets/
│   ├── logo.svg
│   └── styles.css
│
├── data/
│   └── codeguard.db
│
├── docs/
│   └── screenshots/
│       ├── workspace.png
│       ├── semantic.png
│       ├── batch.png
│       ├── pdf-detail.png
│       └── pdf-summary.png
│
├── samples/
│
├── src/
│   ├── accounts.py
│   ├── ast_analyzer.py
│   ├── batch.py
│   ├── boilerplate.py
│   ├── charts.py
│   ├── code_normalizer.py
│   ├── code_viewer.py
│   ├── database.py
│   ├── file_handler.py
│   ├── models.py
│   ├── report_generator.py
│   ├── semantic.py
│   ├── similarity_engine.py
│   ├── structure_analyzer.py
│   └── ui_components.py
│
├── views/
│   ├── about.py
│   ├── account.py
│   ├── assignments.py
│   ├── comparison_history.py
│   ├── compare_code.py
│   ├── dashboard.py
│   ├── home.py
│   ├── login.py
│   └── results.py
│
└── tests/
```

## 🚀 Installation and Setup

### Prerequisites

- Python 3.12 recommended
- Git
- pip

### 1. Clone the Repository

```bash
git clone https://github.com/jasika1909/DataScience.git
```

### 2. Navigate to the Project Directory

```bash
cd DataScience/CodeGuard_AI
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

**Windows:**

```bash
venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Run the Application

```bash
python -m streamlit run app.py
```

Open your browser and visit:

```text
http://localhost:8501
```

## 🧪 Testing

Run the automated test suite from the project directory:

```bash
python -m unittest discover -s tests -t . -v
```

The tests cover important application components, including file validation, similarity analysis, semantic and structural comparison, reports, database operations, and account management.

## 🔐 Security & Privacy

- Uploaded source-code files are analyzed as text and are never executed.
- Passwords are stored using salted PBKDF2-HMAC-SHA256 hashing.
- Login attempts are protected through account lockout mechanisms.
- User sessions expire after inactivity.
- Role-based access controls protect teacher and student data.
- ZIP uploads are validated with file-size, entry-count, and compression-ratio limits.

**Note:** Similarity scores are indicators for human review, not definitive proof of plagiarism. Results should always be evaluated alongside the highlighted code and assignment context.

## ⚠️ Limitations

- The analysis engine uses lexical, structural, and rule-based semantic techniques; it does not use a neural network or LLM for plagiarism detection.
- Java, C, C++, and JavaScript structural analysis uses lightweight parsers rather than complete compiler grammars.
- Common algorithms, templates, and short programs may produce high similarity scores.
- Similarity scores cannot independently establish plagiarism.

## 🔮 Future Enhancements

- Support for additional programming languages.
- Advanced visualization of code similarity patterns.
- Enhanced plagiarism detection for larger code repositories.
- More detailed analytics and reporting.
- Improved assignment evaluation and classroom workflows.

## 👩‍💻 Author

**Jasika Awasthi**

B.Tech | Computer Science Engineering (Data Science & Artificial Intelligence)

- **GitHub:** [jasika1909](https://github.com/jasika1909)
- **LinkedIn:** [Jasika Awasthi](https://www.linkedin.com/in/jasika-awasthi-608037311/)


\<p align="center">   ⭐ If you find this project useful, consider giving the repository a star! \</p>
