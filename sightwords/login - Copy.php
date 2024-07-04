<?php
function Login() {
            $success = false;           
            try {
                //$con = new PDO( 'mysql:host=localhost;dbname=MY_DB_NAME', 'MY_USRNAME', 'MY_PSW' );
                //$sql = "SELECT * FROM users WHERE username = :username AND password = :password LIMIT 1";

                //$stmt = $con->prepare( $sql );

                //$stmt->execute(array(':username'=>$_POST['username'], ':password'=>$_POST['password']));

                //$valid = $stmt->fetchColumn();
$valid = true;
                if( $valid ) {
                    $success = true;
                    session_start();
                    session_regenerate_id();
                    $_SESSION['user'] = $_POST['username'];
                    session_write_close();
                    echo ('CORRECTO');
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