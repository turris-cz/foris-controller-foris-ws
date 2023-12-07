#
# foris-ws
# Copyright (C) 2017 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
#

import copy
import os
import pytest
import subprocess
import socket
import time
import websocket
import json
import threading
import uuid

from paho.mqtt import client as mqtt


UBUS_PATH = "/tmp/ubus-foris-ws-test.soc"
SOCK_PATH = "/tmp/foris-ws-test.soc"
NOTIFICATIONS_SOCK_PATH = "/tmp/foris-ws-notifications-test.soc"
WS_HOST4 = "127.0.0.1"
WS_HOST6 = "::1"
WS_PORT = 8888
WS_OUTPUT = "/tmp/foris-ws-test-output.json"
MQTT_PORT = 11883
MQTT_HOST = "localhost"

ID = f"{uuid.getnode():016X}"


def read_wc_client_output(old_data=None):
    while not os.path.exists(WS_OUTPUT):
        time.sleep(0.2)

    while True:
        with open(WS_OUTPUT) as f:
            data = f.readlines()
        last_data = [json.loads(e.strip()) for e in data]
        if not old_data == last_data:
            break
        time.sleep(0.2)

    return last_data


def _wait_for_opened_socket(host, ipv6):
    s = socket.socket(socket.AF_INET6 if ipv6 else socket.AF_INET)
    while True:
        try:
            s.connect((host, WS_PORT))
            s.close()
            break
        except Exception:
            time.sleep(0.2)


@pytest.fixture(params=["none", "ubus"], ids=["auth_none", "auth_ubus"], scope="function")
def authentication(request):
    return request.param


@pytest.fixture(params=["ipv6", "ipv4"], scope="function")
def address_family(request):
    if request.param == "ipv6":
        return WS_HOST6, True
    elif request.param == "ipv4":
        return WS_HOST4, False


@pytest.fixture(scope="function")
def ubus_ws(request, ubusd_test, address_family, authentication, rpcd):
    host, ipv6 = address_family
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.3)

    new_env = copy.deepcopy(dict(os.environ))
    new_env["FORIS_WS_UBUS_AUTH_SOCK"] = UBUS_PATH
    kwargs = {"env": new_env}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, "wb")
        kwargs["stderr"] = devnull
        kwargs["stdout"] = devnull
    args = [
        "python",
        "-m",
        "foris_ws",
        "-d",
        "-a",
        authentication,
        "--host",
        host,
        "--port",
        str(WS_PORT),
        "ubus",
        "--path",
        UBUS_PATH,
    ]
    process = subprocess.Popen(args, **kwargs)
    _wait_for_opened_socket(host, ipv6)

    yield process, read_wc_client_output, host, WS_PORT
    process.kill()


@pytest.fixture(scope="function")
def unix_ws(request, ubusd_test, address_family, authentication, rpcd):
    host, ipv6 = address_family
    try:
        os.unlink(NOTIFICATIONS_SOCK_PATH)
    except Exception:
        pass

    new_env = copy.deepcopy(dict(os.environ))
    new_env["FORIS_WS_UBUS_AUTH_SOCK"] = UBUS_PATH
    kwargs = {"env": new_env}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, "wb")
        kwargs["stderr"] = devnull
        kwargs["stdout"] = devnull
    args = [
        "python",
        "-m",
        "foris_ws",
        "-d",
        "-a",
        authentication,
        "--host",
        host,
        "--port",
        str(WS_PORT),
        "unix-socket",
        "--path",
        NOTIFICATIONS_SOCK_PATH,
    ]
    process = subprocess.Popen(args, **kwargs)
    _wait_for_opened_socket(host, ipv6)

    yield process, read_wc_client_output, host, WS_PORT
    process.kill()


