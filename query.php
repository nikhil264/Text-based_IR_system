<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <title>INFER®</title>
  <link rel='stylesheet' href='infer_results_style.css'>
</head>
<body>
<div class ='header'>
  	<form action='query.php' method='post'>
	<input type="text" id="search" name="search"  autofocus autocomplete="off"><br />
	<input type='submit' value='Infer Search'>
	</form>
</div>
<div class= "all_results">


<?php

$user_input = $_POST['search'];


//$user_input = readline("Query: ");

if(strlen($user_input)){
		
	include 'stemmer.php';

	$conn = mysqli_connect('127.0.0.1', 'root', 'yourmom.h','handouts');
	if (!$conn) {
	    die('Something went wrong while connecting to MSSQL');
	}


	$st = microtime();


	$query_token = explode(" ",strtolower($user_input));
	$query_tokens = preg_split('([f-h][0-9]{3})',$user_input);
	$query_tokens = array_merge($query_tokens, explode($query_tokens[0], $user_input));
	// $query_tokens = array();
	foreach ($query_token as $value) 
	{
		$temp = PorterStemmer::Stem($value);
		array_push($query_tokens, $temp);
	}

	//var_dump($query_tokens);


	        
	$t = implode('\',\'', $query_tokens);
	$t = '\''.$t.'\'';


	$query = "SELECT postings from matrix where tokens in ($t)";
	$result = mysqli_query($conn,$query);
	
	if (!$result) {
	  die('Invalid query: ' . mysqli_error());
	}

	if (mysqli_num_rows($result) > 0) 
	{
		$doc_list = array();
		$result_or = array();
	    while ($row = mysqli_fetch_array($result, MYSQLI_NUM)) 
	    {
	    	
			$temp = explode(',', $row[0]);
			array_push($doc_list, $temp);
			$result_or = array_merge($result_or, $temp);

		}
		$result_and = $doc_list[0];
		foreach ($doc_list as $value) 
		{
			$result_and = array_intersect($result_and, $value);
		}
		array_unique($result_or);
		// // var_dump($doc_list);
		//  var_dump($result_and);
		//  var_dump($result_or);
		//  printf(sizeof($result_and));

		if (sizeof($result_and)) 
		{
			$results  = array();
			foreach ($result_and as $value) 
			{
				
				$query = "SELECT doc$value FROM docvectors WHERE tokens in ($t)";
				$result = mysqli_query($conn,$query);
				if (!$result) 
				{
				  die('Invalid query: ' . mysqli_error());
				}
				
				while ($row = mysqli_fetch_array($result, MYSQLI_NUM))
				{	
					$results["doc$value"] = isset($results["doc$value"]) ? $results["doc$value"] : 0.0;
					$results["doc$value"] += floatval($row[0]);
				}
			}
			arsort($results);
			foreach ($results as $key => $value) 
			{
				$query = "SELECT * FROM docnames WHERE docno = '$key'";
				$result = mysqli_query($conn, $query);
				if (!$result) 
				{
				  die('Invalid query: ' . mysqli_error());
				}
				while ($row = mysqli_fetch_array($result, MYSQLI_NUM))
				{
					printf ("<div class='card'>");
					printf("<a class = 'result' href='http://cms.bits-hyderabad.ac.in/moodle/course/view.php?id=%s' > <p class ='course_id'>%s</p> <p class='course_name'>%s</p> </a>\n <a class='direct_doc' href='http://localhost/IR/Handouts/%s'>Open</a>", $row[3], $row[1], $row[2],$key);
					printf("</div>");
				}		
			}

		}
		else
		{
			$results  = array();
			foreach ($result_or as $value) {
				$query = "SELECT doc$value FROM docvectors WHERE tokens in ($t)";
				$result = mysqli_query($conn,$query);
				if (!$result) {
				  die('Invalid query: ' . mysqli_error());
				}
				while ($row = mysqli_fetch_array($result, MYSQLI_NUM)){
					$results["doc$value"] = isset($results["doc$value"]) ? $results["doc$value"] : 0.0;
					$results["doc$value"] += floatval($row[0]);
					
				}
			}
			arsort($results);
			foreach ($results as $key => $value) {
				$query = "SELECT * FROM docnames WHERE docno = '$key'";
				$result = mysqli_query($conn,$query);
				if (!$result) {
				  die('Invalid query: ' . mysqli_error());
				}
				while ($row = mysqli_fetch_array($result, MYSQLI_NUM))
				{
					printf ("<div class='card'>");
					printf("<a class = 'result' href='http://cms.bits-hyderabad.ac.in/moodle/course/view.php?id=%s' > <p class ='course_id'>%s</p> <p class='course_name'>%s</p> </a>\n <a class='direct_doc' href='http://localhost/IR/Handouts/%s'>Open</a>", $row[3], $row[1], $row[2],$key);
					printf("</div>");
				}
			}

		}

		
		
	}
	else{
		printf("<h1 class='no_results'>\nNo relevant documents containing all the search terms\n</h1>");
	}


	printf("<p class='time'>Results obtained in %0.4lf secs</p>\n", microtime()-$st);
}
else{
		
		function Redirect($url, $permanent = false)
		{
		    if (headers_sent() === false)
		    {
		    	header('Location: ' . $url, true, ($permanent === true) ? 301 : 302);
		    }

		    exit();
		}
	Redirect('http://localhost/IR/infer.html', false);
}

?>
</div>
</body>
</html>
