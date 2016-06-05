<?php
$HOST = (isset($_REQUEST['host']) ? htmlentities($_REQUEST['host']) : 'localhost');
$PORT = (isset($_REQUEST['port']) ? htmlentities($_REQUEST['port']) : '4344');

$settings = null;

if(function_exists('curl_version'))
{
	$curl = curl_init("http://{$HOST}:{$PORT}/settings");
	curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
	
	if($_SERVER['REQUEST_METHOD'] == 'POST')
	{
		curl_setopt($curl, CURLOPT_POST, true);
		
		if(isset($_POST['settings']))
		{
			// multipart/form-data
			curl_setopt($curl, CURLOPT_POSTFIELDS, array('settings' => json_encode($_POST['settings'], JSON_NUMERIC_CHECK)));
			
			// application/x-www-form-urlencoded
			//curl_setopt($curl, CURLOPT_POSTFIELDS , 'settings=' . curl_escape($curl,json_encode($_POST['settings'], JSON_NUMERIC_CHECK)));
		}
		else
			curl_setopt($curl, CURLOPT_POSTFIELDS, $_POST);
	}
	
	$settings = curl_exec($curl);
		
	if($settings === false)
		$settings = json_encode(array('error' => curl_error($curl)));
	
	curl_close($curl);
}
else
	$settings = json_encode(array('error' => 'php-curl extension is not enabled in your web server'));
		
echo(preg_replace('/\s+/', ' ', str_replace("\n", '', $settings)));
?>