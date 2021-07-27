import json
from pathlib import Path
from datetime import datetime

import helpers as hlp

# Load settings
with open("./settings.json", "r") as f:
    settings = json.load(f)
Path(settings["old-worlds"]).mkdir(parents=True, exist_ok=True)

# Instance states
dead_instances = [hlp.Instance(-1, i+1, settings["mc-folders"][i])
                  for i in range(settings["instance-count"])]
free_instances = []
macro_instances = []
gen_instances = []
ready_instances = []
approved_instances = []

active_instance = None
focused_instance = None
list_with_focussed = None


def main_loop():
    global active_instance
    global focused_instance
    global list_with_focussed
    # Handle free instances
    instances_against_cap = len(macro_instances) + len(gen_instances)
    for inst in free_instances:
        if instances_against_cap < settings["max-concurrent-gen"]:
            free_instances.remove(inst)
            if inst.is_in_title():
                inst.reset_state = 2
            macro_instances.append(inst)
            instances_against_cap += 1
        elif not inst.is_suspended:
            inst.suspend()

    # Handle macro instances
    for inst in macro_instances:
        if inst.reset_state == 0:
            inst.resume()
        for i in range(1, 6):
            if inst.reset_state == i:
                hlp.run_ahk(f"./ahk/macro/{i}.ahk",
                            pid=inst.PID, delay=settings["delay"])
                break
        if inst.reset_state == 6:
            hlp.move_worlds(inst, settings["old-worlds"])
            macro_instances.remove(inst)
            gen_instances.append(inst)
        inst.reset_state += 1

    # Handle world gen instances
    for inst in gen_instances:
        if inst.is_in_world():
            gen_instances.remove(inst)
            inst.when_genned = datetime.now()
            ready_instances.append(inst)

    # Pick focussed instance with priority
    # Could focus approved, might be confusing tho, idk
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

    # Handle ready and approved instances
    for inst in ready_instances:
        delta = datetime.now() - inst.when_genned
        if not inst.is_suspended and delta.total_seconds() * 1000 >= settings["freeze-delay"]:
            inst.suspend()
        if settings["auto-reset"] and delta.total_seconds() / 60 >= 5:  # Auto reset after 5 minutes
            ready_instances.remove(inst)
            free_instances.append(inst)

    for inst in approved_instances:
        delta = datetime.now() - inst.when_genned
        if not inst.is_suspended and delta.total_seconds() * 1000 >= settings["freeze-delay"]:
            inst.suspend()
        if settings["auto-reset"] and delta.total_seconds() / 60 >= 5:  # Auto reset after 5 minutes
            approved_instances.remove(inst)
            free_instances.append(inst)

    if active_instance is None:
        if len(approved_instances) > 0:
            active_instance = approved_instances[0]
        elif len(ready_instances) > 0:
            active_instance = ready_instances[0]
        elif len(gen_instances) > 0:
            active_instance = gen_instances[0]
        else:
            # Not sure what to do here, probably genning, then macro
            pass
    # elif we're finished with active, make active next in line
    active_instance.resume()

    if list_with_focussed is not None:
        # If reset focussed. move focussed to free
        # If approve focussed, move focussed to approved
        pass


if __name__ == "__main__":
    # TODO:
    # Boot up instance, get PID, create world, freeze
    # Loop that settings["instance-count"] times
    PIDs = list(map(int, hlp.run_ahk("./ahk/getPIDs.ahk").split("|")))
    for i in range(len(dead_instances)):
        inst = dead_instances.pop(0)
        inst.PID = PIDs[i]
        free_instances.append(inst)
