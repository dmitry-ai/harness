@echo off
REM 2026-10-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
set "GIT_OPTIONAL_LOCKS=0"
REM 2026-10-24
REM "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
REM https://github.com/dmitry-ai/harness/issues/17
python "%~dp0..\git_shim.py" %*
exit /b %ERRORLEVEL%
