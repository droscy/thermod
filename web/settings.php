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

$HOST = (isset($_REQUEST['host']) ? htmlentities($_REQUEST['host']) : 'localhost');
$PORT = (isset($_REQUEST['port']) ? htmlentities($_REQUEST['port']) : '4344');

$settings = null;
$socket_http_code = null;

if(function_exists('curl_version'))
{
	$curl = curl_init("http://{$HOST}:{$PORT}/settings");
	curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
	
	if($_SERVER['REQUEST_METHOD'] == 'POST')
	{
		curl_setopt($curl, CURLOPT_POST, true);
		
		if(isset($_POST['settings']))
		{
			// manage grace_time null value
			if(empty($_POST['settings']['grace_time'])
					|| trim($_POST['settings']['grace_time']) === ''
					|| trim(strtolower($_POST['settings']['grace_time']) == 'null'))
				$_POST['settings']['grace_time'] = null;
			
			// multipart/form-data
			curl_setopt($curl, CURLOPT_POSTFIELDS, array('settings' => json_encode($_POST['settings'], JSON_NUMERIC_CHECK)));
			
			// application/x-www-form-urlencoded
			//curl_setopt($curl, CURLOPT_POSTFIELDS , 'settings=' . curl_escape($curl,json_encode($_POST['settings'], JSON_NUMERIC_CHECK)));
		}
		else
			curl_setopt($curl, CURLOPT_POSTFIELDS, $_POST);
	}
	
	$settings = curl_exec($curl);
	$socket_http_code = curl_getinfo($curl, CURLINFO_HTTP_CODE);
		
	if($settings === false)
		$settings = json_encode(array('error' => curl_error($curl), 'socket_http_code' => $socket_http_code));
	else
	{
		// adding Thermod response HTTP code to the JSON response
		$settings = json_decode($settings);
		$settings->{'socket_http_code'} = $socket_http_code;
		$settings = json_encode($settings);
	}
	
	curl_close($curl);
}
else
	$settings = json_encode(array('error' => 'php-curl extension is not enabled in your web server'));

header('Content-Type: application/json;charset=utf-8');
echo(preg_replace('/\s+/', ' ', str_replace("\n", '', $settings)));
?>