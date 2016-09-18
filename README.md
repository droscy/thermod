# Thermod
Programmable thermostat daemon for smart-heating automation.

## License
Thermod v1.0.0-beta4 \
Copyright (C) 2016 Simone Rossetto <simros85@gmail.com> \
GNU General Public License v3

    Thermod is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Thermod is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


## How to install

### Requirements
*Thermod* requires [Python3](https://www.python.org/) (at least version 3.4)
and the following packages:

 - [python-daemon](https://pypi.python.org/pypi/python-daemon) (>=2.0)
 - [jsonschema](https://pypi.python.org/pypi/jsonschema)
 - [requests](http://docs.python-requests.org/) (>=2.4.3)


### Installation
To install *Thermod* first uncompress the tarball and run

```bash
python3 setup.py install
```

then copy the source file `etc/thermod.conf` in one of the following paths:

 - `/etc/thermod/thermod.conf`
 - `/usr/local/etc/thermod/thermod.conf`
 - `${HOME}/thermod/thermod.conf` (where `${HOME}` is the *home* folder of
   the user running the daemon)

and adjust it to meet your requirements, in particular set the paths of:

 - `timetable` file
 - `scripts` for heating and thermometer


## Starting/Stopping the daemon
TODO
