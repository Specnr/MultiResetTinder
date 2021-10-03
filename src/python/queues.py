import settings
from instance import Instance, State


all_instances = [Instance(i+1) for i in range(settings.get_num_instances())]

all_queues = {}

for state in State:
    all_queues[state] = []

all_queues[State.DEAD] = [inst for inst in all_instances]

def update_all():
    for state in all_queues.keys():
        all_queues[state].clear()
    for inst in all_instances:
        all_queues[inst.state].append(inst)
    for state in all_queues.keys():
        all_queues[state].sort(key=lambda inst: inst.priority)

def get_all_instances():
    return all_instances

def get_dead_instances():
    return all_queues[State.DEAD]

def get_booting_instances():
    return all_queues[State.BOOTING]

def get_pregen_instances():
    return all_queues[State.PREGEN]

def get_free_instances():
    return all_queues[State.FREE]

def get_gen_instances():
    return all_queues[State.GEN]

def get_paused_instances():
    return all_queues[State.PAUSED]

def get_ready_instances():
    return all_queues[State.READY]

def get_approved_instances():
    return all_queues[State.APPROVED]

def get_all_queues():
    return all_queues