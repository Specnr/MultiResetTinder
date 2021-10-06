#Persistent
WinGetTitle, title, ahk_pid %pid%
if InStr(title, "-") && !InStr(title, "Instance") { ; - implies youre in the game, instance has - but is on title
  inGame := True
} else {
  inGame := False
}
FileAppend, %inGame%, *
ExitApp