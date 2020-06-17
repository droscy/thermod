[Unit]
Description=Thermod thermostat daemon
Requires=syslog.service
Wants=network.target
After=syslog.service network.target

[Service]
Type=simple
User=<WRITE_HERE_USERNAME>
ExecStart=<WRITE_HERE_VRITUALENV_FOLDER>/bin/thermod --daemon
ExecReload=/bin/kill -HUP $MAINPID
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
