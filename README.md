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
*Thermod* requires [Python3](https://www.python.org/) (version 3.5)
and the following packages:

 - [jsonschema](https://pypi.python.org/pypi/jsonschema) (>=2.3.0)
 - [async-timeout](https://github.com/aio-libs/async-timeout) (>=1.3.0)
 - [aiohttp](https://aiohttp.readthedocs.io/) (>=1.2.0, <2.3)
 - [nose](http://nose.readthedocs.io/) (>=1.3.4, only to run tests)
 - [requests](http://docs.python-requests.org/) (>=2.4.3, only to run tests)
 - [numpy](http://www.numpy.org/) (>=1.8.0, only to run tests)

*Thermod*, currently, is not compatible with aiohttp version 2.3 (or greater)
and Python 3.6 and 3.7 are not supported by aiohttp from version 2.3 onward,
so Python 3.5 is a strict requirement for *Thermod*.

### Installation
To install *Thermod* you need to have Python and [virtualenv](https://virtualenv.pypa.io/en/stable/)
already installed on the system, then the basic steps are:

 1. download and uncompress the source tarball of a *Thermod* release or clone
    the repository (in the following we assume that the source files are in
    `${HOME}/thermod-src` where `${HOME}` is the *home* folder of the user that
    will run the daemon)

 2. create the virtual environment and activate it

       ```bash
       virtualenv -p /path/to/python3.5 ${HOME}/thermod-daemon
       source ${HOME}/thermod-daemon/bin/activate
       ```

 3. install required packages

       ```bash
       pip install -r ${HOME}/thermod-src/requirements.txt
       ```

    if you are on Raspberry Pi, or similar hardware, and you want to use
    the GPIO pins to switch on/off the heating you also need
    `pip install -r ${HOME}/thermod-src/requirements.gpio.txt`

 5. install the daemon

      ```bash
      python3 ${HOME}/thermod-src/setup.py install
      ```

 6. finally copy the config file `${HOME}/thermod-src/etc/thermod.conf` in
    one of the following paths:

    - `${HOME}/.thermod/thermod.conf`
    - `${HOME}/.config/thermod/thermod.conf`
    - `/usr/local/etc/thermod/thermod.conf`
    - `/var/lib/thermod/thermod.conf`
    - `/etc/thermod/thermod.conf`

    and adjust it to meet your requirements (documentation inside the file).
    If more than one config file is found they are all merged but the top
    most take precedence over the others.

### Building and installing on Debian-based system
A Debian package can be build using
[git-buildpackage](https://honk.sigxcpu.org/piki/projects/git-buildpackage/).

Assuming you have already configured your system to use git-buildpackage
(if not see Debian Wiki for [git-pbuilder](https://wiki.debian.org/git-pbuilder),
[cowbuilder](https://wiki.debian.org/cowbuilder),
[Packaging with Git](https://wiki.debian.org/PackagingWithGit) and
[Using Git for Debian Packaging](https://www.eyrie.org/~eagle/notes/debian/git.html))
and cloned the repository, then these are the basic steps:

```bash
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
If *systemd* is in use in the system, copy the file `debian/thermod.service`
to `/lib/systemd/system/thermod.service` or `/usr/local/lib/systemd/system/thermod.service`,
change it to your needs then, to automatically start *Thermod* at system startup, execute:

```bash
systemctl daemon-reload
systemctl enable thermod.service
```

To manually start/stop *Thermod* daemon execute:

```bash
systemctl [start|stop] thermod.service
```


## Fail2ban filter and jail
If [fail2ban](https://www.fail2ban.org/) is in use, specific filter and jail
are available to protect the system against multiple invalid requests
in order to slow down (and possibly avoid) exploitations of bugs.

To enable *Thermod*'s jail copy the two file `etc/fail2ban.filter` and
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
   collects statistics on *Thermod* operation: records status changes in order to
   track switch ON and OFF of the heating along with timestamp.
