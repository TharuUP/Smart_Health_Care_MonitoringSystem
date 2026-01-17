@echo off
REM ==============================================
REM Activate virtual environment
REM ==============================================
cd /d "D:\Project 101\SmartHealthProject"
call venv\Scripts\activate.bat

REM ==============================================
REM Run Django project
REM ==============================================
cd /d "D:\Project 101\SmartHealthProject\health_project"
start cmd /k "python manage.py runserver"

REM ==============================================
REM Run your bot script
REM ==============================================
start cmd /k "python run_bot.py"

REM ==============================================
REM Keep this window open
REM ==============================================
pause
