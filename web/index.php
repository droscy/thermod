<?php
/*
 * Copyright (C) 2018 Simone Rossetto <simros85@gmail.com>
 *
 * This file is part of Thermod.
 *
 * Thermod is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Thermod is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Thermod.  If not, see <http://www.gnu.org/licenses/>.
 */

	/*
	 * Hostname (or IP address), port and path where Thermod is listening on.
	 * 
	 * If Thermod is proxied by a webserver, $PATH must be set accordingly to
	 * the webserver configuration while $HOST and $PORT must be left empty.
	 * If no webserver is used, $PATH must be left empty and $HOST and $PORT
	 * must be set to the same value configured in the 'socket' section of
	 * etc/thermod.conf file.
	 * 
	 * Note: the proxy functionality of webservers is required if HTTPS is in
	 * use to serve Thermod Web Manager.
	 * 
	 * Sample configuration for Apache proxy:
	 * 
	 *   // this file
	 *   $HOST = '';
	 *   $PORT = '';
	 *   $PATH = 'thermodpath'; // whatever you want, the same set in apache config file
	 *   
	 *   // apache.conf
	 *   ProxyPass /thermodpath/ http://real.thermod.hostname:4344/
	 *   ProxyPassReverse /thermodpath/ http://real.thermod.hostname:4344/
	 * 
	 * Sample configuration without webserver proxy:
	 * 
	 *   $HOST = 'real.thermod.hostname';
	 *   $PORT = '4344';
	 *   $PATH = '';
	 * 
	 * The $PATH value can also be a multiple path like:
	 * 
	 *   $PATH = 'thermod/socket';
	 * 
	 * without leading and trailing slash.
	 * 
	 * For example, if Thermod Web Manager is reachable at https://webserver:9090/thermod
	 * and you want to use the webserver as a proxy, you can set the following configuration:
	 * 
	 *   // this file
	 *   $HOST = '';
	 *   $PORT = '';
	 *   $PATH = 'thermod/socket';
	 *   
	 *   // apache.conf
	 *   ProxyPass /thermod/socket/ http://real.thermod.hostname:4344/
	 *   ProxyPassReverse /thermod/socket/ http://real.thermod.hostname:4344/
	 */
	$HOST = '';
	$PORT = '';
	$PATH = 'thermod/socket';
	
	// base request url (do not change unless you know what you are doing)
	if($HOST && $PORT)  // no webserver proxy
		$BASEURL = 'http://' . preg_replace(array('/\/+/', '/\/+$/'), array('/', ''), "{$HOST}:{$PORT}/{$PATH}");
	else
		$BASEURL = preg_replace(array('/\/+/', '/\/+$/'), array('/', ''), "/{$PATH}");
