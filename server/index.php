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
        <component name="counter" value="0" min="0" max="10">
            <row eid="friend">
                <style>
                    gap: 1
                    height: shrink
                </style>
                <script>
                    value = $value

                    function add(num)
                        value = math.min(math.max(value + num, $min), $max)
                    end
                </script>
                <_slot />
                <button on-submit="add(-1)"> - </button>
                <text>$value</text>
                <button on-submit="add(1)"> + </button>
            </row>
        </component>
        <component name="counters">
            <tower>
                <style>
                    gap: 0
                    height: shrink
                </style>
                <_slot />
                <counter />
                <counter />
                <counter />
            </tower>
        </component>
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
            <tower pre-content="drawcount = drawcount + 1">
                <script> drawcount = 0 </script>
                <text>Drawn: $drawcount times</text>
                <style> frame: rounded </style>
                <field name="content" multiline="true">
                </field>
                <button on-submit=":POST /lua; SWAP IN #output">Run</button>
                <tower eid="output"></tower>
            </tower>
            <counter value="2" max="20"/>
            <counters>
                <text>[bold]This is a title</text>
                <counter value="69"/>
            </counters>
            <row>
                <style>
                    alignment: [center, start]
                    gap: 1
                    width: shrink
                </style>
                <script>
                    count = 0
                </script>
                <button on-submit="count = count - 1">
                    Remove!
                </button>
                <text>Clicked $count times</text>

                <button on-submit="count = count + 1"> Add! </button>

                <button>
                    Add
                    <script>
                        function on_submit()
                            count = count + 1
                        end
                    </script>
                </button>

                <button on-submit=":POST /add; SWAP IN self"> Submit </button>

            </row> 
            <text>[bold]Imagine this is a form</text>
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
