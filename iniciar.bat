@echo off
echo Iniciando o sistema financeiro do restaurante...
call venv\Scripts\activate
streamlit run app_financeiro.py
pause