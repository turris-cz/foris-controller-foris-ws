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

import argparse
import logging
import os

import threading

from foris_ws import __version__
from foris_ws.websocket_listener import make_ws_listener
from foris_ws.bus_listener import make_bus_listener

logger = logging.getLogger("foris_ws")


def manage_listeners(ws_listener, bus_listener):
    """ Starts and waits for listener threads
        and tries to perform a proper termination if necessary.

    :param ws_listener: websocket server instance
    :type ws_listener: websocket_server.WebsocketServer
    :param bus_listener: foris socket listener instace
    :type bus_listener: foris_client.buses.base.BaseListener
    """

    logger.debug("Starting to listen to websocket server.")
    ws_listener_thread = threading.Thread(target=ws_listener.run_forever)
    ws_listener_thread.daemon = True
    ws_listener_thread.start()

    logger.debug("Starting to listen to foris bus.")
    bus_listener_thread = threading.Thread(target=bus_listener.listen)
    bus_listener_thread.daemon = True
    bus_listener_thread.start()

    try:
        while True:
            ws_listener_thread.join(0.2)
            if not ws_listener_thread.is_alive():
                logger.error("websocket server is not running. Exiting...")
                break
            bus_listener_thread.join(0.2)
            if not bus_listener_thread.is_alive():
                logger.error("bus listener is not running. Exiting...")
                break
    except Exception:
        bus_listener.disconnect()
        try:
            ws_listener.shutdown()
        except Exception:
            pass
        try:
            ws_listener.server_close()
        except Exception:
            pass
        ws_listener_thread.join(1.0)
        bus_listener_thread.join(1.0)


def main():
    # Parse the command line options
    parser = argparse.ArgumentParser(prog="foris-ws")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", default=False)
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        "-a", "--authentication", type=str, choices=["ubus", "none"],
        help="Which authentication method should be used", required=True
    )
    parser.add_argument(
        "--ipv6", help="Should the ws server listen on ipv6 instead of ipv4",
        action="store_true", default=False, dest="ipv6"
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

    # prepare workers
    ws_listener = make_ws_listener(options.host, options.port, authenticate, options.ipv6)
    bus_listener = make_bus_listener(listener_class, options.path)

    manage_listeners(ws_listener, bus_listener)


if __name__ == "__main__":
    main()