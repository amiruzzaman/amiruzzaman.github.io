<?php
function Login() {
            $success = false;           
            try {
                $valid = true;
                if( $_POST['username'] == "admin" && $_POST['password'] =="admin123") {
                    $success = true;
                    session_start();
                    session_regenerate_id();
                    $_SESSION['user'] = $_POST['username'];
                    
                    echo ('CORRECTO');
					//header("Location: csvupload.php");
					//session_write_close();
                    exit();
                }

                $con = null;
                return $success;
            }
            catch (PDOException $e) {
                echo $e->getMessage();
                return $success;
            }
        }

 Login();
?>