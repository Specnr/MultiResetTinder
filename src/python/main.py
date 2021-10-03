import settings
import queues
import helpers as hlp
from instance import Instance, State
import json
import sched
import time
import os
import keyboard as kb
from pathlib import Path
from datetime import datetime

# Load settings
SCHEDULER = sched.scheduler(time.time, time.sleep)

listening = True
active_instance = None
focused_instance = None
list_with_focussed = None
need_to_reset_timer = False

max_concurrent = settings.get_max_concurrent()
max_concurrent_boot = settings.get_max_concurrent_boot()

unfrozen_queue_size = settings.get_unfrozen_queue_size()

unfreeze_delay = settings.get_unfreeze_delay()

last_log_time = time.time()

def try_set_active(new_active_instance):
    global active_instance
    if active_instance is not None and new_active_instance is not None:
        if new_active_instance.num != active_instance.num:
            hlp.set_new_active(active_instance, settings)
            active_instance = new_active_instance
        active_instance.mark_active()

def try_set_focused(new_focused_inst):
    global active_instance
    global focused_instance
    if active_instance is not None and new_focused_instance is not None:
        if not focused_instance.is_ready() and new_focused_instance.num != focused_instance.num and new_focused_instance.num != active_instance.num:
            hlp.set_new_focused(new_focused_instance)
            focused_instance = new_focused_instance
            focused_instance.mark_focused()

