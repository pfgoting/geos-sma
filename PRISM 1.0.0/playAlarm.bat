@echo off
set "file=audio2.mp3"
( echo Set Sound = CreateObject("WMPlayer.OCX.7"^)
  echo Sound.URL = "%file%"
  echo Sound.Controls.play
  echo do while Sound.currentmedia.duration = 0
  echo wscript.sleep 100
  echo loop
  echo wscript.sleep (int(Sound.currentmedia.duration^)+1^)*1000) >sound.vbs
set /a count=0
:loop
start "" /wait /min sound.vbs 
set /a count=count+1
if "%count%" == "4" (
  goto end
) else (
  goto loop
)	
:end
pause