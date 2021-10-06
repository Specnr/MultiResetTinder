import os
import shutil
import uuid
from datetime import datetime
from ahk import AHK
from obswebsocket import requests
ahk = AHK()


class Instance:
    when_genned = 0
    first_reset = True
    is_suspended = False

    def __init__(self, pid, num, mcdir):
        self.PID = pid
        self.num = num
        self.mcdir = mcdir

    def suspend(self):
        run_ahk("suspendInstance", pid=self.PID)
        self.is_suspended = True

    def resume(self):
        run_ahk("resumeInstance", pid=self.PID)
        self.is_suspended = False

    def reset(self):
        self.resume()
        if self.first_reset:
            run_ahk("resetFromTitle", pid=self.PID)
            self.first_reset = False
        else:
            run_ahk("reset", pid=self.PID)

    def move_worlds(self, old_worlds):
        for dir_name in os.listdir(self.mcdir + "/saves"):
            if dir_name.startswith("New World"):
                try:
                    shutil.move(self.mcdir + "/saves/" + dir_name,
                                old_worlds + f"/{uuid.uuid1()}")
                except:
                    continue

    def read_logs(self, func_check, lines_from_bottom=2):
        log_file = self.mcdir + "/logs/latest.log"
        with open(log_file, "r") as logs:
            lines = logs.readlines()
            for i in range(len(lines)):
                if (len(lines) - i <= lines_from_bottom):
                    if (func_check(lines[i])):
                        return True
        return False

    def is_in_world(self, lines_from_bottom=2):
        if self.first_reset or not bool(int(run_ahk("titleCheck", pid=self.PID))):
            return False
        # Read logs and see if is done world gen
        return self.read_logs(lambda x: "Saving chunks for level 'ServerLevel" in x and "minecraft:the_end" in x, lines_from_bottom)


def remove_from_list(from_list, idx_list):
    idx_set = set(idx_list)
    return [item for i, item in enumerate(from_list) if i not in idx_set]


def is_livesplit_open():
    return ahk.find_window(title=b"LiveSplit") is not None


def set_new_active(inst, ws, settings):
    if inst is not None:
        update_obs(ws, active=inst.num)
        inst.resume()
        # TODO: Update ls user config
        run_ahk("activateWindow", switchDelay=settings["switch-delay"],
                pid=inst.PID, idx=inst.num, obsDelay=settings["obs-delay"])
        if settings["fullscreen"]:
            run_ahk("toggleFullscreen")


def set_new_focused(inst, ws):
    update_obs(ws, focused=(inst.num if inst is not None else 0))


def file_to_script(script_name, **kwargs):
    script_str = ""
    for key in kwargs:
        script_str += f'global {key} := "{kwargs[key]}"\n'
    with open("./ahk/" + script_name + ".ahk", "r") as ahk_script:
        script_str += ahk_script.read()
    return script_str


def run_ahk(script_name, **kwargs):
    return ahk.run_script(file_to_script(script_name, **kwargs))


def add_attempt():
    curr_attempts = 0
    if os.path.exists("./attempts.txt"):
        with open("attempts.txt", "r") as f:
            curr_attempts = int(f.read().strip())
    with open("attempts.txt", "w") as f:
        f.write(str(curr_attempts + 1))


def unhide_all(ws):
    scenes_items = ws.call(requests.GetSceneItemList()).getSceneItems()
    for s in scenes_items:
        name = s["sourceName"]
        if 'active' in name or 'focus' in name:
            ws.call(requests.SetSceneItemProperties(name, visible=True))


def update_obs(ws, active=None, focused=None):
    scenes_items = ws.call(requests.GetSceneItemList()).getSceneItems()
    # Unhide current
    for s in scenes_items:
        name = s['sourceName']
        if active is not None and 'active' in name:
            if str(active) == name.split("active")[-1]:
                print(f'Unhiding {name}')
                ws.call(requests.SetSceneItemProperties(name, visible=True))
        if focused is not None and 'focus' in name:
            if str(focused) == name.split("focus")[-1]:
                print(f'Unhiding {name}')
                ws.call(requests.SetSceneItemProperties(name, visible=True))
    # Hide non-current
    for s in scenes_items:
        name = s['sourceName']
        if active is not None and 'active' in name:
            if not str(active) == name.split("active")[-1]:
                print(f'Hiding {name}')
                ws.call(requests.SetSceneItemProperties(name, visible=False))
        if focused is not None and 'focus' in name:
            if not str(focused) == name.split("focus")[-1]:
                print(f'Hiding {name}')
                ws.call(requests.SetSceneItemProperties(name, visible=False))