@pytest.fixture(scope="function")
def mqtt_ws(request, mosquitto_test, address_family, authentication, rpcd):
    host, ipv6 = address_family

    new_env = copy.deepcopy(dict(os.environ))
    new_env["FORIS_WS_UBUS_AUTH_SOCK"] = UBUS_PATH
    kwargs = {"env": new_env}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, "wb")
        kwargs["stderr"] = devnull
        kwargs["stdout"] = devnull
    args = [
        "python",
        "-m",
        "foris_ws",
        "-d",
        "-a",
        authentication,
        "--host",
        host,
        "--port",
        str(WS_PORT),
        "mqtt",
        "--mqtt-host",
        MQTT_HOST,
        "--mqtt-port",
        str(MQTT_PORT),
    ]
    process = subprocess.Popen(args, **kwargs)
    _wait_for_opened_socket(host, ipv6)

    yield process, read_wc_client_output, host, WS_PORT
    process.kill()


@pytest.fixture(scope="function")
def unix_controller(request, unix_ws):
    try:
        os.unlink(SOCK_PATH)
    except Exception:
        pass

    while not os.path.exists(NOTIFICATIONS_SOCK_PATH):
        time.sleep(0.3)

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, "wb")
        kwargs["stderr"] = devnull
        kwargs["stdout"] = devnull

    new_env = copy.deepcopy(dict(os.environ))
    new_env["FC_UPDATER_MODULE"] = "foris_controller_testtools.svupdater"
    kwargs["env"] = new_env
    process = subprocess.Popen(
        [
            "foris-controller",
            "-d",
            "-m",
            "about",
            "-m",
            "web",
            "-m",
            "remote",
            "--backend",
            "mock",
            "unix-socket",
            "--path",
            SOCK_PATH,
            "--notifications-path",
            NOTIFICATIONS_SOCK_PATH,
        ],
        **kwargs,
    )
    yield process
    process.kill()


@pytest.fixture(scope="function")
def ubus_controller(request, ubusd_test, ubus_ws):
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.3)

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, "wb")
        kwargs["stderr"] = devnull
        kwargs["stdout"] = devnull

    new_env = copy.deepcopy(dict(os.environ))
    new_env["FC_UPDATER_MODULE"] = "foris_controller_testtools.svupdater"
    kwargs["env"] = new_env
    process = subprocess.Popen(
        [
            "foris-controller",
            "-d",
            "-m",
            "about",
            "-m",
            "web",
            "-m",
            "remote",
            "--backend",
            "mock",
            "ubus",
            "--path",
            UBUS_PATH,
        ],
        **kwargs,
    )
    yield process

    process.kill()


@pytest.fixture(scope="function")
def mqtt_controller(request, mosquitto_test, mqtt_ws):
    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, "wb")
        kwargs["stderr"] = devnull
        kwargs["stdout"] = devnull

    new_env = copy.deepcopy(dict(os.environ))
    new_env["FC_UPDATER_MODULE"] = "foris_controller_testtools.svupdater"
    kwargs["env"] = new_env
    process = subprocess.Popen(
        [
            "foris-controller",
            "-d",
            "-m",
            "about",
            "-m",
            "web",
            "-m",
            "remote",
            "--backend",
            "mock",
            "mqtt",
            "--host",
            MQTT_HOST,
            "--port",
            str(MQTT_PORT),
        ],
        **kwargs,
    )
    yield process

    process.kill()


@pytest.fixture(scope="session")
def ubusd_test():
    try:
        os.unlink(UBUS_PATH)
    except Exception:
        pass

    ubusd_instance = subprocess.Popen(["ubusd", "-A", "tests/ubus-acl", "-s", UBUS_PATH])
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.2)
    yield ubusd_instance
    ubusd_instance.kill()
    try:
        os.unlink(UBUS_PATH)
    except Exception:
        pass


@pytest.fixture(scope="session")
def mosquitto_test(request):

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, "wb")
        kwargs["stderr"] = devnull
        kwargs["stdout"] = devnull

    mosquitto_path = os.environ.get("MOSQUITTO_PATH", "/usr/sbin/mosquitto")
    mosquitto_instance = subprocess.Popen([mosquitto_path, "-v", "-p", str(MQTT_PORT)], **kwargs)
    yield mosquitto_instance
    mosquitto_instance.kill()


