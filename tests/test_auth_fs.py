#
# foris-ws
# Copyright (C) 2018 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
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

import json
from werkzeug.contrib.cache import FileSystemCache

import pytest
import websocket

from .fixtures import mqtt_ws

SESSIONS_DIR = "/tmp/foris-sessions"
SESSIONS_ID = "some-testing-sessions-id"


def test_fail(mqtt_ws):
    _, _, host, port = mqtt_ws
    ws = websocket.WebSocket()

    with pytest.raises(websocket.WebSocketBadStatusException):
        ws.connect(
            "ws://%s:%d/" % ("[%s]" % host if ":" in host else host, port),
            cookie="session=not-existed-session",
        )
        ws.close()


def test_logged(mqtt_ws):
    fs_cache = FileSystemCache(SESSIONS_DIR)
    fs_cache.add('session:%s' % SESSIONS_ID, {'logged': True})

    _, _, host, port = mqtt_ws
    ws = websocket.WebSocket()

    ws.connect(
        "ws://%s:%d/" % ("[%s]" % host if ":" in host else host, port),
        cookie="session=%s" % SESSIONS_ID,
    )

    ws.send(b'{"action": "subscribe", "params": ["testd"]}')
    res = ws.recv()
    assert json.loads(res)["result"]

    ws.close()
    fs_cache.clear()


def test_not_logged(mqtt_ws):
    fs_cache = FileSystemCache(SESSIONS_DIR)
    fs_cache.add('session:%s' % SESSIONS_ID, {'logged': True})

    _, _, host, port = mqtt_ws
    ws = websocket.WebSocket()

    with pytest.raises(websocket.WebSocketBadStatusException):
        ws.connect(
            "ws://%s:%d/" % ("[%s]" % host if ":" in host else host, port),
            cookie="session=%s" % SESSIONS_ID,
        )
        ws.close()
        fs_cache.clear()
