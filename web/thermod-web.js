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

// thermod settings
var settings;

// capitalize only first letter
String.prototype.ucfirst = function()
{
    return this.charAt(0).toUpperCase() + this.slice(1);
}

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

// refresh the selectmenu of target mode
function target_mode_refresh()
{
	$('#target-mode option[value=' + settings['mode'] + ']').prop('selected', true);
}

// handle the change event of target status
function target_mode_change(event, ui)
{
	var target_mode = $('#target-mode option:selected').prop('value');

	$.ajax(
	{
		type: 'POST',
		url: baseurl + '/settings',
		data: {'mode': target_mode},
		success: function(data)
		{
			settings['mode'] = target_mode;
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
			$('#dialog').dialog('option', 'title', 'Cannot change mode');
			$('#dialog').dialog('option', 'buttons', {'Close': function() { $(this).dialog('close'); }});
			$('#dialog').html('<p><span class="ui-icon ui-icon-alert"></span>Cannot change mode: <em>&quot;' + error + '&quot;</em>.</p>');

			stop_loading();
			$('#dialog').dialog('open');

			if(jqXHR.status = 423)
			{
				settings['mode'] = target_mode;
				get_heating_status_and_refresh();
			}

			target_mode_refresh();
		}
	});
}

// retrieve heating status from daemon and refresh header web page
function get_heating_status_and_refresh()
{
	$.ajax(
	{
		type: 'GET',
		url: baseurl + '/status',
		success: function(data)
		{
			$('#current-status').prop('value', (data['status']==1 ? 'On' : 'Off'));
			$('#current-temperature').prop('value', data['current_temperature'].toFixed(1));
			$('#target-temperature').prop('value', (data['target_temperature'] ? data['target_temperature'].toFixed(1) : 'n.a.'));

			if(data['hvac_mode'] == 'cooling')
			{
				$('label[for=current-status]').text('Cooling');
				$('#target-mode option[value=t0]').text('Fastfreeze');
			}
			else
			{
				$('label[for=current-status]').text('Heating');
				$('#target-mode option[value=t0]').text('Antifreeze');
			}

			$('#target-mode').selectmenu('refresh');
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
			$('#dialog').html('<p><span class="ui-icon ui-icon-alert"></span>Cannot get current temperature and status: <em>&quot;' + error + '&quot;</em>.</p>');

			stop_loading();
			$('#dialog').dialog('open');
		}
	});
}

$(function()
{
	// main objects of the page
	$('#target-mode').selectmenu({disabled: true, change: target_mode_change});
	$('#tabs').tabs();
	$('#days').controlgroup({disabled: true});
	$('#days input').checkboxradio({icon: false});
	$('.hour').button({disabled: true, icon: false});
	$('.quarter').button({disabled: true, icon: false});
	
	$('#device').selectmenu(
	{
		disabled: true,
		change: function()
		{
			settings['hvac_mode'] = $('#device option:selected').prop('value');
		}
	});

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
			url: baseurl + '/settings',
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
		url: baseurl + '/settings',
		success: function(data)
		{
			// refresh values
			settings = data;
			target_mode_refresh();
			$('#' + today).prop('checked', true).change();

			var device = settings['hvac_mode'];
			$('#device option[value=' + device + ']').prop('selected', true);
			$('label[for=current-status]').text(device.ucfirst());

			if(settings['hvac_mode'] == 'cooling')
				$('#target-mode option[value=t0]').text('Fastfreeze');
			else
				$('#target-mode option[value=t0]').text('Antifreeze');

			$('#tmax').prop('value', settings['temperatures']['tmax'].toFixed(1));
			$('#tmin').prop('value', settings['temperatures']['tmin'].toFixed(1));
			$('#t0').prop('value', settings['temperatures']['t0'].toFixed(1));
			$('#differential').prop('value', settings['differential'].toFixed(1));

			var grace = settings['grace_time'] ? (settings['grace_time']/60) : 0;
			$('#grace-time').spinner('value', grace.toFixed(0));

			// enable objects
			$('#target-mode').selectmenu('option', 'disabled', false).selectmenu('refresh');
			$('#days').controlgroup('option', 'disabled', false);
			$('.hour').button('option', 'disabled', false);
			$('.quarter').button('option', 'disabled', false).button('refresh');
			$('.set-temperatures').spinner('option', 'disabled', false);
			$('#differential').spinner('option', 'disabled', false);
			$('#grace-time').spinner('option', 'disabled', false);
			$('#save').button('option', 'disabled', false);
			$('#device').selectmenu('option', 'disabled', false).selectmenu('refresh');
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

	$.get(baseurl + '/version', {}, function(data){ $('#version').html('v' + data['version']); },'json');
});

$(document).ajaxStart(start_loading).ajaxStop(stop_loading);

// vim: fileencoding=utf-8 tabstop=4
