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
import websockets

from typing import NoReturn

from . import __version__
from .bus_listener import make_bus_listener
from .ws_handling import connection_handler as ws_connection_handler

logger = logging.getLogger(__name__)


def main() -> NoReturn:
    # Parse the command line options
    parser = argparse.ArgumentParser(prog="foris-ws")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", default=False)
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        "-a", "--authentication", type=str, choices=["ubus", "none"],
        help="Which authentication method should be used", required=True
    )
    parser.add_argument(
        "--host", type=str, help="Hostname of the websocket server.", required=True
    )
    parser.add_argument(
        "--port", type=int, help="Port of the websocket server.", required=True
    )

    subparsers = parser.add_subparsers(help="buses", dest="bus")
    ubus_parser = subparsers.add_parser("ubus", help="use ubus to obtain notificatins")
    ubus_parser.add_argument("--path", dest="path", default='/var/run/ubus.sock')
    unix_parser = subparsers.add_parser(
        "unix-socket", help="use unix socket to obtain notifications")
    unix_parser.add_argument("--path", dest="path", default='/tmp/foris-controller-notify.soc')

    options = parser.parse_args()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
    logger.debug("Version %s" % __version__)

    if options.bus == "ubus":
        from foris_client.buses.ubus import UbusListener
        listener_class = UbusListener
        logger.debug("Using ubus to listen for notifications.")

    elif options.bus == "unix-socket":
        from foris_client.buses.unix_socket import UnixSocketListener
        logger.debug("Using unix-socket to listen for notifications.")
        try:
            os.unlink(options.path)
        except OSError:
            pass
        listener_class = UnixSocketListener

    if options.authentication == "ubus":
        from foris_ws.authentication.ubus import authenticate
    elif options.authentication == "none":
        from foris_ws.authentication.none import authenticate

    loop = asyncio.get_event_loop()

    # prepare bus listener
    bus_listener = make_bus_listener(listener_class, options.path)

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

    loop.run_until_complete(
        asyncio.wait([
            websocket_server,
            run_listener(),
        ])
    )
    loop.run_forever()


if __name__ == "__main__":
    main()