def main_loop(sc):
    global active_instance
    global focused_instance
    global need_to_reset_timer
    global last_log_time


    if time.time() - last_log_time > settings.get_debug_interval():
        last_log_time = time.time()
        tmp_all_queues = queues.get_all_queues()
        for key in tmp_all_queues.keys():
            print(key,end="|")
            for value in tmp_all_queues[key]:
                print(value,end=" ")
            print()

    if need_to_reset_timer and hlp.is_livesplit_open():
        hlp.run_ahk("callTimer", timerReset=settings["timer-hotkeys"]["timer-reset"],
                    timerStart=settings["timer-hotkeys"]["timer-start"])

    # remove active from all lists, focused can stay in lists
    queues.update_all()

    num_working_instances = len(queues.get_gen_instances()) + len(queues.get_booting_instances()) + len(queues.get_pregen_instances()) + len(queues.get_paused_instances()) + unfrozen_queue_size
    num_booting_instances = len(queues.get_booting_instances())

    num_to_boot = max_concurrent - num_working_instances - len(queues.get_free_instances())
    num_to_boot = max(0,min(1, num_to_boot))

    num_to_boot = min(num_to_boot, max_concurrent_boot-len(queues.get_booting_instances()))
    num_to_boot = min(num_to_boot, len(queues.get_dead_instances()))

    # Handle dead instances
    for i in range(num_to_boot):
        inst = queues.get_dead_instances()[i]
        inst.mark_booting()
        inst.boot()
        num_booting_instances += 1
        num_working_instances += 1
    
    # Handle booting instances
    for inst in queues.get_booting_instances():
        if not inst.is_done_booting():
            continue
        inst.mark_generating()
        inst.initialize_after_boot(queues.get_all_instances())

    # Handle pregen instances (recently unfrozen worlds that need to be generated)
    for inst in queues.get_pregen_instances():
        if not inst.is_done_unfreezing():
            continue
        # state = GENERATING
        inst.mark_generating()
        inst.reset()

    # Handle free instances (frozen instances that are on a world, and we've decided to reset this world)
    for inst in queues.get_free_instances():
        if num_working_instances == max_concurrent:
            continue
        if not inst.is_ready_for_unfreeze():
            inst.suspend()
            continue
        # state = PREGEN
        inst.mark_pregen()
        inst.resume()
        num_working_instances += 1

    # Handle world gen instances
    for inst in queues.get_gen_instances():
        if not inst.is_in_world(settings.get_lines_from_bottom()):
            continue
        # state = PAUSED
        inst.mark_worldgen_finished()
        # TODO - why do we need to pause after creating a world? shouldnt it auto-pause?
        inst.pause()

    # Handle paused instances
    for inst in queues.get_paused_instances():
        # let chunks load some amount
        if not inst.is_ready_for_freeze():
            continue
        # state = READY
        inst.mark_ready()
        inst.suspend()

    # Handle ready instances (paused instances on a world we haven't evaluated yet. may or may not be frozen)
    index = 0
    # make sure we prioritize having approved worlds unfrozen since they will become active before us
    total_to_unfreeze = unfrozen_queue_size - len(queues.get_approved_instances())
    for inst in queues.get_ready_instances():
        index += 1
        if inst.check_should_auto_reset():
            continue
        if index <= total_to_unfreeze:
            inst.resume()
            continue
        inst.suspend()

    # Handle approved instances
    index = 0
    # this is fine because we will either loop up to this number, and all ready are frozen, or we will loop to less than this number anyways
    total_to_unfreeze = unfrozen_queue_size
    for inst in queues.get_approved_instances():
        index += 1
        if inst.check_should_auto_reset():
            continue
        if index <= total_to_unfreeze:
            inst.resume()
            continue
        inst.suspend()
    
    # Pick active instance
    if active_instance is None:
        # only needed for initialization, so let's just show nothing until a world is ready
        if len(queues.get_ready_instances()) > 0:
            active_instance = queues.get_ready_instances()[0]
            active_instance.mark_active()
            hlp.set_new_active(active_instance)
            need_to_reset_timer = True
    elif not active_instance.is_active():
        new_active_instance = None
        if len(queues.get_approved_instances()) > 0:
            new_active_instance = queues.get_approved_instances()[0]
        elif len(queues.get_ready_instances()) > 0:
            new_active_instance = queues.get_ready_instances()[0]
        elif len(queues.get_paused_instances()) > 0:
            new_active_instance = queues.get_paused_instances()[0]
        elif len(queues.get_gen_instances()) > 0:
            new_active_instance = queues.get_gen_instances()[0]
        try_set_active(new_active_instance)
        need_to_reset_timer = True

    # Pick focused instance
    if focused_instance is None:
        # only needed for initialization, so let's just show nothing until a world is ready
        if len(queues.get_ready_instances()) > 0 and active_instance is not None:
            new_focused_instance = queues.get_ready_instances()[0]
            # we don't want an instance to be both focused and active
            if not new_focused_instance.is_active():
                focused_instance.mark_focused()
                hlp.set_new_focused(focused_instance)
    else:
        new_focused_instance = None
        if len(queues.get_ready_instances()) > 0:
            new_focused_instance = queues.get_ready_instances()[0]
        elif len(queues.get_paused_instances()) > 0:
            new_focused_instance = queues.get_paused_instances()[0]
        elif len(queues.get_gen_instances()) > 0:
            new_focused_instance = queues.get_gen_instances()[0]
        try_set_focused(new_focused_instance)

    SCHEDULER.enter(settings.get_loop_delay(), 1, main_loop, (sc,))

# Callbacks
def reset_active():
    global active_instance
    if listening and active_instance is not None:
        active_instance.reset_active()

def reset_focused():
    global focused_instance
    if listening and focused_instance is not None:
        if focused_instance.state == State.PAUSED or focused_instance.state == State.READY:
            focused_instance.release()

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
    assert unfrozen_queue_size < max_concurrent
    kb.add_hotkey(settings.get_hotkeys()['reset-active'], reset_active)
    kb.add_hotkey(settings.get_hotkeys()['reset-focused'], reset_focused)
    kb.add_hotkey(settings.get_hotkeys()['approve-focused'], approve_focused)
    kb.add_hotkey(settings.get_hotkeys()['toggle-hotkeys'], toggle_hotkeys)
    if settings.should_use_tts():
        hlp.run_ahk("ready")
    SCHEDULER.enter(settings.get_loop_delay(), 1, main_loop, (SCHEDULER,))
    SCHEDULER.run()
