# Thermod
Programmable thermostat daemon for smart-heating automation.

## License
Thermod v2.0.0-alpha<br/>
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
*Thermod* requires [Python3](https://www.python.org/) (at least version 3.6)
and the following packages:

 - [jsonschema](https://pypi.python.org/pypi/jsonschema) (>=3.2.0)
 - [async-timeout](https://github.com/aio-libs/async-timeout) (>=3.0.1)
 - [aiohttp](https://aiohttp.readthedocs.io/) (>=3.5.4)
 - [nose](http://nose.readthedocs.io/) (>=1.3.7, only to run tests)
 - [aiounittest](https://github.com/kwarunek/aiounittest) (>=1.4.0, only to run tests)
 - [numpy](http://www.numpy.org/) (>=1.18.4, only to run tests)

### Installation
To install *Thermod* you need to have Python and [virtualenv](https://virtualenv.pypa.io/en/stable/)
already installed on the system, then the basic steps are:

 1. download and uncompress the source tarball of a *Thermod* release or clone
    the repository somewhere

 2. create the virtual environment and activate it

       ```bash
       virtualenv -p /path/to/python3 ~/thermod-daemon
       source ~/thermod-daemon/bin/activate
       ```

 3. install required packages

       ```bash
       pip install -r requirements.txt
       ```

    if you are on Raspberry Pi, or similar hardware, and you want to use
    the GPIO pins to switch on/off the heating you also need to add
		the group `gpio` to the user that will run *Thermod* and also
		install the package listed in `requirements.gpio.txt` file:

       ```bash
       sudo adduser thermod gpio
       pip install -r requirements.gpio.txt
       ```

 5. install the daemon

      ```bash
      python3 setup.py install
      ```

 6. finally copy the config file `etc/thermod.conf` in
    one of the following paths:

    - `~/.thermod/thermod.conf`
    - `~/.config/thermod/thermod.conf`
    - `/usr/local/etc/thermod/thermod.conf`
    - `/var/lib/thermod/thermod.conf`
    - `/etc/thermod/thermod.conf`

    and adjust it to meet your requirements (documentation inside the file).
    If more than one config file is found they are all merged but the top
    most take precedence over the others.


## Starting/Stopping the daemon
If *systemd* is in use in the system, copy the file `etc/thermod.inc.service`
to `/etc/systemd/system/thermod.service` or `/usr/local/lib/systemd/system/thermod.service`,
and change it to your needs (pay attention to `User` value and `ExecStart` path).

To automatically start *Thermod* at system startup, execute:

```bash
sudo systemctl daemon-reload
sudo systemctl enable thermod.service
```

To manually start/stop *Thermod* daemon execute:

```bash
sudo systemctl [start|stop] thermod.service
```


## Fail2ban filter and jail
If [fail2ban](https://www.fail2ban.org/) is in use, specific filter and jail
are available to protect the system against multiple invalid requests
in order to slow down (and possibly avoid) exploitations of bugs.

To enable *Thermod*'s jail copy the two file `etc/fail2ban.filter` and
`etc/fail2ban.jail` respectively to `/etc/fail2ban/filter.d/thermod.conf` and
`/etc/fail2ban/jail.d/thermod.conf` and restart *fail2ban* daemon.

```bash
sudo cp etc/fail2ban.filter /etc/fail2ban/filter.d/thermod.conf
sudo cp etc/fail2ban.jail /etc/fail2ban/jail.d/thermod.conf
sudo systemctl restart fail2ban.service
```


## Web interface
To enable the web interface of *Thermod* you need a working installation of a
web server with php support. The web interface can also be in a different server
just be sure that the other server can reach *Thermod*'s socket.

### lighttpd
These are the instructions to setup [lighttpd](https://www.lighttpd.net/) with
[php-fpm](https://www.php.net/manual/en/install.fpm.php) on a Debian-based system
on the same server where *Thermod* is running:

1. install *lighttpd*, *php-fpm* and *jquery*:

      ```bash
      sudo apt-get install lighttpd php-fpm libjs-jquery libjs-jquery-ui
      ```

2. copy the `web/` folder somewhere in the system and make sure *lighttpd*'s user
   can access it:

      ```bash
      sudo mkdir -p /srv/www/thermod
      sudo cp -R web/* /srv/www/thermod
      sudo chown -R www-data:www-data /srv/www/thermod
      ```

   Even the same source folder can be used without copying files somewhere else:

      ```bash
      chmod +x ~ ~/thermod
      chmod +rx ~/thermod/web
      ```

3. copy `etc/lighttpd.inc.conf` to `/etc/lighttpd/conf-available`, change in
   it `<WEB-FILE-PATH>` to the folder path where you copied the web interface:

      ```bash
      sudo cp etc/lighttpd.inc.conf /etc/lighttpd/conf-available/95-thermod.conf
      sudo sed -i 's|<WEB-FILE-PATH>|/srv/www/thermod|' /etc/lighttpd/conf-available/95-thermod.conf
      ```

   If *Thermod* is running on a different server edit the just copied file: change the
   last `127.0.0.1` to the right IP address.

4. enable the just copied module together with *fastcgi* and *fastcgi-php*,
   then restart *lighttpd*:

      ```bash
      sudo lighttpd-enable-mod thermod
      sudo lighttpd-enable-mod fastcgi
      sudo lighttpd-enable-mod fastcgi-php
      sudo systemctl restart lighttpd.service
      ```

5. open browser and navigate to `http://<hostname>/thermod` you should see the web interface

### Apache2
If you use Apache2 web server follow these steps:

1. install *Apache2*, *php* and *jquery*:

      ```bash
      sudo apt-get install apache2 libapache2-mod-php libjs-jquery libjs-jquery-ui
      ```

2. copy the `web/` folder somewhere in the system and make sure *Apache*'s user
   can access it:

      ```bash
      sudo mkdir -p /srv/www/thermod
      sudo cp -R web/* /srv/www/thermod
      sudo chown -R www-data:www-data /srv/www/thermod
      ```

   Even the same source folder can be used without copying files somewhere else:

      ```bash
      chmod +x ~ ~/thermod
      chmod +rx ~/thermod/web
      ```

3. copy `etc/apache2.inc.conf` to `/etc/apache2/conf-available`, change in
   it `<WEB-FILE-PATH>` to the folder path where you copied the web interface:

      ```bash
      sudo cp etc/apache2.inc.conf /etc/apache2/conf-available/thermod.conf
      sudo sed -i 's|<WEB-FILE-PATH>|/srv/www/thermod|' /etc/apache2/conf-available/thermod.conf
      ```

   If *Thermod* is running on a different server edit the just copied file: change
   `localhost` to the right hostname or IP address in the two settings `ProxyPass`
   and `ProxyPassReverse`.

4. enable the just copied module together with `mod_proxy` and restart *Apache2*:

      ```bash
      sudo a2enconf thermod
      sudo a2enmod proxy
      sudo systemctl restart apache2.service
      ```

5. open browser and navigate to `http://<hostname>/thermod` you should see the web interface


## Thermod monitors
Some monitors have been developed:

 - [thermod-monitor-buttonled](https://github.com/droscy/thermod-monitor-buttonled)
   for Raspberry Pi with one button and one RGB LED: the LED reports the current
   status of the thermostat, while the button can be used to change the status.

 - [thermod-monitor-dbstats](https://github.com/droscy/thermod-monitor-dbstats)
   collects statistics on *Thermod* operation: records status changes in order to
   track switch ON and OFF of the heating along with timestamp.

 - search [other monitors](https://github.com/search?q=thermod-monitor) on GitHub.

