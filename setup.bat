@echo off
echo Criando o ambiente virtual...
python -m venv venv

echo Ativando o ambiente e instalando as dependencias...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install streamlit pandas plotly openpyxl fpdf pyTelegramBotAPI

echo.
echo Tudo pronto! O ambiente foi configurado com sucesso.
pause