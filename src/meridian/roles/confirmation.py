"""The confirmation role (SDK 0.35; spec/each-role-is-one-generated-class, ruling
1009): its base, `Role`, generated from the matrix and the confirmation suite into
`meridian/roles/_generated/confirmation.py`. A plugin holding the role writes one
class extending it -- the role's acts on `self`, its events as `on_<row>`
methods -- and registers it with `meridian.run(roles=[...])`.
"""

from ._generated.confirmation import Role

__all__ = ["Role"]
