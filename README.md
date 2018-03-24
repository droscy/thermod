# Thermod
Programmable thermostat daemon for smart-heating automation.

## License
Thermod v1.0.0 \
Copyright (C) 2018 Simone Rossetto <simros85@gmail.com> \
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
*Thermod* requires [Python3](https://www.python.org/) (at least version 3.5)
and the following packages:

 - [jsonschema](https://pypi.python.org/pypi/jsonschema) (>=2.3.0)
 - [async_timeout](https://github.com/aio-libs/async-timeout) (>=1.3.0)
 - [aiohttp](https://aiohttp.readthedocs.io/) (>=1.2.0)
 - [numpy](http://www.numpy.org/) (>=1.8.0)
 - [requests](http://docs.python-requests.org/) (>=2.4.3)
 - [nose](http://nose.readthedocs.io/) (>=1.3.4, only to run tests)


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

and adjust it to meet your requirements (documentation inside the file).


### Debian
On Debian-based systems a *deb* package can be built before installing the
software. To build the package extract the tarball, install all the required
Python modules and then execute:

```bash
dpkg-buildpackage
```

After having built the package install, at least, the following packages:

```bash
dpkg -i \
  thermod_{version}_all.deb \
  python3-thermod_{version}_{arch}.deb
```


## Starting/Stopping the daemon
If *systemd* is in use in the system, copy the script `debian/thermod.service`
to `/lib/systemd/system/thermod.service` then execute

```bash
systemctl daemon-reload
systemctl enable thermod.service
```

to automatically start *Thermod* at system startup.

To manually start/stop *Thermod* daemon execute:

```bash
systemctl [start|stop] thermod.service
```