?>
<!DOCTYPE html>
<html lang="en">
	<head>
		<meta charset="utf-8">
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
		
		<title>Thermod Web Manager</title>
		<meta name="Description" content="Web manager for Thermod daemon." />
		<meta name="author" content="Simone Rossetto" />
		<meta name="keywords" content="thermod, thermostat, temperature, heating" />
		<meta name="viewport" content="width=device-width, initial-scale=1" />
		
		<script type="text/javascript" src="/javascript/jquery/jquery.js"></script>
		<script type="text/javascript" src="/javascript/jquery-ui/jquery-ui.js"></script>
		<link rel="stylesheet" type="text/css" href="/javascript/jquery-ui/themes/base/jquery-ui.css" />
		
		<script>
			var baseurl = '<?=$BASEURL;?>';
			var today = '<?=strtolower(date('l'));?>';
		</script>
		<script type="text/javascript" src="thermod-web.js"></script>
		<link rel="stylesheet" type="text/css" href="thermod-web.css" />
	</head>
	<body>
		<h1>Thermod Web Manager</h1>
		<div id="main" class="ui-widget-header ui-corner-all">
			<ul>
				<li id="target-mode-li">
					<label for="target-mode">Mode</label>
					<select id="target-mode" name="target-mode">
						<!-- TODO t_max e t_min non hanno il pedice!! -->
						<option value="auto">Auto</option>
						<option value="tmax">Tmax</option>
						<option value="tmin">Tmin</option>
						<option value="t0">Antifreeze</option>
						<option value="off">Off</option>
					</select>
				</li>
				<li>
					<label for="current-status">Heating</label>
					<input id="current-status" class="ui-widget ui-button ui-corner-all ui-state-default" type="text" value="" readonly="readonly" />
				</li>
				<li>
					<label for="current-temperature">Curr. Temp.</label>
					<input id="current-temperature" class="ui-widget ui-button ui-corner-all ui-state-default" type="text" value="" readonly="readonly" />
				</li>
				<li>
					<label for="target-temperature">Target Temp.</label>
					<input id="target-temperature" class="ui-widget ui-button ui-corner-all ui-state-default" type="text" value="" readonly="readonly" />
				</li>
			</ul>
			<div class="clearer"></div>
		</div>

		<div id="dialog"></div>
		<div id="loading">
			<div id="loading-img"></div>
			<div id="loading-back" class="ui-front"></div>
		</div>

		<div id="tabs">
			<ul>
				<li><a href="#schedule">Schedule</a></li>
				<li><a href="#settings">Settings</a></li>
			</ul>

			<div id="schedule">
				<p>Select day</p>
				<div id="days">
					<input type="radio" name="day" id="monday" value="monday" /><label for="monday">Monday</label>
					<input type="radio" name="day" id="tuesday" value="tuesday" /><label for="tuesday">Tuesday</label>
					<input type="radio" name="day" id="wednesday" value="wednesday" /><label for="wednesday">Wednesday</label>
					<input type="radio" name="day" id="thursday" value="thursday" /><label for="thursday">Thursday</label>
					<input type="radio" name="day" id="friday" value="friday" /><label for="friday">Friday</label>
					<input type="radio" name="day" id="saturday" value="saturday" /><label for="saturday">Saturday</label>
					<input type="radio" name="day" id="sunday" value="sunday" /><label for="sunday">Sunday</label>
				</div>

				<div id="hours">
					<p>Select switch-on hours</p>
					<?php for($i=0; $i<24; $i++): ?>
						<div class="hour-box">
							<?php $h = sprintf('%02d',$i); ?>
							<input type="checkbox" class="hour" id="h<?=$h?>" name="h<?=$h?>" /><label for="h<?=$h?>"><?=$h?>:--</label>
							<div class="quarters-box">
								<input type="checkbox" class="quarter" id="h<?=$h?>q0" name="h<?=$h?>q0" value="1" /><label for="h<?=$h?>q0">00</label>
								<input type="checkbox" class="quarter" id="h<?=$h?>q1" name="h<?=$h?>q1" value="1" /><label for="h<?=$h?>q1">15</label>
								<input type="checkbox" class="quarter" id="h<?=$h?>q2" name="h<?=$h?>q2" value="1" /><label for="h<?=$h?>q2">30</label>
								<input type="checkbox" class="quarter" id="h<?=$h?>q3" name="h<?=$h?>q3" value="1" /><label for="h<?=$h?>q3">45</label>
							</div>
						</div>
					<?php endfor; ?>
					<div class="clearer"></div>
				</div>
			</div>

			<div id="settings">
				<p>Set temperatures</p>
				<ul id="temperature-settings">
					<li><label for="tmax">Max</label> <input class="set-temperatures" type="text" id="tmax" name="tmax" size="4" /> degrees</li>
					<li><label for="tmin">Min</label> <input class="set-temperatures" type="text" id="tmin" name="tmin" size="4" /> degrees</li>
					<li><label for="t0">Antifreeze</label> <input class="set-temperatures" type="text" id="t0" name="t0" size="4" /> degrees</li>
				</ul>
				
				<p>Set other settings</p>
				<ul id="other-settings">
					<li>
						<label for="device">Device</label>
						<select id="device" name="device">
							<option value="heating">Heating</option>
							<option value="cooling">Cooling</option>
						</select>
					</li>
					<li><label for="differential">Differential</label> <input class="set-other" type="text" id="differential" name="differential" size="4" /> degrees</li>
				</ul>
			</div>
		</div>

		<div id="buttons" class="ui-widget ui-widget-content ui-corner-all">
			<p>Save settings</p>
			<input type="button" id="save" value="Save" />
		</div>
		
		<div id="copyright">
			<p>Thermod (Web Manager) <span id="version"></span></p>
			<p>Copyright &copy; 2018<?=(date('Y')>2018?'-'.date('Y'):'');?> Simone Rossetto</p>
			<p>GNU General Public License v3.0</p>
		</div>
	</body>
</html>

<!-- vim: set fileencoding=utf-8 tabstop=4: -->
