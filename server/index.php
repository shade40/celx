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
                <tower>
                    <style>
                        frame: [null, null, light, null]
                        gap: 1
                    </style>
                    <button>
                        <script>
                            function on_submit()
                                if 1 or 2 then
                                    print('one')
                                else
                                    print('two')
                                end

                                error('test')
                            end
                        </script>
                        Error
                    </button>
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

                        Global count: [!threshold(g_count,main.success,10,main.error)]$g_count[/]
                        [!random(0,100)]Random number: %i[/]
                    </text>
                    <text>
                        <style>
                            wrap: true
                            width: 1.0
                        </style>
                        Before forecasts, studies were only forks. A hen is a japan from the right perspective. A pint is a scorpio from the right perspective. Those coffees are nothing more than sciences. The zeitgeist contends that the first pelting donna is, in its own way, a rod.

                    </text>
                    <text>
                        <style>
                            wrap: true
                            width: 1.0
                        </style>
                        Unfortunately, that is wrong; on the contrary, a turn of the larch is assumed to be a boughten refund. The fancied ruth reveals itself as a spacial team to those who look. A history of the menu is assumed to be a halest backbone. The stylized boy comes from a stickit sleep.
                    </text>
                    <text>
                        <style>
                            wrap: true
                            width: 1.0
                        </style>
                        Their fly was, in this moment, a claustral indonesia. Mouths are hurried beams. The chastest donkey reveals itself as a rooky sturgeon to those who look. A broccoli of the reward is assumed to be a foggy lace.
                    </text>
                    <text>[bold]Counter component instance</text>
                    <form.counter initial="2" max="20"/>
                    <tower>
                        <style>
                            gap: 1
                            height: shrink
                        </style>
                        <text>[bold]Confirmation dialogue</text>
                        <button
                            on-submit="
                                confirm('DJ Crazy Times', 'If you want parties to be making?\n...have some noise!',
                                    function(result)
                                        if result then
                                            alert('Women are my favorite guy! &lt;3')
                                        else
                                            alert('The rythm is not glad.')
                                        end
                                    end
                                )
                            "
                        >
                            Alert alert
                        </button>
                    </tower>
                </tower> 
                <tower>
                    <style>
                        gap: 1
                        frame: [padded, null, null, null]
                    </style>
                    <?php if (0): ?>
                    <field>
                        <style>
                            overflow: [hide, hide]
                        </style>
                        &lt;text&gt;
                            [bold]Primary color: [/fg @main.primary]<?= $primary ?>[/]

                            GCount: [!threshold(g_count,main.success,10,main.error)]0[/]
                            [!random(0,100)]Random: %i[/]
                        &lt;/text&gt;
                    </field>
                    <?php endif; ?>
                    <field multiline="true">
                        <script>
                            initial = "initial"
                            min = "min"
                            max = "max"
                            value = "value"
                        </script>
                        <style>
                            overflow: [hide, hide]
                        </style>
                        &lt;complib namespace="form"&gt;
                            &lt;component name="counter" initial="0" min="0" max="10"&gt;
                                &lt;row eid="friend"&gt;
                                    &lt;style&gt;
                                        gap: 1
                                        height: shrink
                                    &lt;/style&gt;
                                    &lt;script&gt;
                                        value = $initial

                                        function add(num)
                                            value = math.min(math.max(value + num, $min), $max)
                                        end

                                        function init()
                                            on_change("value", function() count = count + 1 end)
                                        end
                                    &lt;/script&gt;
                                    &lt;_slot /&gt;
                                    &lt;button on-submit="add(-1)"&gt; - &lt;/button&gt;
                                    &lt;text&gt;$value&lt;/text&gt;
                                    &lt;button on-submit="add(1)"&gt; + &lt;/button&gt;
                                &lt;/row&gt;
                            &lt;/component&gt;
                        &lt;/complib&gt;

                        &lt;form.counter initial="2" max="20"/&gt;
                    </field>
                </tower>
            </row>
        </tower>
    </page>
</celx>
