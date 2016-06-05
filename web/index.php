<?php
	// hostname (or IP address) and port on which Thermod is listening
	$HOST = 'localhost';
	$PORT = '4344';
?>
<!DOCTYPE html>
<html lang="en">
	<head>
		<meta charset="utf-8">
		<title>Thermod Web Manager</title>
		<script src="js/jquery.js"></script>
		<script src="js/jquery-ui.js"></script>
		<link href="css/jquery-ui.css" rel="stylesheet">
		<link href="css/jquery-ui.theme.css" rel="stylesheet">
		<script>
			// thermod settings
			var settings;  

			// map tmax temperature to 'heating on'
			function is_on(temp)
			{
				if(temp == 'tmax')
					return true;
				else
					return false;
			}

			// update the selectmenu of current status
			function update_current_status()
			{
				$('#target-status option[value=' + settings['status'] + ']').prop('selected', true);
				$('#target-status').selectmenu('refresh');
			}

			// retrieve heating status from daemon and update web page
			function get_heating_status()
			{
				$.get('status.php', {'host':'<?=$HOST;?>', 'port':'<?=$PORT;?>'}, function(data)
				{
					if(!('error' in data))
					{
						// TODO non elabora quando siamo in Off e thermod ritorna -Infinity sulla target-temp
						$('#current-status').prop('value', (data['status']==1 ? 'On' : 'Off'));
						$('#current-temperature').prop('value', data['temperature'].toPrecision(4));
						$('#target-temperature').prop('value', data['target'].toPrecision(4));
					}
					else
					{
						$('#current-status').prop('value', 'n.a.');
						$('#current-temperature').prop('value', 'n.a.');
						$('#target-temperature').prop('value', 'n.a.');
					}
				},'json');
			}

			$(function()
			{
				// main objects of the page
				$('#tabs').tabs();

				$('#target-status').selectmenu({change: function(event, ui)
				{
					var target_status = $('#target-status option:selected').prop('value');
					
					$.post('settings.php', {'host':'<?=$HOST;?>', 'port':'<?=$PORT;?>', 'status': target_status}, function(data)
					{
						if(!('error' in data))
						{
							settings['status'] = target_status;
							get_heating_status();
						}
						else
						{
							var error = (('explain' in data) ? data['explain'] : data['error']);
							$("#dialog").dialog('option', 'title', 'Cannot change status');
							$("#dialog").dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
							$("#dialog").html('<p><span class="ui-icon ui-icon-alert" style="float: left; margin: 0.3ex 1ex 7ex 0;"></span>Cannot change status: <em>&quot;' + error + '&quot;</em>.</p>');
							$("#dialog").dialog('open');
							update_current_status();
						}
					},'json');
				}});
				
				$('#days').buttonset();
				$('.hour').button({disabled: true});
				$('.quarter').button({disabled: true});
				$('#save').button({disabled: true});

				$("#dialog").dialog(
				{
					autoOpen: false,
					modal: true,
					resizable: false,
					minWidth: 370,
					closeOnEscape: true
				});

				// bind events
				/*$('#target-status').change(function()
				{
					// TODO gestire la selezione e il salvataggio dello stato
					$(this).selectmenu('refresh');
				});*/

				$('#days input').change(function()
				{
					$('#save').button('option', 'disabled', false);

					var day = $(this).prop('value');
					for(var hour in settings['timetable'][day])
					{
						$('#' + hour).button('option', 'disabled', false);
						
						for(quarter=0; quarter<4; quarter++)
						{
							$('#' + hour + 'q' + quarter).button('option', 'disabled', false);
							$('#' + hour + 'q' + quarter).prop('checked',is_on(settings['timetable'][day][hour][quarter])).change();
						}
					}
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
					$.post('settings.php', {'host':'<?=$HOST;?>', 'port':'<?=$PORT;?>', 'settings': settings}, function(data)
					{
						if(!('error' in data))
						{
							$("#dialog").dialog('option', 'title', 'Settings saved');
							$("#dialog").dialog('option', 'buttons', {'Ok': function() { $(this).dialog('close'); }});
							$("#dialog").html('<p><span class="ui-icon ui-icon-circle-check" style="float: left; margin: 0.3ex 1ex 2ex 0;"></span>New settings correctly saved!</p>');
						}
						else
						{
							$("#dialog").dialog('option', 'title', 'Cannot save settings');
							$("#dialog").dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
							$("#dialog").html('<p><span class="ui-icon ui-icon-alert" style="float: left; margin: 0.3ex 1ex 7ex 0;"></span>Cannot save new settings, this is the reported error: <em>&quot;' + data['error'] + '&quot;</em>.</p>');
						}
						
						$("#dialog").dialog('open');
					},'json');
				});

				// settings initialization
				get_heating_status();
				
				$.get('settings.php', {'host':'<?=$HOST;?>', 'port':'<?=$PORT;?>'}, function(data)
				{
					if(!('error' in data))
					{
						settings = data;
						update_current_status();
						$('#<?=strtolower(date('l'));?>').prop('checked', true).change();
					}
					else
					{
						$('#days').buttonset('option', 'disabled', true);
						$("#dialog").dialog('option', 'title','Error');
						$("#dialog").dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
						$("#dialog").html('<p><span class="ui-icon ui-icon-alert" style="float: left; margin: 0.3ex 1ex 7ex 0;"></span>Cannot retrieve data from Thermod, this is the reported error: <em>&quot;' + data['error'] + '&quot;</em>.</p>');
						$("#dialog").dialog('open');
					}
				},'json');
			});
		</script>
		<style>
			#main { font-size: 90%; }
			#main ul { list-style-type: none; }
			#main ul li { display: block; float: left; text-align: center; width: 10em; margin-bottom: 1em; }
			#main ul li input { cursor: default; }
			#target-status { width: 9.8em; }
			#target-status-button { margin-top: 0.3ex; }
			#current-status { width: 4em; margin-top: 0.3ex; }
			#current-temperature { width: 4em; margin-top: 0.3ex; }
			#target-temperature { width: 4em; margin-top: 0.3ex; }
			
			#tabs { font-size: 90%; }
			#schedule p { margin: 0px 0px 1ex 0px; }
			#days { margin-bottom: 3ex; }
			#hours { margin-bottom: 1.5ex; }
			.hour-box { float: left; text-align: center; margin-bottom: 1.5ex; width: 4.8em; }
			.quarters-box { font-size: 60%; margin: 0.2ex; }
			.clearer { clear: both; }
		</style>
	</head>
	<body>
		<h1>Thermod Web Manager</h1>
		<div id="main" class="ui-widget-header ui-corner-all">
			<ul>
				<li>
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
					<p>Select hour(s)</p>
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
				
				<div id="buttons">
					<p>Save settings</p>
					<form action="?">
					<input type="button" id="save" value="Save" />
				</div>
			</div>
			
			<div id="settings">
				
			</div>
		</div>
	</body>
</html>