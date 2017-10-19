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


def send_notification_worker(data):
    connections.publish_notification(data["module"], data)


def handler(data):
    logger.debug("Notification recieved: %s" % data)
    thread = threading.Thread(target=send_notification_worker, args=(data, ))
    thread.daemon = True
    thread.start()


def make_bus_listener(listener_class, socket_path):
    logger.debug("Initializing bus listener (%s)" % (socket_path))
    listener = listener_class(socket_path, handler)
    return listener
