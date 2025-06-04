import requests
import json
import time

host = "localhost"
port = 15120


class ApiError(Exception):
    """
    Indicates an error while calling the Fusion REST API.
    """

    def __init__(self, endpoint, code, reason):
        """
        Creates an new `ApiError` instance.
        """
        self._endpoint = endpoint
        self._code = code
        self._reason = reason

    def __repr__(self):
        return "<ApiError at {}: {} {}>".format(self._endpoint, self._code, self._reason)

    def __str__(self):
        return self.__repr__()

    def endpoint(self):
        """
        Gives the name of the API endpoint for which the error happened.
        """
        return self._endpoint

    def code(self):
        """
        Gives the HTTP response code for the error, as returned by the API.
        Also see `.reason()` for a more readable description of the problem.
        """
        return self._code

    def reason(self):
        """
        Gives the reason for the error, as returned by the API. (a string)
        """
        return self._reason


def __make_address(endpoint):
    return "http://{}:{}{}".format(host, port, endpoint)


def __raise_on_error(endpoint, response):
    if (response.status_code < 200) or (response.status_code > 299):
        raise ApiError(endpoint, response.status_code, response.reason)


def __get(endpoint):
    response = requests.get(__make_address(endpoint))
    __raise_on_error(endpoint, response)
    # print("debug: received text [[%s]]" % response.text)
    return response.json()


def __get_plain(endpoint):
    response = requests.get(__make_address(endpoint))
    __raise_on_error(endpoint, response)
    return response.text


def __get_value(endpoint, key):
    struct = __get(endpoint)
    return struct[key]


def __put(endpoint, obj):
    body = json.dumps(obj)
    __put_plain(endpoint, body)


def __put_plain(endpoint, body):
    response = requests.put(__make_address(endpoint), data=body)
    __raise_on_error(endpoint, response)


def __put_value(endpoint, key, value):
    struct = {key: value}
    __put(endpoint, struct)


# low-level API

def _get_state():
    return __get_value("/v1/protocol/state", 'State')


def _set_state(value):
    return __put_value("/v1/protocol/state", 'State', value)


def _get_selected_protocol():
    return __get_value("/v1/protocol/current", 'Name')


def _set_selected_protocol(value):
    return __put_value("/v1/protocol/current", 'Name', value)


def _get_protocol_progress():
    """
    According to Andor returns the following variables formatted like
    "StartTime": "2019-01-31T11:53:37.6799174Z",
    "ElapsedTime": "00:00:06.9610000",
    "RemainingTime": "00:00:20.4000000",
    "EstimatedTimeOfCompletion": "2019-01-31T11:54:05.1522273Z",
    "Progress": 0.2
    """
    return __get("/v1/protocol/progress")


# low-level API custom by Jana

def _get_current_image_path():
    """This should return a string like:
    "Path": "C:\\FusionImages\\Snap.ims"
    """
    return __get_value("/v1/datasets/current", "Path")


def _get_list_of_devices():
    """
    This should return a list like "Devices": ["dummy-camera","dummy-xy-stage","dummy-z-control","microscope",
    "light-source", "dummy-confocal-unit","dummy-light-source"]
    """
    return __get_value("/v1/devices", "Devices")


def _get_list_of_device_features(device_name):
    return __get_plain("/v1/devices/" + device_name)


def _get_value_of_feature_of_device(device_name, feature_name):
    return __get_value("/v1/devices/" + device_name + "/" + feature_name + "/", "Value")


def _set_value_of_feature_of_device(device_name, feature_name, value):
    return __put_value("/v1/devices/" + device_name + "/", feature_name, value)


# high-level API

def change_protocol(name):
    """
    Changes to the protocol named.
    """
    _set_selected_protocol(name)


def run(name):
    """
    Changes to the named protocol and starts to run it.
    If no name is given, runs the currently-selected protocol.
    NB: this function does not block until the state changes; use `get_state()` to be sure the protocol
    has actually started.
    """
    if name is not None:
        _set_selected_protocol(name)
    _set_state('Running')


def pause():
    """
    Pauses a protocol that is currently running.
    The protocol can be resumed with a `resume()` call.
    It is an error to call this if no protocol is running.
    NB: this function does not block until the state changes; use `get_state()` to be sure the protocol
    has actually paused.
    """
    _set_state('Paused')


