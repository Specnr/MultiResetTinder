import os
import shutil
import uuid
from datetime import datetime
from ahk import AHK
ahk = AHK()


def get_pids():
    return list(map(int, hlp.run_ahk("getPIDs", instances=int(settings['num-instances']), MultiMC=settings['multi-mc']).split("|")))

def is_livesplit_open():
    return ahk.find_window(title=b"LiveSplit") is not None

def set_new_active(inst, settings):
    if inst is not None:
        run_ahk("updateTitle", pid=inst.PID,
                title="Minecraft* - Active Instance")
        inst.resume()
        # TODO: Update ls user config
        run_ahk("activateWindow", switchDelay=settings["switch-delay"],
                pid=inst.pid, idx=inst.num, obsDelay=settings["obs-delay"])
        if settings["fullscreen"]:
            run_ahk("toggleFullscreen")


def set_new_focused(inst):
    if inst is not None:
        run_ahk("updateTitle", pid=inst.PID,
                title="Minecraft* - Focused Instance")


def file_to_script(script_name, **kwargs):
    script_str = ""
    for key in kwargs:
        script_str += f'global {key} := "{kwargs[key]}"\n'
    with open("../ahk/" + script_name + ".ahk", "r") as ahk_script:
        script_str += ahk_script.read()
    return script_str

def run_cmd(cmd):
    if settings.is_test_mode():
        print("Run command {}".format(cmd))
        return
    # TODO - run the command
    pass

def run_ahk(script_name, **kwargs):
    if settings.is_test_mode():
        print("Run AHK script {}".format(script_name))
        return
    return ahk.run_script(file_to_script(script_name, **kwargs))

def add_attempt():
    curr_attempts = 0
    if os.path.exists("./attempts.txt"):
        with open("attempts.txt", "r") as f:
            curr_attempts = int(f.read().strip())
    with open("attempts.txt", "w") as f:
        f.write(str(curr_attempts + 1))
