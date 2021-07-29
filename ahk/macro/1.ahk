#Persistent
; Exit World
SetKeyDelay, 1
ControlSend, ahk_parent, {Tab 9}{Enter}, ahk_pid %pid%
ExitApp