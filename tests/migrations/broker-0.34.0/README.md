# broker

A plugin written against open-meridian 0.34.0 in the shape Alpaca's took: one
connection holding `data`, `custody` and `connectivity`, the lake's handlers
and the SDK's Trader's merged into one `receive` call, a custody class making
its acts on the connection, and a page acting on it too. 0.35.0's step makes
the lake a data role class and drops the Trader's handlers; the entry point,
the custody class and the page are left by hand.
