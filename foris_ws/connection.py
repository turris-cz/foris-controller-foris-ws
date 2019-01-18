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


import asyncio
import json
import logging
import threading
import websockets

from typing import List, Set, Union, Callable, Type

from functools import wraps
from collections import Iterable

logger = logging.getLogger(__name__)


class IncorrectMessage(Exception):
    pass


def _with_lock(func: Callable) -> Callable:
    """Wraps function with self.lock

    :param func: the function to be wrapped
    :returns: wrapped function
    """

    @wraps(func)
    def inner(self, *args, **kwargs):
        with self.lock:
            return func(self, *args, **kwargs)

    return inner


class Connection:
    """ Class which represents the connection between the client and the websocket server
    """
    PING_THREAD_TIMEOUT: float = 60.0

    def __init__(self, client_id: int, handler: websockets.WebSocketServerProtocol):
        """ Initializes the connection

        :param client_id: unique client id
        :param handler: handler which is used to communicate with the client
        """
        self.client_id: int = client_id
        self.handler: websockets.WebSocketServerProtocol = handler
        self.lock: threading.Lock = threading.Lock()
        self.modules: Set[str] = set()
        self.exiting: bool = False

    @staticmethod
    def _prepare_modules(modules: Union[List[str], str]) -> List[str]:
        """ Prepares and checks whether the modules are valid.
        :param modules: list of available modules
        :returns: processed modules
        :raises IncorrectMessage: on incorrect modules format
        """
        res: List[str] = []
        if isinstance(modules, str):
            return [modules]
        if not isinstance(modules, Iterable):
            logger.warning("Invalid module list '%s'." % modules)
            raise IncorrectMessage("Not a valid module list '%s'" % modules)

        for module in modules:
            if isinstance(module, str):
                res.append(module)
            else:
                logger.warning("Module item is not a string '%s'." % module)
                raise IncorrectMessage("Module item is not a string '%s'" % module)
        return res

    def _subscribe(self, modules: List[str]) -> dict:
        """ Subscribes modules to the client and prepares appropriate response

        :param modules: moduels to subscribe
        :returns: response to client
        :raises IncorrectMessage: on incorrect modules format
        """

        modules = Connection._prepare_modules(modules)
        logger.debug("Subscribing client '%d' for modules %s." % (self.client_id, modules))
        self.modules = self.modules.union(set(modules))
        logger.debug("Client '%d' subscriptions: %s" % (self.client_id, ", ".join(self.modules)))
        return {"result": True, "subscriptions": list(self.modules)}

    def _unsubscribe(self, modules: List[str]) -> dict:
        """ Unsubscribes modules to the client and prepares appropriate response

        :param modules: moduels to subscribe
        :returns: response to client
        :raises IncorrectMessage: on incorrect modules format
        """

        modules = Connection._prepare_modules(modules)
        logger.debug("Unsubscribing client '%d' from modules %s." % (self.client_id, modules))
        self.modules = self.modules.difference(set(modules))
        logger.debug("Client '%d' subscriptions: %s" % (self.client_id, ", ".join(self.modules)))
        return {"result": True, "subscriptions": list(self.modules)}

    @_with_lock
    async def send_message_to_client(self, msg: dict):
        """ Sends a message to the connected client
        :param msg: message to be sent to the client (in json format)
        """
        str_msg = json.dumps(msg)
        logger.debug("Sending message to client %d: %s", self.client_id, str_msg)
        await self.handler.send(str_msg)

    async def process_message(self, message: str):
        """ Processes a message which is recieved from the client
        :param message: message which will be processed
        """
        try:
            try:
                parsed: dict = json.loads(message)
            except ValueError:
                logger.warning("The message is not in json format. (%s)" % message)
                raise IncorrectMessage("Not in json format.")

            if "action" not in parsed:
                logger.warning("Action was not defined in the message.")
                raise IncorrectMessage("Action not defined.")

            if "params" not in parsed:
                logger.warning("Params were not defined in the message.")
                raise IncorrectMessage("Params not defined.")

            if parsed["action"] == "subscribe":
                await self.send_message_to_client(self._subscribe(parsed["params"]))
                return
            elif parsed["action"] == "unsubscribe":
                await self.send_message_to_client(self._unsubscribe(parsed["params"]))
                return

            logger.warning("Unkown action '%s'" % parsed["action"])
            raise IncorrectMessage("Unknown action '%s'" % parsed["action"])
        except IncorrectMessage as e:
            await self.send_message_to_client({"result": False, "error": str(e)})

    def close(self):
        """ Sets a flag which should eventually close the connection.
        """
        self.exiting = True


class Connections:
    """ Class which represents all active connections
    """
    client_id: int = 1

    def __init__(self):
        """ Initializes Connections
        """
        self.lock = threading.Lock()
        self._connections = {}
        self.current_event_loop: Type[asyncio.AbstractEventLoop] = asyncio.get_event_loop()

    @_with_lock
    async def register_connection(self, handler: websockets.WebSocketServerProtocol):
        """ creates and adds a Connection instance among active connections

        :param handler: handler which is used to communicate with the client
        """
        new_client_id = Connections.client_id
        self._connections[new_client_id] = Connection(new_client_id, handler)
        Connections.client_id += 1
        return new_client_id

    @_with_lock
    def remove_connection(self, client_id: int):
        """ removes a Connection instance from active connections

        :param client_id: unique client id
        """
        if client_id not in self._connections:
            return
        try:
            self._connections[client_id].close()
        except Exception:
            pass
        del self._connections[client_id]

    @_with_lock
    async def handle_message(self, client_id: int, message: str):
        """ Handles a message recieved from the client

        :param client_id: unique client id
        :param message: message to be handeled
        """
        if client_id not in self._connections:
            logging.warning("Client '%d' is present it the connection list" % client_id)
            return
        try:
            await self._connections[client_id].process_message(message)
        except Exception as e:
            logging.error("Exception was raised: %s" % str(e))
            raise

    @_with_lock
    def publish_notification(self, controller_id: str, module: str, message: dict):
        """ Publishes notification of the module to clients which have the module subscribed
            does nothing if no module is present in the message

        :param controller_id: id of the controller from which the notification came
        :param module: name of the module related to the notification
        :param message: a notification which will be published to all relevant clients
        """
        message["controller_id"] = controller_id
        for _, connection in self._connections.items():
            if module in connection.modules:
                asyncio.run_coroutine_threadsafe(  # can be scheduled from another thread
                    connection.send_message_to_client(message),
                    self.current_event_loop,
                )


connections = Connections()
