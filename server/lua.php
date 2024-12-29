<?php
file_put_contents("request.lua", $_POST["content"]);

echo shell_exec("lua request.lua 2>&1");
