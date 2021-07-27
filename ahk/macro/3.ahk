#Persistent
; World Selection Screen
SetKeyDelay, delay
ControlSend, ahk_parent, {Tab}{Enter}, ahk_pid %pid% 
ExitApp