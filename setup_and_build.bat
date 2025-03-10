@echo off
setlocal enabledelayedexpansion
title AutoLoader Setup Tool
color 0A

REM Check if we are in the correct directory
if not exist "auto_loader.py" (
    echo [WARNING] auto_loader.py not found in current directory
    echo Checking parent directory...
    cd ..
    if exist "auto_loader.py" (
        echo [OK] Found auto_loader.py in parent directory
    ) else (
        echo [ERROR] Could not find auto_loader.py
        echo Please run this script from the same directory as auto_loader.py
        pause
        exit /b 1
    )
)

echo ========================================
echo    AutoLoader Installation Tool
echo ========================================
echo.

REM Create logs directory
if not exist "logs\" mkdir logs
set LOG_FILE=logs\setup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
set LOG_FILE=%LOG_FILE: =0%

echo [%time%] Starting installation > %LOG_FILE%

REM Check Python
echo [Step 1/4] Checking Python...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
) else (
    python --version
    echo [OK] Python check passed
    echo.
)

REM Check PostgreSQL
echo [Step 2/4] Checking PostgreSQL...

REM Try multiple ways to check PostgreSQL installation
echo Checking PostgreSQL in PATH...
where psql > nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3" %%i in ('psql --version') do set PG_VERSION=%%i
    echo [OK] PostgreSQL version: %PG_VERSION% found in PATH
    goto pg_found
)

echo Checking common installation locations...
if exist "C:\Program Files\PostgreSQL" (
    echo PostgreSQL directory found at C:\Program Files\PostgreSQL
    dir "C:\Program Files\PostgreSQL" /b
    
    REM Search for psql.exe in PostgreSQL directories
    for /d %%d in ("C:\Program Files\PostgreSQL\*") do (
        if exist "%%d\bin\psql.exe" (
            echo [OK] Found PostgreSQL at: %%d\bin
            goto pg_found
        )
    )
)

:pg_not_found
echo [WARNING] PostgreSQL not detected through automatic checks
echo.
echo You have indicated that PostgreSQL is installed.
echo This could be due to:
echo 1. PostgreSQL bin directory not in PATH
echo 2. Recent PATH changes not refreshed in this command window
echo 3. PostgreSQL installed in a non-standard location
echo.
echo Options:
echo 1. Continue anyway (if you're sure PostgreSQL is installed)
echo 2. Exit and fix PATH (add PostgreSQL bin directory to PATH)
echo.
set /p pg_choice="Your choice (1 or 2): "

if "%pg_choice%"=="1" (
    echo Continuing with build process...
    goto pg_continue
) else (
    echo.
    echo To add PostgreSQL to PATH:
    echo 1. Right-click on 'This PC' or 'My Computer'
    echo 2. Select 'Properties'
    echo 3. Click 'Advanced system settings'
    echo 4. Click 'Environment Variables'
    echo 5. Under 'System variables', find and edit 'Path'
    echo 6. Add PostgreSQL bin directory (usually C:\Program Files\PostgreSQL\[version]\bin)
    echo 7. Click OK and restart command prompt
    echo.
    echo After fixing PATH, please run this script again.
    pause
    exit /b 1
)

:pg_found
echo PostgreSQL check passed
echo.

:pg_continue

REM Install Python dependencies
echo [Step 3/4] Installing Python packages...

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo [WARNING] requirements.txt not found
    echo Creating a minimal requirements.txt with essential packages...
    
    echo psycopg2-binary>=2.9.3 > requirements.txt
    echo pyinstaller>=5.6.2 >> requirements.txt
    echo pyautogui>=0.9.53 >> requirements.txt
    echo pyperclip>=1.8.2 >> requirements.txt
    echo requests>=2.27.1 >> requirements.txt
    echo pystray>=0.19.0 >> requirements.txt
    echo pillow>=9.3.0 >> requirements.txt
    echo pyserial>=3.5 >> requirements.txt
    
    echo Created minimal requirements.txt
)

echo Installing required packages...
pip install -r requirements.txt >> %LOG_FILE% 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python packages
    echo Trying to install essential packages individually...
    
    pip install psycopg2-binary >> %LOG_FILE% 2>&1
    pip install pyinstaller >> %LOG_FILE% 2>&1
    pip install pyautogui >> %LOG_FILE% 2>&1
    pip install pyperclip >> %LOG_FILE% 2>&1
    pip install pystray >> %LOG_FILE% 2>&1
    pip install pillow >> %LOG_FILE% 2>&1
    pip install requests >> %LOG_FILE% 2>&1
    pip install pyserial >> %LOG_FILE% 2>&1
    
    REM Check if PyInstaller was installed
    python -c "import PyInstaller" > nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Critical packages installation failed
        echo Please check your internet connection
        echo Or try to run: pip install pyinstaller
        pause
        exit /b 1
    ) else (
        echo [OK] Essential packages installed
    )
) else (
    echo [OK] All Python packages installed successfully
)
echo.

