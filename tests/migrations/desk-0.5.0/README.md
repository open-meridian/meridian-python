# desk

A plugin written against open-meridian 0.5.0, for the migrations to rewrite
(meridian-python's tests/test_migrations.py). It declares a tag, reads a
person's access tag by tag through `Caller.access` and `TagAccess`, and tells
the unlinked refusal apart by its words: each of what 0.6.0 and 0.7.0 changed.

Two places decide something by a tag's name, which no migration can keep:
`files_statements` in `src/desk/access.py`, and the registered tags logged in
`src/desk/__main__.py`. Its tests leave both alone, so they pass once it is
migrated and those two are on the record left by hand.
