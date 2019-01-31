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

import logging

from typing import Type, Optional, Tuple
from foris_client.buses.base import BaseListener
from foris_client.buses.mqtt import MqttListener

from .connection import connections

logger = logging.getLogger(__name__)


def handler(notification: dict, controller_id: str):
    """ Recieves a notifiation and triggers coroutine to propage it

    :param notification: notification to be sent
    :param controller_id: id of the controller from which the notification came
    """
    logger.debug("Handling bus notification from %s: %s", controller_id, notification)
    connections.publish_notification(controller_id, notification["module"], notification)
    logger.debug("Handling finished: %s - %s", controller_id, notification)


def make_bus_listener(
    listener_class: Type[BaseListener],
    socket_path: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    credentials: Optional[Tuple[str]] = None,
) -> BaseListener:
    """ Prepares a new foris notification listener

    :param listener_class: listener class to be used (UbusListener, UnixSocketListner, ...)
    :param socket_path: path to socket
    :param host: mqtt host
    :param port: mqtt port
    :param credentils: path to mqtt passwd file
    :returns: instantiated listener
    """

    if listener_class is MqttListener:
        logger.debug("Initializing bus listener (%s:%d)", host, port)
        listener = listener_class(host, port, handler, credentials=credentials)
    else:
        logger.debug("Initializing bus listener (%s)", socket_path)
        listener = listener_class(socket_path, handler)
    return listener