REM Prepare config file
if not exist "config.py" (
    if exist "config_example.py" (
        echo Creating config.py from example...
        copy config_example.py config.py >> %LOG_FILE% 2>&1
        echo [OK] config.py created
    ) else (
        echo [WARNING] config.py or config_example.py not found
        echo Creating a minimal config.py...
        
        echo # Database Configuration > config.py
        echo POSTGRES_HOST = "localhost" >> config.py
        echo POSTGRES_PORT = 5432 >> config.py
        echo POSTGRES_USERNAME = "postgres" >> config.py
        echo POSTGRES_PASSWORD = "postgres" >> config.py
        echo POSTGRES_DATABASE = "postgres" >> config.py
        echo # Serial Port Configuration >> config.py
        echo SERIAL_PORT = "COM1" >> config.py
        echo BAUDRATE = "115200" >> config.py
        
        echo [OK] Created minimal config.py
        echo Please edit config.py with your specific settings before running the application
    )
)

REM Check for required files for build
if not exist "auto_loader.py" (
    echo [ERROR] auto_loader.py not found
    echo This file is required for building the application
    echo Current directory files:
    dir /b *.py
    pause
    exit /b 1
)

REM Convert logo.jpg to icon.ico if needed
echo [INFO] Checking for logo and icon files...
if exist "logo.jpg" (
    echo [INFO] logo.jpg found, will convert to icon format
    
    REM Use direct Python command instead of creating a script
    echo Creating icon from logo.jpg...
    
    REM Delete existing convert_icon.py if it exists
    if exist "convert_icon.py" (
        del /f /q convert_icon.py > nul 2>&1
        timeout /t 1 /nobreak > nul
    )
    
    REM Use a single Python command with inline code
    python -c "from PIL import Image; img = Image.open('logo.jpg'); img.save('icon.ico', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128)]); print('Conversion successful')" > nul 2>&1
    
    if %errorlevel% neq 0 (
        echo [WARNING] Failed to convert logo.jpg to icon.ico
        echo Trying alternative method...
        
        REM Try an alternative approach with delayed execution
        timeout /t 2 /nobreak > nul
        
        REM Create the Python script through a separate temp file
        (
            echo from PIL import Image
            echo try:
            echo     img = Image.open('logo.jpg'^)
            echo     icon_sizes = [(16,16^), (32,32^), (48,48^), (64,64^), (128,128^)]
            echo     img.save('icon.ico', sizes=icon_sizes^)
            echo     print("Conversion successful"^)
            echo except Exception as e:
            echo     print(f"Error converting image: {e}"^)
            echo     import sys
            echo     sys.exit(1^)
        ) > convert_temp.py
        
        REM Copy the temp file to the final script
        move /y convert_temp.py convert_icon.py > nul 2>&1
        
        REM Wait to ensure file is released
        timeout /t 1 /nobreak > nul
        
        REM Execute the script
        python convert_icon.py
        
        if %errorlevel% neq 0 (
            echo [WARNING] Both conversion methods failed
            echo Will build without icon
            if exist "icon.ico" del /f /q icon.ico > nul 2>&1
        ) else (
            echo [OK] Successfully converted logo.jpg to icon.ico
        )
    ) else (
        echo [OK] Successfully converted logo.jpg to icon.ico
    )
)

REM Build executable
echo [Step 4/4] Building executable...
echo This may take a few minutes...

REM Clean up previous build files
echo [INFO] Cleaning up previous build files...
if exist "dist\auto_loader" (
    echo Removing old build files...
    rd /s /q "dist\auto_loader" >> %LOG_FILE% 2>&1
)
if exist "build" (
    rd /s /q "build" >> %LOG_FILE% 2>&1
)
if exist "*.spec" (
    del /f /q *.spec >> %LOG_FILE% 2>&1
)

