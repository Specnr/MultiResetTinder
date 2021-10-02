#Persistent
SetKeyDelay, 1
ControlSend, ahk_parent, {Esc 2}{Shift Down}{Tab}{Shift Up}{Enter}, ahk_pid %pid%
ExitApp