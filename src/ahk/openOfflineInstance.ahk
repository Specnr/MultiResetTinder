#SingleInstance, Force
SendMode Input
CoordMode, Mouse, Screen
SetKeyDelay, 0

; Open MMC, have all instances next to each other in a row, and highlight the first one

; Launch Offline: 1200, 235
instances := 4
WinActivate, MultiMC
WinMove, A,,0,0,1280,720
Loop, %instances% {
  Send, {Click 1200, 235} ; Launch Offline
  slp := 150 * A_Index
  sleep, %slp%
  Send, {Enter} ; Select Name
  sleep, 50
  Send, {Right} ; Hit Next
  sleep, 10
}