import settings
import psutil
from copy import copy
from multiprocessing import Process
import os

def launch_instance_inner(inst_name):
    os.popen(f'{settings.get_multimc_path()} -l "{inst_name}"')

def launch_instance(inst):
    if settings.is_test_mode():
        return
    inst = Process(target=launch_instance_inner, args=(inst.name,))
    inst.start()

def launch_obs():
    # TODO @Sharpieman20 - replace with something better
    os.system(f'start /d "{settings.get_obs_path()}" "" obs64.exe')

def launch_livesplit():
    os.startfile(settings["livesplit-path"])

def launch_all_programs():
    if settings.is_test_mode() or not settings.should_auto_launch():
        return
    # TODO: add stat tracker?
    all_programs = ["OBS", "LiveSplit", "MultiMC"]
    are_launched = {program: False for program in all_programs}
    launch_funcs = {all_programs[0]: launch_obs, all_programs[1]: launch_livesplit, all_programs[2]: launch_multimc}
    for process in psutil.process_iter():
        for program in all_programs:
            if program in process.name():
                are_launched[program] = True
    for program in all_programs:
        if not are_launched[program]:
            launch_funcs[program]()