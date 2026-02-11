@echo off
wmic process where "name='node.exe'" get commandline > procs.txt
type procs.txt | findstr "listener.js"
if %errorlevel%==0 (
    echo BAILEYS_IS_RUNNING
) else (
    echo BAILEYS_NOT_RUNNING
)
del procs.txt
