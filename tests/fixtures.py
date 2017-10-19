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

import os
import pytest
import subprocess
import socket
import time
import websocket
import json
import threading


UBUS_PATH = "/tmp/ubus-foris-ws-test.soc"
SOCK_PATH = "/tmp/foris-ws-test.soc"
NOTIFICATIONS_SOCK_PATH = "/tmp/foris-ws-notifications-test.soc"
WS_HOST = "localhost"
WS_PORT = 8888
WS_OUTPUT = "/tmp/foris-ws-test-output.json"


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


def _wait_for_opened_socket():
    s = socket.socket()
    while True:
        try:
            s.connect((WS_HOST, WS_PORT))
            s.close()
            break
        except:
            time.sleep(0.2)


@pytest.fixture(scope="module")
def ubus_ws(request, ubusd_test):
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.3)

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull
    process = subprocess.Popen([
        "bin/foris-ws", "-d", "-a", "none", "--host", WS_HOST, "--port", str(WS_PORT),
        "ubus", "--path", UBUS_PATH
    ], **kwargs)
    _wait_for_opened_socket()

    yield process, read_wc_client_output
    process.kill()


@pytest.fixture(scope="module")
def unix_ws(request):
    try:
        os.unlink(NOTIFICATIONS_SOCK_PATH)
    except:
        pass

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull
    process = subprocess.Popen([
        "bin/foris-ws", "-d", "-a", "none", "--host", WS_HOST, "--port", str(WS_PORT),
        "unix-socket", "--path", NOTIFICATIONS_SOCK_PATH
    ], **kwargs)
    _wait_for_opened_socket()

    yield process, read_wc_client_output
    process.kill()


@pytest.fixture(scope="module")
def unix_controller(request, unix_ws):
    try:
        os.unlink(SOCK_PATH)
    except:
        pass

    while not os.path.exists(NOTIFICATIONS_SOCK_PATH):
        time.sleep(0.3)

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull

    process = subprocess.Popen([
        "foris-controller", "-d", "-m", "about,web", "--backend", "mock",
        "unix-socket", "--path", SOCK_PATH, "--notifications-path", NOTIFICATIONS_SOCK_PATH
    ], **kwargs)
    yield process
    process.kill()


@pytest.fixture(scope="module")
def ubus_controller(request, ubusd_test, ubus_ws):
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.3)

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull

    process = subprocess.Popen([
        "foris-controller", "-d", "-m", "about,web", "--backend", "mock",
        "ubus", "--path", UBUS_PATH
    ], **kwargs)
    yield process

    process.kill()


@pytest.fixture(scope="session")
def ubusd_test():
    try:
        os.unlink(UBUS_PATH)
    except:
        pass

    ubusd_instance = subprocess.Popen(["ubusd", "-A", "tests/ubus-acl", "-s", UBUS_PATH])
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.2)
    yield ubusd_instance
    ubusd_instance.kill()
    try:
        os.unlink(UBUS_PATH)
    except:
        pass


@pytest.fixture(scope="function")
def ws_client():
    try:
        os.unlink(WS_OUTPUT)
    except:
        pass

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
            "ws://%s:%d/" % (WS_HOST, WS_PORT),
            on_message=on_message, on_open=on_open
        )
        started[0] = True
        ws.run_forever()

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()

    while not started[0]:
        time.sleep(0.2)

    yield send_message
    exiting[0] = True
    thread.join(0.2)


@pytest.fixture(scope="function")
def unix_notify(unix_ws):
    from foris_controller.buses.unix_socket import UnixSocketNotificationSender
    while not os.path.exists(NOTIFICATIONS_SOCK_PATH):
        time.sleep(0.2)
    sender = UnixSocketNotificationSender(NOTIFICATIONS_SOCK_PATH)
    yield sender
    sender.disconnect()


@pytest.fixture(scope="function")
def ubus_notify(ubus_ws):
    from foris_controller.buses.ubus import UbusNotificationSender
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.2)
    sender = UbusNotificationSender(UBUS_PATH)
    yield sender
    sender.disconnect()
