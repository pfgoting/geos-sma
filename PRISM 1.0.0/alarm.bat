@echo off
set /a count=0
:loop
start "" /wait /min sounds.vbs 
set /a count=count+1
if "%count%" == "4" (
  goto end
) else (
  goto loop
)	
:end
