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
                frame: rounded
                gap: 1
            </style>
            <script>
                count = 0
                g_count = 0

                init = function()
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

                    zml.define("random", function(fmt, minval, maxval)
                        return string.format(
                            fmt,
                            math.random(tonumber(minval), tonumber(maxval))
                        )
                    end)

                    zml.define("eid", function(fmt)
                        return string.format(fmt, self.eid)
                    end)
                end

                on_change("count", function()
                    g_count = count
                end)
            </script>
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
                    confirm('A question?', 'soething', function()
                        dialogue = true
                        alert(self)
                    end)
                "
            >
                <script> dialogue = false </script>
                test $dialogue
            </button>
            <tower>
                <style>
                    width: 80
                    gap: 1
                    overflow: [hide, auto]
                    frame: verticalouter
                </style>
                <field>This is some text</field>
                <field>This is some more text</field>
                <field>This is even more text</field>
                <field>This is some text</field>
                <field>This is some more text</field>
                <field>This is even more text</field>
                <field>This is some text</field>
                <field>This is some more text</field>
                <field>This is even more text</field>
                <row>
                    <style>
                        gap: 1
                        height: shrink
                    </style>
                    <text>My happiness</text>
                    <slider></slider>
                </row>
                <field multiline="true">
                    <style>
                        height: 10
                    </style>
                    <?php for ($i = 0; $i < 10; $i++): ?>
                    function on_submit(env)
                        count = count + 1
                    end
                    <?php endfor; ?>
                </field>
            </tower> 
        </tower> 
    </page>
</celx>
