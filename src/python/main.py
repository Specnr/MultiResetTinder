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
pregen_instances = []
free_instances = []
gen_instances = []
paused_instances = []
ready_instances = []
approved_instances = []

listening = True
active_instance = None
focused_instance = None
list_with_focussed = None
need_to_reset_timer = False


max_concurrent = int(settings['max-concurrent'])
max_concurrent_boot = int(settings['max-concurrent-boot'])

unfreeze_delay = float(settings['unfreeze-delay']) / 1000.0


def get_pids():
    return list(map(int, hlp.run_ahk("getPIDs", instances=int(settings['num-instances']), MultiMC=settings['multi-mc']).split("|")))

def try_set_active(new_active_instance):
    if active_instance is not None and new_active_instance is not None:
        if new_active_instance.num != new_active_instance.num:
            hlp.set_new_active(active_instance, settings)
            active_instance = new_active_inst
        active_instance.mark_active()

def try_set_focused(new_focused_inst):
    if active_instance is not None and new_focused_instance is not None:
        if not focused_instance.is_ready() and new_focused_instance.num != focused_instance.num and new_focused_instance.num != active_instance.num:
            hlp.set_new_focused(new_focused_instance)
            focused_instance = new_focused_instance
            focused_instance.mark_focused()


def main_loop(sc):
    global active_instance
    global focused_instance
    global list_with_focussed
    global need_to_reset_timer

    if need_to_reset_timer and hlp.is_livesplit_open():
        hlp.run_ahk("callTimer", timerReset=settings["timer-hotkeys"]["timer-reset"],
                    timerStart=settings["timer-hotkeys"]["timer-start"])

    # remove active from all lists, focused can stay in lists
    assign_lists(all_instances)

    num_working_instances = len(gen_instances) + len(booting_instances) + len(pregen_instances) + len(paused_instances) + unfrozen_queue_size
    num_booting_instances = len(booting_instances)

    # Handle dead instances
    for i in range(max(1,max_concurrent_boot))):
        inst = dead_instances[i]
        if num_booting_instances == max_concurrent_boot:
            continue
        if num_working_instances == max_concurrent:
            continue
        inst = dead_instances[i]
        inst.initialize()
        num_booting_instances += 1
        num_working_instances += 1
    
    # Handle booting instances
    for inst in booting_instances:
        if num_working_instances == max_concurrent:
            continue
        if get_time() - inst.timestamp < float(settings['boot-delay']):
            continue
        inst.timestamp = get_time()
        # state = GENERATING
        inst.initialize_after_boot()

    # Handle pregen instances (recently unfrozen worlds that need to be generated)
    for inst in pregen_instances:
        if num_working_instances == max_concurrent:
            continue
        if get_time() - inst.timestamp < unfreeze_delay:
            continue
        # state = GENERATING
        inst.reset()
        num_working_instances += 1

    # Handle free instances
    for inst in free_instances:
        if num_working_instances == max_concurrent:
            continue
        if not inst.is_ready_for_unfreeze():
            continue
        # state = PREGEN
        inst.mark_pregen()
        inst.resume()
        num_working_instances += 1

    # Handle world gen instances
    for inst in gen_instances:
        if not inst.is_in_world(settings['lines-from-bottom']):
            continue
        # state = PAUSED
        inst.mark_worldgen_finished()

    # Handle paused instances
    for inst in paused_instances:
        if not inst.is_ready_for_freeze():
            continue
        if not inst.is_in_world(settings['lines-from-bottom']):
            continue
        # state = PAUSED
        inst.mark_ready()

    # Handle ready instances
    index = 0
    total_to_unfreeze = unfrozen_queue_size - len(approved_instances)
    for inst in ready_instances:
        inst.check_should_auto_reset()
        index += 1
        if index <= total_to_unfreeze:
            continue
        if inst.is_suspended():
            continue
        inst.suspend()

    # Handle approved instances
    index = 0
    total_to_unfreeze = unfrozen_queue_size
    for inst in approved_instances:
        inst.check_should_auto_reset()
        index += 1
        if index <= total_to_unfreeze:
            continue
        inst.suspend()
    
    # Pick active instance
    if active_instance is None:
        # only needed for initialization
        if len(ready_instances) > 0:
            active_instance = ready_instances[0]
            active_instance.mark_active()
            hlp.set_new_active(active_instance)
            need_to_reset_timer = True
    elif not active_instance.is_active():
        new_active_instance = None
        if len(approved_instances) > 0:
            new_active_instance = approved_instances[0]
        elif len(ready_instances) > 0:
            new_active_instance = ready_instances[0]
        elif len(paused_instances) > 0:
            new_active_instance = paused_instances[0]
        elif len(gen_instances) > 0:
            new_active_instance = gen_instances[0]
        try_set_active(new_active_instance)
        need_to_reset_timer = True

    # Pick focused instance
    if focused_instance is None:
        # only needed for initialization
        if len(ready_instances) > 0 and active_instance is not None:
            new_focused_instance = ready_instances[0]
            if not new_focused_instance.is_active():
                focused_instance.mark_focused()
                hlp.set_new_focused(focused_instance)
    else:
        new_focused_instance = None
        if len(ready_instances) > 0:
            new_focused_instance = ready_instances[0]
        elif len(paused_instances) > 0:
            new_focused_instance = paused_instances[0]
        elif len(gen_instances) > 0:
            new_focused_instance = gen_instances[0]
        try_set_focused(new_focused_instance)

    SCHEDULER.enter(settings["loop-delay"], 1, main_loop, (sc,))

# Callbacks
def reset_active():
    global active_instance
    if listening and active_instance is not None:
        active_instance.mark_inactive()

def reset_focused():
    global focused_instance
    if listening and focused_instance is not None:
        focused_instance.mark_free()

def approve_focused():
    global focused_instance
    if listening and focused_instance is not None:
        focused_instance.mark_approved()

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
