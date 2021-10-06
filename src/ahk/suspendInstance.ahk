#Persistent
hProcess := DllCall("OpenProcess", "UInt", 0x1F0FFF, "Int", 0, "Int", pid)
If (hProcess) {
  DllCall("ntdll.dll\NtSuspendProcess", "Int", hProcess)
  DllCall("SetProcessWorkingSetSize", "UInt", hProcess, "Int", -1, "Int", -1)
  DllCall("CloseHandle", "Int", hProcess)
}
ExitApp