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
import logging
import time
import threading
import websocket_server

from functools import wraps
from collections import Iterable

logger = logging.getLogger(__name__)

try:
    basestring
except NameError:
    basestring = str  # python 3


class IncorrectMessage(Exception):
    pass


def _with_lock(func):
    """Wraps function with self.lock

    :param func: the function to be wrapped
    :type func: callable
    :returns: wrapped function
    :rtype: callable
    """

    @wraps(func)
    def inner(self, *args, **kwargs):
        with self.lock:
            return func(self, *args, **kwargs)

    return inner


def ping_worker(connection, timeout):
    while True:
        time.sleep(timeout)
        if connection.exiting:
            break
        else:
            connection.send_ping()


class Connection(object):
    PING_THREAD_TIMEOUT = 60.0

    def __init__(self, client_id, handler, server):
        self.client_id = client_id
        self.handler = handler
        self.server = server
        self.lock = threading.Lock()
        self.modules = set()
        self.exiting = False

        # ping thread handling
        self.ping_thread = threading.Thread(
            target=ping_worker, args=(self, Connection.PING_THREAD_TIMEOUT))
        logger.debug("Starting ping thread (timeout=%d)." % Connection.PING_THREAD_TIMEOUT)
        self.ping_thread.start()

    @staticmethod
    def _prepare_modules(modules):
        if isinstance(modules, basestring):
            return [modules]
        if not isinstance(modules, Iterable):
            logger.warning("Invalid module list '%s'." % modules)
            raise IncorrectMessage("Not a valid module list '%s'" % modules)

        for module in modules:
            if not isinstance(module, basestring):
                logger.warning("Module item is not a string '%s'." % module)
                raise IncorrectMessage("Module item is not a string '%s'" % module)
        return modules

    def _subscribe(self, modules):
        modules = Connection._prepare_modules(modules)
        logger.debug("Subscribing client '%d' for modules %s." % (self.client_id, modules))
        self.modules = self.modules.union(set(modules))
        logger.debug("Client '%d' subscriptions: %s" % (self.client_id, ", ".join(self.modules)))
        return {"result": True, "subscriptions": list(self.modules)}

    def _unsubscribe(self, modules):
        modules = Connection._prepare_modules(modules)
        logger.debug("Unsubscribing client '%d' from modules %s." % (self.client_id, modules))
        self.modules = self.modules.difference(set(modules))
        logger.debug("Client '%d' subscriptions: %s" % (self.client_id, ", ".join(self.modules)))
        return {"result": True, "subscriptions": list(self.modules)}

    @_with_lock
    def send_ping(self):
        logger.info("Sending ping to client '%d'.", self.client_id)
        self.handler.send_text("ping!", websocket_server.OPCODE_PING)

    @_with_lock
    def send_message_to_client(self, msg):
        str_msg = json.dumps(msg)
        logger.debug("Sending message to client %d: %s", self.client_id, str_msg)
        self.handler.send_message(str_msg)

    def process_message(self, message):
        try:
            try:
                message = json.loads(message)
            except ValueError:
                logger.warning("The message is not in json format. (%s)" % message)
                raise IncorrectMessage("Not in json format.")

            if "action" not in message:
                logger.warning("Action was not defined in the message.")
                raise IncorrectMessage("Action not defined.")

            if "params" not in message:
                logger.warning("Params were not defined in the message.")
                raise IncorrectMessage("Params not defined.")

            if message["action"] == "subscribe":
                self.send_message_to_client(self._subscribe(message["params"]))
                return
            elif message["action"] == "unsubscribe":
                self.send_message_to_client(self._unsubscribe(message["params"]))
                return

            logger.warning("Unkown action '%s'" % message["action"])
            raise IncorrectMessage("Unknown action '%s'" % message["action"])
        except IncorrectMessage as e:
            self.send_message_to_client({"result": False, "error": str(e)})

    def close(self):
        # notify ping thread to exit
        self.exiting = True


class Connections(object):
    def __init__(self):
        self.lock = threading.Lock()
        self._connections = {}

    @_with_lock
    def append_connection(self, client_id, handler, server):
        self._connections[client_id] = Connection(client_id, handler, server)

    @_with_lock
    def remove_connection(self, client_id):
        if client_id not in self._connections:
            return
        try:
            self._connections[client_id].close()
        except:
            pass
        del self._connections[client_id]

    @_with_lock
    def handle_message(self, client_id, message):
        if client_id not in self._connections:
            logging.warning("Client '%d' is present it the connection list" % client_id)
            return
        try:
            self._connections[client_id].process_message(message)
        except Exception as e:
            logging.error("Exception was raised: %s" % str(e))
            raise

    @_with_lock
    def publish_notification(self, module, message):
        for cliet_id, connection in self._connections.items():
            if module in connection.modules:
                connection.send_message_to_client({
                    'module': module,
                    'message': message,
                })


connections = Connections()
