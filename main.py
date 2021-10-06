import helpers as hlp
import json
import sched
import time
import os
import psutil
from copy import copy
import keyboard as kb
from pathlib import Path
from datetime import datetime
from multiprocessing import Process
from obswebsocket import obsws

# Load settings
with open("./settings.json", "r") as f:
    settings = json.load(f)
Path(settings["old-worlds"]).mkdir(parents=True, exist_ok=True)
SCHEDULER = sched.scheduler(time.time, time.sleep)
OBS_WS = obsws(settings["obs-settings"]["web-host"],
               settings["obs-settings"]["port"],
               settings["obs-settings"]["password"])

# Instance states
dead_instances = [hlp.Instance(-1, i+1, settings["mc-folders"][i])
                  for i in range(len(settings["mc-folders"]))]
free_instances = []
gen_instances = []
ready_instances = []
approved_instances = []

listening = True
active_instance = None
focused_instance = None
list_with_focussed = None
need_to_reset_timer = False


def main_loop(sc):
    global free_instances
    global gen_instances
    global ready_instances
    global approved_instances
    global active_instance
    global focused_instance
    global list_with_focussed
    global need_to_reset_timer

    if need_to_reset_timer and hlp.is_livesplit_open():
        hlp.run_ahk("callTimer", timerReset=settings["timer-hotkeys"]["timer-reset"],
                    timerStart=settings["timer-hotkeys"]["timer-start"])
        need_to_reset_timer = False

    # Handle free instances
    idx_list = []
    for i in range(len(free_instances)):
        if len(gen_instances) < settings["max-concurrent-gen"]:
            free_instances[i].resume()
            free_instances[i].reset()
            gen_instances.append(copy(free_instances[i]))
            idx_list.append(i)
        elif not free_instances[i].is_suspended:
            free_instances[i].suspend()
    free_instances = hlp.remove_from_list(free_instances, idx_list)

    # Handle world gen instances
    idx_list = []
    for i in range(len(gen_instances)):
        if gen_instances[i].is_in_world(settings['lines-from-bottom']):
            hlp.run_ahk("pauseGame", pid=gen_instances[i].PID)
            gen_instances[i].when_genned = datetime.now()
            ready_instances.append(copy(gen_instances[i]))
            idx_list.append(i)
    gen_instances = hlp.remove_from_list(gen_instances, idx_list)

    # Pick focussed instance with priority
    # Could focus approved, might be confusing tho, idk
    if focused_instance is None:
        if len(ready_instances) > 0:
            focused_instance = ready_instances[0]
            list_with_focussed = ready_instances
        elif len(gen_instances) > 0:
            focused_instance = gen_instances[0]
            list_with_focussed = gen_instances
        hlp.set_new_focused(focused_instance, OBS_WS)

    # Handle ready and approved instances
    idx_list = []
    for i in range(len(ready_instances)):
        delta = datetime.now() - ready_instances[i].when_genned
        if not ready_instances[i].is_suspended and delta.total_seconds() * 1000 >= settings["freeze-delay"]:
            ready_instances[i].suspend()
        if settings["auto-reset"] and delta.total_seconds() / 60 >= 5:  # Auto reset after 5 minutes
            free_instances.append(copy(ready_instances[i]))
            idx_list.append(i)
    ready_instances = hlp.remove_from_list(ready_instances, idx_list)

    idx_list = []
    for i in range(len(approved_instances)):
        delta = datetime.now() - approved_instances[i].when_genned
        if not approved_instances[i].is_suspended and delta.total_seconds() * 1000 >= settings["freeze-delay"]:
            approved_instances[i].suspend()
        if settings["auto-reset"] and delta.total_seconds() / 60 >= 5:  # Auto reset after 5 minutes
            free_instances.append(copy(approved_instances[i]))
            idx_list.append(i)
    approved_instances = hlp.remove_from_list(approved_instances, idx_list)

    if active_instance is None:
        if len(approved_instances) > 0:
            active_instance = approved_instances.pop(0)
        elif focused_instance in ready_instances and len(ready_instances) > 1:
            active_instance = ready_instances.pop(1)
        elif not focused_instance in ready_instances and len(ready_instances) > 0:
            active_instance = ready_instances.pop(0)
        elif len(gen_instances) > 0:
            active_instance = gen_instances.pop(0)
        hlp.set_new_active(active_instance, OBS_WS, settings)
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
        hlp.set_new_active(active_instance, OBS_WS, settings)
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
        else:
            focused_instance = None
        hlp.set_new_focused(focused_instance, OBS_WS)


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
        else:
            focused_instance = None
        hlp.set_new_focused(focused_instance, OBS_WS)


def toggle_hotkeys():
    print("Toggle Hotkeys")
    global listening
    listening = not listening


def open_instance(inst_id):
    os.popen(f'{settings["multi-mc-path"]} -l "{inst_id}"')


def open_needed_programs():
    seen_ls, seen_obs = False, False
    for p in psutil.process_iter():
        if not seen_obs and "OBS" in p.name():
            seen_obs = True
        if not seen_ls and "LiveSplit" in p.name():
            seen_ls = True
    if not seen_ls:
        os.startfile(settings["livesplit-path"])
        print("Opened LiveSplit")
    if not seen_obs:
        os.system(f'start /d "{settings["obs-path"]}" "" obs64.exe')
        print("Opened OBS")


if __name__ == "__main__":
    if settings['multi-mc-path'] != "":
        for mc_folder in settings["mc-folders"]:
            inst_id = mc_folder.split("/")[-2]
            print("Starting Instance", inst_id)
            inst = Process(target=open_instance, args=(inst_id,))
            inst.start()
            # TODO: read the log and wait for access token or something
            time.sleep(2.5)
    # TODO: wait for 'Component list save performed now for "<inst_id>"'
    time.sleep(7.5)
    PIDs = list(map(int, hlp.run_ahk(
        "getPIDs", instances=len(settings["mc-folders"]), MultiMC=settings['multi-mc-path'] != "").split("|")))
    for i in range(len(dead_instances)):
        inst = dead_instances.pop(0)
        inst.PID = PIDs[i]
        inst.resume()
        hlp.run_ahk("updateTitle", pid=inst.PID,
                    title=f"Minecraft* - Instance {i+1}")
        free_instances.append(inst)
    open_needed_programs()
    input("Press any key to continue...")
    # TODO: unhide all
    OBS_WS.connect()
    hlp.unhide_all(OBS_WS)
    kb.add_hotkey(settings['hotkeys']['reset-active'], reset_active)
    kb.add_hotkey(settings['hotkeys']['reset-focused'], reset_focused)
    kb.add_hotkey(settings['hotkeys']['approve-focused'], approve_focused)
    kb.add_hotkey(settings['hotkeys']['toggle-hotkeys'], toggle_hotkeys)
    if not settings["disable-tts"]:
        hlp.run_ahk("ready")
    SCHEDULER.enter(settings["loop-delay"], 1, main_loop, (SCHEDULER,))
    SCHEDULER.run()
