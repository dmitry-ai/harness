@echo off
set "GIT_OPTIONAL_LOCKS=0"
python "%~dp0..\git_shim.py" %*
exit /b %ERRORLEVEL%
