<?php
$file = "/var/www/html/data/message.txt";

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $new_message = trim($_POST["message"] ?? "");
    file_put_contents($file, $new_message);
}

$current_message = file_exists($file) ? file_get_contents($file) : "No data found.";
?>

<!DOCTYPE html>
<html>
<head>
    <title>Cloud Backup Demo</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
        }
        .box {
            padding: 20px;
            border: 1px solid #ccc;
            max-width: 700px;
        }
        textarea {
            width: 100%;
            height: 120px;
        }
        .current {
            background: #f5f5f5;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 4px solid #0077cc;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Simulated Data Center Homepage</h1>
        <p>This page displays editable site data that will be backed up to AWS S3.</p>

        <div class="current">
            <h2>Current Stored Data</h2>
            <p><?php echo nl2br(htmlspecialchars($current_message)); ?></p>
        </div>

        <form method="POST">
            <label for="message"><strong>Update the displayed data:</strong></label><br><br>
            <textarea name="message" id="message"><?php echo htmlspecialchars($current_message); ?></textarea><br><br>
            <button type="submit">Save Update</button>
        </form>
    </div>
</body>
</html>
