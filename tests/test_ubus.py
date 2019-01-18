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

import json
import pytest
import subprocess
import websocket

from .fixtures import (
    authentication, address_family, ubusd_test, rpcd, ubus_ws, ubus_controller, ws_client,
    ID,
    ubus_notify, UBUS_PATH,
)


def test_incorrect_input(ubusd_test, ubus_ws, ubus_controller, ws_client):
    _, read_output, _, _ = ubus_ws
    last_output = read_output()
    ws_client, _ = ws_client
    ws_client("rgh")
    last_output = read_output(last_output)
    assert last_output[-1]['error'] == 'Not in json format.'
    assert last_output[-1]['result'] is False
    ws_client(json.dumps({}))
    last_output = read_output(last_output)
    assert last_output[-1]['error'] == 'Action not defined.'
    assert last_output[-1]['result'] is False
    ws_client(json.dumps({"action": "subscribe"}))
    last_output = read_output(last_output)
    assert last_output[-1]['error'] == 'Params not defined.'
    assert last_output[-1]['result'] is False
    ws_client(json.dumps({"action": "unkonwn", "params": ["web"]}))
    last_output = read_output(last_output)
    assert last_output[-1]['error'] == "Unknown action 'unkonwn'"
    assert last_output[-1]['result'] is False


def test_subscribe_and_unsubscribe(ubusd_test, ubus_ws, ubus_controller, ws_client):
    _, read_output, _, _ = ubus_ws
    last_output = read_output()
    ws_client, _ = ws_client
    ws_client(json.dumps({"action": "subscribe", "params": ["test1", "test2", "test3"]}))
    last_output = read_output(last_output)
    assert last_output[-1]["result"] is True
    assert set(last_output[-1]["subscriptions"]) == set([u'test1', u'test2', u'test3'])
    ws_client(json.dumps({"action": "unsubscribe", "params": ["test1", "test3"]}))
    last_output = read_output(last_output)
    assert last_output[-1]["result"] is True
    assert set(last_output[-1]["subscriptions"]) == set([u'test2'])


def test_notification(ubusd_test, ubus_ws, ubus_controller, ws_client, ubus_notify):
    _, read_output, _, _ = ubus_ws
    last_output = read_output()
    ws_client, _ = ws_client

    ws_client(json.dumps({"action": "subscribe", "params": ["testa", "testb", "testc"]}))
    last_output = read_output(last_output)
    assert last_output[-1]["result"] is True
    assert set(last_output[-1]["subscriptions"]) == set([u'testa', u'testb', u'testc'])

    ubus_notify.notify("testa", "testa", {"test": "a"})
    last_output = read_output(last_output)
    assert last_output[-1] == {
        'action': 'testa',
        'data': {'test': 'a'},
        'kind': 'notification',
        'module': 'testa',
        'controller_id': ID,
    }

    ubus_notify.notify("testd", "testd", {"test": "d"})
    ubus_notify.notify("testb", "testb", {"test": "b"})
    last_output = read_output(last_output)
    assert {e["module"] for e in last_output if "module" in e} == {"testa", "testb"}

    ws_client(json.dumps({"action": "subscribe", "params": ["testd"]}))
    last_output = read_output(last_output)
    assert last_output[-1]["result"] is True
    assert set(last_output[-1]["subscriptions"]) == set([u'testa', u'testb', u'testc', u'testd'])
    ws_client(json.dumps({"action": "unsubscribe", "params": ["testc"]}))
    last_output = read_output(last_output)
    assert last_output[-1]["result"] is True
    assert set(last_output[-1]["subscriptions"]) == set([u'testa', u'testb', u'testd'])
    ubus_notify.notify("testc", "testc", {"test": "c"})
    ubus_notify.notify("testd", "testd", {"test": "d"})
    last_output = read_output(last_output)
    assert {e["module"] for e in last_output if "module" in e} == {"testa", "testb", "testd"}


@pytest.mark.parametrize("authentication", ["ubus"], ids=["auth_ubus"], indirect=True, scope="function")
def test_authentication_ubus(authentication, ubus_ws, rpcd, ubus_controller):
    _, _, host, port = ubus_ws

    # test fail
    ws = websocket.WebSocket()
    with pytest.raises(websocket.WebSocketBadStatusException):
        ws.connect(
            "ws://%s:%d/" % ("[%s]" % host if ":" in host else host, port),
            cookie="foris.ws.session=%s" % "EEEEEEEEEEEEEE",
        )
        ws.close()

    # test pass
    subprocess.check_output([
        "ubus", "-s", UBUS_PATH,  "wait_for", "session",
    ])
    raw_session = subprocess.check_output([
        "ubus", "-s", UBUS_PATH,  "call", "session", "create", '{"timeout":600}'
    ])
    session_id = json.loads(raw_session)["ubus_rpc_session"]
    subprocess.check_output([
        "ubus", "-s", UBUS_PATH,  "call", "session", "grant", json.dumps({
            "ubus_rpc_session": session_id, "scope": "ubus",
            "objects": [["websocket-listen", "listen-allowed"]]
        })
    ])

    ws.connect(
        "ws://%s:%d/" % ("[%s]" % host if ":" in host else host, port),
        cookie="foris.ws.session=%s" % session_id,
    )
    ws.send(b'{"action": "subscribe", "params": ["testd"]}')
    res = ws.recv()
    assert json.loads(res)["result"]
    ws.close()

    # test rpcd not running
    rpcd.terminate()
    rpcd.wait()

    with pytest.raises(websocket.WebSocketBadStatusException):
        ws.connect(
            "ws://%s:%d/" % ("[%s]" % host if ":" in host else host, port),
            cookie="foris.ws.session=%s" % session_id,
        )
        ws.close()
