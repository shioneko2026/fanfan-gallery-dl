@echo off
echo Starting FanFan Gallery-DL...
echo.
python main.py
echo.
echo ===========================================
if errorlevel 1 (
    echo Error occurred! Check the error above.
) else (
    echo GUI closed normally.
)
echo ===========================================
pause
