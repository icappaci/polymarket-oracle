' Silent launcher for update_and_push.ps1.
' WScript.Shell.Run(..., 0, False) launches PowerShell with truly
' hidden window (0 = hide) and async (False = don't block on exit).
' This avoids the brief flash of a PowerShell console window that
' happens every minute when Task Scheduler runs `powershell.exe`
' directly, even with -WindowStyle Hidden.

Dim shell, scriptDir, ps1Path, cmd
Set shell = CreateObject("WScript.Shell")

' Resolve script's own directory so the .ps1 path stays relative.
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
ps1Path = scriptDir & "\update_and_push.ps1"

cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ps1Path & """"

' Run hidden (0) and don't wait for it (False = async)
shell.Run cmd, 0, False
