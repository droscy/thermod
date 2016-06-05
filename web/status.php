<?php
$HOST = (isset($_GET['host']) ? htmlentities($_GET['host']) : 'localhost');
$PORT = (isset($_GET['port']) ? htmlentities($_GET['port']) : '4344');

$status = null;

if(function_exists('curl_version'))
{
	$curl = curl_init("http://{$HOST}:{$PORT}/heating");
	curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
	$status = curl_exec($curl);
		
	if($status === false)
		$status = json_encode(array('error' => curl_error($curl)));
	
	curl_close($curl);
}
else
	$status = json_encode(array('error' => 'php-curl extension is not enabled in your web server'));
		
echo(preg_replace('/\s+/', ' ', str_replace("\n", '', $status)));
?>