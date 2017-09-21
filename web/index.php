<?php
/*
 * Copyright (C) 2017 Simone Rossetto <simros85@gmail.com>
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
		
		<script language="javascript" type="text/javascript" src="/javascript/jquery/jquery.js"></script>
		<script language="javascript" type="text/javascript" src="/javascript/jquery-ui/jquery-ui.js"></script>
		<link type="text/css" href="/javascript/jquery-ui/themes/base/jquery-ui.css" rel="stylesheet" />
		<script>
			// thermod settings
			var settings;  

			// map tmax temperature to 'heating on' in hours/quarters buttons
			function is_on(temp)
			{
				if(temp == 'tmax')
					return true;
				else
					return false;
			}

			// show loading wheel for long operations
			function start_loading()
			{
				$('body').addClass('loading');
				$('#loading-back').addClass('ui-widget-overlay');
			}

			// hide loading wheel
			function stop_loading()
			{
				$('body').removeClass('loading');
				$('#loading-back').removeClass('ui-widget-overlay');
			}

			// refresh the selectmenu of target status
			function target_status_refresh()
			{
				$('#target-status option[value=' + settings['status'] + ']').prop('selected', true);
			}

			// handle the change event of target status
			function target_status_change(event, ui)
			{
				var target_status = $('#target-status option:selected').prop('value');

				$.ajax(
				{
					type: 'POST',
					url: '<?=$BASEURL;?>/settings',
					data: {'status': target_status},
					success: function(data)
					{
						settings['status'] = target_status;
						get_heating_status_and_refresh();
					},
					error: function(jqXHR, textStatus, errorThrown)
					{
						var data = null;

						if(jqXHR.getResponseHeader('content-type').search(/json/i) >= 0)
							data = $.parseJSON(jqXHR.responseText);
						else
							data = {'error': errorThrown};

						var error = (('explain' in data) ? data['explain'] : data['error']);
						$('#dialog').dialog('option', 'title', 'Cannot change status');
						$('#dialog').dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
						$('#dialog').html('<p><span class="ui-icon ui-icon-alert"></span>Cannot change status: <em>&quot;' + error + '&quot;</em>.</p>');

						stop_loading();
						$('#dialog').dialog('open');

						if(jqXHR.status = 423)
						{
							settings['status'] = target_status;
							get_heating_status_and_refresh();
						}

						target_status_refresh();
					}
				});
			}

			// retrieve heating status from daemon and refresh header web page
			function get_heating_status_and_refresh()
			{
				$.ajax(
				{
					type: 'GET',
					url: '<?=$BASEURL;?>/status',
					success: function(data)
					{
						$('#current-status').prop('value', (data['heating_status']==1 ? 'On' : 'Off'));
						$('#current-temperature').prop('value', data['current_temperature'].toFixed(2));
						$('#target-temperature').prop('value', (data['target_temperature'] ? data['target_temperature'].toFixed(2) : 'n.a.'));
					},
					error: function(jqXHR, textStatus, errorThrown)
					{
						$('#current-status').prop('value', 'n.a.');
						$('#current-temperature').prop('value', 'n.a.');
						$('#target-temperature').prop('value', 'n.a.');

						var data = null;

						if(jqXHR.getResponseHeader('content-type').search(/json/i) >= 0)
							data = $.parseJSON(jqXHR.responseText);
						else
							data = {'error': errorThrown};

						var error = (('explain' in data) ? data['explain'] : data['error']);
						$('#dialog').dialog('option', 'title', 'Cannot get current status');
						$('#dialog').dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
						$('#dialog').html('<p><span class="ui-icon ui-icon-alert"></span>Cannot get current temperature and heating status: <em>&quot;' + error + '&quot;</em>.</p>');

						stop_loading();
						$('#dialog').dialog('open');
					}
				});
			}

			$(function()
			{
				// main objects of the page
				$('#target-status').selectmenu({disabled: true, change: target_status_change});
				$('#tabs').tabs();
				$('#days').controlgroup({disabled: true});
				$('#days input').checkboxradio({icon: false});
				$('.hour').button({disabled: true, icon: false});
				$('.quarter').button({disabled: true, icon: false});

				$('.set-temperatures').spinner(
				{
					disabled: true,
					max: 30,
					min: 0,
					step: 0.1,
					page: 5,
					change: function()
					{
						var val = Number($(this).prop('value'));
						$(this).prop('value', val.toFixed(1));

						var tname = $(this).attr('id');
						settings['temperatures'][tname] = val;
					}
				});

				$('#differential').spinner(
				{
					disabled: true,
					max: 1,
					min: 0,
					step: 0.1,
					page: 0.1,
					change: function(event, ui)
					{
						var val = Number($(this).prop('value'));

						if(val >= 0 && val <= 1)
							settings['differential'] = val;
						else
						{
							$("#dialog").dialog('option', 'title', 'Invalid value');
							$("#dialog").dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
							$("#dialog").html('<p><span class="ui-icon ui-icon-alert"></span>Differential value must be between 0 and 1 degree.</p>');
							$("#dialog").dialog('open');

							$(this).prop('value', settings['differential']);
						}
					}
				});

				$('#grace-time').spinner(
				{
					disabled: true,
					max: 120,
					min: 0,
					step: 1,
					page: 10,
					spin: function(event, ui)
					{
						if(ui.value == 0)
						{
							$(this).prop('value', 'disabled');
							return false;
						}
					},
					change: function()
					{
						var val = $(this).prop('value');
						if(isNaN(val) || Number(val) == 0)
						{
							settings['grace_time'] = null;
							$(this).prop('value', 'disabled');
						}
						else
						{
							settings['grace_time'] = Number(val) * 60;
							$(this).prop('value', Number(val).toFixed(0));
						}
					}
				});
				
				$('#save').button({disabled: true});

				$("#dialog").dialog(
				{
					autoOpen: false,
					modal: true,
					resizable: false,
					//minWidth: 250,
					closeOnEscape: true
				});

				// bind events
				$('#days input').change(function()
				{
					var day = $(this).prop('value');
					for(var hour in settings['timetable'][day])
						for(quarter=0; quarter<4; quarter++)
							$('#' + hour + 'q' + quarter).prop('checked', is_on(settings['timetable'][day][hour][quarter])).change();
				});

				$('.hour').click(function(event)
				{
					var day = $('#days input:checked').prop('value');
					var hour = $(this).prop('name');
					var checked = $(this).prop('checked');

					for(quarter=0; quarter<4; quarter++)
					{
						$('#' + hour + 'q' + quarter).prop('checked',checked).button('refresh');
						settings['timetable'][day][hour][quarter] = (checked ? 'tmax' : 'tmin');
					}
				});

				$('.quarter').change(function()
				{
					var day = $('#days input:checked').prop('value');
					var hour = $(this).prop('name').substr(0,3);
					var quarter = $(this).prop('name').substr(4,1);
					var checked = false;

					if($(this).prop('checked'))
						checked = true;
					else
						if($('#' + hour + 'q0').prop('checked')
								|| $('#' + hour + 'q1').prop('checked')
								|| $('#' + hour + 'q2').prop('checked')
								|| $('#' + hour + 'q3').prop('checked'))
							checked = true;

					$('#' + hour).prop('checked', checked).button('refresh');
				});

				$('.quarter').click(function()
				{
					var day = $('#days input:checked').prop('value');
					var hour = $(this).prop('name').substr(0,3);
					var quarter = $(this).prop('name').substr(4,1);
					settings['timetable'][day][hour][quarter] = ($(this).prop('checked') ? 'tmax' : 'tmin');
				});

				$('#save').click(function()
				{
					$.ajax(
					{
						type: 'POST',
						url: '<?=$BASEURL;?>/settings',
						data: {'settings': JSON.stringify(settings)},
						success: function(data)
						{
							$("#dialog").dialog('option', 'title', 'Settings saved');
							$("#dialog").dialog('option', 'buttons', {'Ok': function() { $(this).dialog('close'); }});
							$("#dialog").html('<p><span class="ui-icon ui-icon-circle-check"></span>New settings correctly saved!</p>');
							get_heating_status_and_refresh();

							stop_loading();
							$("#dialog").dialog('open');
						},
						error: function(jqXHR, textStatus, errorThrown)
						{
							var data = null;

							if(jqXHR.getResponseHeader('content-type').search(/json/i) >= 0)
								data = $.parseJSON(jqXHR.responseText);
							else
								data = {'error': errorThrown};

							var error = (('explain' in data) ? data['explain'] : data['error']);
							$("#dialog").dialog('option', 'title', 'Cannot save settings');
							$("#dialog").dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
							$("#dialog").html('<p><span class="ui-icon ui-icon-alert"></span>Cannot save new settings: <em>&quot;' + error + '&quot;</em>.</p>');

							stop_loading();
							$("#dialog").dialog('open');
						}
					});
				});

				// settings initialization
				get_heating_status_and_refresh();

				$.ajax(
				{
					type: 'GET',
					url: '<?=$BASEURL;?>/settings',
					success: function(data)
					{
						// refresh values
						settings = data;
						target_status_refresh();
						$('#<?=strtolower(date('l'));?>').prop('checked', true).change();

						$('#tmax').prop('value', settings['temperatures']['tmax'].toFixed(1));
						$('#tmin').prop('value', settings['temperatures']['tmin'].toFixed(1));
						$('#t0').prop('value', settings['temperatures']['t0'].toFixed(1));
						$('#differential').prop('value', settings['differential'].toFixed(1));

						var grace = settings['grace_time'] ? (settings['grace_time']/60) : 0;
						$('#grace-time').spinner('value', grace.toFixed(0));

						// enable objects
						$('#target-status').selectmenu('option', 'disabled', false).selectmenu('refresh');
						$('#days').controlgroup('option', 'disabled', false);
						$('.hour').button('option', 'disabled', false);
						$('.quarter').button('option', 'disabled', false).button('refresh');
						$('.set-temperatures').spinner('option', 'disabled', false);
						$('#differential').spinner('option', 'disabled', false);
						$('#grace-time').spinner('option', 'disabled', false);
						$('#save').button('option', 'disabled', false);
					},
					error: function(jqXHR, textStatus, errorThrown)
					{
						var data = null;

						if(jqXHR.getResponseHeader('content-type').search(/json/i) >= 0)
							data = $.parseJSON(jqXHR.responseText);
						else
							data = {'error': errorThrown};

						var error = (('explain' in data) ? data['explain'] : data['error']);
						$('#days').controlgroup('option', 'disabled', true); // TODO capire come mai questo comando serve
						$("#dialog").dialog('option', 'title', 'Error');
						$("#dialog").dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
						$("#dialog").html('<p><span class="ui-icon ui-icon-alert"></span>Cannot retrieve data from Thermod: <em>&quot;' + error + '&quot;</em>.</p>');

						stop_loading();
						$("#dialog").dialog('open');
					}
				});

				$.get('<?=$BASEURL;?>/version', {}, function(data){ $('#version').html('v' + data['version']); },'json');
			});

			$(document).ajaxStart(start_loading).ajaxStop(stop_loading);
		</script>
		<style>
			/* global */
			h1 { font-size: 150%; margin: 0.5ex 0;}
			.ui-dialog { font-size: 90%; }
			
			#loading { display: none; }
			#loading-img
			{
				position: fixed;
				z-index: 1000;
				top: 0;
				left: 0;
				height: 100%;
				width: 100%;
				background: url('images/wheel.gif') 50% 50% no-repeat;
			}
			
			body.loading { overflow: hidden; }
			body.loading #loading { display: block; }
			
			.clearer { clear: both; }
			
			/* header */
			#main { font-size: 90%; }
			#main ul { list-style-type: none; padding: 0px 1.5em; margin: 0.8em 0 0 0; }
			#main ul li { display: block; float: left; text-align: center; width: 8em; margin-bottom: 1.2em; }
			#main ul li label { display: block; width: 100%; }
			#main ul li input { cursor: default; }
			
			#target-status-li { margin-right: 2em; }
			#target-status-button { width: 7em; margin-top: 0.3ex; }
			#current-status { width: 4em; margin-top: 0.3ex; }
			#current-temperature { width: 4em; margin-top: 0.3ex; }
			#target-temperature { width: 4em; margin-top: 0.3ex; }
			
			#tabs { font-size: 90%; margin-top: 1em; }
			
			/* schedule */
			#schedule p { margin: 0 0 1ex 0; }
			#days { margin-bottom: 3ex; }
			#hours { margin-bottom: 1.5ex; }
			.hour-box { float: left; text-align: center; margin-bottom: 1.5ex; width: 4.8em; }
			.quarters-box { font-size: 58%; margin: 0.2ex; }
			.quarters-box label { margin-top: 0.5ex; }
			
			/* settings */
			#settings p { margin: 0 0 1.2ex 0; }
			#settings ul { list-style-type: none; padding-left: 20px; }
			#settings ul li { margin-bottom: 0.8ex; }
			#settings ul li label { float: left; width: 10ex; text-align: right; margin: 0.5ex 1ex 0 0; }
			#temperature-settings { margin: 0 0 2em 0; }
			#other-settings { margin: 0; }
			.set-temperatures, .set-other { float: left; text-align: center; }
			
			/* save */
			#buttons { font-size: 90%; padding: 1em 1.4em; background: #eee; margin-top: 1em; }
			#buttons p { margin: 0 0 1ex 0; }
			
			/* copyright */
			#copyright { margin: 1em auto; text-align: center; }
			#copyright p { margin: 0; padding: 0.2ex 0; font-size: 80%; color: #999999; }
		</style>
	</head>
	<body>
		<h1>Thermod Web Manager</h1>
		<div id="main" class="ui-widget-header ui-corner-all">
			<ul>
				<li id="target-status-li">
					<label for="target-status">Status</label>
					<select id="target-status" name="target-status">
						<!-- TODO t_max e t_min non hanno il pedice!! -->
						<option value="auto">Auto</option>
						<option value="tmax">T<small><sub>max</sub></small></option>
						<option value="tmin">T<small><sub>min</sub></small></option>
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
					<li><label for="differential">Differential</label> <input class="set-other" type="text" id="differential" name="differential" size="4" /> degrees</li>
					<li><label for="grace-time">Grace time</label> <input class="set-other" type="text" id="grace-time" name="grace-time" size="4" /> minutes</li>
				</ul>
			</div>
		</div>

		<div id="buttons" class="ui-widget ui-widget-content ui-corner-all">
			<p>Save settings</p>
			<input type="button" id="save" value="Save" />
		</div>
		
		<div id="copyright">
			<p>Thermod (Web Manager) <span id="version"></span></p>
			<p>Copyright &copy; 2017<?=(date('Y')>2017?'-'.date('Y'):'');?> Simone Rossetto</p>
			<p>GNU General Public License v3.0</p>
		</div>
	</body>
</html>
