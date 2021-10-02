import json


with open("./settings.json", "r") as f:
    settings = json.load(f)


global_pid = 81461

def is_test_mode():
    return settings['test-mode']

def get_global_test_pid():
    global global_pid
    global_pid += 1
    return global_pid

# Path(settings["old-worlds"]).mkdir(parents=True, exist_ok=True)