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
        <style>
            Palette/main:
                primary: "<?= $primary ?>"
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

                        return string.format("[%s]%s", color, text)
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
            <text eid="friend">
                [bold]Primary color: [/fg @main.primary]<?= $primary ?>[/]

                GCount: [!threshold(g_count,lime,10,tomato)]$g_count[/]
                [!random(0,100)]Random: %i[/]
            </text>
            <row>
                <style>
                    alignment: [center, start]
                    gap: 1
                    width: shrink
                </style>
                <script>
                    count = 0
                </script>
                <button>
                    Remove!
                    <script>
                        function on_submit() count = count - 1 end
                    </script>
                </button>
                <text>Clicked $count times</text>
                <button>
                    Add!
                    <script>
                        function on_submit() count = count + 1 end
                    </script>
                </button>
            </row> 
            <text>[bold]Imagine this is a form</text>
            <tower>
                <style>
                    width: 80
                    gap: 1
                    overflow: [hide, auto]
                    frame: horizontalouter
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
