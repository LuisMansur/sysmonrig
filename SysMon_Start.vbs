' SysMon_Start.vbs
' Launches SysMon tray completely silently — no console, no flash.
' Put a shortcut to this file in shell:startup for auto-start on boot.

Set objShell = CreateObject("Shell.Application")
objShell.ShellExecute "python", """" & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\tray.py""", "", "runas", 0
