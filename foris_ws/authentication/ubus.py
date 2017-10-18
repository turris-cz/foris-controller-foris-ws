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

from __future__ import absolute_import

import logging
import re
import ubus

logger = logging.getLogger(__name__)


def authenticate(self, message):
        """ Performs an authentication based on authentication token placed in cookie
        and ubus session object.

        :param message: should contain clients initial request
        :type message: str
        :returns: True when the authentication passes False otherwise
        :rtype: bool
        """

        logger.debug("Logging using authentication cookie of the ubus session object.")
        if not ubus.get_connected():
            logger.debug("Conncting to ubus.")

        cookie_lines = [
            e.strip() for e in message.split("\r\n") if e.strip().startswith("Cookie:")
        ]
        if not cookie_lines:
            logger.debug("Missing cookie.")
            return False

        foris_ws_session_re = re.search(
            r'foris.ws.session=([^;\s]*)', cookie_lines[0])
        if not foris_ws_session_re:
            logger.debug("Foris session in cooking.")
            return False

        session_id = foris_ws_session_re.group(1)

        params = {
            "ubus_rpc_session": session_id or "",
            "scope": "ubus",
            "object": "websocket-listen",
            "function": "listen-allowed"
        }

        # Verify whether the client is able to access the listen function
        try:
            data = ubus.call("session", "access", params)
        except:
            logger.debug("Session '%s' not found." % session_id)
            return False

        if data["access"]:
            return True

        return False
