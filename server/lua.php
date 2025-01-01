<?php
error_log(implode(",", array_keys($_POST)));
file_put_contents("request.lua", $_POST["content"]);

echo shell_exec("lua request.lua 2>&1");
