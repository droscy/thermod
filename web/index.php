<?php
	// hostname (or IP address) and port on which Thermod is listening
	$HOST = 'localhost';
	$PORT = 4344;
?>
<!DOCTYPE html>
<html lang="en">
	<head>
		<meta charset="utf-8">
		<title>Thermod Web Manager</title>
		<script src="js/jquery.js"></script>
		<script src="js/jquery-ui.js"></script>
		<script src="js/jquery-ui.labeledslider.min.js"></script>
		<link href="css/jquery-ui.css" rel="stylesheet">
		<link href="css/jquery-ui.theme.css" rel="stylesheet">
		<link href="css/jquery-ui.labeledslider.css" rel="stylesheet">
		<script>
			var settings = jQuery.parseJSON('<?php $settings = @file_get_contents('http://localhost:4344/settings'); if($settings !== false) { echo(str_replace("\n",'',$settings)); } else { echo('{"error": "TODO"}'); }; ?>');

			function jsontemp2slidevalue(temp)
			{
				var value = null;
				
				switch(temp)
				{
					case 'tmax':
						value = 3;
						break;
	
					case 'tmin':
						value = 2;
						break;
	
					case 't0':
						value = 1;
						break;

					default:
						value = 4;
				}
	
				return value;
			}
			
			/*function slidevalue2jsontemp(value)
			{
				var temp = null;
				
				switch(value)
				{
					case 3:
						temp = 'tmax';
						break;

					case 2:
						temp = 'tmin';
						break;

					case 1:
						temp = 't0';
						break;

					default:
						
				
					case 'tmax':
						value = 3;
						break;
	
					case 'tmin':
						value = 2;
						break;
	
					case 't0':
						value = 1;
						break;

					default:
						if(temp > settings['temperatures']['tmax'])
							value = 4;
						else
							value = 0;
				}
	
				return value;
			}*/

			function check_dayhour(clicked)
			{
				var ndays = $('#days input[type=checkbox]:checked').length;
				var nhours = $('#hours input[type=checkbox]:checked').length;

				if(ndays > 0 && nhours > 0)
				{
					$('.slidevert').slider('option', 'disabled', false);
					// TODO aggiornare le slider al valore dell'orario selezionato, se questo è univoco, altrimenti decidere come fare

					if(ndays == 1 && nhours == 1)
					{
						var day = $('#days input[type=checkbox]:checked').prop('name');
						var hour = $('#hours input[type=checkbox]:checked').prop('name');
						var quarters = settings['timetable'][day][hour];

						$('#quarter_0').slider('value', jsontemp2slidevalue(quarters[0]));
						$('#quarter_1').slider('value', jsontemp2slidevalue(quarters[1]));
						$('#quarter_2').slider('value', jsontemp2slidevalue(quarters[2]));
						$('#quarter_3').slider('value', jsontemp2slidevalue(quarters[3]));
					}
					else
					{
						$('#quarter_0').slider('value', 0);
						$('#quarter_1').slider('value', 0);
						$('#quarter_2').slider('value', 0);
						$('#quarter_3').slider('value', 0);
					}
				}
				else
					$('.slidevert').slider('option', 'disabled', true);
			}
			
			$(function()
			{
				$('#tabs').tabs();
				$('#days').buttonset();
				$('#hours').buttonset();
				$('input[type=button]').button();
				
				//$('.slidevert').slider({
				//	orientation: 'vertical',
				//	range: 'min',
				//	min: 0,
				//	max: 30,
				//	value: 20,
				//	step: 0.1,
				//	slide: function(event,ui)
				//	{
				//		var slideid = '#' + $(this).prop('id');
				//		var tempid = '#temp_' + $(this).prop('id');
				//		$(tempid).html(ui.value);
				//	}
				//});
				
				/*$('.slidevert_last').labeledslider({
					//disabled: true,
					orientation: 'vertical',
					range: 'min',
					min: 0,
					max: 30,
					value: 20,
					step: 1,
					tickArray: [20,17,6],
					tickLabels: { 20: 'tmax', 17: 'tmin', 6: 't0'},
					slide: function(event,ui)
					{
						var slideid = '#' + $(this).prop('id');
						var tempid = '#temp_' + $(this).prop('id');
						//$(tempid).html(ui.value);
						$(tempid).prop('value',ui.value);
					}
				});*/
				
				$('.slidevert_last').labeledslider({
					//disabled: true,
					orientation: 'vertical',
					range: 'min',
					min: 0,
					max: 4,
					value: 3,
					step: 1,
					tickLabels: { 4: 'custom', 3: 'tmax', 2: 'tmin', 1: 't0', 0: 'mixed'},
					change: function(event,ui)
					{
						var slideid = '#' + $(this).prop('id');
						var tempid = '#temp_' + $(this).prop('id');
						//$(tempid).html(ui.value);
						$(tempid).prop('value',ui.value);
					}
				});
				
				$('.slidevert').slider({
					disabled: true,
					orientation: 'vertical',
					range: 'min',
					min: 0,
					max: 4,
					value: 3,
					step: 1,
					change: function(event,ui)
					{
						var slideid = '#' + $(this).prop('id');
						var tempid = '#temp_' + $(this).prop('id');
						//$(tempid).html(ui.value);
						$(tempid).prop('value',ui.value);
					}
				});

				

				$('#days input[type=checkbox]').click(function(){ check_dayhour($(this)); });
				$('#hours input[type=checkbox]').click(function(){ check_dayhour($(this)); });
				
				$('#save').click(function(){
					var days = [];
					var hours = [];
					
					$('#days input:checked').each(function(){ days.push($(this).prop('name')); });
					$('#hours input:checked').each(function(){ hours.push($(this).prop('name')); });
					
					for(d=0; d<days.length; d++)
					{
						for(h=0; h<hours.length; h++)
						{
							settings['timetable'][days[d]][hours[h]] = [1,2,3,4];
							alert(days[d] + ',' + hours[h] + ': ' + settings['timetable'][days[d]][hours[h]]);
						}
					}
					
				});
				
				$('#clear').click(function(){
					$('#days input:checked').each(function(){ $(this).prop('checked', false).change(); });
					$('#hours input:checked').each(function(){ $(this).prop('checked', false).change(); });
				});
			});
		</script>
		<style>
			/*select { width: 100px; }*/
			/*#settings { float: left; border: 1px solid #000000; height: 150px; }*/
			
			/*.ui-slider-vertical { width: 1px; }
			.ui-slider .ui-slider-handle { height: 1px; width: 0.8em; }
			.head { float: left; background-color: #DDFFFF; }*/
			
			/* quelli buoni */
			#tabs { font-size: 70%; }
			#schedule p { margin: 0px 0px 1ex 0px; }
			#days { margin-bottom: 3ex; }
			#hours { margin-bottom: 3ex; }
			#temperatures { margin-bottom: 3ex; }
			#buttons { margin-top: 3ex; }
			.degrees { text-align: center; }
			
			.quarter { float: left; text-align: center; width: 6.2ex; margin-right: 1ex; background-color: #DDFFFF; }
			.slidevert { height: 150px; margin: 1ex auto; }
			.slidevert_last { height: 150px; margin: 1ex 0px; }
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
				<p>Select day(s)</p>
				<div id="days">
					<input type="checkbox" id="monday" name="monday" /> <label for="monday">Monday</label>
					<input type="checkbox" id="tuesday" name="tuesday" /><label for="tuesday">Tuesday</label>
					<input type="checkbox" id="wednesday" name="wednesday" /><label for="wednesday">Wednesday</label>
					<input type="checkbox" id="thursday" name="thursday" /><label for="thursday">Thursday</label>
					<input type="checkbox" id="friday" name="friday" /><label for="friday">Friday</label>
					<input type="checkbox" id="saturday" name="saturday" /><label for="saturday">Saturday</label>
					<input type="checkbox" id="sunday" name="sunday" /><label for="sunday">Sunday</label>
				</div>
				
				<div id="hours">
					<p>Select hour(s)</p>
					<input type="checkbox" id="hour_00" name="h00" /><label for="hour_00">00</label>
					<input type="checkbox" id="hour_01" name="h01" /><label for="hour_01">01</label>
					<input type="checkbox" id="hour_02" name="h02" /><label for="hour_02">02</label>
					<input type="checkbox" id="hour_03" name="h03" /><label for="hour_03">03</label>
					<input type="checkbox" id="hour_04" name="h04" /><label for="hour_04">04</label>
					<input type="checkbox" id="hour_05" name="h05" /><label for="hour_05">05</label>
					<input type="checkbox" id="hour_06" name="h06" /><label for="hour_06">06</label>
					<input type="checkbox" id="hour_07" name="h07" /><label for="hour_07">07</label>
					<input type="checkbox" id="hour_08" name="h08" /><label for="hour_08">08</label>
					<input type="checkbox" id="hour_09" name="h09" /><label for="hour_09">09</label>
					<input type="checkbox" id="hour_10" name="h10" /><label for="hour_10">10</label>
					<input type="checkbox" id="hour_11" name="h11" /><label for="hour_11">11</label>
					<input type="checkbox" id="hour_12" name="h12" /><label for="hour_12">12</label>
					<input type="checkbox" id="hour_13" name="h13" /><label for="hour_13">13</label>
					<input type="checkbox" id="hour_14" name="h14" /><label for="hour_14">14</label>
					<input type="checkbox" id="hour_15" name="h15" /><label for="hour_15">15</label>
					<input type="checkbox" id="hour_16" name="h16" /><label for="hour_16">16</label>
					<input type="checkbox" id="hour_17" name="h17" /><label for="hour_17">17</label>
					<input type="checkbox" id="hour_18" name="h18" /><label for="hour_18">18</label>
					<input type="checkbox" id="hour_19" name="h19" /><label for="hour_19">19</label>
					<input type="checkbox" id="hour_20" name="h20" /><label for="hour_20">20</label>
					<input type="checkbox" id="hour_21" name="h21" /><label for="hour_21">21</label>
					<input type="checkbox" id="hour_22" name="h22" /><label for="hour_22">22</label>
					<input type="checkbox" id="hour_23" name="h23" /><label for="hour_23">23</label>
				</div>
				
				<!--div id="temperatures">
					<p>Choose temperature for each quarter of an hour</p>
					<div class="quarter"><p>00</p><div id="quarter_0" class="slidevert"></div><p id="temp_quarter_0">20.0</p></div>
					<div class="quarter"><p>15</p><div id="quarter_1" class="slidevert"></div><p id="temp_quarter_1">20.0</p></div>
					<div class="quarter"><p>30</p><div id="quarter_2" class="slidevert"></div><p id="temp_quarter_2">20.0</p></div>
					<div class="quarter"><p>45</p><div id="quarter_3" class="slidevert"></div><p id="temp_quarter_3">20.0</p></div>
				</div-->
				
				<div id="temperatures">
					<p>Choose temperature for each quarter of an hour</p>
					<div class="quarter">Prova</div>
					<div class="quarter"><p>00</p><div id="quarter_0" class="slidevert"></div><input type="text" id="temp_quarter_0" class="degrees" value="20.0" size="2" /></div>
					<div class="quarter"><p>15</p><div id="quarter_1" class="slidevert"></div><input type="text" id="temp_quarter_1" class="degrees" value="20.0" size="2" /></div>
					<div class="quarter"><p>30</p><div id="quarter_2" class="slidevert"></div><input type="text" id="temp_quarter_2" class="degrees" value="20.0" size="2" /></div>
					<div class="quarter"><p>45</p><div id="quarter_3" class="slidevert"></div><input type="text" id="temp_quarter_3" class="degrees" value="20.0" size="2" /></div>
				</div>
				
				<div class="clearer"></div>
				
				<div id="buttons">
					<p>Save settings</p>
					<input type="button" id="save" value="Save" />
					<input type="button" id="clear" value="Clear" />
				</div>
				
			</div>
			
			<div id="settings">
				
			</div>
			
			<!--
			<div id="monday">
				<div class="temperatures">
					<div class="quarter"><p class="hourlabel">00:00</p><div id="slide_000" class="slidevert"></div><p id="temp_slide_000">20.0</p></div>
					<div class="quarter"><p class="hourlabel">00:15</p><div id="slide_001" class="slidevert"></div><p id="temp_slide_001">20.0</p></div>
					<div class="quarter"><p class="hourlabel">00:30</p><div id="slide_002" class="slidevert"></div><p id="temp_slide_002">20.0</p></div>
					<div class="quarter"><p class="hourlabel">00:45</p><div id="slide_003" class="slidevert"></div><p id="temp_slide_003">20.0</p></div>
					<div class="quarter"><p class="hourlabel">01:00</p><div id="slide_010" class="slidevert"></div><p id="temp_slide_010">20.0</p></div>
					<div class="quarter"><p class="hourlabel">01:15</p><div id="slide_011" class="slidevert"></div><p id="temp_slide_011">20.0</p></div>
					<div class="quarter"><p class="hourlabel">01:30</p><div id="slide_012" class="slidevert"></div><p id="temp_slide_012">20.0</p></div>
					<div class="quarter"><p class="hourlabel">01:45</p><div id="slide_013" class="slidevert"></div><p id="temp_slide_013">20.0</p></div>
					<div class="quarter"><p class="hourlabel">02:00</p><div id="slide_020" class="slidevert"></div><p id="temp_slide_020">20.0</p></div>
					<div class="quarter"><p class="hourlabel">02:15</p><div id="slide_021" class="slidevert"></div><p id="temp_slide_021">20.0</p></div>
					<div class="quarter"><p class="hourlabel">02:30</p><div id="slide_022" class="slidevert"></div><p id="temp_slide_022">20.0</p></div>
					<div class="quarter"><p class="hourlabel">02:45</p><div id="slide_023" class="slidevert"></div><p id="temp_slide_023">20.0</p></div>
					<div class="quarter"><p class="hourlabel">03:00</p><div id="slide_030" class="slidevert"></div><p id="temp_slide_030">20.0</p></div>
					<div class="quarter"><p class="hourlabel">03:15</p><div id="slide_031" class="slidevert"></div><p id="temp_slide_031">20.0</p></div>
					<div class="quarter"><p class="hourlabel">03:30</p><div id="slide_032" class="slidevert"></div><p id="temp_slide_032">20.0</p></div>
					<div class="quarter"><p class="hourlabel">03:45</p><div id="slide_033" class="slidevert"></div><p id="temp_slide_033">20.0</p></div>
				</div>
				
				<div class="clearer"></div>
			</div>
			<div id="tuesday">
				<table>
					<tr><th>Ore</th><th colspan="4">Minuti</th></tr>
					<tr><th></th><th>00</th><th>15</th><th>30</th><th>45</th></tr>
					<tr>
						<th>00:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>01:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>02:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>03:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>04:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>05:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>06:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>07:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>08:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>09:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>10:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>11:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>12:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>13:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>14:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>15:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>16:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>17:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>18:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>19:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>20:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>21:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>22:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>23:00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
				</table>
			</div>
			
			<div id="wednesday">
				<table>
					<tr>
						<th></th>
						<th>00:00</th>
						<th>01:00</th>
						<th>02:00</th>
						<th>03:00</th>
						<th>04:00</th>
						<th>05:00</th>
						<th>06:00</th>
						<th>07:00</th>
						<th>08:00</th>
						<th>09:00</th>
						<th>10:00</th>
						<th>11:00</th>
						<th>12:00</th>
						<th>13:00</th>
						<th>14:00</th>
						<th>15:00</th>
						<th>16:00</th>
						<th>17:00</th>
						<th>18:00</th>
						<th>19:00</th>
						<th>20:00</th>
						<th>21:00</th>
						<th>22:00</th>
						<th>23:00</th>
					</tr>
					<tr>
						<th>00</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>15</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>30</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
					<tr>
						<th>45</th>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
						<td><input type="text" value="20.0" size="3"></td>
					</tr>
				</table>
			</div>
			
			<div id="thursday">
				<div id="days">
					<input type="radio" id="mon" name="day"><label for="mon">Monday</label>
					<input type="radio" id="tue" name="day"><label for="tue">Tuesday</label>
					<input type="radio" id="wed" name="day"><label for="wed">Wednesday</label>
					<input type="radio" id="thu" name="day"><label for="thu">Thursday</label>
					<input type="radio" id="fri" name="day"><label for="fri">Friday</label>
					<input type="radio" id="sat" name="day"><label for="sat">Saturday</label>
					<input type="radio" id="sun" name="day"><label for="sun">Sunday</label>
				</div>
				
				<div id="hours">
					<input type="radio" id="hour_00" name="hour"><label for="hour_00">00</label>
					<input type="radio" id="hour_01" name="hour"><label for="hour_01">01</label>
					<input type="radio" id="hour_02" name="hour"><label for="hour_02">02</label>
					<input type="radio" id="hour_03" name="hour"><label for="hour_03">03</label>
					<input type="radio" id="hour_04" name="hour"><label for="hour_04">04</label>
					<input type="radio" id="hour_05" name="hour"><label for="hour_05">05</label>
					<input type="radio" id="hour_06" name="hour"><label for="hour_06">06</label>
					<input type="radio" id="hour_07" name="hour"><label for="hour_07">07</label>
					<input type="radio" id="hour_08" name="hour"><label for="hour_08">08</label>
					<input type="radio" id="hour_09" name="hour"><label for="hour_09">09</label>
					<input type="radio" id="hour_10" name="hour"><label for="hour_10">10</label>
					<input type="radio" id="hour_11" name="hour"><label for="hour_11">11</label>
					<input type="radio" id="hour_12" name="hour"><label for="hour_12">12</label>
					<input type="radio" id="hour_13" name="hour"><label for="hour_13">13</label>
					<input type="radio" id="hour_14" name="hour"><label for="hour_14">14</label>
					<input type="radio" id="hour_15" name="hour"><label for="hour_15">15</label>
					<input type="radio" id="hour_16" name="hour"><label for="hour_16">16</label>
					<input type="radio" id="hour_17" name="hour"><label for="hour_17">17</label>
					<input type="radio" id="hour_18" name="hour"><label for="hour_18">18</label>
					<input type="radio" id="hour_19" name="hour"><label for="hour_19">19</label>
					<input type="radio" id="hour_20" name="hour"><label for="hour_20">20</label>
					<input type="radio" id="hour_21" name="hour"><label for="hour_21">21</label>
					<input type="radio" id="hour_22" name="hour"><label for="hour_22">22</label>
					<input type="radio" id="hour_23" name="hour"><label for="hour_23">23</label>
				</div>
			</div>
			-->
		</div>
	</body>
</html>