<?php
$HOST = (isset($_REQUEST['host']) ? htmlentities($_REQUEST['host']) : 'localhost');
$PORT = (isset($_REQUEST['port']) ? htmlentities($_REQUEST['port']) : '4344');

$result = null;

if(function_exists('curl_version'))
{
	$curl = curl_init("http://{$HOST}:{$PORT}/settings");
	curl_setopt($curl, CURLOPT_RETURNTRANSFER, 1);
	
	if(isset($_POST['settings']))
	{
		curl_setopt_array($curl, array
		(
			CURLOPT_POST => 1,
			//CURLOPT_POSTFIELDS => array('settings' => json_encode($_POST['settings'],JSON_NUMERIC_CHECK))
			CURLOPT_POSTFIELDS => 'settings=' . urlencode(json_encode($_POST['settings'],JSON_NUMERIC_CHECK))
		));
	}
	
	$result = curl_exec($curl);
		
	if($result === false)
		$result = json_encode(array('error' => curl_error($curl)));
	
	curl_close($curl);
}
else
	$result = json_encode(array('error' => 'php-curl extension is not enabled in your web server'));
		
echo(preg_replace('/\s+/',' ',str_replace("\n",'',$result)));
?>