REM Check if we have a valid icon file
if exist "icon.ico" (
    echo [INFO] Using icon.ico for application
    pyinstaller --name="auto_loader" --windowed --icon=icon.ico --add-data="icon.ico;." --add-data="config.py;." auto_loader.py -y >> %LOG_FILE% 2>&1
    
    REM Check if beep.wav exists before adding it
    if exist "beep.wav" (
        echo [INFO] Adding beep.wav resource
        pyinstaller --name="auto_loader" --windowed --icon=icon.ico --add-data="icon.ico;." --add-data="config.py;." --add-data="beep.wav;." auto_loader.py -y >> %LOG_FILE% 2>&1
    ) else (
        echo [INFO] beep.wav not found, building without it
        pyinstaller --name="auto_loader" --windowed --icon=icon.ico --add-data="icon.ico;." --add-data="config.py;." auto_loader.py -y >> %LOG_FILE% 2>&1
    )
) else (
    echo [INFO] Building without custom icon
    
    REM Check if beep.wav exists before adding it
    if exist "beep.wav" (
        echo [INFO] Adding beep.wav resource
        pyinstaller --name="auto_loader" --windowed --add-data="config.py;." --add-data="beep.wav;." auto_loader.py -y >> %LOG_FILE% 2>&1
    ) else (
        echo [INFO] beep.wav not found, building without resources
        pyinstaller --name="auto_loader" --windowed --add-data="config.py;." auto_loader.py -y >> %LOG_FILE% 2>&1
    )
)

if %errorlevel% neq 0 (
    echo [ERROR] Build failed
    echo Checking for issues...
    
    python -c "import PyInstaller" > nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] PyInstaller not properly installed
        echo Try running: pip install pyinstaller --upgrade
    )
    
    echo Check %LOG_FILE% for detailed error information
    echo.
    type %LOG_FILE%
    echo.
    pause
    exit /b 1
)

REM Copy configuration files to dist directory
echo [INFO] Setting up configuration files...
echo [%time%] Setting up configuration files... >> %LOG_FILE%

REM Ensure dist\auto_loader directory exists
if not exist "dist\auto_loader" (
    echo [WARNING] dist\auto_loader directory not found
    echo Creating directory...
    mkdir "dist\auto_loader" >> %LOG_FILE% 2>&1
)

REM Copy or create config.py
if exist "config.py" (
    echo [INFO] Copying existing config.py...
    copy /Y "config.py" "dist\auto_loader\config.py" >> %LOG_FILE% 2>&1
) else (
    echo [INFO] Creating new config.py...
    (
        echo # Database Configuration
        echo POSTGRES_HOST = "localhost"
        echo POSTGRES_PORT = 5432
        echo POSTGRES_USERNAME = "postgres"
        echo POSTGRES_PASSWORD = "postgres"
        echo POSTGRES_DATABASE = "postgres"
        echo # Serial Port Configuration
        echo SERIAL_PORT = "COM1"
        echo BAUDRATE = "115200"
    ) > "dist\auto_loader\config.py"
)

