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
<img width="975" height="796" alt="image" src="https://github.com/user-attachments/assets/2fd4b98c-39c5-4c49-a857-f3c23894fbd1" />

<img width="1917" height="907" alt="image" src="https://github.com/user-attachments/assets/f91d8810-22cf-4cf8-824c-9d673f878ec1" />

### 2. Code Analysis
<img width="1917" height="871" alt="image" src="https://github.com/user-attachments/assets/fc73cf85-38ba-496d-8f39-a83699640132" />

### 3. Analysis Results
<img width="1917" height="818" alt="image" src="https://github.com/user-attachments/assets/f8074090-f546-46c7-9c73-4ef4824ef458" />

<img width="1917" height="877" alt="image" src="https://github.com/user-attachments/assets/778e7c8d-1c36-4a10-a1a3-c3c6e846623a" />

### 4. Code Review and Suggestions
<img width="1917" height="805" alt="image" src="https://github.com/user-attachments/assets/dd50bbf7-3441-43b7-944b-0afd2bd13da8" />

### 5. Teacher Dashboard
<img width="1917" height="867" alt="image" src="https://github.com/user-attachments/assets/eb04f8ef-a652-4d03-84a2-c19617ec2ed1" />

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
