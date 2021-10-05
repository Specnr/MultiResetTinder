import json
from pathlib import Path


with open("./settings.json", "r") as f:
    settings = json.load(f)

global_pid = 81461

def is_test_mode():
    return settings['test-mode']

def get_global_test_pid():
    global global_pid
    global_pid += 1
    return global_pid

def get_num_instances():
    return int(settings['num-instances'])

def get_max_concurrent():
    return int(settings['max-concurrent'])

def get_max_concurrent_boot():
    return int(settings['max-concurrent-boot'])

def get_unfreeze_delay():
    return float(settings['unfreeze-delay']) / 1000.0

def get_unfrozen_queue_size():
    return int(settings['unfrozen-queue-size'])

def get_hotkeys():
    return settings['hotkeys']

def should_use_tts():
    return not settings['disable-tts']

def get_loop_delay():
    return float(settings['loop-delay']) / 1000.0

def get_lines_from_bottom():
    return int(settings['lines-from-bottom'])

def get_multimc_executable():
    return Path(settings['multimc-executable'])

def get_base_instance_name():
    return settings['template-instance']

def get_boot_delay():
    return float(settings['boot-delay'])

def get_debug_interval():
    return 5.0

def get_switch_delay():
    return float(settings['switch-delay'])

def get_obs_delay():
    return float(settings['obs-delay'])

def is_fullscreen_enabled():
    return settings['fullscreen']

# Path(settings["old-worlds"]).mkdir(parents=True, exist_ok=True)