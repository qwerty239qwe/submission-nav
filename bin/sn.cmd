@echo off
setlocal
set "SN_HOME=%~dp0.."
uv run --project "%SN_HOME%\scripts" sn %*
