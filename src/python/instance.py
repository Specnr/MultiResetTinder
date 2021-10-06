import settings
import helpers as hlp
from helpers import get_time
import os
import shutil
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path

num_per_state = {}

def assign_to_state(instance, state):
    global num_per_state
    if state not in num_per_state:
        num_per_state[state] = 0
    num_per_state[state] = num_per_state[state] + 1
    instance.state = state
    instance.priority = num_per_state[state]

def has_passed(start_time, duration):
    return (hlp.get_time() - start_time) > duration

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

class DisplayState(Enum):
    HIDDEN = 0
    FOCUSED = 1
    PRIMARY = 2

class Process:
    def assign_pid(self, all_processes):
        if settings.is_test_mode():
            self.pid = settings.get_global_test_pid()
            return
        all_pids = hlp.get_pids()
        for pid in all_pids:
            pid_maps_to_instance = False
            for instance in all_processes:
                if instance.pid == pid:
                    pid_maps_to_instance = True
            if not pid_maps_to_instance:
                self.pid = pid

class Suspendable(Process):
    def suspend(self):
        if self.is_suspended():
            return
        self.suspended = True
        hlp.run_ahk("suspendInstance", pid=self.pid)

    def resume(self):
        if not self.is_suspended():
            return
        self.suspended = False
        hlp.run_ahk("resumeInstance", pid=self.pid)

    def is_suspended(self):
        return self.suspended



class Stateful(Suspendable):

    def mark_booting(self):
        assign_to_state(self, State.BOOTING)
        self.timestamp = get_time()
    
    def mark_pregen(self):
        self.was_active = False
        assign_to_state(self, State.PREGEN)
    
    def mark_generating(self):
        assign_to_state(self, State.GEN)
        self.timestamp = get_time()
    
    def mark_worldgen_finished(self):
        assign_to_state(self, State.PAUSED)
        self.timestamp = get_time()
    
    def mark_free(self):
        assign_to_state(self, State.FREE)
    
    def release(self):
        if self.is_suspended():
            assign_to_state(self, State.FREE)
        else:
            assign_to_state(self, State.PREGEN)
        self.timestamp = get_time()

    def mark_ready(self):
        assign_to_state(self, State.READY)

    def is_ready(self):
        return self.state == State.READY

    def mark_active(self):
        assign_to_state(self, State.ACTIVE)
        self.was_active = True

    def mark_inactive(self):
        # add to pregen
        self.mark_pregen()

class DisplayStateful(Stateful):

    def mark_primary(self):


    def is_primary(self):
        return self.displayState == DisplayState.PRIMARY

class ConditionalTransitionable(Stateful):

    def is_ready_for_freeze(self):
        duration = 2.0
        if self.state == State.PAUSED:
            duration = 2.0
        return has_passed(self.timestamp, duration)

    def is_done_unfreezing(self):
        duration = 0.5
        return has_passed(self.timestamp, duration)

    def is_ready_for_unfreeze(self):
        duration = 0.5
        return has_passed(self.timestamp, duration)
    
    def is_done_booting(self):
        duration = settings.get_boot_delay()
        return has_passed(self.timestamp, duration)

    def check_should_auto_reset(self):
        duration = 300.0
        if has_passed(self.timestamp, duration):
            self.release()
            return True
            

    def is_active(self):
        return self.state == State.ACTIVE

class Instance(ConditionalTransitionable):

    def __init__(self, num):
        self.num = num
        self.pid = -1
        self.first_reset = True
        self.suspended = False
        self.state = State.DEAD
        assign_to_state(self, self.state)
        self.timestamp = 0
        self.was_active = False
        self.name = '{}{}'.format(settings.get_base_instance_name(), self.num)
        self.mcdir = settings.get_multimc_executable() / "instances" / self.name / ".minecraft"
        self.current_world = None
    
    def boot(self):
        hlp.run_ahk("openOfflineInstance", pid=self.pid)
        
    # not yet implemented (not needed in v1)
    def create_multimc_instance(self):
        # probably make some click macro to import instance from zip
        pass

    # not yet implemented (not needed in v1)
    def create_obs_instance(self):
        # create a source with this:
        # https://github.com/Elektordi/obs-websocket-py/blob/master/obswebsocket/requests.py#L551
        # we can create a source that is a copy of a different source returned from
        # https://github.com/Elektordi/obs-websocket-py/blob/master/obswebsocket/requests.py#L524

        # obs1
        #      create a source for when this instance is active
        #   create a source for when this instance is focused
        # obs2
        #   create a source for this instance
        #       tile based on total number of instances
        pass

    def initialize_after_boot(self, all_instances):
        # assign our pid somehow
        self.assign_pid(all_instances)
        # set our title
        hlp.run_ahk("updateTitle", pid=self.pid,
            title="Minecraft* - Instance {}".format(self.num))
        # start generating world w/ duncan mod
        hlp.run_ahk("startDuncanModSession", pid=self.pid)
        # set state to generating
        self.mark_generating()

    def reset_active(self):
        self.pause()
        self.mark_inactive()

    def reset(self):
        hlp.run_ahk("reset", pid=self.pid)

    def pause(self):
        hlp.run_ahk("pauseGame", pid=self.pid)

    # TODO - call this method somewhere
    def move_worlds(self, old_worlds):
        if settings.is_test_mode():
            print("Moving worlds for instance {}".format(self.name))
            return
        for dir_name in os.listdir(self.mcdir + "/saves"):
            # TODO - i think this should be like "Attempt #X" or something cuz of duncan mod
            if dir_name.startswith("New World"):
                try:
                    shutil.move(self.mcdir + "/saves/" + dir_name,
                                old_worlds + f"/{uuid.uuid1()}")
                except:
                    continue

    # TODO - call this method somewhere
    def copy_logs(self):
        # we should copy all relevant logs out of the instance probably since we want to dynamically create instances
        pass

    def get_current_world(self):
        if self.current_world is not None:
            return self.current_world
        max_time = 0.0
        for world in (self.mcdir / "saves").iterdir():
            world_time = world.stat().st_mtime
            if world_time > max_time:
                max_time = world_time
                self.current_world = world
        return self.current_world

    def is_in_world(self):
        if settings.is_test_mode():
            if has_passed(self.timestamp, 5.0):
                return True
            return False

        cur_world = self.get_current_world()

        if cur_world is None:
            return False

        return (cur_world / "icon.png").exists()

    def __str__(self):
        return self.name