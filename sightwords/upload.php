<?php
/**
 * function : uploadCSVFile 
 *      Sanitizes file name and prepends date for uniqueness
 *      Checks file sizes form config allowed file size 
 *      Checkes extensions for legal file type in this case csv, as mentioned in config
 *      Uploads the file to the temporary path for csv mentioned in the config
 * param:
 *      The name attribute of the input type file in the form field
 * return:
 *      returns the uploaded file name on success else returns null
 */
define('CSV_FILETYPE_REGX',  "/^\.(csv){1}$/i"); 
define('CSV_TEMP_UPLOAD_PATH', 'C:\xampp\htdocs\csvupload\\');
define('MAXIMUM_CSV_FILESIZE_KB', 100);

function uploadCSVFile($formfilename){
$this->error=false;
$this->errorstack=array();

	$isFile = is_uploaded_file($_FILES[$formfilename]['tmp_name']); 
	$safe_filename='';
	if($isFile){
			//  sanatize file name
			//     - remove extra spaces/convert to _,
			//     - remove non 0-9a-Z._- characters,
			//     - remove leading/trailing spaces
			//  check if under allowed size,
			//  check file extension for legal file types also prepending datestring
			$safe_filename = preg_replace(
							 array("/\s+/", "/[^-\.\w]+/"),
							 array("_", ""),
							 trim(date("Ymdhis").$_FILES[$formfilename]['name'])); 

			if ($_FILES[$formfilename]['size'] <= (MAXIMUM_CSV_FILESIZE_KB*1024)){

			}else{
				$this->error=true;
				array_push($this->errorstack," Filesize is greater than ".MAXIMUM_CSV_FILESIZE_KB." KB")	;
			}

			if(preg_match(CSV_FILETYPE_REGX, strrchr($safe_filename, '.')) ){

			 }else {
				$this->error=true;
				array_push($this->errorstack," File type is not allowed");
			}

		   if(!$this->error){   
					$isMove = move_uploaded_file (
							$_FILES[$formfilename]['tmp_name'],
							CSV_TEMP_UPLOAD_PATH.$safe_filename);
					if($isMove){

					} else {
						$this->error=true;
						array_push($this->errorstack,"Upload Error");
					}
		   }

	}else{
		$this->error=true;
		array_push($this->errorstack,"File not uploaded");
	}

	if($this->error){
		return NULL;
	}else {
		return $safe_filename;
	}

}

        
	
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
	<meta http-equiv="content-type" content="text/html; charset=iso-8859-1" />
	<meta name="author" content="Raju Gautam" />
	<title>Test</title>
</head>
<body>
    <form enctype="multipart/form-data" action="" method="post" id="add-courses"> 
        <table cellpadding="5" cellspacing="0" width="500" border="0"> 
            <tr> 
                <td class="width"><label for="image">Upload CSV file : </label></td> 
                <td><input type="hidden" name="MAX_FILE_SIZE" value="10000000" /><input type="file" name="csvfile" id="csvfile" value=""/></td> 
                <td><input type="submit" name="uploadCSV" value="Upload" /></td> 
            </tr> 
        </table> 
    </form>
</body>
</html>
