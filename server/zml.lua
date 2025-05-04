zml.define("random", function(fmt, minval, maxval)
    return string.format(
        fmt,
        math.random(tonumber(minval), tonumber(maxval))
    )
end)

zml.define("eid", function(fmt)
    return string.format(fmt, self.eid)
end)
