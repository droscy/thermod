<?php

$HOST = (isset($_REQUEST['host']) ? htmlentities($_REQUEST['host']) : 'localhost');
$PORT = (isset($_REQUEST['port']) ? htmlentities($_REQUEST['port']) : '4344');

if(!isset($_POST['settings']))
{
	$settings = @file_get_contents("http://{$HOST}:{$PORT}/settings");
	
	if($settings !== false)
		echo(preg_replace('/\s+/',' ',str_replace("\n",'',$settings)));
	else
	{
		//print_r($http_response_header);
		echo('{"error": "unable to retrive settings from Thermod, maybe wrong address or daemon down?"}');
	}
}
else
{
	$postdata = http_build_query(array('settings' => json_encode($_POST['settings'],JSON_NUMERIC_CHECK)));
	$opts = array
	(
		'http' => array
		(
			'method'  => 'POST',
			'header'  => 'Content-type: application/x-www-form-urlencoded',
			'content' => $postdata
		)
	);
	
	$context = stream_context_create($opts);
	$result = @file_get_contents("http://{$HOST}:{$PORT}/settings", false, $context);
}
?>