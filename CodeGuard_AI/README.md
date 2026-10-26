# 🛡️ CodeGuard AI — Intelligent Code Analysis & Review

[![Live Demo](https://img.shields.io/badge/Live-Demo-success?style=for-the-badge&logo=streamlit)](https://datascience-codeguardai.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Web_App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)

## Project Overview

CodeGuard AI is an AI-powered code analysis application designed to help developers identify potential programming errors, understand code quality issues, and improve code reliability. The platform aims to simplify code review by providing intelligent analysis and actionable feedback through an interactive web interface.

By combining Artificial Intelligence with software development practices, CodeGuard AI helps developers understand potential issues, improve code readability, and write more maintainable code.

**Live Demo:** https://datascience-codeguardai.streamlit.app/

## Objectives

- Automate code analysis and review.
- Identify potential bugs and programming issues.
- Improve code readability and maintainability.
- Provide actionable suggestions for code improvement.
- Simplify the debugging and code review process.
- Demonstrate the practical application of AI in software development.

## Problem Statement

Manual code reviews and debugging can be time-consuming, particularly when identifying logical errors, reviewing complex code, and maintaining consistent coding practices.

CodeGuard AI aims to streamline this process by providing an interactive platform for analyzing source code and presenting useful feedback, helping developers identify areas that may require attention.

## Key Features

### 🔍 Intelligent Code Analysis
Analyze submitted source code to identify potential issues and areas for improvement.

### 🐞 Bug Detection
Assist in identifying potential programming errors and logical issues that may affect code execution.

### 🔒 Security Analysis
Help identify potentially unsafe coding patterns and security-related concerns.

### 💡 Code Improvement Suggestions
Provide recommendations to improve code structure, readability, and maintainability.

### 🤖 AI-Powered Insights
Use AI-assisted analysis to explain code issues and help developers understand possible solutions.

### 🖥️ Interactive Web Interface
Access code analysis capabilities through a user-friendly Streamlit application.

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Web Framework | Streamlit |
| Artificial Intelligence | AI-assisted code analysis |
| Data Processing | Python-based processing |
| Development Tools | VS Code, Git, GitHub |
| Deployment | Streamlit Community Cloud |

*The exact AI provider, supporting libraries, and analysis techniques should be documented according to the project's implementation.*

## Application Workflow

1. **Code Input:** Provide source code for analysis through the application.
2. **Code Processing:** Process the submitted code for analysis.
3. **Issue Identification:** Examine potential errors and areas of concern.
4. **AI-Assisted Review:** Generate explanations and improvement suggestions where supported.
5. **Results Presentation:** Display analysis results through the application interface.
6. **Code Improvement:** Use the feedback to review and improve the source code.

## Application Screenshots

Screenshots provide a visual overview of the application's interface and functionality.

### 1. Home Page
![CodeGuard AI Home Page](images/home_page.png)

### 2. Code Analysis
![CodeGuard AI Code Analysis](images/code_analysis.png)

### 3. Analysis Results
![CodeGuard AI Analysis Results](images/analysis_results.png)

### 4. Code Review and Suggestions
![CodeGuard AI Code Review](images/code_review.png)

> Replace these image paths with screenshots captured from the actual application. Remove any section for which a corresponding screenshot or feature is unavailable.

## Project Structure

```text
CodeGuard_AI/
│
├── app.py
├── requirements.txt
├── README.md
├── images/
│   ├── home_page.png
│   ├── code_analysis.png
│   ├── analysis_results.png
│   └── code_review.png
│
└── [Additional project modules]
```

*Update the structure to match the actual files and folders in your repository.*

## Installation and Setup

### Prerequisites

- Python 3.x
- pip
- Git
- Any API credentials required by the configured AI provider, if applicable

### 1. Clone the Repository

```bash
git clone https://github.com/jasika1909/DataScience.git
```

### 2. Navigate to the Project Directory

```bash
cd DataScience/CodeGuard_AI
```

### 3. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
```

Activate the environment on Windows:

```bash
venv\Scripts\activate
```

On macOS or Linux:

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

If the application requires an AI API key, configure it using the environment variable name expected by the project. Do not commit API keys or other secrets to GitHub.

### 6. Run the Application

```bash
streamlit run app.py
```

Open the local URL displayed in the terminal to access the application.

## Use Cases

- Reviewing code during development.
- Identifying potential programming errors.
- Understanding code quality concerns.
- Exploring security-related coding risks.
- Learning better programming practices.
- Supporting software debugging and maintenance.

## Limitations

- AI-generated findings may include false positives or miss certain issues.
- Suggestions should be reviewed and tested before implementation.
- Automated analysis does not replace comprehensive security testing, code review, or execution-based testing.
- Results depend on the capabilities and configuration of the underlying analysis system.

## Future Enhancements

- Support for additional programming languages.
- Advanced static code analysis.
- Automated code correction and validation.
- Code complexity analysis.
- Downloadable code review reports.
- Integration with GitHub repositories.
- Unit test generation and validation.
- Expanded security vulnerability detection.

## Learning Outcomes

This project demonstrates practical exploration of:

- AI-assisted software development.
- Python application development.
- Interactive web application design.
- Code quality and debugging concepts.
- Software security awareness.
- Application deployment and version control.

## Author

**Jasika Awasthi**

B.Tech CSE — Data Science & Artificial Intelligence

GitHub: https://github.com/jasika1909

LinkedIn: https://www.linkedin.com/in/jasika-awasthi-608037311/

## Project Links

- **Live Application:** https://datascience-codeguardai.streamlit.app/
- **GitHub Repository:** https://github.com/jasika1909/DataScience/tree/main/CodeGuard_AI

---

*CodeGuard AI — Making code review more accessible through intelligent analysis.*
