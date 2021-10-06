import settings
import obswebsocket.requests as obsrequests
from obswebsocket import obsws



focused_instance = None
primary_instance = None

def get_primary_instance():
    global primary_instance
    return primary_instance

def get_focused_instance():
    global focused_instance
    return focused_instance

def set_primary_instance(inst):
    global primary_instance
    primary_instance = inst

def set_focused_instance(inst):
    global focused_instance
    focused_instance = inst

def connect_to_stream_obs():
    if settings.is_test_mode():
        return
    stream_obs = obsws(settings.get_obs_web_host(),
               settings.get_obs_port(),
               settings.get_obs_password())
    stream_obs.connect()

def call_stream_websocket(*args):
    if settings.is_test_mode():
        return None
    return ws.call(args)

def get_scene_items():
    websocket_result = call_stream_websocket(obsrequests.GetSceneItemList())
    if websocket_result is None:
        return []
    return websocket_result.getSceneItems()

def set_scene_item_properties(name, visible):
    call_stream_websocket(obsrequests.SetSceneItemProperties(name, visible=True))

def set_new_primary(inst):
    print(inst)
    if inst is not None:
        global primary_instance
        if primary_instance is not None:
            primary_instance.mark_hidden()
        set_primary_instance(inst)
        primary_instance.mark_primary()
        primary_instance.resume()
        # TODO @Specnr: Update ls user config (is this still needed?)
        # TODO @Specnr: Change sound source on stream maybe?
        if settings.is_fullscreen_enabled():
            run_ahk("toggleFullscreen")

def set_new_focused(inst):
    global focused_instance
    if inst is not None:
        focused_instance = inst

def create_scene_item_for_instance(inst):
    # TODO @Specnr

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

def unhide_all():
    scene_items = get_scene_items()
    for s in scene_items:
        name = s["sourceName"]
        if 'active' in name or 'focus' in name:
            ws.call(requests.SetSceneItemProperties(name, visible=True))


def update_state():
    if settings.is_test_mode():
        return
    scenes_items = get_scene_items()
    global primary_instance
    global focused_instance
    # Unhide current
    for item in scenes_items:
        name = item['sourceName']
        if primary_instance is not None and 'active' in name:
            if str(primary_instance.num) == name.split("active")[-1]:
                print(f'Unhiding {name}')
                set_scene_item_properties(name, True)
        if focused_instance is not None and 'focus' in name:
            if str(focused_instance.num) == name.split("focus")[-1]:
                print(f'Unhiding {name}')
                set_scene_item_properties(name, True)
    # Hide non-current
    for item in scenes_items:
        name = s['sourceName']
        if active is not None and 'active' in name:
            if not str(primary_instance.num) == name.split("active")[-1]:
                print(f'Hiding {name}')
                set_scene_item_properties(name, False)
        if focused is not None and 'focus' in name:
            if not str(focused_instance.num) == name.split("focus")[-1]:
                print(f'Hiding {name}')
                set_scene_item_properties(name, False)
