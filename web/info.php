<?php
/*
 * Copyright (C) 2016 Simone Rossetto <simros85@gmail.com>
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

$HOST = (isset($_GET['host']) ? htmlentities($_GET['host']) : 'localhost');
$PORT = (isset($_GET['port']) ? htmlentities($_GET['port']) : '4344');
$INFO = (isset($_GET['info']) ? htmlentities($_GET['info']) : null);

$status = null;
$socket_http_code = null;

if(!$INFO)
	$status = json_encode(array('error' => 'no information requested from daemon'));
else if(function_exists('curl_version'))
{
	$curl = curl_init("http://{$HOST}:{$PORT}/{$INFO}");
	curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
	$status = curl_exec($curl);
	$socket_http_code = curl_getinfo($curl, CURLINFO_HTTP_CODE);
		
	if($status === false)
		$status = json_encode(array('error' => curl_error($curl), 'socket_http_code' => $socket_http_code));
	else
	{
		// adding Thermod response HTTP code to the JSON response
		$status = json_decode($status);
		$status->{'socket_http_code'} = $socket_http_code;
		$status = json_encode($status);
	}
	
	curl_close($curl);
}
else
	$status = json_encode(array('error' => 'php-curl extension is not enabled in your web server'));

header('Content-Type: application/json;charset=utf-8');
echo(preg_replace('/\s+/', ' ', str_replace("\n", '', $status)));
?>