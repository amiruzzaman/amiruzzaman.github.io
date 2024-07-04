<?php
error_reporting(E_ERROR | E_PARSE);
session_start();
if (!isset($_SESSION['user'])){
	header("Location: login.html");
}else{
	echo $_SESSION['user'] ."<br/>";
}
if (isset($_POST["import"])) {
    $fileName = $_FILES["file"]["tmp_name"];
    if ($_FILES["file"]["size"] > 0) {
        $file = fopen($fileName, "r");
        $find_header = 0;
        $csv = "word,need,focus\n";//Column headers
        while (($column = fgetcsv($file, 10000, ",")) !== FALSE) {
            $find_header++; //update counter
            //this ensures we skip the header
            if ($find_header > 1) {
                $csv .= $column[0] . ',' . $column[1] . ',' . $column[2] . "\n"; //Append data to csv
            }
        }
        try {
            $csv_handler = fopen('data.csv', 'w');
            if(is_resource($csv_handler)) {
                fwrite($csv_handler, $csv);
                fclose($csv_handler);
                echo '<div style="width: 50%; margin: 0 auto;color:green;">Data saved to data.csv</div>';
            }else{
                echo '<div style="width: 50%; margin: 0 auto;color:red;">An error occured!</div>';
            }

            
        } catch (RuntimeException $e) {
            echo $e->getMessage();
            echo '<div style="width: 50%; margin: 0 auto;color:red;">Try again!!</div>';
            
        }
    }
}
?>
<!DOCTYPE html>
<html>

<head>
    <title>Welcome Home</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.4.0/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"></script>
	<style>
        
    </style>
    <style>
	.gg-log-out {
    box-sizing: border-box;
    position: relative;
    display: block;
    width: 6px;
    height: 16px;
    border: 2px solid;
    transform: scale(var(--ggs,1));
    border-right: 0;
    border-top-left-radius: 2px;
    border-bottom-left-radius: 2px;
    margin-left: -10px
}
.gg-log-out::after,
.gg-log-out::before {
    content: "";
    display: block;
    box-sizing: border-box;
    position: absolute
}
.gg-log-out::after {
    border-top: 2px solid;
    border-left: 2px solid;
    transform: rotate(-45deg);
    width: 8px;
    height: 8px;
    left: 4px;
    bottom: 2px
}
.gg-log-out::before {
    border-radius: 3px;
    width: 10px;
    height: 2px;
    background: currentColor;
    left: 5px;
    bottom: 5px
}

	</style>
</head>

<body>
    <div class="container">
        <!-- <div class="jumbotron">
    </div>    -->

        <form class="form-horizontal" action="" method="post" name="uploadCSV" enctype="multipart/form-data">
            <div class="input-row">
                <label class="col-md-4 control-label">Choose CSV File</label> <input type="file" name="file" id="file"
                    accept=".csv">
                <button type="submit" id="submit" name="import" class="btn-submit">Import</button>
                <br />

            </div>
            <div id="labelError"></div>
        </form>
    </div>
    <hr>
    <br>

    <script type="text/javascript">
        // $(document).ready(
        // function() {
        // 	$("#frmCSVImport").on(
        // 	"submit",
        // 	function() {

        // 		$("#response").attr("class", "");
        // 		$("#response").html("");
        // 		var fileType = ".csv";
        // 		var regex = new RegExp("([a-zA-Z0-9\s_\\.\-:])+("
        // 				+ fileType + ")$");
        // 		if (!regex.test($("#file").val().toLowerCase())) {
        // 			$("#response").addClass("error");
        // 			$("#response").addClass("display-block");
        // 			$("#response").html(
        // 					"Invalid File. Upload : <b>" + fileType
        // 							+ "</b> Files.");
        // 			return false;
        // 		}
        // 		return true;
        // 	});
        // });
    </script>
	<div style="width:800px; margin:0 auto;">
		<a href="logout.php"><i class="gg-log-out"></i></a>
	</div>
</body>

</html>