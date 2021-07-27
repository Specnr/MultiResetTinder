#Persistent
; Exit World
SetKeyDelay, 1
ControlSend, ahk_parent, {Shift Down}{Tab}{Shift Up}{Enter}, ahk_pid %pid%
ExitApp