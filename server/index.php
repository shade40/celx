<?php
if ($_SERVER["REQUEST_URI"] == "/lua") {
    include "lua.php";
    die();
}

if (($_SERVER["HTTP_CELX_REQUEST"] ?? "") == "") {
    include "lua_compiler.php";
    die();
}

$primary = sprintf('#%06X', mt_rand(0, 0xFFFFFF));
?>
<celx version="1.0">
    <page title="home">
        <script src="/zml.lua"></script>
        <complib src="/counters.xml"/>
        <style>
            Palette/main:
                primary: "<?= $primary ?>"

            Text.body:
                overflow: [auto, auto]
        </style>
        <tower>
            <style>
                alignment: [center, center]
                frame: [padded, heavy, padded, padded]
                gap: 1
            </style>
            <script>
                count = 0
                g_count = 0

                on_change("count", function()
                    g_count = count
                end)

                function init()
                    zml.define("threshold", function(
                        text, field, under, threshold, over
                    )
                        local color

                        if tonumber(threshold) > _ENV[field] then
                            color =  under
                        else
                            color = over
                        end

                        return zml.expand_aliases(string.format(
                            "[%s]%s", color, text
                        ))
                    end)
                end
            </script>
            <row>
                <style>
                    height: 1
                    width: shrink
                    gap: 1
                </style>
                <link to="/">Main</link>
                <link to="/test">Test</link>
                <button>
                    <script> function on_submit() alert(zml.escape(tostring(app.history))) end </script>
                    history
                </button>
            </row>
            <?php if ($_SERVER["REQUEST_URI"] == "/test"): ?>
            <text>[bold red]TEST PAGE</text>
            <?php endif; ?>
            <text>
                [bold]Primary color: [/fg @main.primary]<?= $primary ?>[/]

                GCount: [!threshold(g_count,main.success,10,main.error)]$g_count[/]
                [!random(0,100)]Random: %i[/]
            </text>
            <form.counters>
                <text>[bold]Multiple counters</text>
                <form.counter initial="69"></form.counter>
                <form.counter initial="2" max="20"/>
                <form.counter initial="420"/>
            </form.counters>
            <text>[bold]Imagine this is a form</text>
            <button
                on-submit="
                    confirm('DJ Crazy Times', 'If you want parties to be making?\n...have some noise!', function(result)
                        if result then
                            alert('Women are my favorite guy! &lt;3')
                        else
                            alert('The rythm is not glad.')
                        end
                    end)
                "
            >
                Alert alert
            </button>
        </tower> 
    </page>
</celx>
