import json
from pathlib import Path
import sys


with open(sys.argv[1], "r") as f:
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

def get_multimc_path():
    return Path(settings['multi-mc-path'])

def get_base_instance_name():
    return settings['template-instance']

def get_boot_delay():
    return float(settings['boot-delay'])

def get_switch_delay():
    return float(settings['switch-delay'])

def get_obs_delay():
    return float(settings['obs-delay'])

def is_fullscreen_enabled():
    return settings['fullscreen']

def get_debug_interval():
    return 1.0

def get_test_boot_time():
    return 5.0

def get_test_worldgen_time():
    return 2.0

def should_auto_launch():
    return settings['auto-launch']

def get_obs_web_host():
    if is_test_mode():
        return None
    return settings['obs-settings']['web-host']

def get_obs_port():
    if is_test_mode():
        return None
    return settings['obs-settings']['port']

def get_obs_password():
    if is_test_mode():
        return None
    return settings['obs-settings']['password']

# Path(settings["old-worlds"]).mkdir(parents=True, exist_ok=True)