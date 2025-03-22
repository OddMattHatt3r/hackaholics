<?php
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $to = "rodrigo1514.rg@gmail.com"; // Replace with your email
    $subject = "New Form Submission";
    $message = "Phone Number: " . $_POST['phone'];
    $headers = "From: " . $_POST['email'];

    if (mail($to, $subject, $message, $headers)) {
        echo "Email sent successfully.";
    } else {
        echo "Failed to send email.";
    }
}
?>