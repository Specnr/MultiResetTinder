#Persistent
WinActivate, OBS
sleep, %switchDelay%
WinActivate, ahk_pid %pid%
send {Numpad%idx% down}
sleep, %obsDelay%
send {Numpad%idx% up}
ExitApp