@pytest.fixture(scope="function")
def rpcd(ubusd_test):

    while not os.path.exists(UBUS_PATH):
        time.sleep(0.2)

    rpcd_instance = subprocess.Popen(["rpcd", "-s", UBUS_PATH])
    yield rpcd_instance
    rpcd_instance.kill()


@pytest.fixture(scope="function")
def ws_client(address_family, rpcd):
    host, ipv6 = address_family
    if ipv6:
        host = "[%s]" % host
    try:
        os.unlink(WS_OUTPUT)
    except Exception:
        pass

    # create cookies in ubus
    subprocess.check_output(["ubus", "-s", UBUS_PATH, "wait_for", "session"])
    raw_session = subprocess.check_output(
        ["ubus", "-s", UBUS_PATH, "call", "session", "create", '{"timeout":600}']
    )
    session_id = json.loads(raw_session)["ubus_rpc_session"]
    subprocess.check_output(
        [
            "ubus",
            "-s",
            UBUS_PATH,
            "call",
            "session",
            "grant",
            json.dumps(
                {
                    "ubus_rpc_session": session_id,
                    "scope": "ubus",
                    "objects": [["websocket-listen", "listen-allowed"]],
                }
            ),
        ]
    )

    exiting = [False]
    started = [False]
    lock = threading.Lock()
    event = threading.Event()
    data_container = [""]

    def send_message(msg):
        data_container[0] = msg
        event.set()

    with open(WS_OUTPUT, "w") as f:
        f.flush()

    def on_message(ws, message):
        with lock:
            with open(WS_OUTPUT, "a") as f:
                f.write(message + "\n")
                f.flush()

    def on_open(ws):
        def msg_loop():
            while True:
                event.wait(0.2)
                if event.is_set():
                    ws.send(data_container[0])
                    event.clear()
                else:
                    if exiting[0]:
                        break
            ws.close()

        thread = threading.Thread(target=msg_loop)
        thread.daemon = True
        thread.start()

    def worker():
        ws = websocket.WebSocketApp(
            "ws://%s:%d/" % (host, WS_PORT),
            on_message=on_message,
            on_open=on_open,
            cookie="foris.ws.session=%s" % session_id,
        )
        started[0] = True
        ws.run_forever()

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()

    while not started[0]:
        time.sleep(0.2)

    yield send_message, session_id
    exiting[0] = True
    thread.join(0.2)


@pytest.fixture(scope="function")
def unix_notify(unix_ws):
    from foris_controller.buses.unix_socket import UnixSocketNotificationSender

    while not os.path.exists(NOTIFICATIONS_SOCK_PATH):
        time.sleep(0.2)
    sender = UnixSocketNotificationSender(NOTIFICATIONS_SOCK_PATH)
    yield sender
    try:
        sender.disconnect()
    except RuntimeError:
        pass  # wasn't connected


@pytest.fixture(scope="function")
def ubus_notify(ubus_ws):
    from foris_controller.buses.ubus import UbusNotificationSender

    while not os.path.exists(UBUS_PATH):
        time.sleep(0.2)
    sender = UbusNotificationSender(UBUS_PATH)
    yield sender
    try:
        sender.disconnect()
    except RuntimeError:
        pass  # wasn't connected


@pytest.fixture(scope="function")
def mqtt_notify(mqtt_ws):
    from foris_controller.buses.mqtt import MqttNotificationSender

    # wait till object present
    def on_connect(client, userdata, flags, rc):
        client.subscribe(f"foris-controller/{ID}/notification/remote/action/advertize")

    def on_message(client, userdata, msg):
        try:
            if json.loads(msg.payload)["data"]["state"] in ["started", "running"]:
                client.loop_stop(True)
        except Exception:
            pass

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 30)
    client.loop_start()
    client._thread.join(10)
    client.disconnect()

    sender = MqttNotificationSender(MQTT_HOST, MQTT_PORT, None)

    yield sender
    try:
        sender.disconnect()
    except RuntimeError:
        pass  # wasn't connected
