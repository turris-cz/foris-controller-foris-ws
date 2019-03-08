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

import asyncio
import argparse
import logging
import os
import typing
import re
import signal
import websockets


from . import __version__
from .bus_listener import make_bus_listener
from .ws_handling import connection_handler as ws_connection_handler

logger = logging.getLogger(__name__)


available_buses: typing.List[str] = ['unix-socket']


try:
    __import__("ubus")
    available_buses.append("ubus")
except ModuleNotFoundError:
    pass


try:
    __import__("paho.mqtt.client")
    available_buses.append("mqtt")
except ModuleNotFoundError:
    pass


def main() -> typing.NoReturn:
    # Parse the command line options
    parser = argparse.ArgumentParser(prog="foris-ws")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", default=False)
    parser.add_argument('--version', action='version', version=__version__)

    auth_choices = ["filesystem", "none"]
    if "ubus" in available_buses:
        auth_choices.append("ubus")
    parser.add_argument(
        "-a", "--authentication", type=str,
        choices=auth_choices,
        help="Which authentication method should be used", required=True
    )

    parser.add_argument(
        "--host", type=str, help="Hostname of the websocket server.", required=True
    )
    parser.add_argument(
        "--port", type=int, help="Port of the websocket server.", required=True
    )

    subparsers = parser.add_subparsers(help="buses", dest="bus")
    subparsers.required = True

    unix_parser = subparsers.add_parser(
        "unix-socket", help="use unix socket to obtain notifications")
    unix_parser.add_argument("--path", dest="path", default='/tmp/foris-controller-notify.soc')
    if "ubus" in available_buses:
        ubus_parser = subparsers.add_parser("ubus", help="use ubus to obtain notificatins")
        ubus_parser.add_argument("--path", dest="path", default='/var/run/ubus.sock')
    if "mqtt" in available_buses:
        mqtt_parser = subparsers.add_parser("mqtt", help="use mqtt to obtain notificatins")
        mqtt_parser.add_argument("--mqtt-host", dest="mqtt_host", default='localhost')
        mqtt_parser.add_argument("--mqtt-port", dest="mqtt_port", default=1883, type=int)
        mqtt_parser.add_argument(
            "--mqtt-passwd-file", type=lambda x: read_passwd_file(x),
            help="path to passwd file (first record will be used to authenticate)",
            default=None,
        )

    options = parser.parse_args()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
    logger.debug("Version %s" % __version__)

    if options.bus == "ubus":
        from foris_client.buses.ubus import UbusListener
        listener_class = UbusListener
        listener_args = {"socket_path": options.path}
        logger.debug("Using ubus to listen for notifications.")

    elif options.bus == "unix-socket":
        from foris_client.buses.unix_socket import UnixSocketListener
        logger.debug("Using unix-socket to listen for notifications.")
        try:
            os.unlink(options.path)
        except OSError:
            pass
        listener_class = UnixSocketListener
        listener_args = {"socket_path": options.path}

    elif options.bus == "mqtt":
        from foris_client.buses.mqtt import MqttListener
        logger.debug("Using mqtt to listen for notifications.")
        listener_class = MqttListener
        listener_args = {
            "host": options.mqtt_host, "port": options.mqtt_port,
            "credentials": options.mqtt_passwd_file,
        }

    if options.authentication == "ubus":
        from foris_ws.authentication.ubus import authenticate
    elif options.authentication == "filesystem":
        from foris_ws.authentication.filesystem import authenticate
    elif options.authentication == "none":
        from foris_ws.authentication.none import authenticate

    loop = asyncio.get_event_loop()

    # prepare bus listener
    bus_listener = make_bus_listener(listener_class, **listener_args)

    def shutdown():
        bus_listener.disconnect()
        loop.stop()

    loop.add_signal_handler(signal.SIGTERM, shutdown)
    loop.add_signal_handler(signal.SIGINT, shutdown)

    async def run_listener():
        logger.debug("Starting to listen to foris bus.")
        res = await loop.run_in_executor(None, bus_listener.listen)
        logger.debug("Finished listening to foris bus. (res=%s)", res)

    # prepare websocket
    websocket_server = websockets.serve(
        ws_connection_handler,
        options.host,
        options.port,
        process_request=authenticate,
    )

    asyncio.ensure_future(websocket_server)
    asyncio.ensure_future(run_listener())
    loop.run_forever()


def read_passwd_file(path: str) -> typing.Tuple[str]:
    """ Returns username and password from passwd file
    """
    with open(path, "r") as f:
        return re.match(r"^([^:]+):(.*)$", f.readlines()[0][:-1]).groups()


if __name__ == "__main__":
    main()
