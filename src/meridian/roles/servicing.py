"""The servicing role (SDK 0.35; spec/each-role-is-one-generated-class, ruling
1009): its base, `Role`, generated from the matrix and the servicing suite into
`meridian/roles/_generated/servicing.py`. A plugin holding the role writes one
class extending it -- the role's acts on `self`, its events as `on_<row>`
methods -- and registers it with `meridian.run(roles=[...])`.
"""

from ._generated.servicing import Role

__all__ = ["Role"]
