import os
import shutil
import uuid
from datetime import datetime
from ahk import AHK
ahk = AHK()


num_per_state = {}


def assign_to_state(instance, state):
    global num_per_state
    if state not in num_per_state:
        num_per_state[state] = 0
    


class State(Enum):
    DEAD = 0
    BOOTING = 1
    FREE = 2
    PREGEN = 3
    GEN = 4
    PAUSED = 5
    READY = 6
    APPROVED = 7
    ACTIVE = 8

class Instance:

    def __init__(self, num):
        self.num = num
        self.priority = assign_to_state(self, 0)
        self.pid = -1
        self.first_reset = True
        self.suspended = False
        self.state = -1
        self.timestamp = 0
        self.was_active = False
    
    def boot(self):
        self.timestamp = time.time()
        run_cmd('{} --launch "{}"'.format(executable, inst_name))

    def create_multimc_instance(self):


    def create_obs_instance(self):


    def is_suspended(self):
        return self.suspended


    def initialize_after_boot(self, all_instances):
        hlp.run_ahk("updateTitle", pid=inst.PID,
            title=f"Minecraft* - Instance {i+1}")
        self.assign_pid(all_instances)
        # start generating world

    def assign_pid(self, all_instances):
        all_pids = get_pids()
        for pid in all_pids:
            pid_maps_to_instance = False
            for instance in all_instances:
                if instance.pid == pid:
                    pid_maps_to_instance = True
            if not pid_maps_to_instance:
                self.pid = pid
    
    def mark_active(self):
        assign_to_state(self, State.ACTIVE)
        was_active = True
        # hlp.set_new_active(active_instance)
    
    def mark_pregen(self):
        self.was_active = False
        assign_to_state(self, State.PREGEN)

    def is_ready_for_freeze(self):
        if self.state == 
        return has_passed(self.timestamp, duration):
    
    def check_should_auto_reset(self):
        duration = 300.0
        if has_passed(self.timestamp, duration):
            self.mark_free()

    
    def mark_inactive(self):
        # pause
        # add to free

    def mark_free(self):
        self.state = State.FREE

    def suspend(self):
        self.is_suspended = True
        run_ahk("suspendInstance", pid=self.PID)
        

    def resume(self):
        self.is_suspended = False
        run_ahk("resumeInstance", pid=self.PID)

    def reset(self):
        self.resume()
        run_ahk("reset", pid=self.PID)
        self.first_reset = False
    
    def mark_worldgen_finished(self):
        hlp.run_ahk("pauseGame", pid=gen_instances[j].PID)

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
        if self.first_reset:
            return False
        # Read logs and see if is done world gen
        return self.read_logs(lambda x: "Saving chunks for level 'ServerLevel" in x and "minecraft:the_end" in x, lines_from_bottom)


def is_livesplit_open():
    return ahk.find_window(title=b"LiveSplit") is not None


def set_new_active(inst, settings):
    if inst is not None:
        run_ahk("updateTitle", pid=inst.PID,
                title="Minecraft* - Active Instance")
        inst.resume()
        # TODO: Update ls user config
        run_ahk("activateWindow", switchDelay=settings["switch-delay"],
                pid=inst.PID, idx=inst.num, obsDelay=settings["obs-delay"])
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


def run_ahk(script_name, **kwargs):
    return ahk.run_script(file_to_script(script_name, **kwargs))


def add_attempt():
    curr_attempts = 0
    if os.path.exists("./attempts.txt"):
        with open("attempts.txt", "r") as f:
            curr_attempts = int(f.read().strip())
    with open("attempts.txt", "w") as f:
        f.write(str(curr_attempts + 1))
