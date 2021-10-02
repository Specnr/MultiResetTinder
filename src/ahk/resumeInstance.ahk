#Persistent
hProcess := DllCall("OpenProcess", "UInt", 0x1F0FFF, "Int", 0, "Int", pid)
If (hProcess) {
  DllCall("ntdll.dll\NtResumeProcess", "Int", hProcess)
  DllCall("CloseHandle", "Int", hProcess)
}
ExitApp