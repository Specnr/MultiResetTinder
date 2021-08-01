#Persistent
RunHide(Command)
{
  dhw := A_DetectHiddenWindows
  DetectHiddenWindows, On
  Run, %ComSpec%,, Hide, cPid
  WinWait, ahk_pid %cPid%
  DetectHiddenWindows, %dhw%
  DllCall("AttachConsole", "uint", cPid)

  Shell := ComObjCreate("WScript.Shell")
  Exec := Shell.Exec(Command)
  Result := Exec.StdOut.ReadAll()

  DllCall("FreeConsole")
  Process, Close, %cPid%
  Return Result
}

GetInstanceNum(pid)
{
  inst := -1
  command := Format("powershell.exe $x = Get-WmiObject Win32_Process -Filter \""ProcessId = {1}\""; $x.CommandLine", pid)
  rawOut := RunHide(command)
  strArr := MultiMC ? StrSplit(rawOut, "-") : StrSplit(rawOut, "--")
  for i, item in strArr {
    if (MultiMC) {
      if (InStr(item, "Djava.library.path")) {
        item := RTrim(item)
        StringRight, tmp, item, 9
        StringLeft, inst, tmp, 1
        break
      }
    } else {
      if (InStr(item, "gameDir")) {
        item := RTrim(item)
        StringRight, inst, item, 1
        break
      }
    }
  }
  return inst
}

orderedPIDs := []
loop, %instances%
  orderedPIDs.Push(-1)
WinGet, all, list
Loop, %all%
{
  WinGet, pid, PID, % "ahk_id " all%A_Index%
  WinGetTitle, title, ahk_pid %pid%
  if (InStr(title, "Minecraft*") && !InStr(title, "Not Responding"))
    Output .= pid "`n"
}
tmpPids := StrSplit(Output, "`n")
for i, pid in tmpPids {
  if (pid) {
    inst := GetInstanceNum(pid)
    orderedPIDs[inst] := pid
  }
}

PIDs := ""
For i, pid In orderedPIDs
  PIDs .= pid . "|"
PIDs := RTrim(PIDs, "|")

FileAppend, %PIDs%, *
ExitApp