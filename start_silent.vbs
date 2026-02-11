Set WshShell = CreateObject("WScript.Shell")
currentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "py """ & currentDir & "\backend\main.py""", 0
Set WshShell = Nothing
