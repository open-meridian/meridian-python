# listed

A plugin written against open-meridian 0.33.5, cut to how it imports the
SDK's topic modules -- `meridian.roles.chains`, `.packages`, `.lifecycle` and
`.debt` -- in every form a plugin does: a module imported by its dotted path
and with an alias, imported from `meridian.roles` alone and beside a role's
module, a name imported from it, a name reached through the package or
through `meridian.roles` bound by name, and a patch target's string. For the
0.33.5 to 0.34.0 migration to rewrite onto `meridian.helpers` (ruling 1001;
meridian-python's tests/test_migrations.py).
