import time
import os
import shutil
import uuid
import subprocess as sp
from datetime import datetime
import settings
from pathlib import Path
if not settings.is_test_mode():
    from ahk import AHK
    ahk = AHK()

def get_time():
    return time.time()

def get_pids():
    if settings.is_test_mode():
        return list(inst for inst in queues.get_all_instances() if inst.pid != -1)
    # TODO @Specnr - check that this actually works correctly
    return list(map(int, run_ahk("getPIDs", instances=int(settings.get_num_instances()), MultiMC=True).split("|")))

def is_livesplit_open():
    if settings.is_test_mode():
        return  
    return ahk.find_window(title=b"LiveSplit") is not None

def file_to_script(script_name, **kwargs):
    script_str = ""
    for key in kwargs:
        script_str += f'global {key} := "{kwargs[key]}"\n'
    path = Path.cwd() / "src" / "ahk" / "{}.ahk".format(script_name)
    with open(path, "r") as ahk_script:
        script_str += ahk_script.read()
    return script_str

def run_ahk(script_name, **kwargs):
    if settings.is_test_mode():
        print("Run AHK script {} {}".format(script_name, kwargs))
        return
    return ahk.run_script(file_to_script(script_name, **kwargs))

def add_attempt():
    curr_attempts = 0
    if os.path.exists("./attempts.txt"):
        with open("attempts.txt", "r") as f:
            curr_attempts = int(f.read().strip())
    with open("attempts.txt", "w") as f:
        f.write(str(curr_attempts + 1))
