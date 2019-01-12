# -*- coding: utf-8 -*-
"""Init of `thermod` package.

Copyright (C) 2018 Simone Rossetto <simros85@gmail.com>

This file is part of Thermod.

Thermod is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Thermod is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Thermod.  If not, see <http://www.gnu.org/licenses/>.
"""

from thermod.common import ThermodStatus, SOCKET_DEFAULT_PORT, \
    SOCKET_REQ_SETTINGS, SOCKET_REQ_STATUS, SOCKET_REQ_VERSION, \
    SOCKET_REQ_MONITOR, SOCKET_REQ_MONITOR_NAME, SOCKET_RSP_VERSION, \
    SOCKET_RSP_MESSAGE, DEGREE_CELSIUS, DEGREE_FAHRENHEIT, \
    LogStyleAdapter, LOGGER_BASE_NAME, LOGGER_FMT_MSG, \
    LOGGER_FMT_TIME, LOGGER_FMT_STYLE, LOGGER_FMT_MSG_SYSLOG, \
    LOGGER_FMT_DATETIME

# There is no import of other modules and classes because on slow platforms the
# import of the whole thermod package can be very slow and there is no need
# to import everything while the user requires only the basic functionality
# to query Thermod socket (i.e. it is developing a client or a monitor).

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
