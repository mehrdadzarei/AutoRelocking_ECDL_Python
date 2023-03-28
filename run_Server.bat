

@echo off
@REM set path of activeate.bat file
call C:\Users\srcal\anaconda3\Scripts\activate.bat

@REM set the path which you save the Server.py file
cd C:\Users\UMK\Documents\cavity_progs\py-ws7\Mehrdad

@REM args: dllpath(wavemeter) Wavemeter_Version 
python AutoRelocking.py "C:\Windows\System32\wlmData.dll" 491

@pause