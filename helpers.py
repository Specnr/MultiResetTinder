import os
import shutil
from ahk import AHK
ahk = AHK()


class Instance:
    reset_state = 0
    when_genned = 0
    is_suspended = False

    def __init__(self, pid, num, mcdir):
        self.PID = pid
        self.num = num
        self.mcdir = mcdir

    def suspend(self):
        run_ahk("./ahk/suspendInstance.ahk", pid=self.PID)
        self.is_suspended = True

    def resume(self):
        run_ahk("./ahk/resumeInstance.ahk", pid=self.PID)
        self.is_suspended = False

    def is_in_world(self):
        # Read logs and see if is done world gen
        pass

    def is_in_title(self):
        # Read logs and see if saving is done
        pass


def run_ahk(script_name, **kwargs):
    script_str = ""
    for key in kwargs:
        script_str += f"{key} := {kwargs[key]}\n"
    with open(script_name, "r") as ahk_script:
        script_str += ahk_script.read()
    out = ahk.run_script(script_str)
    return out


def move_worlds(inst, old_worlds):
    for dir_name in os.listdir(inst.mcdir + "/saves"):
        if dir_name.startswith("New World"):
            shutil.move(dir_name, old_worlds)
