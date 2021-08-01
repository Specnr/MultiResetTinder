import os
import shutil
import uuid
from datetime import datetime
from ahk import AHK
ahk = AHK()


class Instance:
    reset_state = 0
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

    def is_in_world(self):
        if self.first_reset:
            return False
        # Read logs and see if is done world gen
        return self.read_logs(lambda x: "Saving chunks for level 'ServerLevel" in x and "minecraft:the_end" in x)

    def is_in_title(self):
        # Read logs and see if saving is done
        if self.first_reset:
            return True
        return self.read_logs(lambda x: "Stopping worker threads" in x)


def file_to_script(script_name, **kwargs):
    script_str = ""
    for key in kwargs:
        script_str += f'{key} := "{kwargs[key]}"\n'
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