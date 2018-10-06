# -*- coding: utf-8 -*-
"""Interface to the real cooling system.

Many of these classes are the same classes of heating module because the same
hardware can be used both for heating and cooling.

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

from . import heating

__date__ = '2018-06-23'
__updated__ = '2018-06-23'

class BaseCooling(heating.BaseHeating):
    """Exactly the same class of `heating.BaseHeating`.
    
    Subclassed just to print messages with right class name.
    """
    pass

class FakeCooling(heating.FakeHeating):
    """Exactly the same class of `heating.FakeHeating`.
    
    Subclassed just to print messages with right class name.
    """
    pass

class ScriptCooling(heating.ScriptHeating):
    """Exactly the same class of `heating.ScriptHeating`.
    
    Subclassed just to print messages with right class name.
    """
    pass

class PiPinsRelayCooling(heating.PiPinsRelayHeating):
    """Exactly the same class of `heating.PiPinsRelayHeating`.
    
    Subclassed just to print messages with right class name.
    """
    pass

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
