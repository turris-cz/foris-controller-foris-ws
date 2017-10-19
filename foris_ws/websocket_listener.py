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


import logging
import socket

from websocket_server import WebsocketServer
from .connection import connections

logger = logging.getLogger(__name__)


def client_connected(client, server):
    """ Handle when a new client was connected
    this function is used in another thread

    :param client: dict which contains "id", "handler" and "address(ip,port)"
    :type client: dict
    :param server: server instace
    :type server: websocket_server.WebsocketServer
    """
    connections.append_connection(client["id"], client["handler"], server)
    logger.debug("New client '%d' connected.", client["id"])


def client_left(client, server):
    """ Handle when a new client was connected
    properly dispose client instance and try to terminate all its threads
    this function is used in another thread

    :param client: dict which contains "id", "handler" and "address(ip,port)"
    :type client: dict
    :param server: server instance
    :type server: websocket_server.WebsocketServer
    """
    connections.remove_connection(client["id"])
    logger.debug("Client '%d' was disconnected.", client["id"])


def message_received(client, server, message):
    """ Handles when a message was recieved from the client
    this function is used in another thread

    :param client: dict which contains "id", "handler" and "address(ip,port)"
    :type client: dict
    :param server: server instance
    :type server: websocket_server.WebsocketServer
    :param msg: the message recieved from the client
    :type msg: str
    """
    logger.debug("Message recieved (client %d): %s", client["id"], message)
    connections.handle_message(client["id"], message)
    logger.debug("Message processed (client %d): %s", client["id"], message)


def make_ws_listener(listen_host, listen_port, authenticate_method, ipv6=False):
    logger.debug("Initializing websocket server on '%s:%d'." % (listen_host, listen_port))
    server = WebsocketServer(listen_port, host=listen_host)
    server.set_fn_new_client(client_connected)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    server.set_fn_authenticate(authenticate_method)

    if ipv6:
        server.address_family = socket.AF_INET6
    else:
        server.address_family = socket.AF_INET

    return server
