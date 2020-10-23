# Thermod
Programmable thermostat daemon for smart-heating automation.

## License
Thermod v1.2.1+dev<br/>
Copyright (C) 2018 Simone Rossetto <simros85@gmail.com><br/>
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
 - [aiohttp](https://aiohttp.readthedocs.io/) (>=3.0.1)
 - [numpy](http://www.numpy.org/) (>=1.8.0)
 - [requests](http://docs.python-requests.org/) (>=2.4.3, only to run tests)
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

### Building and installing on Debian-based system
A Debian package can be build using
[git-buildpackage](https://honk.sigxcpu.org/piki/projects/git-buildpackage/).

Assuming you have already configured your system to use git-buildpackage
(if not see Debian Wiki for [git-pbuilder](https://wiki.debian.org/git-pbuilder),
[cowbuilder](https://wiki.debian.org/cowbuilder),
[Packaging with Git](https://wiki.debian.org/PackagingWithGit) and
[Using Git for Debian Packaging](https://www.eyrie.org/~eagle/notes/debian/git.html))
then these are the basic steps:

```bash
git clone https://github.com/droscy/thermod.git
cd thermod
git branch --track pristine-tar origin/pristine-tar
git checkout -b debian/master origin/debian/master
gbp buildpackage
```

The packages can then be installed as usual:

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


## Fail2ban filter and jail
If [fail2ban](https://www.fail2ban.org/) is in use, specific filter and jail
are available to protect the system against multiple invalid requests
in order to slow down (and possibly avoid) exploitations of bugs.

To enable *Thermod* jail copy the two file `etc/fail2ban.filter` and
`etc/fail2ban.jail` respectively to `/etc/fail2ban/filter.d/thermod.conf` and
`/etc/fail2ban/jail.d/thermod.conf` and restart *fail2ban* daemon.

```bash
cp etc/fail2ban.filter /etc/fail2ban/filter.d/thermod.conf
cp etc/fail2ban.jail /etc/fail2ban/jail.d/thermod.conf
systemctl restart fail2ban.service
```


## Thermod monitors
Some monitors have been developed to read the status of *Thermod*:

 - [thermod-monitor-buttonled](https://github.com/droscy/thermod-monitor-buttonled)
   for Raspberry Pi with one button and one RGB LED: the LED reports the current
   status of the thermostat, while the button can be used to change the status.
 - [thermod-monitor-dbstats](https://github.com/droscy/thermod-monitor-dbstats)
   collects statistics on Thermod operation: records status changes in order to
   track switch ON and OFF of the heating along with timestamp.
