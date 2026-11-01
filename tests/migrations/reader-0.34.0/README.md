# reader

A reporting plugin written against open-meridian 0.34.0: it hears the lake's
prices for the subjects it holds (`receive(..., subjects=held)`) and reads
closes on the connection. 0.35.0's step leaves its `receive` -- a class's
`subjects()` is the plugin's to write -- its entry point and its reads on the
connection by hand; its own tests pass unchanged.