REM Create update_config.bat
echo [INFO] Creating configuration update tool...
echo @echo off > "dist\auto_loader\update_config.bat"
echo chcp 65001 > nul >> "dist\auto_loader\update_config.bat"
echo setlocal enabledelayedexpansion >> "dist\auto_loader\update_config.bat"
echo title AutoLoader Configuration Tool >> "dist\auto_loader\update_config.bat"
echo color 0A >> "dist\auto_loader\update_config.bat"
echo. >> "dist\auto_loader\update_config.bat"
echo :menu >> "dist\auto_loader\update_config.bat"
echo cls >> "dist\auto_loader\update_config.bat"
echo echo ======================================== >> "dist\auto_loader\update_config.bat"
echo echo    AutoLoader Configuration Tool >> "dist\auto_loader\update_config.bat"
echo echo ======================================== >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo Checking available COM ports... >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo for /f "tokens=1,2*" %%%%a in ('reg query HKLM\HARDWARE\DEVICEMAP\SERIALCOMM 2^^^>nul') do ( >> "dist\auto_loader\update_config.bat"
echo    echo     %%%%c is available >> "dist\auto_loader\update_config.bat"
echo ) >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo Current configuration: >> "dist\auto_loader\update_config.bat"
echo echo ---------------------------------------- >> "dist\auto_loader\update_config.bat"
echo type config.py >> "dist\auto_loader\update_config.bat"
echo echo ---------------------------------------- >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo Options: >> "dist\auto_loader\update_config.bat"
echo echo [1] Use current config.py >> "dist\auto_loader\update_config.bat"
echo echo [2] Edit config.py >> "dist\auto_loader\update_config.bat"
echo echo [3] Exit >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo set /p choice="Enter your choice (1-3): " >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo if "%%choice%%"=="1" goto use_current >> "dist\auto_loader\update_config.bat"
echo if "%%choice%%"=="2" goto edit_config >> "dist\auto_loader\update_config.bat"
echo if "%%choice%%"=="3" goto end >> "dist\auto_loader\update_config.bat"
echo echo Invalid choice. Please try again. >> "dist\auto_loader\update_config.bat"
echo pause >> "dist\auto_loader\update_config.bat"
echo goto menu >> "dist\auto_loader\update_config.bat"
echo. >> "dist\auto_loader\update_config.bat"
echo :edit_config >> "dist\auto_loader\update_config.bat"
echo copy /Y config.py config.py.bak ^> nul 2^>^&1 >> "dist\auto_loader\update_config.bat"
echo if exist config.py.bak ( >> "dist\auto_loader\update_config.bat"
echo    echo [OK] Backup created: config.py.bak >> "dist\auto_loader\update_config.bat"
echo ) else ( >> "dist\auto_loader\update_config.bat"
echo    echo [WARNING] Failed to create backup >> "dist\auto_loader\update_config.bat"
echo ) >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo Opening config.py in Notepad... >> "dist\auto_loader\update_config.bat"
echo echo NOTE: Do not close this window while editing. >> "dist\auto_loader\update_config.bat"
echo start /wait notepad config.py >> "dist\auto_loader\update_config.bat"
echo goto verify_config >> "dist\auto_loader\update_config.bat"
echo. >> "dist\auto_loader\update_config.bat"
echo :use_current >> "dist\auto_loader\update_config.bat"
echo echo Using current configuration. >> "dist\auto_loader\update_config.bat"
echo goto verify_config >> "dist\auto_loader\update_config.bat"
echo. >> "dist\auto_loader\update_config.bat"
echo :verify_config >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo Verifying configuration... >> "dist\auto_loader\update_config.bat"
echo echo ---------------------------------------- >> "dist\auto_loader\update_config.bat"
echo type config.py >> "dist\auto_loader\update_config.bat"
echo echo ---------------------------------------- >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo Testing COM port access... >> "dist\auto_loader\update_config.bat"
echo for /f "tokens=2 delims==" %%%%a in ('findstr /i "SERIAL_PORT" config.py') do ( >> "dist\auto_loader\update_config.bat"
echo    set "PORT=%%%%a" >> "dist\auto_loader\update_config.bat"
echo    set "PORT=%%PORT: =%%" >> "dist\auto_loader\update_config.bat"
echo    set "PORT=%%PORT:"=%%" >> "dist\auto_loader\update_config.bat"
echo    echo Checking port %%PORT%%... >> "dist\auto_loader\update_config.bat"
echo    mode %%PORT%% ^> nul 2^>^&1 >> "dist\auto_loader\update_config.bat"
echo    if errorlevel 1 ( >> "dist\auto_loader\update_config.bat"
echo        echo [WARNING] Could not access %%PORT%% >> "dist\auto_loader\update_config.bat"
echo        echo Please check if the port exists and is not in use >> "dist\auto_loader\update_config.bat"
echo    ) else ( >> "dist\auto_loader\update_config.bat"
echo        echo [OK] %%PORT%% is accessible >> "dist\auto_loader\update_config.bat"
echo    ) >> "dist\auto_loader\update_config.bat"
echo ) >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo Configuration update completed. >> "dist\auto_loader\update_config.bat"
echo echo The new settings will take effect when you restart the application. >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo [1] Return to main menu >> "dist\auto_loader\update_config.bat"
echo echo [2] Exit >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo set /p next_action="Enter your choice (1-2): " >> "dist\auto_loader\update_config.bat"
echo if "%%next_action%%"=="1" goto menu >> "dist\auto_loader\update_config.bat"
echo if "%%next_action%%"=="2" goto end >> "dist\auto_loader\update_config.bat"
echo echo Invalid choice. Please try again. >> "dist\auto_loader\update_config.bat"
echo pause >> "dist\auto_loader\update_config.bat"
echo goto verify_config >> "dist\auto_loader\update_config.bat"
echo. >> "dist\auto_loader\update_config.bat"
echo :end >> "dist\auto_loader\update_config.bat"
echo echo. >> "dist\auto_loader\update_config.bat"
echo echo Thank you for using AutoLoader Configuration Tool >> "dist\auto_loader\update_config.bat"
echo pause >> "dist\auto_loader\update_config.bat"
echo exit >> "dist\auto_loader\update_config.bat"

echo.
echo ========================================
echo    Build completed!
echo    Executable is in 'dist\auto_loader' folder
echo ========================================
echo.
echo Post-installation notes:
echo 1. Make sure config.py has correct PostgreSQL settings:
echo    - POSTGRES_HOST (localhost or your server IP)
echo    - POSTGRES_PORT (default: 5432)
echo    - POSTGRES_USERNAME 
echo    - POSTGRES_PASSWORD
echo    - POSTGRES_DATABASE
echo 2. Use update_config.bat to modify configuration after deployment
echo.
echo Log file: %LOG_FILE%
echo.
pause
exit /b 0 