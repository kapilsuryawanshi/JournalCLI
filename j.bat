@echo off
REM cls
set APP_DIR=E:\Documents\04 My Personal Stuff\01 Kapil\05 MyApplications\JournalCLI

REM Save the current directory
set OLDDIR=%cd%

REM Change into target directory
cd /d "%APP_DIR%"

REM Do your work here
REM echo Now inside: %cd%

REM Run your Python script with arguments passed to the batch file
python jrnl_app.py %*

REM Go back to the original directory
cd /d "%OLDDIR%"
REM echo Back to: %cd%