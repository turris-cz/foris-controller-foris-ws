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

import websockets
import logging

from .connection import connections


logger = logging.getLogger(__name__)


async def connection_handler(handler: websockets.WebSocketServerProtocol, path: str):
    logger.debug("New client connected.")
    client_id = await connections.register_connection(handler)
    logger.debug("New client id allocated (id=%d)", client_id)
    try:
        async for message in handler:
            logger.debug("Message recieved (client %d): %s", client_id, message)
            await connections.handle_message(client_id, message)
            logger.debug("Message processed (client %d): %s", client_id, message)

    except Exception as e:
        logger.debug("Exception caught: %s", e)
    finally:
        connections.remove_connection(client_id)
    logger.debug("Disconnecting client (id=%d).", client_id)
