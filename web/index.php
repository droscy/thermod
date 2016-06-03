<?php
	// hostname (or IP address) and port on which Thermod is listening
	$HOST = 'localhost';
	$PORT = '4344';
	
	// TODO gestione errori se non si comunica con thermod
?>
<!DOCTYPE html>
<html lang="en">
	<head>
		<meta charset="utf-8">
		<title>Thermod Web Manager</title>
		<script src="js/jquery.js"></script>
		<script src="js/jquery-ui.js"></script>
		<script src="js/jquery-ui.labeledslider.js"></script>
		<script src="js/jquery-ui.buttonsetv.js"></script>
		<link href="css/jquery-ui.css" rel="stylesheet">
		<link href="css/jquery-ui.theme.css" rel="stylesheet">
		<link href="css/jquery-ui.labeledslider.css" rel="stylesheet">
		<script>
			var settings;

			function is_on(temp)
			{
				if(temp == 'tmax')
					return true;
				else
					return false;
			}

			$(function()
			{
				$('#tabs').tabs();
				$('#days').buttonset();
				$('.hour').button({disabled: true});
				$('.quarter').button({disabled: true});
				$('#save').button({disabled: true});

				$('#days input').change(function()
				{
					$('#save').button('option','disabled',false);

					var day = $(this).prop('value');
					for(var hour in settings['timetable'][day])
					{
						$('#' + hour).button('option','disabled',false);
						
						for(quarter=0; quarter<4; quarter++)
						{
							$('#' + hour + 'q' + quarter).button('option','disabled',false);
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

					$('#' + hour).prop('checked',checked).button('refresh');
				});

				$('.quarter').click(function()
				{
					var day = $('#days input:checked').prop('value');
					var hour = $(this).prop('name').substr(0,3);
					var quarter = $(this).prop('name').substr(4,1);
					settings['timetable'][day][hour][quarter] = ($(this).prop('checked') ? 'tmax' : 'tmin');
				});
				
				$('#save').click(function(){
					$.post('settings.php', {'settings': settings});
				});
				
				/*$('#clear').click(function(){
					$('#days input:checked').each(function(){ $(this).prop('checked', false).change(); });
					$('#hours input:checked').each(function(){ $(this).prop('checked', false).change(); });
				});*/

				$.get('settings.php', {'host':'<?=$HOST;?>', 'port':'<?=$PORT;?>'}, function(data){ settings = data; }, 'json');
			});
		</script>
		<style>
			/*select { width: 100px; }*/
			/*#settings { float: left; border: 1px solid #000000; height: 150px; }*/
			
			/*.ui-slider-vertical { width: 1px; }
			.ui-slider .ui-slider-handle { height: 1px; width: 0.8em; }
			.head { float: left; background-color: #DDFFFF; }*/
			
			/* quelli buoni */
			#tabs { font-size: 90%; }
			#schedule p { margin: 0px 0px 1ex 0px; }
			#days { margin-bottom: 3ex; }
			#hours { margin-bottom: 1.5ex; }
			.hour-box { float: left; text-align: center; margin-bottom: 1.5ex; width: 4.8em; }
			.quarters-box { font-size: 60%; margin: 2px; }
			.clearer { clear: both; }
		</style>
	</head>
	<body>
		<h1>Thermod Web Manager</h1>
		<div id="settings">
			<p>Current status: <span id="status">AUTO</span></p>
			<p>Change status to
				<select name="target-status" id="target-status">
					<option value="auto" selected="selected">Auto</option>
					<option value="on">On</option>
					<option value="off">Off</option>
					<option value="tmax">t_max</option>
					<option value="tmin">t_min</option>
					<option value="t0">t_0</option>
				</select>
			</p>
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
					<!--input type="button" id="clear" value="Clear" /-->
				</div>
			</div>
			
			<div id="settings">
				
			</div>
		</div>
	</body>
</html>