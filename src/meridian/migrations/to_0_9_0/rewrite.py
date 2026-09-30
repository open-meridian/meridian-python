"""open-meridian 0.8.0 to 0.9.0: the SDK declares contract v4, and the asset
class a plugin reports with a miss is an enum.

On 0.8.0 `report_missing_instrument(asset_class=...)` took any string and sent
it as given, so EQUITY, Equity and equities were three classes. On 0.9.0 it
takes a `meridian.AssetClass`, its name (`ASSET_CLASS_EQUITY`) or the ruled
spelling (`equity`), and raises ValueError for anything else, before sending.

A string literal naming one of the seven classes in another case, or with the
prefix in another case, becomes the ruled spelling, which keeps what it meant.
One naming no class ("etf", "stock") is left by hand: which class a vendor's
kind of instrument belongs to is a judgment, not a spelling. So is a value this
cannot read. migration.toml, beside this, records all three.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .. import Finding, Rewritten
from .._cst import dotted, imports_of, line_of, literal

#: The classes, as ruled (sdk-contract/asset-class-is-an-enum).
CLASSES = ("equity", "debt", "fund", "derivative", "crypto_asset", "event_contract", "cash")

#: The enum's prefix, which protobuf puts on each of its names.
PREFIX = "ASSET_CLASS_"

#: What 0.9.0 takes as it is: no class, the ruled spelling, the enum's names.
#: UNSPECIFIED is the enum's own "no class", which it takes in both spellings.
TAKEN = frozenset(
    {"", "unspecified", f"{PREFIX}UNSPECIFIED"}
    | set(CLASSES)
    | {PREFIX + name.upper() for name in CLASSES}
)

#: The call the field belongs to, a method of the plugin's client.
CALL = "report_missing_instrument"
FIELD = "asset_class"


def _named(text: str) -> str | None:
    """The class `text` names, in any case and with the prefix or without."""
    lowered = text.lower().removeprefix(PREFIX.lower())
    return lowered if lowered in CLASSES else None


def _the_enum(node: cst.BaseExpression) -> bool:
    """None, or one of the enum's values named: AssetClass.ASSET_CLASS_FUND."""
    name = dotted(node)
    return name is not None and (name == "None" or name.split(".")[-1].startswith(PREFIX))


def _text(node: cst.BaseExpression) -> str | None:
    """A string literal's whole text; None for anything with a value in it."""
    text = literal(node)
    return None if text is None or "\0" in text else text


def _asset_class(call: cst.Call) -> cst.Arg | None:
    if not (isinstance(call.func, cst.Attribute) and call.func.attr.value == CALL):
        return None
    return next(
        (arg for arg in call.args if arg.keyword is not None and arg.keyword.value == FIELD),
        None,
    )


def _uses_sdk(module: cst.Module) -> bool:
    imports = imports_of(module)
    return bool(imports.modules or imports.names)


def rewrite(path: str, text: str) -> Rewritten:
    if not path.endswith(".py"):
        return Rewritten(text)
    module = cst.parse_module(text)
    if not _uses_sdk(module):
        return Rewritten(text)
    spelling = _Spelling()
    rewritten = module.visit(spelling)
    return Rewritten(rewritten.code, tuple(spelling.applied))


def left(path: str, text: str) -> list[Finding]:
    if not path.endswith(".py"):
        return []
    module = cst.parse_module(text)
    if not _uses_sdk(module):
        return []
    found = _Left()
    MetadataWrapper(module).visit(found)
    return [
        Finding(rule, path, line, line_of(text, line)) for line, rule in sorted(found.places)
    ]


# ── The rewrite ──────────────────────────────────────────────────────────


def _quotes(node: cst.BaseExpression) -> tuple[str, str]:
    """The prefix and quote a literal opens with, its first part's when it is
    joined, and an f-string's without its f."""
    if isinstance(node, cst.ConcatenatedString):
        return _quotes(node.left)
    if isinstance(node, cst.FormattedString):
        return node.start.lower().replace("f", "").rstrip("\"'"), node.end
    if isinstance(node, cst.SimpleString):
        return node.prefix, node.quote
    return "", '"'


class _Spelling(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self.applied: list[str] = []

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        call = updated_node
        arg = _asset_class(call)
        if arg is None:
            return call
        text = _text(arg.value)
        if text is None or text in TAKEN:
            return call
        named = _named(text)
        if named is None:
            return call  # left by hand
        prefix, quote = _quotes(arg.value)
        value = cst.SimpleString(
            f"{prefix}{quote}{named}{quote}", lpar=arg.value.lpar, rpar=arg.value.rpar
        )
        self.applied.append("asset-class-spelling")
        args = [each.with_changes(value=value) if each is arg else each for each in call.args]
        return call.with_changes(args=args)


# ── What is left ─────────────────────────────────────────────────────────


class _Left(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.places: list[tuple[int, str]] = []

    def visit_Call(self, node: cst.Call) -> None:
        arg = _asset_class(node)
        if arg is None or _the_enum(arg.value):
            return
        line = self.get_metadata(PositionProvider, arg).start.line
        text = _text(arg.value)
        if text is None:
            self.places.append((line, "asset-class-computed"))
        elif text not in TAKEN and _named(text) is None:
            self.places.append((line, "asset-class-unknown"))
