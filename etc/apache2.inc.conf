# Basic apache2 configuration file for Thermod web interface.

# Change '<WEB-FILE-PATH>' with the path where you copied the web files.
Alias /thermod <WEB-FILE-PATH>

<Location /thermod>
	DirectoryIndex index.php

	# Change these settings to match your own networks (if you want
	# some sort of access control).
	<RequireAny>
		Require local
		Require ip 192.168.0.0/24
	</RequireAny>
</Location>

# Change 'localhost' with the hostname (or IP address) where Thermod is running.
ProxyPass /thermod/socket/ http://localhost:4344/
ProxyPassReverse /thermod/socket/ http://localhost:4344/

# vim: syntax=apache ts=4 sw=4 sts=4 sr noet
