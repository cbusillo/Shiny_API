@echo off
REM If Winget is not installed use the Microsoft Store to install App Installer
REM powershell -ep bypass -command "(new-object net.webclient).DownloadFile('https://raw.githubusercontent.com/cbusillo/Shiny_API/main/install_client.bat','local.bat') | ./local.bat"

cd %userprofile%
set APPNAME="Shiny_API"
set PYTHONVERSION=10
set "PYTHONROOT=%LOCALAPPDATA%\Programs\Python"
for /d %%d in (%PYTHONROOT%\Python3%REQVERSION%*) do (set "PYTHONVERSION=%%d" & goto break)
:break
set "PYTHON=%PYTHONVERSION%\python"
set "PATH=%PYTHONVERSION%;%PROGRAMFILES%\tesseract-ocr;%PATH%"

tasklist | find /i "python3.exe" && taskkill /im "python3.exe" /F || echo process "python3.exe" not running

%PYTHON% --version
if %errorlevel% NEQ 0 (
	winget install --silent  --accept-package-agreements --accept-source-agreements python3.%PYTHONVERSION%
	echo "Restarting script."
	%0
	exit
)

if not exist "%PROGRAMFILES%\Tesseract-OCR" (
	winget install --silent  --accept-package-agreements --accept-source-agreements tesseract-ocr
)

%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install --upgrade %APPNAME%

%PYTHON% -m shiny_api.main