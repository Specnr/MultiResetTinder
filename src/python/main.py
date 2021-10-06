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
primary_instance = None
focused_instance = None
list_with_focussed = None
need_to_reset_timer = False

max_concurrent = settings.get_max_concurrent()
max_concurrent_boot = settings.get_max_concurrent_boot()

unfrozen_queue_size = settings.get_unfrozen_queue_size()

unfreeze_delay = settings.get_unfreeze_delay()

last_log_time = time.time()

def try_set_primary(new_primary_instance):
    global primary_instance
    if primary_instance is not None and new_primary_instance is not None:
        if new_primary_instance.num != primary_instance.num:
            primary_instance.mark_hidden()
            hlp.set_new_primary(primary_instance)
            primary_instance = new_primary_instance
        primary_instance.mark_primary()

def try_set_focused(new_focused_instance):
    global primary_instance
    global focused_instance
    if primary_instance is not None and new_focused_instance is not None:
        if not focused_instance.is_ready() and new_focused_instance.num != focused_instance.num and new_focused_instance.num != primary_instance.num:
            hlp.set_new_focused(new_focused_instance)
            focused_instance = new_focused_instance

def schedule_next(sc):
    SCHEDULER.enter(settings.get_loop_delay(), 1, main_loop, (sc,))

def main_loop(sc):
    global primary_instance
    global focused_instance
    global need_to_reset_timer
    global last_log_time

    if settings.is_test_mode() and time.time() - last_log_time > settings.get_debug_interval():
        last_log_time = time.time()
        tmp_all_queues = queues.get_all_queues()
        print('---------------')
        for key in tmp_all_queues.keys():
            print(key,end="|")
            for value in tmp_all_queues[key]:
                print(value,end=" ")
            print()
        print('---------------')

    if need_to_reset_timer and hlp.is_livesplit_open():
        hlp.run_ahk("callTimer", timerReset=settings["timer-hotkeys"]["timer-reset"],
                    timerStart=settings["timer-hotkeys"]["timer-start"])

    # remove primary from all lists, focused can stay in lists
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
        if settings.should_auto_boot():
            inst.mark_booting()
            inst.boot()
            num_booting_instances += 1
            num_working_instances += 1
        else:
            old_pid = inst.pid
            inst.assign_pid()
            if inst.pid != old_pid:
                inst.mark_booting()
            break
    
    # Handle booting instances
    for inst in queues.get_booting_instances():
        if not inst.is_done_booting():
            continue
        if not settings.should_auto_boot():
            inst.suspend()
            inst.release()
        else:
            inst.mark_generating()
            inst.initialize_after_boot(queues.get_all_instances())

    if not settings.should_auto_boot():
        if len(free_instances) < settings.get_num_instances():
            schedule_next(sc)
            return

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
        if not inst.is_in_world():
            continue
        # state = PAUSED
        # TODO - why do we need to pause after creating a world? shouldnt it auto-pause?
        if not inst.is_primary():
            inst.mark_worldgen_finished()
            inst.pause()
        else:
            inst.mark_active()
            inst.mark_primary()

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
        # if inst.is_primary():
        #     inst.mark_active()
        #     continue
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
    
    # Pick primary instance
    if primary_instance is None:
        # only needed for initialization, so let's just show nothing until a world is ready
        if len(queues.get_booting_instances()) > 0:
            primary_instance = queues.get_booting_instances()[0]
            primary_instance.mark_primary()
            hlp.set_new_primary(primary_instance)
            need_to_reset_timer = True
    elif not primary_instance.is_primary():
        new_primary_instance = None
        if len(queues.get_approved_instances()) > 0:
            new_primary_instance = queues.get_approved_instances()[0]
        elif len(queues.get_ready_instances()) > 0:
            new_primary_instance = queues.get_ready_instances()[0]
        elif len(queues.get_paused_instances()) > 0:
            new_primary_instance = queues.get_paused_instances()[0]
        elif len(queues.get_gen_instances()) > 0:
            new_primary_instance = queues.get_gen_instances()[0]
        try_set_primary(new_primary_instance)
        need_to_reset_timer = True

    # Pick focused instance
    if focused_instance is None:
        # only needed for initialization, so let's just show nothing until a world is ready
        if len(queues.get_booting_instances()) > 0 and primary_instance is not None:
            focused_instance = queues.get_booting_instances()[0]
            # we don't want an instance to be both focused and primary
            if not focused_instance.is_primary():
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

    schedule_next(sc)

# Callbacks
def reset_primary():
    global primary_instance
    if listening and primary_instance is not None:
        primary_instance.reset_primary()

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
    # TODO: Automatically startup instances
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
    open_needed_programs()
    input("Press any key to continue...")
    # TODO: unhide all
    OBS_WS.connect()
    hlp.unhide_all(OBS_WS)
    assert unfrozen_queue_size < max_concurrent
    kb.add_hotkey(settings.get_hotkeys()['reset-active'], reset_primary)
    kb.add_hotkey(settings.get_hotkeys()['reset-focused'], reset_focused)
    kb.add_hotkey(settings.get_hotkeys()['approve-focused'], approve_focused)
    kb.add_hotkey(settings.get_hotkeys()['toggle-hotkeys'], toggle_hotkeys)
    if settings.should_use_tts():
        hlp.run_ahk("ready")
    SCHEDULER.enter(settings.get_loop_delay(), 1, main_loop, (SCHEDULER,))
    SCHEDULER.run()
