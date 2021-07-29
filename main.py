import helpers as hlp
import json
import sched
import time
import os
import keyboard as kb
from pathlib import Path
from datetime import datetime


# Load settings
LOOP_DELAY = 0.01
with open("./settings.json", "r") as f:
    settings = json.load(f)
Path(settings["old-worlds"]).mkdir(parents=True, exist_ok=True)
SCHEDULER = sched.scheduler(time.time, time.sleep)

# Instance states
dead_instances = [hlp.Instance(-1, i+1, settings["mc-folders"][i])
                  for i in range(len(settings["mc-folders"]))]
free_instances = []
macro_instances = []
gen_instances = []
ready_instances = []
approved_instances = []

listening = True
active_instance = None
focused_instance = None
list_with_focussed = None


def main_loop(sc):
    global active_instance
    global focused_instance
    global list_with_focussed

    # Handle free instances
    j = 0
    instances_against_cap = len(macro_instances) + len(gen_instances)
    for i in range(len(free_instances)):
        if instances_against_cap < settings["max-concurrent-gen"]:
            if free_instances[j].is_in_title():
                free_instances[j].reset_state = 2
                free_instances[j].resume()
            macro_instances.append(free_instances.pop(j))
            instances_against_cap += 1
        elif not free_instances[j].is_suspended:
            free_instances[j].suspend()
            j += 1
        else:
            j += 1

    # Handle macro instances
    j = 0
    for i in range(len(macro_instances)):
        if macro_instances[j].reset_state == 0:
            macro_instances[j].resume()
            macro_instances[j].reset_state += 1
        for i in range(1, 6):
            if macro_instances[j].reset_state == i:
                hlp.run_ahk(f"/macro/{i}",
                            pid=macro_instances[j].PID, delay=settings["delay"])
                macro_instances[j].reset_state += 1
                break
        if macro_instances[j].reset_state == 6:
            macro_instances[j].move_worlds(settings["old-worlds"])
            macro_instances[j].first_reset = False
            gen_instances.append(macro_instances.pop(j))
            if (settings["count-attempts"]):
                hlp.add_attempt()
            j -= 1
        j += 1

    # Handle world gen instances
    j = 0
    for i in range(len(gen_instances)):
        if gen_instances[j].is_in_world():
            hlp.run_ahk("pauseGame", pid=gen_instances[j].PID)
            gen_instances[j].when_genned = datetime.now()
            ready_instances.append(gen_instances.pop(j))
        else:
            j += 1

    # Pick focussed instance with priority
    # Could focus approved, might be confusing tho, idk
    if focused_instance is None:
        if len(ready_instances) > 0:
            focused_instance = ready_instances[0]
            list_with_focussed = ready_instances
        elif len(gen_instances) > 0:
            focused_instance = gen_instances[0]
            list_with_focussed = gen_instances
        elif len(macro_instances) > 0:
            focused_instance = macro_instances[0]
        else:
            # Show a meme or something lol
            pass
    if focused_instance is not None:
        hlp.run_ahk("updateTitle", pid=focused_instance.PID,
                    title="Minecraft* 1.16.1 - Focused Instance")

    # Handle ready and approved instances
    j = 0
    for i in range(len(ready_instances)):
        delta = datetime.now() - ready_instances[j].when_genned
        if not ready_instances[j].is_suspended and delta.total_seconds() * 1000 >= settings["freeze-delay"]:
            ready_instances[j].suspend()
        if settings["auto-reset"] and delta.total_seconds() / 60 >= 5:  # Auto reset after 5 minutes
            free_instances.append(ready_instances.pop(j))
            j -= 1
        j += 1

    for i in range(len(approved_instances)):
        delta = datetime.now() - approved_instances[j].when_genned
        if not approved_instances[j].is_suspended and delta.total_seconds() * 1000 >= settings["freeze-delay"]:
            approved_instances[j].suspend()
        if settings["auto-reset"] and delta.total_seconds() / 60 >= 5:  # Auto reset after 5 minutes
            free_instances.append(approved_instances.pop(j))
            j -= 1
        j += 1

    if active_instance is None:
        if len(approved_instances) > 0:
            active_instance = approved_instances.pop(0)
        elif focused_instance in ready_instances and len(ready_instances) > 1:
            active_instance = ready_instances.pop(1)
        elif not focused_instance in ready_instances and len(ready_instances) > 0:
            active_instance = ready_instances.pop(0)
        else:
            # Not sure what to do here lol
            pass
        hlp.run_ahk("callTimer", timerReset=settings["timer-hotkeys"]["timer-reset"],
                    timerStart=settings["timer-hotkeys"]["timer-start"])
    if active_instance is not None:
        hlp.run_ahk("updateTitle", pid=active_instance.PID,
                    title="Minecraft* 1.16.1 - Active Instance")
        active_instance.resume()
        print(active_instance.num)
    print("loop")
    SCHEDULER.enter(LOOP_DELAY, 1, main_loop, (sc,))


# Callbacks
def reset_active():
    global active_instance
    if listening and active_instance is not None:
        print("Reset Active")
        free_instances.append(active_instance)
        if len(approved_instances) > 0:
            active_instance = approved_instances.pop(0)
        elif len(ready_instances) > 0:
            active_instance = ready_instances.pop(0)
        else:
            # Not sure what to do here lol
            pass


def reset_focused():
    global focused_instance
    global list_with_focussed
    if listening and focused_instance is not None:
        print("Reset Focused")
        free_instances.append(focused_instance)
        if list_with_focussed is not None:
            list_with_focussed.remove(focused_instance)
        if len(ready_instances) > 0:
            focused_instance = ready_instances[0]
            list_with_focussed = ready_instances
        elif len(gen_instances) > 0:
            focused_instance = gen_instances[0]
            list_with_focussed = gen_instances
        elif len(macro_instances) > 0:
            focused_instance = macro_instances[0]
        else:
            # Show a meme or something lol
            pass


def approve_focused():
    global focused_instance
    global list_with_focussed
    if listening and focused_instance is not None:
        print("Approve Focused")
        approved_instances.append(focused_instance)
        if list_with_focussed is not None:
            list_with_focussed.remove(focused_instance)
        if len(ready_instances) > 0:
            focused_instance = ready_instances[0]
            list_with_focussed = ready_instances
        elif len(gen_instances) > 0:
            focused_instance = gen_instances[0]
            list_with_focussed = gen_instances
        elif len(macro_instances) > 0:
            focused_instance = macro_instances[0]
        else:
            # Show a meme or something lol
            pass


def toggle_hotkeys():
    print("Toggle Hotkeys")
    global listening
    listening = not listening


if __name__ == "__main__":
    # TODO: Automatically startup instances
    PIDs = list(map(int, hlp.run_ahk("getPIDs").split("|")))
    for i in range(len(dead_instances)):
        inst = dead_instances.pop(0)
        inst.PID = PIDs[i]
        inst.resume()
        hlp.run_ahk("updateTitle", pid=inst.PID,
                    title=f"Minecraft* 1.16.1 - Instance {i+1}")
        free_instances.append(inst)
    kb.add_hotkey(settings['hotkeys']['reset-active'], reset_active)
    kb.add_hotkey(settings['hotkeys']['reset-focused'], reset_focused)
    kb.add_hotkey(settings['hotkeys']['approve-focused'], approve_focused)
    kb.add_hotkey(settings['hotkeys']['toggle-hotkeys'], toggle_hotkeys)
    if not settings["disable-tts"]:
        hlp.run_ahk("ready")
    SCHEDULER.enter(LOOP_DELAY, 1, main_loop, (SCHEDULER,))
    SCHEDULER.run()
