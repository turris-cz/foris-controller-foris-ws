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

import threading
import logging

from .connection import connections

logger = logging.getLogger(__name__)


def send_notification_worker(notification):
    """ Sends a notification via all active connections.

    :param notification: notification to be sent
    :param notification: dict
    """
    connections.publish_notification(notification["module"], notification)


def handler(notification):
    """ Recieves a notifiation and starts a thread which is responsible for publishing it

    :param notification: notification to be processsed
    :param notification: dict
    """
    logger.debug("Notification recieved: %s" % notification)
    thread = threading.Thread(target=send_notification_worker, args=(notification, ))
    thread.daemon = True
    thread.start()


def make_bus_listener(listener_class, socket_path):
    """ Prepares a new foris notification listener

    :param listener_class: listener class to be used (UbusListener, UnixSocketListner, ...)
    :type listener_class: type
    :param socket_path: path to socket
    :type socket_path: str
    :returns: instantiated listener
    :rtype: foris_client.buses.base.BaseListener
    """
    logger.debug("Initializing bus listener (%s)" % (socket_path))
    listener = listener_class(socket_path, handler)
    return listener
