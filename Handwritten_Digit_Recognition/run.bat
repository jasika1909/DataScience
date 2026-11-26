@echo off
REM One-click launcher for Windows: install -> train (only if needed) -> run app
cd /d "%~dp0"

echo [1/3] Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Installation failed. Check your Python version ^(3.9 - 3.12^) and internet.
    pause
    exit /b 1
)

if not exist "model\digit_model.keras" (
    echo [2/3] Trained model not found. Training now ^(a few minutes^)...
    python train.py
    if errorlevel 1 (
        echo Training failed. See the error above.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Trained model found. Skipping training.
)

echo [3/3] Starting the Streamlit app...
python -m streamlit run app.py
pause
