import helpers as hlp
import json
import sched
import time
import os
import keyboard as kb
from pathlib import Path
from datetime import datetime


# Load settings
with open("./settings.json", "r") as f:
    settings = json.load(f)
Path(settings["old-worlds"]).mkdir(parents=True, exist_ok=True)
SCHEDULER = sched.scheduler(time.time, time.sleep)

# Instance states
all_instances = [hlp.Instance(-1, i+1) for i in range(int(settings['num-instances']))]
dead_instances = [inst for inst in all_instances]
booting_instances = []
free_instances = []
menu_instances = []
gen_instances = []
ready_instances = []
approved_instances = []

listening = True
active_instance = None
focused_instance = None
list_with_focussed = None
need_to_reset_timer = False


def get_pids():
    return list(map(int, hlp.run_ahk("getPIDs", instances=int(settings['num-instances']), MultiMC=settings['multi-mc']).split("|")))


def main_loop(sc):
    global active_instance
    global focused_instance
    global list_with_focussed
    global need_to_reset_timer

    if need_to_reset_timer and hlp.is_livesplit_open():
        hlp.run_ahk("callTimer", timerReset=settings["timer-hotkeys"]["timer-reset"],
                    timerStart=settings["timer-hotkeys"]["timer-start"])


    # Handle dead instances
    for i in range(max(1,int(settings['max-concurrent-boot']))):
        inst = dead_instances.pop(0)
        inst.initialize()
        booting_instances.append(inst)
    
    # Handle booting instances
    j = 0
    num_working_instances = len(booting_instances)
    for i in range(len(booting_instances)):
        inst = booting_instances[j]
        if num_working_instances < int(settings['max-concurrent-gen']):
            if get_time() - inst.timestamp > float(settings['boot-delay']):
                inst.timestamp = get_time()
                inst.initialize_after_boot(all_instances)
                menu_instances.append(inst)
                booting_instances.remove(j)
                j -= 1


    # Handle menu instances (prepared to create world & unfrozen)
    j = 0
    for i in range(len(menu_instances)):
        if num_working_instances < int(settings['max-concurrent-gen']):
            inst = menu_instances[j]
            if get_time() - inst.timestamp > float(settings['unfreeze-delay']*1000.0):
                inst.reset()
                menu_instances.remove(j)
                j -= 1

    # Handle free instances
    num_working_instances += len(gen_instances)
    j = 0
    for i in range(len(free_instances)):
        inst = free_instances[j]
        if num_working_instances < int(settings["max-concurrent-gen"]):
            inst.resume()
            menu_instances.append(inst)
            free_instances.remove(j)
            j -= 1
        elif not free_instances[j].is_suspended:
            free_instances[j].suspend()
        j += 1

    # Handle world gen instances
    for i in range(len(gen_instances)):
        inst = gen_instances[j]
        if inst.is_in_world(settings['lines-from-bottom']):
            hlp.run_ahk("pauseGame", pid=gen_instances[j].PID)
            inst.when_genned = get_time()
            gen_instances.remove(j)
            ready_instances.append(inst)
        else:
            j += 1

    # Pick focussed instance with priority
    if focused_instance is None:
        if len(ready_instances) > 0:
            focused_instance = ready_instances[0]
            list_with_focussed = ready_instances
            hlp.set_new_focused(focused_instance)
        elif len(gen_instances) > 0:
            focused_instance = gen_instances[0]
            list_with_focussed = gen_instances
            hlp.set_new_focused(focused_instance)
        else:
            # Show a meme or something lol
            pass

    # Handle ready instances
    j = 0
    for i in range(len(ready_instances)):
        delta = datetime.now() - ready_instances[j].when_genned
        if not ready_instances[j].is_suspended and delta.total_seconds() * 1000 >= settings["freeze-delay"]:
            ready_instances[j].suspend()
        if settings["auto-reset"] and delta.total_seconds() / 60 >= 5:  # Auto reset after 5 minutes
            free_instances.append(ready_instances.pop(j))
            j -= 1
        j += 1

    # Handle approved instances
    for i in range(len(approved_instances)):
        delta = datetime.now() - approved_instances[j].when_genned
        if not approved_instances[j].is_suspended and delta.total_seconds() * 1000 >= settings["freeze-delay"]:
            approved_instances[j].suspend()
        if settings["auto-reset"] and delta.total_seconds() / 60 >= 5:  # Auto reset after 5 minutes
            free_instances.append(approved_instances.pop(j))
            j -= 1
        j += 1

    # Set active instance
    if active_instance is None:
        if len(approved_instances) > 0:
            active_instance = approved_instances.pop(0)
        elif focused_instance in ready_instances and len(ready_instances) > 1:
            active_instance = ready_instances.pop(1)
        elif not focused_instance in ready_instances and len(ready_instances) > 0:
            active_instance = ready_instances.pop(0)
        elif len(gen_instances) > 0:
            active_instance = gen_instances.pop(0)
        hlp.set_new_active(active_instance, settings)
        need_to_reset_timer = True
    SCHEDULER.enter(settings["loop-delay"], 1, main_loop, (sc,))

# Callbacks
def reset_active():
    global active_instance
    if listening and active_instance is not None:
        print("Reset Active")
        hlp.run_ahk("pauseActive", pid=active_instance.PID)
        free_instances.append(active_instance)
        if len(approved_instances) > 0:
            active_instance = approved_instances.pop(0)
        elif len(ready_instances) > 0:
            active_instance = ready_instances.pop(0)
        elif len(gen_instances) > 0:
            active_instance = gen_instances.pop(0)
        hlp.set_new_active(active_instance, settings)
        need_to_reset_timer = True


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
        hlp.set_new_focused(focused_instance)


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
        hlp.set_new_focused(focused_instance)


def toggle_hotkeys():
    print("Toggle Hotkeys")
    global listening
    listening = not listening


if __name__ == "__main__":
    # TODO: Automatically startup instances
    kb.add_hotkey(settings['hotkeys']['reset-active'], reset_active)
    kb.add_hotkey(settings['hotkeys']['reset-focused'], reset_focused)
    kb.add_hotkey(settings['hotkeys']['approve-focused'], approve_focused)
    kb.add_hotkey(settings['hotkeys']['toggle-hotkeys'], toggle_hotkeys)
    if not settings["disable-tts"]:
        hlp.run_ahk("ready")
    SCHEDULER.enter(settings["loop-delay"], 1, main_loop, (SCHEDULER,))
    SCHEDULER.run()
