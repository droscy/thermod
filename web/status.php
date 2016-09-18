<?php
$HOST = (isset($_GET['host']) ? htmlentities($_GET['host']) : 'localhost');
$PORT = (isset($_GET['port']) ? htmlentities($_GET['port']) : '4344');

$status = null;
$socket_http_code = null;

if(function_exists('curl_version'))
{
	$curl = curl_init("http://{$HOST}:{$PORT}/heating");
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