@Echo Off
echo Installing...
Set "VIRTUAL_ENV=venv"
If Not Exist "%VIRTUAL_ENV%\Scripts\activate.bat" (
    python -m venv %VIRTUAL_ENV%
)
If Not Exist "%VIRTUAL_ENV%\Scripts\activate.bat" (
    echo "Installation Failed. Please try again!"
    Exit /B 1
)
Call "%VIRTUAL_ENV%\Scripts\activate.bat"
python -m pip install --upgrade pip
"%VIRTUAL_ENV%\Scripts\pip.exe" install -r requirements.txt
echo Installed successfully!
echo Close?
pause
Exit /B 0