def resume():
    """
    Resumes a previously-paused protocol.
    It is an error to call this if no protocol is running or paused.
    NB: this function does not block until the state changes; use `get_state()` to be sure the protocol
    has actually resumed.
    """
    _set_state('Running')


def stop():
    """
    Stops a protocol that is currently running.
    It is an error to call this if no protocol is running or paused.
    NB: this function does not block until the state changes; use `get_state()` to be sure the protocol
    has actually stopped.
    """
    _set_state('Aborted')


def get_state():
    """
    Returns the current run state of the protocol.
    Always returns one of the following strings:
    * Idle:     The protocol is not running.
    * Waiting:  User requested protocol run (transitional state).
    * Running:  Protocol is running.
    * Paused:   Protocol was running and is now paused.
    * Aborting: User has requested protocol stop (transitional state).
    * Aborted:  The protocol has stopped (transitional state, will become Idle).
    """
    return _get_state()


def wait_until_state(target_state, check_interval_secs):
    """
    Waits until the protocol is in the given `target_state`.
    This call will block until the target state is reached.
    """
    while _get_state() != target_state:
        time.sleep(check_interval_secs)


def wait_until_idle():
    """
    Waits until the protocol has completed, checking every 1 second.
    This call will block until the target state is reached.
    """
    wait_until_state('Idle', 1)


def wait_until_running():
    """
    Waits until the protocol has started up, checking every 100 milliseconds.
    This call will block until the target state is reached.
    """
    wait_until_state('Running', 0.1)


def completion_percentage():
    """
    Returns the current protocol completion percentage, as a number ranging from 0 to 100.
    If called after the protocol has stopped, this function will return whatever the final completion percentage was.
    This may be less than 100 if the protocol was manually stopped early.
    """
    info = _get_protocol_progress()
    return 100 * info['Progress']


def run_protocol_completely(protocol_name):
    """
    Tells Fusion to run the named protocol, and waits for it to complete.
    This call will block until the protocol has finished.
    """
    run(protocol_name)
    wait_until_running()
    wait_until_idle()


# high level API custom Jana
def get_current_image_path():
    """
    Gets the current image path and returns it to the user as a string
    """
    return _get_current_image_path()


def get_list_of_devices():
    """
    Gets all devices as a list
    """
    return _get_list_of_devices()


def get_list_of_device_features(device_name):
    return _get_list_of_device_features(device_name)


def get_value_of_feature_of_device(device_name, feature_value):
    return _get_value_of_feature_of_device(device_name, feature_value)


def for_all_devices_get_all_features():
    device_list = get_list_of_devices()
    print(device_list)
    # ['andor-bob', 'light-source', 'xyz-stage', 'microscope', 'confocal-unit', 'sona-2', 'sona-1']
    for device in device_list:
        print(device)
        device_features = get_list_of_device_features(device)
        print("    ", device_features)
    return


def time_string_to_sensible_output(time_string):
    from dateutil.parser import isoparse
    dt = isoparse(time_string)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def time_delta_to_sensible_output(time_string):
    if time_string.startswith("-"):
        time_string = time_string[1:]
    try:
        h, m, s = time_string.split(":")
        s = s.split(".")[0]  # remove ms and even smaller time units also works if there are no smaller things
        return_string = f"{h} h {m} min {s} s"
    except ValueError:
        return_string = "Time string not in h:m:s format, not read in properly"
    return return_string


def get_protocol_progress():
    progress = _get_protocol_progress()
    start_time = time_string_to_sensible_output(progress["StartTime"])
    elapsed_time = time_delta_to_sensible_output(progress["ElapsedTime"])
    remaining_time = time_delta_to_sensible_output(progress["RemainingTime"])
    estimated_completion_time = time_string_to_sensible_output(progress["EstimatedTimeOfCompletion"])
    progress_percentage = progress["Progress"] * 100
    return_string = f"Started : {start_time} \n " + \
                    f"Elapsed time: {elapsed_time} \n " + \
                    f"Remaining time: {remaining_time} \n " + \
                    f"Estimated completion: {estimated_completion_time} \n " + \
                    f"Progress in %: {progress_percentage:.2f}"
    return return_string


def get_values_of_stage():
    get_value_of_feature_of_device("xyz-stage", "xposition")


if __name__ == "__main__":
    print(time_string_to_sensible_output("2019-01-31T11:53:37.6799174Z"))
    print(time_delta_to_sensible_output("00:00:06.9610000"))
