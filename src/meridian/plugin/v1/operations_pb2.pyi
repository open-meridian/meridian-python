from meridian.v1 import sidecar_pb2 as _sidecar_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AccountKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCOUNT_KIND_UNSPECIFIED: _ClassVar[AccountKind]
    ACCOUNT_KIND_CASH: _ClassVar[AccountKind]
    ACCOUNT_KIND_MARGIN: _ClassVar[AccountKind]
    ACCOUNT_KIND_RETIREMENT: _ClassVar[AccountKind]

class SyncState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SYNC_STATE_UNSPECIFIED: _ClassVar[SyncState]
    SYNC_STATE_CURRENT: _ClassVar[SyncState]
    SYNC_STATE_STALE: _ClassVar[SyncState]
    SYNC_STATE_NEEDS_SIGN_IN: _ClassVar[SyncState]
    SYNC_STATE_DISABLED: _ClassVar[SyncState]
    SYNC_STATE_DELAYED_BY_DESIGN: _ClassVar[SyncState]
    SYNC_STATE_HOLDINGS_UNAVAILABLE: _ClassVar[SyncState]

class CollateralDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COLLATERAL_DIRECTION_UNSPECIFIED: _ClassVar[CollateralDirection]
    COLLATERAL_DIRECTION_POSTED: _ClassVar[CollateralDirection]
    COLLATERAL_DIRECTION_RECEIVED: _ClassVar[CollateralDirection]

class ProvenanceKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROVENANCE_KIND_UNSPECIFIED: _ClassVar[ProvenanceKind]
    PROVENANCE_KIND_REPORTED: _ClassVar[ProvenanceKind]
    PROVENANCE_KIND_SECOND_SOURCE: _ClassVar[ProvenanceKind]
    PROVENANCE_KIND_SUPPLIED: _ClassVar[ProvenanceKind]
    PROVENANCE_KIND_DERIVED: _ClassVar[ProvenanceKind]

class HoldingSide(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HOLDING_SIDE_UNSPECIFIED: _ClassVar[HoldingSide]
    HOLDING_SIDE_LONG: _ClassVar[HoldingSide]
    HOLDING_SIDE_SHORT: _ClassVar[HoldingSide]

class AvailableBasis(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AVAILABLE_BASIS_UNSPECIFIED: _ClassVar[AvailableBasis]
    AVAILABLE_BASIS_SETTLED: _ClassVar[AvailableBasis]
    AVAILABLE_BASIS_TRADED: _ClassVar[AvailableBasis]
    AVAILABLE_BASIS_CONTRACTUAL: _ClassVar[AvailableBasis]
    AVAILABLE_BASIS_ORDER_NETTED: _ClassVar[AvailableBasis]

class EncumbranceKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ENCUMBRANCE_KIND_UNSPECIFIED: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_PLEDGED: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_POSTED: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_ON_LOAN: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_BLOCKED: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_RESTRICTED: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_IN_TRANSIT: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_OTHER: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_PENDING: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_REHYPOTHECATED: _ClassVar[EncumbranceKind]
    ENCUMBRANCE_KIND_BORROWED: _ClassVar[EncumbranceKind]

class AssetClass(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ASSET_CLASS_UNSPECIFIED: _ClassVar[AssetClass]
    ASSET_CLASS_EQUITY: _ClassVar[AssetClass]
    ASSET_CLASS_DEBT: _ClassVar[AssetClass]
    ASSET_CLASS_FUND: _ClassVar[AssetClass]
    ASSET_CLASS_DERIVATIVE: _ClassVar[AssetClass]
    ASSET_CLASS_CRYPTO_ASSET: _ClassVar[AssetClass]
    ASSET_CLASS_EVENT_CONTRACT: _ClassVar[AssetClass]
    ASSET_CLASS_CASH: _ClassVar[AssetClass]

class InstrumentType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    INSTRUMENT_TYPE_UNSPECIFIED: _ClassVar[InstrumentType]
    INSTRUMENT_TYPE_MONEY_MARKET_FUND: _ClassVar[InstrumentType]

class MissReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MISS_REASON_UNSPECIFIED: _ClassVar[MissReason]
    MISS_REASON_NOT_FOUND: _ClassVar[MissReason]
    MISS_REASON_AMBIGUOUS: _ClassVar[MissReason]

class InstrumentLifecycleState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    INSTRUMENT_LIFECYCLE_STATE_UNSPECIFIED: _ClassVar[InstrumentLifecycleState]
    INSTRUMENT_LIFECYCLE_STATE_DEFINE: _ClassVar[InstrumentLifecycleState]
    INSTRUMENT_LIFECYCLE_STATE_ACTIVE: _ClassVar[InstrumentLifecycleState]
    INSTRUMENT_LIFECYCLE_STATE_DECOMMISSIONED: _ClassVar[InstrumentLifecycleState]

class InstrumentField(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    INSTRUMENT_FIELD_UNSPECIFIED: _ClassVar[InstrumentField]
    INSTRUMENT_FIELD_ASSET_CLASS: _ClassVar[InstrumentField]
    INSTRUMENT_FIELD_CURRENCY: _ClassVar[InstrumentField]
    INSTRUMENT_FIELD_DESCRIPTION: _ClassVar[InstrumentField]
    INSTRUMENT_FIELD_IDENTIFIER: _ClassVar[InstrumentField]
    INSTRUMENT_FIELD_INSTRUMENT_TYPE: _ClassVar[InstrumentField]
    INSTRUMENT_FIELD_MONEY_MARKET_FUND: _ClassVar[InstrumentField]

class MoneyMarketFundCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MONEY_MARKET_FUND_CATEGORY_UNSPECIFIED: _ClassVar[MoneyMarketFundCategory]
    MONEY_MARKET_FUND_CATEGORY_GOVERNMENT: _ClassVar[MoneyMarketFundCategory]
    MONEY_MARKET_FUND_CATEGORY_PRIME: _ClassVar[MoneyMarketFundCategory]
    MONEY_MARKET_FUND_CATEGORY_TAX_EXEMPT: _ClassVar[MoneyMarketFundCategory]

class MoneyMarketFundInvestors(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MONEY_MARKET_FUND_INVESTORS_UNSPECIFIED: _ClassVar[MoneyMarketFundInvestors]
    MONEY_MARKET_FUND_INVESTORS_RETAIL: _ClassVar[MoneyMarketFundInvestors]
    MONEY_MARKET_FUND_INVESTORS_INSTITUTIONAL: _ClassVar[MoneyMarketFundInvestors]

class MoneyMarketFundNav(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MONEY_MARKET_FUND_NAV_UNSPECIFIED: _ClassVar[MoneyMarketFundNav]
    MONEY_MARKET_FUND_NAV_STABLE: _ClassVar[MoneyMarketFundNav]
    MONEY_MARKET_FUND_NAV_FLOATING: _ClassVar[MoneyMarketFundNav]

class LiquidityFeeRegime(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LIQUIDITY_FEE_REGIME_UNSPECIFIED: _ClassVar[LiquidityFeeRegime]
    LIQUIDITY_FEE_REGIME_MANDATORY: _ClassVar[LiquidityFeeRegime]
    LIQUIDITY_FEE_REGIME_DISCRETIONARY: _ClassVar[LiquidityFeeRegime]
    LIQUIDITY_FEE_REGIME_NONE: _ClassVar[LiquidityFeeRegime]

class AccountState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCOUNT_STATE_UNSPECIFIED: _ClassVar[AccountState]
    ACCOUNT_STATE_OPEN: _ClassVar[AccountState]
    ACCOUNT_STATE_CLOSED: _ClassVar[AccountState]

class OpeningSourceKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OPENING_SOURCE_KIND_UNSPECIFIED: _ClassVar[OpeningSourceKind]
    OPENING_SOURCE_KIND_CUSTODIAN: _ClassVar[OpeningSourceKind]
    OPENING_SOURCE_KIND_PRIOR_SYSTEM: _ClassVar[OpeningSourceKind]

class PositionBasis(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    POSITION_BASIS_UNSPECIFIED: _ClassVar[PositionBasis]
    POSITION_BASIS_TRADE_DATE: _ClassVar[PositionBasis]
    POSITION_BASIS_SETTLE_DATE: _ClassVar[PositionBasis]

class LotSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOT_SOURCE_UNSPECIFIED: _ClassVar[LotSource]
    LOT_SOURCE_OPENING_BALANCE: _ClassVar[LotSource]
    LOT_SOURCE_ADJUSTMENT: _ClassVar[LotSource]

class FreeBasis(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FREE_BASIS_UNSPECIFIED: _ClassVar[FreeBasis]
    FREE_BASIS_SETTLED: _ClassVar[FreeBasis]
    FREE_BASIS_TRADE_DATE: _ClassVar[FreeBasis]

class BreakCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BREAK_CATEGORY_UNSPECIFIED: _ClassVar[BreakCategory]
    BREAK_CATEGORY_TRADE_DATE_QUANTITY: _ClassVar[BreakCategory]
    BREAK_CATEGORY_SETTLED_QUANTITY: _ClassVar[BreakCategory]
    BREAK_CATEGORY_COST_OR_LOTS: _ClassVar[BreakCategory]
    BREAK_CATEGORY_SETTLED_AGAINST_PENDING: _ClassVar[BreakCategory]
    BREAK_CATEGORY_BOOK_ONLY: _ClassVar[BreakCategory]
    BREAK_CATEGORY_STREET_ONLY: _ClassVar[BreakCategory]
    BREAK_CATEGORY_FIGURE: _ClassVar[BreakCategory]

class BreakState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BREAK_STATE_UNSPECIFIED: _ClassVar[BreakState]
    BREAK_STATE_OPEN: _ClassVar[BreakState]
    BREAK_STATE_RESOLVED: _ClassVar[BreakState]
    BREAK_STATE_CLOSED: _ClassVar[BreakState]

class BreakCauseCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BREAK_CAUSE_CATEGORY_UNSPECIFIED: _ClassVar[BreakCauseCategory]
    BREAK_CAUSE_CATEGORY_UNBOOKED_TRADE: _ClassVar[BreakCauseCategory]
    BREAK_CAUSE_CATEGORY_SETTLEMENT_TIMING: _ClassVar[BreakCauseCategory]
    BREAK_CAUSE_CATEGORY_COST_OR_PRICE: _ClassVar[BreakCauseCategory]
    BREAK_CAUSE_CATEGORY_CORPORATE_ACTION: _ClassVar[BreakCauseCategory]
    BREAK_CAUSE_CATEGORY_FAIL: _ClassVar[BreakCauseCategory]
    BREAK_CAUSE_CATEGORY_CUSTODIAN_ERROR: _ClassVar[BreakCauseCategory]
    BREAK_CAUSE_CATEGORY_UNKNOWN: _ClassVar[BreakCauseCategory]

class LotReliefMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOT_RELIEF_METHOD_UNSPECIFIED: _ClassVar[LotReliefMethod]
    LOT_RELIEF_METHOD_FIRST_IN_FIRST_OUT: _ClassVar[LotReliefMethod]
    LOT_RELIEF_METHOD_LAST_IN_FIRST_OUT: _ClassVar[LotReliefMethod]
    LOT_RELIEF_METHOD_HIGHEST_COST: _ClassVar[LotReliefMethod]
    LOT_RELIEF_METHOD_LOWEST_COST: _ClassVar[LotReliefMethod]
    LOT_RELIEF_METHOD_AVERAGE_COST: _ClassVar[LotReliefMethod]

class SettlementBucket(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SETTLEMENT_BUCKET_UNSPECIFIED: _ClassVar[SettlementBucket]
    SETTLEMENT_BUCKET_SETTLED: _ClassVar[SettlementBucket]
    SETTLEMENT_BUCKET_PENDING: _ClassVar[SettlementBucket]
    SETTLEMENT_BUCKET_NOT_STATED: _ClassVar[SettlementBucket]
ACCOUNT_KIND_UNSPECIFIED: AccountKind
ACCOUNT_KIND_CASH: AccountKind
ACCOUNT_KIND_MARGIN: AccountKind
ACCOUNT_KIND_RETIREMENT: AccountKind
SYNC_STATE_UNSPECIFIED: SyncState
SYNC_STATE_CURRENT: SyncState
SYNC_STATE_STALE: SyncState
SYNC_STATE_NEEDS_SIGN_IN: SyncState
SYNC_STATE_DISABLED: SyncState
SYNC_STATE_DELAYED_BY_DESIGN: SyncState
SYNC_STATE_HOLDINGS_UNAVAILABLE: SyncState
COLLATERAL_DIRECTION_UNSPECIFIED: CollateralDirection
COLLATERAL_DIRECTION_POSTED: CollateralDirection
COLLATERAL_DIRECTION_RECEIVED: CollateralDirection
PROVENANCE_KIND_UNSPECIFIED: ProvenanceKind
PROVENANCE_KIND_REPORTED: ProvenanceKind
PROVENANCE_KIND_SECOND_SOURCE: ProvenanceKind
PROVENANCE_KIND_SUPPLIED: ProvenanceKind
PROVENANCE_KIND_DERIVED: ProvenanceKind
HOLDING_SIDE_UNSPECIFIED: HoldingSide
HOLDING_SIDE_LONG: HoldingSide
HOLDING_SIDE_SHORT: HoldingSide
AVAILABLE_BASIS_UNSPECIFIED: AvailableBasis
AVAILABLE_BASIS_SETTLED: AvailableBasis
AVAILABLE_BASIS_TRADED: AvailableBasis
AVAILABLE_BASIS_CONTRACTUAL: AvailableBasis
AVAILABLE_BASIS_ORDER_NETTED: AvailableBasis
ENCUMBRANCE_KIND_UNSPECIFIED: EncumbranceKind
ENCUMBRANCE_KIND_PLEDGED: EncumbranceKind
ENCUMBRANCE_KIND_POSTED: EncumbranceKind
ENCUMBRANCE_KIND_ON_LOAN: EncumbranceKind
ENCUMBRANCE_KIND_BLOCKED: EncumbranceKind
ENCUMBRANCE_KIND_RESTRICTED: EncumbranceKind
ENCUMBRANCE_KIND_IN_TRANSIT: EncumbranceKind
ENCUMBRANCE_KIND_OTHER: EncumbranceKind
ENCUMBRANCE_KIND_PENDING: EncumbranceKind
ENCUMBRANCE_KIND_REHYPOTHECATED: EncumbranceKind
ENCUMBRANCE_KIND_BORROWED: EncumbranceKind
ASSET_CLASS_UNSPECIFIED: AssetClass
ASSET_CLASS_EQUITY: AssetClass
ASSET_CLASS_DEBT: AssetClass
ASSET_CLASS_FUND: AssetClass
ASSET_CLASS_DERIVATIVE: AssetClass
ASSET_CLASS_CRYPTO_ASSET: AssetClass
ASSET_CLASS_EVENT_CONTRACT: AssetClass
ASSET_CLASS_CASH: AssetClass
INSTRUMENT_TYPE_UNSPECIFIED: InstrumentType
INSTRUMENT_TYPE_MONEY_MARKET_FUND: InstrumentType
MISS_REASON_UNSPECIFIED: MissReason
MISS_REASON_NOT_FOUND: MissReason
MISS_REASON_AMBIGUOUS: MissReason
INSTRUMENT_LIFECYCLE_STATE_UNSPECIFIED: InstrumentLifecycleState
INSTRUMENT_LIFECYCLE_STATE_DEFINE: InstrumentLifecycleState
INSTRUMENT_LIFECYCLE_STATE_ACTIVE: InstrumentLifecycleState
INSTRUMENT_LIFECYCLE_STATE_DECOMMISSIONED: InstrumentLifecycleState
INSTRUMENT_FIELD_UNSPECIFIED: InstrumentField
INSTRUMENT_FIELD_ASSET_CLASS: InstrumentField
INSTRUMENT_FIELD_CURRENCY: InstrumentField
INSTRUMENT_FIELD_DESCRIPTION: InstrumentField
INSTRUMENT_FIELD_IDENTIFIER: InstrumentField
INSTRUMENT_FIELD_INSTRUMENT_TYPE: InstrumentField
INSTRUMENT_FIELD_MONEY_MARKET_FUND: InstrumentField
MONEY_MARKET_FUND_CATEGORY_UNSPECIFIED: MoneyMarketFundCategory
MONEY_MARKET_FUND_CATEGORY_GOVERNMENT: MoneyMarketFundCategory
MONEY_MARKET_FUND_CATEGORY_PRIME: MoneyMarketFundCategory
MONEY_MARKET_FUND_CATEGORY_TAX_EXEMPT: MoneyMarketFundCategory
MONEY_MARKET_FUND_INVESTORS_UNSPECIFIED: MoneyMarketFundInvestors
MONEY_MARKET_FUND_INVESTORS_RETAIL: MoneyMarketFundInvestors
MONEY_MARKET_FUND_INVESTORS_INSTITUTIONAL: MoneyMarketFundInvestors
MONEY_MARKET_FUND_NAV_UNSPECIFIED: MoneyMarketFundNav
MONEY_MARKET_FUND_NAV_STABLE: MoneyMarketFundNav
MONEY_MARKET_FUND_NAV_FLOATING: MoneyMarketFundNav
LIQUIDITY_FEE_REGIME_UNSPECIFIED: LiquidityFeeRegime
LIQUIDITY_FEE_REGIME_MANDATORY: LiquidityFeeRegime
LIQUIDITY_FEE_REGIME_DISCRETIONARY: LiquidityFeeRegime
LIQUIDITY_FEE_REGIME_NONE: LiquidityFeeRegime
ACCOUNT_STATE_UNSPECIFIED: AccountState
ACCOUNT_STATE_OPEN: AccountState
ACCOUNT_STATE_CLOSED: AccountState
OPENING_SOURCE_KIND_UNSPECIFIED: OpeningSourceKind
OPENING_SOURCE_KIND_CUSTODIAN: OpeningSourceKind
OPENING_SOURCE_KIND_PRIOR_SYSTEM: OpeningSourceKind
POSITION_BASIS_UNSPECIFIED: PositionBasis
POSITION_BASIS_TRADE_DATE: PositionBasis
POSITION_BASIS_SETTLE_DATE: PositionBasis
LOT_SOURCE_UNSPECIFIED: LotSource
LOT_SOURCE_OPENING_BALANCE: LotSource
LOT_SOURCE_ADJUSTMENT: LotSource
FREE_BASIS_UNSPECIFIED: FreeBasis
FREE_BASIS_SETTLED: FreeBasis
FREE_BASIS_TRADE_DATE: FreeBasis
BREAK_CATEGORY_UNSPECIFIED: BreakCategory
BREAK_CATEGORY_TRADE_DATE_QUANTITY: BreakCategory
BREAK_CATEGORY_SETTLED_QUANTITY: BreakCategory
BREAK_CATEGORY_COST_OR_LOTS: BreakCategory
BREAK_CATEGORY_SETTLED_AGAINST_PENDING: BreakCategory
BREAK_CATEGORY_BOOK_ONLY: BreakCategory
BREAK_CATEGORY_STREET_ONLY: BreakCategory
BREAK_CATEGORY_FIGURE: BreakCategory
BREAK_STATE_UNSPECIFIED: BreakState
BREAK_STATE_OPEN: BreakState
BREAK_STATE_RESOLVED: BreakState
BREAK_STATE_CLOSED: BreakState
BREAK_CAUSE_CATEGORY_UNSPECIFIED: BreakCauseCategory
BREAK_CAUSE_CATEGORY_UNBOOKED_TRADE: BreakCauseCategory
BREAK_CAUSE_CATEGORY_SETTLEMENT_TIMING: BreakCauseCategory
BREAK_CAUSE_CATEGORY_COST_OR_PRICE: BreakCauseCategory
BREAK_CAUSE_CATEGORY_CORPORATE_ACTION: BreakCauseCategory
BREAK_CAUSE_CATEGORY_FAIL: BreakCauseCategory
BREAK_CAUSE_CATEGORY_CUSTODIAN_ERROR: BreakCauseCategory
BREAK_CAUSE_CATEGORY_UNKNOWN: BreakCauseCategory
LOT_RELIEF_METHOD_UNSPECIFIED: LotReliefMethod
LOT_RELIEF_METHOD_FIRST_IN_FIRST_OUT: LotReliefMethod
LOT_RELIEF_METHOD_LAST_IN_FIRST_OUT: LotReliefMethod
LOT_RELIEF_METHOD_HIGHEST_COST: LotReliefMethod
LOT_RELIEF_METHOD_LOWEST_COST: LotReliefMethod
LOT_RELIEF_METHOD_AVERAGE_COST: LotReliefMethod
SETTLEMENT_BUCKET_UNSPECIFIED: SettlementBucket
SETTLEMENT_BUCKET_SETTLED: SettlementBucket
SETTLEMENT_BUCKET_PENDING: SettlementBucket
SETTLEMENT_BUCKET_NOT_STATED: SettlementBucket

class Published(_message.Message):
    __slots__ = ("message_id",)
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    def __init__(self, message_id: _Optional[str] = ...) -> None: ...

class ReportExternalAccountsParams(_message.Message):
    __slots__ = ("accounts",)
    ACCOUNTS_FIELD_NUMBER: _ClassVar[int]
    accounts: _containers.RepeatedCompositeFieldContainer[ExternalAccount]
    def __init__(self, accounts: _Optional[_Iterable[_Union[ExternalAccount, _Mapping]]] = ...) -> None: ...

class ReportSyncStatusParams(_message.Message):
    __slots__ = ("source", "last_synced_at_ns", "connection_healthy", "status_detail", "observed_at_ns", "external_account_id", "state", "holdings_as_of_ns", "history_as_of_ns")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CONNECTION_HEALTHY_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    HOLDINGS_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    HISTORY_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    source: str
    last_synced_at_ns: int
    connection_healthy: bool
    status_detail: str
    observed_at_ns: int
    external_account_id: str
    state: SyncState
    holdings_as_of_ns: int
    history_as_of_ns: int
    def __init__(self, source: _Optional[str] = ..., last_synced_at_ns: _Optional[int] = ..., connection_healthy: bool = ..., status_detail: _Optional[str] = ..., observed_at_ns: _Optional[int] = ..., external_account_id: _Optional[str] = ..., state: _Optional[_Union[SyncState, str]] = ..., holdings_as_of_ns: _Optional[int] = ..., history_as_of_ns: _Optional[int] = ...) -> None: ...

class RecordHoldingsStatementParams(_message.Message):
    __slots__ = ("source", "external_statement_id", "as_of_date", "read_at_ns", "expected_rows", "buying_power", "margin_requirement", "maintenance_excess", "currency_assumed", "external_account_id", "figures", "institution", "security_interest", "raw_record", "provenance", "acting_for")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    READ_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_ROWS_FIELD_NUMBER: _ClassVar[int]
    BUYING_POWER_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    MAINTENANCE_EXCESS_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_ASSUMED_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    INSTITUTION_FIELD_NUMBER: _ClassVar[int]
    SECURITY_INTEREST_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    source: str
    external_statement_id: str
    as_of_date: str
    read_at_ns: int
    expected_rows: int
    buying_power: Money
    margin_requirement: Money
    maintenance_excess: Money
    currency_assumed: bool
    external_account_id: str
    figures: _containers.RepeatedCompositeFieldContainer[StatementFigures]
    institution: str
    security_interest: bool
    raw_record: RawRecordRef
    provenance: _containers.RepeatedCompositeFieldContainer[Provenance]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, source: _Optional[str] = ..., external_statement_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., read_at_ns: _Optional[int] = ..., expected_rows: _Optional[int] = ..., buying_power: _Optional[_Union[Money, _Mapping]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., maintenance_excess: _Optional[_Union[Money, _Mapping]] = ..., currency_assumed: bool = ..., external_account_id: _Optional[str] = ..., figures: _Optional[_Iterable[_Union[StatementFigures, _Mapping]]] = ..., institution: _Optional[str] = ..., security_interest: bool = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., provenance: _Optional[_Iterable[_Union[Provenance, _Mapping]]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordHoldingsStatementResult(_message.Message):
    __slots__ = ("statement_id", "already_recorded")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ALREADY_RECORDED_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    already_recorded: bool
    def __init__(self, statement_id: _Optional[str] = ..., already_recorded: bool = ...) -> None: ...

class RecordHoldingParams(_message.Message):
    __slots__ = ("statement_id", "instrument_id", "unresolved_identifiers", "quantity", "market_value", "external_account_id", "side", "settle_date_quantity", "currency_assumed", "also_counted_in_cash", "cost_basis", "lots", "margin_requirement", "average_cost", "available_quantity", "not_available_quantity", "available_basis", "encumbrances", "raw_record", "provenance", "pending", "backfill", "acting_for")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    SETTLE_DATE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_ASSUMED_FIELD_NUMBER: _ClassVar[int]
    ALSO_COUNTED_IN_CASH_FIELD_NUMBER: _ClassVar[int]
    COST_BASIS_FIELD_NUMBER: _ClassVar[int]
    LOTS_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_COST_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    NOT_AVAILABLE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_BASIS_FIELD_NUMBER: _ClassVar[int]
    ENCUMBRANCES_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    PENDING_FIELD_NUMBER: _ClassVar[int]
    BACKFILL_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    instrument_id: str
    unresolved_identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    quantity: Decimal
    market_value: Money
    external_account_id: str
    side: HoldingSide
    settle_date_quantity: Decimal
    currency_assumed: bool
    also_counted_in_cash: bool
    cost_basis: Money
    lots: _containers.RepeatedCompositeFieldContainer[ReportedLot]
    margin_requirement: Money
    average_cost: Money
    available_quantity: Decimal
    not_available_quantity: Decimal
    available_basis: AvailableBasis
    encumbrances: _containers.RepeatedCompositeFieldContainer[ReportedEncumbrance]
    raw_record: RawRecordRef
    provenance: _containers.RepeatedCompositeFieldContainer[Provenance]
    pending: _containers.RepeatedCompositeFieldContainer[ReportedPending]
    backfill: Backfill
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, statement_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., unresolved_identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., market_value: _Optional[_Union[Money, _Mapping]] = ..., external_account_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., settle_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., currency_assumed: bool = ..., also_counted_in_cash: bool = ..., cost_basis: _Optional[_Union[Money, _Mapping]] = ..., lots: _Optional[_Iterable[_Union[ReportedLot, _Mapping]]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., average_cost: _Optional[_Union[Money, _Mapping]] = ..., available_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., not_available_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., available_basis: _Optional[_Union[AvailableBasis, str]] = ..., encumbrances: _Optional[_Iterable[_Union[ReportedEncumbrance, _Mapping]]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., provenance: _Optional[_Iterable[_Union[Provenance, _Mapping]]] = ..., pending: _Optional[_Iterable[_Union[ReportedPending, _Mapping]]] = ..., backfill: _Optional[_Union[Backfill, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordHoldingResult(_message.Message):
    __slots__ = ("holding_id", "resolved")
    HOLDING_ID_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_FIELD_NUMBER: _ClassVar[int]
    holding_id: str
    resolved: bool
    def __init__(self, holding_id: _Optional[str] = ..., resolved: bool = ...) -> None: ...

class ListCustodialPositionsParams(_message.Message):
    __slots__ = ("account_id", "include_unresolved", "page_size", "cursor", "since")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_UNRESOLVED_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    include_unresolved: bool
    page_size: int
    cursor: str
    since: Watermark
    def __init__(self, account_id: _Optional[str] = ..., include_unresolved: bool = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListCustodialPositionsResult(_message.Message):
    __slots__ = ("positions", "unresolved", "next_cursor", "as_of")
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.RepeatedCompositeFieldContainer[CustodialPosition]
    unresolved: _containers.RepeatedCompositeFieldContainer[UnresolvedHolding]
    next_cursor: str
    as_of: Watermark
    def __init__(self, positions: _Optional[_Iterable[_Union[CustodialPosition, _Mapping]]] = ..., unresolved: _Optional[_Iterable[_Union[UnresolvedHolding, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListStatementsParams(_message.Message):
    __slots__ = ("account_id", "as_of_date", "since", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    as_of_date: str
    since: Watermark
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListStatementsResult(_message.Message):
    __slots__ = ("statements", "next_cursor", "as_of")
    STATEMENTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    statements: _containers.RepeatedCompositeFieldContainer[StatementRecordedEvent]
    next_cursor: str
    as_of: Watermark
    def __init__(self, statements: _Optional[_Iterable[_Union[StatementRecordedEvent, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ResolveIdentifierParams(_message.Message):
    __slots__ = ("identifiers", "as_of_ns", "exchange_mic", "currency", "stated_asset_class", "stated_currency", "stated_description", "stated_instrument_type")
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    EXCHANGE_MIC_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    STATED_ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    STATED_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    STATED_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    STATED_INSTRUMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    as_of_ns: int
    exchange_mic: str
    currency: str
    stated_asset_class: AssetClass
    stated_currency: str
    stated_description: str
    stated_instrument_type: InstrumentType
    def __init__(self, identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., as_of_ns: _Optional[int] = ..., exchange_mic: _Optional[str] = ..., currency: _Optional[str] = ..., stated_asset_class: _Optional[_Union[AssetClass, str]] = ..., stated_currency: _Optional[str] = ..., stated_description: _Optional[str] = ..., stated_instrument_type: _Optional[_Union[InstrumentType, str]] = ...) -> None: ...

class ResolveIdentifierResult(_message.Message):
    __slots__ = ("found", "instrument_id", "miss_reason", "minted")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    MISS_REASON_FIELD_NUMBER: _ClassVar[int]
    MINTED_FIELD_NUMBER: _ClassVar[int]
    found: bool
    instrument_id: str
    miss_reason: MissReason
    minted: bool
    def __init__(self, found: bool = ..., instrument_id: _Optional[str] = ..., miss_reason: _Optional[_Union[MissReason, str]] = ..., minted: bool = ...) -> None: ...

class ReportMissingInstrumentParams(_message.Message):
    __slots__ = ("source", "asset_class", "identifiers", "as_of_ns", "reason", "observed_at_ns", "asset_class_as_reported")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ASSET_CLASS_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    source: str
    asset_class: AssetClass
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    as_of_ns: int
    reason: MissReason
    observed_at_ns: int
    asset_class_as_reported: AsReported
    def __init__(self, source: _Optional[str] = ..., asset_class: _Optional[_Union[AssetClass, str]] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., as_of_ns: _Optional[int] = ..., reason: _Optional[_Union[MissReason, str]] = ..., observed_at_ns: _Optional[int] = ..., asset_class_as_reported: _Optional[_Union[AsReported, _Mapping]] = ...) -> None: ...

class ResolveInstrumentParams(_message.Message):
    __slots__ = ("instrument_id", "as_of_ns")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    as_of_ns: int
    def __init__(self, instrument_id: _Optional[str] = ..., as_of_ns: _Optional[int] = ...) -> None: ...

class ResolveInstrumentResult(_message.Message):
    __slots__ = ("found", "instrument")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_FIELD_NUMBER: _ClassVar[int]
    found: bool
    instrument: InstrumentRecord
    def __init__(self, found: bool = ..., instrument: _Optional[_Union[InstrumentRecord, _Mapping]] = ...) -> None: ...

class LinkExternalAccountParams(_message.Message):
    __slots__ = ("external_account_id", "account_id", "new_account_name", "new_account_custodian", "new_account_type", "new_account_owner", "new_account_note", "acting_for")
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_NAME_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_CUSTODIAN_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_OWNER_FIELD_NUMBER: _ClassVar[int]
    NEW_ACCOUNT_NOTE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    external_account_id: str
    account_id: str
    new_account_name: str
    new_account_custodian: str
    new_account_type: str
    new_account_owner: str
    new_account_note: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, external_account_id: _Optional[str] = ..., account_id: _Optional[str] = ..., new_account_name: _Optional[str] = ..., new_account_custodian: _Optional[str] = ..., new_account_type: _Optional[str] = ..., new_account_owner: _Optional[str] = ..., new_account_note: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class LinkExternalAccountResult(_message.Message):
    __slots__ = ("plugin_instance_id", "external_account_id", "account_id")
    PLUGIN_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    plugin_instance_id: str
    external_account_id: str
    account_id: str
    def __init__(self, plugin_instance_id: _Optional[str] = ..., external_account_id: _Optional[str] = ..., account_id: _Optional[str] = ...) -> None: ...

class ReadAccountsForLinkingParams(_message.Message):
    __slots__ = ("acting_for",)
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReadAccountsForLinkingResult(_message.Message):
    __slots__ = ("accounts",)
    ACCOUNTS_FIELD_NUMBER: _ClassVar[int]
    accounts: _containers.RepeatedCompositeFieldContainer[AccountRecord]
    def __init__(self, accounts: _Optional[_Iterable[_Union[AccountRecord, _Mapping]]] = ...) -> None: ...

class RecordOpeningBalanceParams(_message.Message):
    __slots__ = ("account_id", "as_of_date", "sources", "positions", "reason", "replaces_entry_id", "idempotency_key", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    REPLACES_ENTRY_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    as_of_date: str
    sources: _containers.RepeatedCompositeFieldContainer[OpeningSource]
    positions: _containers.RepeatedCompositeFieldContainer[OpeningPosition]
    reason: str
    replaces_entry_id: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., sources: _Optional[_Iterable[_Union[OpeningSource, _Mapping]]] = ..., positions: _Optional[_Iterable[_Union[OpeningPosition, _Mapping]]] = ..., reason: _Optional[str] = ..., replaces_entry_id: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordOpeningBalanceResult(_message.Message):
    __slots__ = ("entry", "journal", "positions", "breaks", "figures", "attributes")
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    BREAKS_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    entry: EntryMeta
    journal: JournalRef
    positions: _containers.RepeatedCompositeFieldContainer[BookPosition]
    breaks: _containers.RepeatedCompositeFieldContainer[Break]
    figures: _containers.RepeatedCompositeFieldContainer[AccountFigures]
    attributes: AccountAttributes
    def __init__(self, entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[BookPosition, _Mapping]]] = ..., breaks: _Optional[_Iterable[_Union[Break, _Mapping]]] = ..., figures: _Optional[_Iterable[_Union[AccountFigures, _Mapping]]] = ..., attributes: _Optional[_Union[AccountAttributes, _Mapping]] = ...) -> None: ...

class RecordBreakParams(_message.Message):
    __slots__ = ("account_id", "break_id", "position", "figure", "category", "differences", "book_watermark", "street", "business_date", "candidate_causes", "idempotency_key", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BREAK_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FIGURE_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    DIFFERENCES_FIELD_NUMBER: _ClassVar[int]
    BOOK_WATERMARK_FIELD_NUMBER: _ClassVar[int]
    STREET_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    CANDIDATE_CAUSES_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    break_id: str
    position: PositionKey
    figure: FigureKey
    category: BreakCategory
    differences: _containers.RepeatedCompositeFieldContainer[BreakDifference]
    book_watermark: Watermark
    street: StreetRecordRef
    business_date: str
    candidate_causes: _containers.RepeatedCompositeFieldContainer[BreakCause]
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., break_id: _Optional[str] = ..., position: _Optional[_Union[PositionKey, _Mapping]] = ..., figure: _Optional[_Union[FigureKey, _Mapping]] = ..., category: _Optional[_Union[BreakCategory, str]] = ..., differences: _Optional[_Iterable[_Union[BreakDifference, _Mapping]]] = ..., book_watermark: _Optional[_Union[Watermark, _Mapping]] = ..., street: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., business_date: _Optional[str] = ..., candidate_causes: _Optional[_Iterable[_Union[BreakCause, _Mapping]]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordBreakResult(_message.Message):
    __slots__ = ("entry", "journal", "positions", "breaks", "figures", "attributes")
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    BREAKS_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    entry: EntryMeta
    journal: JournalRef
    positions: _containers.RepeatedCompositeFieldContainer[BookPosition]
    breaks: _containers.RepeatedCompositeFieldContainer[Break]
    figures: _containers.RepeatedCompositeFieldContainer[AccountFigures]
    attributes: AccountAttributes
    def __init__(self, entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[BookPosition, _Mapping]]] = ..., breaks: _Optional[_Iterable[_Union[Break, _Mapping]]] = ..., figures: _Optional[_Iterable[_Union[AccountFigures, _Mapping]]] = ..., attributes: _Optional[_Union[AccountAttributes, _Mapping]] = ...) -> None: ...

class RecordAccountFiguresParams(_message.Message):
    __slots__ = ("account_id", "business_date", "source", "agreements", "idempotency_key", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    AGREEMENTS_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    business_date: str
    source: StreetRecordRef
    agreements: _containers.RepeatedCompositeFieldContainer[AgreementFigures]
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., business_date: _Optional[str] = ..., source: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., agreements: _Optional[_Iterable[_Union[AgreementFigures, _Mapping]]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordAccountFiguresResult(_message.Message):
    __slots__ = ("entry", "journal", "positions", "breaks", "figures", "attributes")
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    BREAKS_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    entry: EntryMeta
    journal: JournalRef
    positions: _containers.RepeatedCompositeFieldContainer[BookPosition]
    breaks: _containers.RepeatedCompositeFieldContainer[Break]
    figures: _containers.RepeatedCompositeFieldContainer[AccountFigures]
    attributes: AccountAttributes
    def __init__(self, entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[BookPosition, _Mapping]]] = ..., breaks: _Optional[_Iterable[_Union[Break, _Mapping]]] = ..., figures: _Optional[_Iterable[_Union[AccountFigures, _Mapping]]] = ..., attributes: _Optional[_Union[AccountAttributes, _Mapping]] = ...) -> None: ...

class RecordEncumbrancesParams(_message.Message):
    __slots__ = ("account_id", "business_date", "source", "positions", "idempotency_key", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    business_date: str
    source: StreetRecordRef
    positions: _containers.RepeatedCompositeFieldContainer[PositionEncumbrances]
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., business_date: _Optional[str] = ..., source: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[PositionEncumbrances, _Mapping]]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordEncumbrancesResult(_message.Message):
    __slots__ = ("entry", "journal", "positions", "breaks", "figures", "attributes")
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    BREAKS_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    entry: EntryMeta
    journal: JournalRef
    positions: _containers.RepeatedCompositeFieldContainer[BookPosition]
    breaks: _containers.RepeatedCompositeFieldContainer[Break]
    figures: _containers.RepeatedCompositeFieldContainer[AccountFigures]
    attributes: AccountAttributes
    def __init__(self, entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[BookPosition, _Mapping]]] = ..., breaks: _Optional[_Iterable[_Union[Break, _Mapping]]] = ..., figures: _Optional[_Iterable[_Union[AccountFigures, _Mapping]]] = ..., attributes: _Optional[_Union[AccountAttributes, _Mapping]] = ...) -> None: ...

class HandleBreakParams(_message.Message):
    __slots__ = ("account_id", "break_id", "confirmed_cause", "handling", "reason", "idempotency_key", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BREAK_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIRMED_CAUSE_FIELD_NUMBER: _ClassVar[int]
    HANDLING_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    break_id: str
    confirmed_cause: BreakCause
    handling: BreakHandling
    reason: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., break_id: _Optional[str] = ..., confirmed_cause: _Optional[_Union[BreakCause, _Mapping]] = ..., handling: _Optional[_Union[BreakHandling, _Mapping]] = ..., reason: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class HandleBreakResult(_message.Message):
    __slots__ = ("entry", "journal", "positions", "breaks", "figures", "attributes")
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    BREAKS_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    entry: EntryMeta
    journal: JournalRef
    positions: _containers.RepeatedCompositeFieldContainer[BookPosition]
    breaks: _containers.RepeatedCompositeFieldContainer[Break]
    figures: _containers.RepeatedCompositeFieldContainer[AccountFigures]
    attributes: AccountAttributes
    def __init__(self, entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[BookPosition, _Mapping]]] = ..., breaks: _Optional[_Iterable[_Union[Break, _Mapping]]] = ..., figures: _Optional[_Iterable[_Union[AccountFigures, _Mapping]]] = ..., attributes: _Optional[_Union[AccountAttributes, _Mapping]] = ...) -> None: ...

class ResolveBreakParams(_message.Message):
    __slots__ = ("account_id", "break_ids", "reason", "adjustment", "reversal", "entries", "explanation", "idempotency_key", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BREAK_IDS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ADJUSTMENT_FIELD_NUMBER: _ClassVar[int]
    REVERSAL_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    break_ids: _containers.RepeatedScalarFieldContainer[str]
    reason: str
    adjustment: Adjustment
    reversal: Reversal
    entries: ResolvedByEntries
    explanation: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., break_ids: _Optional[_Iterable[str]] = ..., reason: _Optional[str] = ..., adjustment: _Optional[_Union[Adjustment, _Mapping]] = ..., reversal: _Optional[_Union[Reversal, _Mapping]] = ..., entries: _Optional[_Union[ResolvedByEntries, _Mapping]] = ..., explanation: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ResolveBreakResult(_message.Message):
    __slots__ = ("entry", "journal", "positions", "breaks", "figures", "attributes")
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    BREAKS_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    entry: EntryMeta
    journal: JournalRef
    positions: _containers.RepeatedCompositeFieldContainer[BookPosition]
    breaks: _containers.RepeatedCompositeFieldContainer[Break]
    figures: _containers.RepeatedCompositeFieldContainer[AccountFigures]
    attributes: AccountAttributes
    def __init__(self, entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[BookPosition, _Mapping]]] = ..., breaks: _Optional[_Iterable[_Union[Break, _Mapping]]] = ..., figures: _Optional[_Iterable[_Union[AccountFigures, _Mapping]]] = ..., attributes: _Optional[_Union[AccountAttributes, _Mapping]] = ...) -> None: ...

class CloseBreaksAsClearedParams(_message.Message):
    __slots__ = ("account_id", "break_ids", "cleared_at", "reason", "idempotency_key", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BREAK_IDS_FIELD_NUMBER: _ClassVar[int]
    CLEARED_AT_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    break_ids: _containers.RepeatedScalarFieldContainer[str]
    cleared_at: StreetRecordRef
    reason: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., break_ids: _Optional[_Iterable[str]] = ..., cleared_at: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., reason: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class CloseBreaksAsClearedResult(_message.Message):
    __slots__ = ("entry", "journal", "positions", "breaks", "figures", "attributes")
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    BREAKS_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    entry: EntryMeta
    journal: JournalRef
    positions: _containers.RepeatedCompositeFieldContainer[BookPosition]
    breaks: _containers.RepeatedCompositeFieldContainer[Break]
    figures: _containers.RepeatedCompositeFieldContainer[AccountFigures]
    attributes: AccountAttributes
    def __init__(self, entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., positions: _Optional[_Iterable[_Union[BookPosition, _Mapping]]] = ..., breaks: _Optional[_Iterable[_Union[Break, _Mapping]]] = ..., figures: _Optional[_Iterable[_Union[AccountFigures, _Mapping]]] = ..., attributes: _Optional[_Union[AccountAttributes, _Mapping]] = ...) -> None: ...

class ListPositionsParams(_message.Message):
    __slots__ = ("account_id", "since", "business_date", "at", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    AT_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    since: Watermark
    business_date: str
    at: Watermark
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., business_date: _Optional[str] = ..., at: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListPositionsResult(_message.Message):
    __slots__ = ("positions", "next_cursor", "as_of")
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.RepeatedCompositeFieldContainer[BookPosition]
    next_cursor: str
    as_of: Watermark
    def __init__(self, positions: _Optional[_Iterable[_Union[BookPosition, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListBreaksParams(_message.Message):
    __slots__ = ("account_id", "states", "since", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STATES_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    states: _containers.RepeatedScalarFieldContainer[BreakState]
    since: Watermark
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., states: _Optional[_Iterable[_Union[BreakState, str]]] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListBreaksResult(_message.Message):
    __slots__ = ("breaks", "next_cursor", "as_of")
    BREAKS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    breaks: _containers.RepeatedCompositeFieldContainer[Break]
    next_cursor: str
    as_of: Watermark
    def __init__(self, breaks: _Optional[_Iterable[_Union[Break, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListAccountFiguresParams(_message.Message):
    __slots__ = ("account_id", "agreement", "from_date", "to_date", "since", "at", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    AGREEMENT_FIELD_NUMBER: _ClassVar[int]
    FROM_DATE_FIELD_NUMBER: _ClassVar[int]
    TO_DATE_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    AT_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    agreement: MarginAgreementRef
    from_date: str
    to_date: str
    since: Watermark
    at: Watermark
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., agreement: _Optional[_Union[MarginAgreementRef, _Mapping]] = ..., from_date: _Optional[str] = ..., to_date: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., at: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListAccountFiguresResult(_message.Message):
    __slots__ = ("figures", "next_cursor", "as_of")
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    figures: _containers.RepeatedCompositeFieldContainer[AccountFigures]
    next_cursor: str
    as_of: Watermark
    def __init__(self, figures: _Optional[_Iterable[_Union[AccountFigures, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListAccountAttributesParams(_message.Message):
    __slots__ = ("account_id", "since", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    since: Watermark
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListAccountAttributesResult(_message.Message):
    __slots__ = ("attributes", "next_cursor", "as_of")
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.RepeatedCompositeFieldContainer[AccountAttributes]
    next_cursor: str
    as_of: Watermark
    def __init__(self, attributes: _Optional[_Iterable[_Union[AccountAttributes, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ReceiveRequest(_message.Message):
    __slots__ = ("rows",)
    ROWS_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, rows: _Optional[_Iterable[str]] = ...) -> None: ...

class Delivery(_message.Message):
    __slots__ = ("meta", "lost", "statement_recorded", "custodial_position_updated", "position_changed", "break_changed", "account_figures_recorded", "account_attribute_changed")
    META_FIELD_NUMBER: _ClassVar[int]
    LOST_FIELD_NUMBER: _ClassVar[int]
    STATEMENT_RECORDED_FIELD_NUMBER: _ClassVar[int]
    CUSTODIAL_POSITION_UPDATED_FIELD_NUMBER: _ClassVar[int]
    POSITION_CHANGED_FIELD_NUMBER: _ClassVar[int]
    BREAK_CHANGED_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_FIGURES_RECORDED_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ATTRIBUTE_CHANGED_FIELD_NUMBER: _ClassVar[int]
    meta: DeliveryMeta
    lost: Lost
    statement_recorded: StatementRecordedEvent
    custodial_position_updated: CustodialPositionUpdatedEvent
    position_changed: PositionChangedEvent
    break_changed: BreakChangedEvent
    account_figures_recorded: AccountFiguresRecordedEvent
    account_attribute_changed: AccountAttributeChangedEvent
    def __init__(self, meta: _Optional[_Union[DeliveryMeta, _Mapping]] = ..., lost: _Optional[_Union[Lost, _Mapping]] = ..., statement_recorded: _Optional[_Union[StatementRecordedEvent, _Mapping]] = ..., custodial_position_updated: _Optional[_Union[CustodialPositionUpdatedEvent, _Mapping]] = ..., position_changed: _Optional[_Union[PositionChangedEvent, _Mapping]] = ..., break_changed: _Optional[_Union[BreakChangedEvent, _Mapping]] = ..., account_figures_recorded: _Optional[_Union[AccountFiguresRecordedEvent, _Mapping]] = ..., account_attribute_changed: _Optional[_Union[AccountAttributeChangedEvent, _Mapping]] = ...) -> None: ...

class DeliveryMeta(_message.Message):
    __slots__ = ("message_id", "correlation_id", "causation_id", "published_at_ns", "row", "journal", "cause", "own")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    CAUSATION_ID_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ROW_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    OWN_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    correlation_id: str
    causation_id: str
    published_at_ns: int
    row: str
    journal: JournalRef
    cause: ChangeCause
    own: bool
    def __init__(self, message_id: _Optional[str] = ..., correlation_id: _Optional[str] = ..., causation_id: _Optional[str] = ..., published_at_ns: _Optional[int] = ..., row: _Optional[str] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ..., own: bool = ...) -> None: ...

class Lost(_message.Message):
    __slots__ = ("dropped", "rows")
    DROPPED_FIELD_NUMBER: _ClassVar[int]
    ROWS_FIELD_NUMBER: _ClassVar[int]
    dropped: int
    rows: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, dropped: _Optional[int] = ..., rows: _Optional[_Iterable[str]] = ...) -> None: ...

class ExternalAccount(_message.Message):
    __slots__ = ("external_account_id", "name", "venue_account_type", "account_kind", "account_kind_as_reported")
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_KIND_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_KIND_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    external_account_id: str
    name: str
    venue_account_type: str
    account_kind: AccountKind
    account_kind_as_reported: AsReported
    def __init__(self, external_account_id: _Optional[str] = ..., name: _Optional[str] = ..., venue_account_type: _Optional[str] = ..., account_kind: _Optional[_Union[AccountKind, str]] = ..., account_kind_as_reported: _Optional[_Union[AsReported, _Mapping]] = ...) -> None: ...

class AsReported(_message.Message):
    __slots__ = ("scheme", "code", "text")
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    scheme: str
    code: str
    text: str
    def __init__(self, scheme: _Optional[str] = ..., code: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class Money(_message.Message):
    __slots__ = ("amount", "currency_code")
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    amount: Decimal
    currency_code: str
    def __init__(self, amount: _Optional[_Union[Decimal, _Mapping]] = ..., currency_code: _Optional[str] = ...) -> None: ...

class Decimal(_message.Message):
    __slots__ = ("high", "low", "scale")
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    high: int
    low: int
    scale: int
    def __init__(self, high: _Optional[int] = ..., low: _Optional[int] = ..., scale: _Optional[int] = ...) -> None: ...

class StatementFigures(_message.Message):
    __slots__ = ("segment", "buying_power", "margin_requirement", "maintenance_excess", "initial_margin", "variation_margin", "net_liquidation", "collateral")
    SEGMENT_FIELD_NUMBER: _ClassVar[int]
    BUYING_POWER_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    MAINTENANCE_EXCESS_FIELD_NUMBER: _ClassVar[int]
    INITIAL_MARGIN_FIELD_NUMBER: _ClassVar[int]
    VARIATION_MARGIN_FIELD_NUMBER: _ClassVar[int]
    NET_LIQUIDATION_FIELD_NUMBER: _ClassVar[int]
    COLLATERAL_FIELD_NUMBER: _ClassVar[int]
    segment: str
    buying_power: Money
    margin_requirement: Money
    maintenance_excess: Money
    initial_margin: Money
    variation_margin: Money
    net_liquidation: Money
    collateral: _containers.RepeatedCompositeFieldContainer[ReportedCollateral]
    def __init__(self, segment: _Optional[str] = ..., buying_power: _Optional[_Union[Money, _Mapping]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., maintenance_excess: _Optional[_Union[Money, _Mapping]] = ..., initial_margin: _Optional[_Union[Money, _Mapping]] = ..., variation_margin: _Optional[_Union[Money, _Mapping]] = ..., net_liquidation: _Optional[_Union[Money, _Mapping]] = ..., collateral: _Optional[_Iterable[_Union[ReportedCollateral, _Mapping]]] = ...) -> None: ...

class ReportedCollateral(_message.Message):
    __slots__ = ("direction", "instrument_id", "unresolved_identifiers", "quantity", "value", "haircut", "value_after_haircut", "held_at", "reusable")
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    HAIRCUT_FIELD_NUMBER: _ClassVar[int]
    VALUE_AFTER_HAIRCUT_FIELD_NUMBER: _ClassVar[int]
    HELD_AT_FIELD_NUMBER: _ClassVar[int]
    REUSABLE_FIELD_NUMBER: _ClassVar[int]
    direction: CollateralDirection
    instrument_id: str
    unresolved_identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    quantity: Decimal
    value: Money
    haircut: Decimal
    value_after_haircut: Money
    held_at: str
    reusable: bool
    def __init__(self, direction: _Optional[_Union[CollateralDirection, str]] = ..., instrument_id: _Optional[str] = ..., unresolved_identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., value: _Optional[_Union[Money, _Mapping]] = ..., haircut: _Optional[_Union[Decimal, _Mapping]] = ..., value_after_haircut: _Optional[_Union[Money, _Mapping]] = ..., held_at: _Optional[str] = ..., reusable: bool = ...) -> None: ...

class Identifier(_message.Message):
    __slots__ = ("scheme", "value", "source")
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    scheme: str
    value: str
    source: str
    def __init__(self, scheme: _Optional[str] = ..., value: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...

class RawRecordRef(_message.Message):
    __slots__ = ("instance_id", "key")
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    key: str
    def __init__(self, instance_id: _Optional[str] = ..., key: _Optional[str] = ...) -> None: ...

class Provenance(_message.Message):
    __slots__ = ("field", "kind", "raw_record", "source", "person", "rule")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    PERSON_FIELD_NUMBER: _ClassVar[int]
    RULE_FIELD_NUMBER: _ClassVar[int]
    field: str
    kind: ProvenanceKind
    raw_record: RawRecordRef
    source: str
    person: str
    rule: str
    def __init__(self, field: _Optional[str] = ..., kind: _Optional[_Union[ProvenanceKind, str]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., source: _Optional[str] = ..., person: _Optional[str] = ..., rule: _Optional[str] = ...) -> None: ...

class ReportedLot(_message.Message):
    __slots__ = ("quantity", "cost", "acquired_date")
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    COST_FIELD_NUMBER: _ClassVar[int]
    ACQUIRED_DATE_FIELD_NUMBER: _ClassVar[int]
    quantity: Decimal
    cost: Money
    acquired_date: str
    def __init__(self, quantity: _Optional[_Union[Decimal, _Mapping]] = ..., cost: _Optional[_Union[Money, _Mapping]] = ..., acquired_date: _Optional[str] = ...) -> None: ...

class ReportedEncumbrance(_message.Message):
    __slots__ = ("kind", "quantity", "available", "source_code", "pledgee", "held_at", "segment", "detail")
    KIND_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_CODE_FIELD_NUMBER: _ClassVar[int]
    PLEDGEE_FIELD_NUMBER: _ClassVar[int]
    HELD_AT_FIELD_NUMBER: _ClassVar[int]
    SEGMENT_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    kind: EncumbranceKind
    quantity: Decimal
    available: bool
    source_code: str
    pledgee: str
    held_at: str
    segment: str
    detail: str
    def __init__(self, kind: _Optional[_Union[EncumbranceKind, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., available: bool = ..., source_code: _Optional[str] = ..., pledgee: _Optional[str] = ..., held_at: _Optional[str] = ..., segment: _Optional[str] = ..., detail: _Optional[str] = ...) -> None: ...

class ReportedPending(_message.Message):
    __slots__ = ("value_date", "quantity")
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    value_date: str
    quantity: Decimal
    def __init__(self, value_date: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ...) -> None: ...

class Backfill(_message.Message):
    __slots__ = ("contract_version", "field")
    CONTRACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    contract_version: str
    field: str
    def __init__(self, contract_version: _Optional[str] = ..., field: _Optional[str] = ...) -> None: ...

class Watermark(_message.Message):
    __slots__ = ("partitions",)
    PARTITIONS_FIELD_NUMBER: _ClassVar[int]
    partitions: _containers.RepeatedCompositeFieldContainer[PartitionSequence]
    def __init__(self, partitions: _Optional[_Iterable[_Union[PartitionSequence, _Mapping]]] = ...) -> None: ...

class PartitionSequence(_message.Message):
    __slots__ = ("partition", "sequence")
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    partition: str
    sequence: int
    def __init__(self, partition: _Optional[str] = ..., sequence: _Optional[int] = ...) -> None: ...

class CustodialPosition(_message.Message):
    __slots__ = ("account_id", "instrument_id", "quantity", "market_value", "last_statement_id", "as_of_date", "updated_at_ns", "side", "settle_date_quantity", "also_counted_in_cash", "cost_basis", "lots", "margin_requirement", "last_change", "removed", "average_cost", "available_quantity", "not_available_quantity", "available_basis", "encumbrances", "raw_record", "provenance", "pending")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    LAST_STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    SETTLE_DATE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ALSO_COUNTED_IN_CASH_FIELD_NUMBER: _ClassVar[int]
    COST_BASIS_FIELD_NUMBER: _ClassVar[int]
    LOTS_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_COST_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    NOT_AVAILABLE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_BASIS_FIELD_NUMBER: _ClassVar[int]
    ENCUMBRANCES_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    PENDING_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    instrument_id: str
    quantity: Decimal
    market_value: Money
    last_statement_id: str
    as_of_date: str
    updated_at_ns: int
    side: HoldingSide
    settle_date_quantity: Decimal
    also_counted_in_cash: bool
    cost_basis: Money
    lots: _containers.RepeatedCompositeFieldContainer[ReportedLot]
    margin_requirement: Money
    last_change: JournalRef
    removed: bool
    average_cost: Money
    available_quantity: Decimal
    not_available_quantity: Decimal
    available_basis: AvailableBasis
    encumbrances: _containers.RepeatedCompositeFieldContainer[ReportedEncumbrance]
    raw_record: RawRecordRef
    provenance: _containers.RepeatedCompositeFieldContainer[Provenance]
    pending: _containers.RepeatedCompositeFieldContainer[ReportedPending]
    def __init__(self, account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., market_value: _Optional[_Union[Money, _Mapping]] = ..., last_statement_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., updated_at_ns: _Optional[int] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., settle_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., also_counted_in_cash: bool = ..., cost_basis: _Optional[_Union[Money, _Mapping]] = ..., lots: _Optional[_Iterable[_Union[ReportedLot, _Mapping]]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., removed: bool = ..., average_cost: _Optional[_Union[Money, _Mapping]] = ..., available_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., not_available_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., available_basis: _Optional[_Union[AvailableBasis, str]] = ..., encumbrances: _Optional[_Iterable[_Union[ReportedEncumbrance, _Mapping]]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., provenance: _Optional[_Iterable[_Union[Provenance, _Mapping]]] = ..., pending: _Optional[_Iterable[_Union[ReportedPending, _Mapping]]] = ...) -> None: ...

class JournalRef(_message.Message):
    __slots__ = ("partition", "sequence", "previous_sequence")
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    partition: str
    sequence: int
    previous_sequence: int
    def __init__(self, partition: _Optional[str] = ..., sequence: _Optional[int] = ..., previous_sequence: _Optional[int] = ...) -> None: ...

class UnresolvedHolding(_message.Message):
    __slots__ = ("holding_id", "account_id", "identifiers", "quantity", "market_value", "source", "as_of_date", "escalated", "raw_record")
    HOLDING_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    ESCALATED_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    holding_id: str
    account_id: str
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    quantity: Decimal
    market_value: Money
    source: str
    as_of_date: str
    escalated: bool
    raw_record: RawRecordRef
    def __init__(self, holding_id: _Optional[str] = ..., account_id: _Optional[str] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., market_value: _Optional[_Union[Money, _Mapping]] = ..., source: _Optional[str] = ..., as_of_date: _Optional[str] = ..., escalated: bool = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ...) -> None: ...

class StatementRecordedEvent(_message.Message):
    __slots__ = ("statement_id", "source", "as_of_date", "rows_received", "rows_resolved", "rows_unresolved", "recorded_at_ns", "account_id", "figures", "currency_assumed", "journal", "cause", "external_account_id", "institution", "security_interest", "raw_record", "provenance")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    ROWS_RECEIVED_FIELD_NUMBER: _ClassVar[int]
    ROWS_RESOLVED_FIELD_NUMBER: _ClassVar[int]
    ROWS_UNRESOLVED_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_ASSUMED_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTITUTION_FIELD_NUMBER: _ClassVar[int]
    SECURITY_INTEREST_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    source: str
    as_of_date: str
    rows_received: int
    rows_resolved: int
    rows_unresolved: int
    recorded_at_ns: int
    account_id: str
    figures: _containers.RepeatedCompositeFieldContainer[StatementFigures]
    currency_assumed: bool
    journal: JournalRef
    cause: ChangeCause
    external_account_id: str
    institution: str
    security_interest: bool
    raw_record: RawRecordRef
    provenance: _containers.RepeatedCompositeFieldContainer[Provenance]
    def __init__(self, statement_id: _Optional[str] = ..., source: _Optional[str] = ..., as_of_date: _Optional[str] = ..., rows_received: _Optional[int] = ..., rows_resolved: _Optional[int] = ..., rows_unresolved: _Optional[int] = ..., recorded_at_ns: _Optional[int] = ..., account_id: _Optional[str] = ..., figures: _Optional[_Iterable[_Union[StatementFigures, _Mapping]]] = ..., currency_assumed: bool = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ..., external_account_id: _Optional[str] = ..., institution: _Optional[str] = ..., security_interest: bool = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., provenance: _Optional[_Iterable[_Union[Provenance, _Mapping]]] = ...) -> None: ...

class ChangeCause(_message.Message):
    __slots__ = ("instance_id", "acting_for_subject", "correlation_id", "causation_id", "committed_at_ns")
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_SUBJECT_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    CAUSATION_ID_FIELD_NUMBER: _ClassVar[int]
    COMMITTED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    acting_for_subject: str
    correlation_id: str
    causation_id: str
    committed_at_ns: int
    def __init__(self, instance_id: _Optional[str] = ..., acting_for_subject: _Optional[str] = ..., correlation_id: _Optional[str] = ..., causation_id: _Optional[str] = ..., committed_at_ns: _Optional[int] = ...) -> None: ...

class InstrumentRecord(_message.Message):
    __slots__ = ("instrument_id", "identifiers", "asset_class", "currency", "exchange_mic", "description", "lifecycle_state", "version", "valid_from_ns", "record_time_ns", "sources", "offers", "instrument_type", "money_market_fund")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    EXCHANGE_MIC_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LIFECYCLE_STATE_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    RECORD_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    OFFERS_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    MONEY_MARKET_FUND_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    asset_class: AssetClass
    currency: str
    exchange_mic: str
    description: str
    lifecycle_state: InstrumentLifecycleState
    version: int
    valid_from_ns: int
    record_time_ns: int
    sources: _containers.RepeatedCompositeFieldContainer[InstrumentValueSource]
    offers: _containers.RepeatedCompositeFieldContainer[OfferedValue]
    instrument_type: InstrumentType
    money_market_fund: MoneyMarketFund
    def __init__(self, instrument_id: _Optional[str] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., asset_class: _Optional[_Union[AssetClass, str]] = ..., currency: _Optional[str] = ..., exchange_mic: _Optional[str] = ..., description: _Optional[str] = ..., lifecycle_state: _Optional[_Union[InstrumentLifecycleState, str]] = ..., version: _Optional[int] = ..., valid_from_ns: _Optional[int] = ..., record_time_ns: _Optional[int] = ..., sources: _Optional[_Iterable[_Union[InstrumentValueSource, _Mapping]]] = ..., offers: _Optional[_Iterable[_Union[OfferedValue, _Mapping]]] = ..., instrument_type: _Optional[_Union[InstrumentType, str]] = ..., money_market_fund: _Optional[_Union[MoneyMarketFund, _Mapping]] = ...) -> None: ...

class InstrumentValueSource(_message.Message):
    __slots__ = ("field", "identifier", "source", "person", "instance_id", "recorded_at_ns", "note", "acting_through_delegation", "client_name")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    PERSON_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    ACTING_THROUGH_DELEGATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    field: InstrumentField
    identifier: Identifier
    source: str
    person: str
    instance_id: str
    recorded_at_ns: int
    note: str
    acting_through_delegation: str
    client_name: str
    def __init__(self, field: _Optional[_Union[InstrumentField, str]] = ..., identifier: _Optional[_Union[Identifier, _Mapping]] = ..., source: _Optional[str] = ..., person: _Optional[str] = ..., instance_id: _Optional[str] = ..., recorded_at_ns: _Optional[int] = ..., note: _Optional[str] = ..., acting_through_delegation: _Optional[str] = ..., client_name: _Optional[str] = ...) -> None: ...

class OfferedValue(_message.Message):
    __slots__ = ("value", "instance_id", "offered_at_ns")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    OFFERED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    value: InstrumentValue
    instance_id: str
    offered_at_ns: int
    def __init__(self, value: _Optional[_Union[InstrumentValue, _Mapping]] = ..., instance_id: _Optional[str] = ..., offered_at_ns: _Optional[int] = ...) -> None: ...

class InstrumentValue(_message.Message):
    __slots__ = ("asset_class", "currency", "description", "identifier", "instrument_type", "money_market_fund", "source")
    ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    MONEY_MARKET_FUND_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    asset_class: AssetClass
    currency: str
    description: str
    identifier: Identifier
    instrument_type: InstrumentType
    money_market_fund: MoneyMarketFund
    source: str
    def __init__(self, asset_class: _Optional[_Union[AssetClass, str]] = ..., currency: _Optional[str] = ..., description: _Optional[str] = ..., identifier: _Optional[_Union[Identifier, _Mapping]] = ..., instrument_type: _Optional[_Union[InstrumentType, str]] = ..., money_market_fund: _Optional[_Union[MoneyMarketFund, _Mapping]] = ..., source: _Optional[str] = ...) -> None: ...

class MoneyMarketFund(_message.Message):
    __slots__ = ("category", "investors", "nav", "liquidity_fee")
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    INVESTORS_FIELD_NUMBER: _ClassVar[int]
    NAV_FIELD_NUMBER: _ClassVar[int]
    LIQUIDITY_FEE_FIELD_NUMBER: _ClassVar[int]
    category: MoneyMarketFundCategory
    investors: MoneyMarketFundInvestors
    nav: MoneyMarketFundNav
    liquidity_fee: LiquidityFeeRegime
    def __init__(self, category: _Optional[_Union[MoneyMarketFundCategory, str]] = ..., investors: _Optional[_Union[MoneyMarketFundInvestors, str]] = ..., nav: _Optional[_Union[MoneyMarketFundNav, str]] = ..., liquidity_fee: _Optional[_Union[LiquidityFeeRegime, str]] = ...) -> None: ...

class AccountRecord(_message.Message):
    __slots__ = ("account_id", "name", "state", "created_at_ns", "custodian", "account_type", "owner", "note")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CUSTODIAN_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    name: str
    state: AccountState
    created_at_ns: int
    custodian: str
    account_type: str
    owner: str
    note: str
    def __init__(self, account_id: _Optional[str] = ..., name: _Optional[str] = ..., state: _Optional[_Union[AccountState, str]] = ..., created_at_ns: _Optional[int] = ..., custodian: _Optional[str] = ..., account_type: _Optional[str] = ..., owner: _Optional[str] = ..., note: _Optional[str] = ...) -> None: ...

class OpeningSource(_message.Message):
    __slots__ = ("kind", "name", "as_of_date", "basis", "street_records")
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    BASIS_FIELD_NUMBER: _ClassVar[int]
    STREET_RECORDS_FIELD_NUMBER: _ClassVar[int]
    kind: OpeningSourceKind
    name: str
    as_of_date: str
    basis: PositionBasis
    street_records: _containers.RepeatedCompositeFieldContainer[StreetRecordRef]
    def __init__(self, kind: _Optional[_Union[OpeningSourceKind, str]] = ..., name: _Optional[str] = ..., as_of_date: _Optional[str] = ..., basis: _Optional[_Union[PositionBasis, str]] = ..., street_records: _Optional[_Iterable[_Union[StreetRecordRef, _Mapping]]] = ...) -> None: ...

class StreetRecordRef(_message.Message):
    __slots__ = ("statement_id", "change", "as_of_date")
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    CHANGE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    statement_id: str
    change: JournalRef
    as_of_date: str
    def __init__(self, statement_id: _Optional[str] = ..., change: _Optional[_Union[JournalRef, _Mapping]] = ..., as_of_date: _Optional[str] = ...) -> None: ...

class OpeningPosition(_message.Message):
    __slots__ = ("instrument_id", "side", "trade_date_quantity", "settled_quantity", "pending", "lots")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    SETTLED_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    PENDING_FIELD_NUMBER: _ClassVar[int]
    LOTS_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: HoldingSide
    trade_date_quantity: Decimal
    settled_quantity: Decimal
    pending: _containers.RepeatedCompositeFieldContainer[PendingSettlement]
    lots: _containers.RepeatedCompositeFieldContainer[OpeningLot]
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., trade_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., settled_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., pending: _Optional[_Iterable[_Union[PendingSettlement, _Mapping]]] = ..., lots: _Optional[_Iterable[_Union[OpeningLot, _Mapping]]] = ...) -> None: ...

class PendingSettlement(_message.Message):
    __slots__ = ("value_date", "quantity", "state")
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    value_date: str
    quantity: Decimal
    state: PendingState
    def __init__(self, value_date: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., state: _Optional[_Union[PendingState, _Mapping]] = ...) -> None: ...

class PendingState(_message.Message):
    __slots__ = ("failing", "fail_reason", "expected_date")
    FAILING_FIELD_NUMBER: _ClassVar[int]
    FAIL_REASON_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_DATE_FIELD_NUMBER: _ClassVar[int]
    failing: bool
    fail_reason: str
    expected_date: str
    def __init__(self, failing: bool = ..., fail_reason: _Optional[str] = ..., expected_date: _Optional[str] = ...) -> None: ...

class OpeningLot(_message.Message):
    __slots__ = ("quantity", "terms")
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    TERMS_FIELD_NUMBER: _ClassVar[int]
    quantity: Decimal
    terms: LotTerms
    def __init__(self, quantity: _Optional[_Union[Decimal, _Mapping]] = ..., terms: _Optional[_Union[LotTerms, _Mapping]] = ...) -> None: ...

class LotTerms(_message.Message):
    __slots__ = ("unit_cost", "cost", "acquired_date", "holding_period_start", "settlement_date", "source")
    UNIT_COST_FIELD_NUMBER: _ClassVar[int]
    COST_FIELD_NUMBER: _ClassVar[int]
    ACQUIRED_DATE_FIELD_NUMBER: _ClassVar[int]
    HOLDING_PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    unit_cost: Money
    cost: Money
    acquired_date: str
    holding_period_start: str
    settlement_date: str
    source: LotSource
    def __init__(self, unit_cost: _Optional[_Union[Money, _Mapping]] = ..., cost: _Optional[_Union[Money, _Mapping]] = ..., acquired_date: _Optional[str] = ..., holding_period_start: _Optional[str] = ..., settlement_date: _Optional[str] = ..., source: _Optional[_Union[LotSource, str]] = ...) -> None: ...

class EntryMeta(_message.Message):
    __slots__ = ("entry_id", "kind", "actor", "event_time_ns", "received_at_ns", "effective_date", "control_sequence", "reference_versions", "reason", "break_ids", "idempotency_key")
    ENTRY_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    EVENT_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    CONTROL_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    REFERENCE_VERSIONS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    BREAK_IDS_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    entry_id: str
    kind: str
    actor: Actor
    event_time_ns: int
    received_at_ns: int
    effective_date: str
    control_sequence: int
    reference_versions: _containers.RepeatedCompositeFieldContainer[ReferenceVersion]
    reason: str
    break_ids: _containers.RepeatedScalarFieldContainer[str]
    idempotency_key: str
    def __init__(self, entry_id: _Optional[str] = ..., kind: _Optional[str] = ..., actor: _Optional[_Union[Actor, _Mapping]] = ..., event_time_ns: _Optional[int] = ..., received_at_ns: _Optional[int] = ..., effective_date: _Optional[str] = ..., control_sequence: _Optional[int] = ..., reference_versions: _Optional[_Iterable[_Union[ReferenceVersion, _Mapping]]] = ..., reason: _Optional[str] = ..., break_ids: _Optional[_Iterable[str]] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class Actor(_message.Message):
    __slots__ = ("person", "system")
    PERSON_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_FIELD_NUMBER: _ClassVar[int]
    person: PersonActor
    system: SystemActor
    def __init__(self, person: _Optional[_Union[PersonActor, _Mapping]] = ..., system: _Optional[_Union[SystemActor, _Mapping]] = ...) -> None: ...

class PersonActor(_message.Message):
    __slots__ = ("subject", "delegation_id", "client_name")
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    DELEGATION_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    subject: str
    delegation_id: str
    client_name: str
    def __init__(self, subject: _Optional[str] = ..., delegation_id: _Optional[str] = ..., client_name: _Optional[str] = ...) -> None: ...

class SystemActor(_message.Message):
    __slots__ = ("instance_id",)
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    def __init__(self, instance_id: _Optional[str] = ...) -> None: ...

class ReferenceVersion(_message.Message):
    __slots__ = ("instrument_id", "version")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    version: int
    def __init__(self, instrument_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class BookPosition(_message.Message):
    __slots__ = ("account_id", "instrument_id", "side", "trade_date_quantity", "settled_quantity", "not_stated_quantity", "pending", "lots", "opened_from", "effective_date", "last_change", "removed", "encumbrances", "free_quantity", "free_basis")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    SETTLED_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    NOT_STATED_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    PENDING_FIELD_NUMBER: _ClassVar[int]
    LOTS_FIELD_NUMBER: _ClassVar[int]
    OPENED_FROM_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    REMOVED_FIELD_NUMBER: _ClassVar[int]
    ENCUMBRANCES_FIELD_NUMBER: _ClassVar[int]
    FREE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    FREE_BASIS_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    instrument_id: str
    side: HoldingSide
    trade_date_quantity: Decimal
    settled_quantity: Decimal
    not_stated_quantity: Decimal
    pending: _containers.RepeatedCompositeFieldContainer[PendingSettlement]
    lots: _containers.RepeatedCompositeFieldContainer[Lot]
    opened_from: _containers.RepeatedCompositeFieldContainer[OpeningSource]
    effective_date: str
    last_change: JournalRef
    removed: bool
    encumbrances: _containers.RepeatedCompositeFieldContainer[Encumbrance]
    free_quantity: Decimal
    free_basis: FreeBasis
    def __init__(self, account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., trade_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., settled_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., not_stated_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., pending: _Optional[_Iterable[_Union[PendingSettlement, _Mapping]]] = ..., lots: _Optional[_Iterable[_Union[Lot, _Mapping]]] = ..., opened_from: _Optional[_Iterable[_Union[OpeningSource, _Mapping]]] = ..., effective_date: _Optional[str] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., removed: bool = ..., encumbrances: _Optional[_Iterable[_Union[Encumbrance, _Mapping]]] = ..., free_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., free_basis: _Optional[_Union[FreeBasis, str]] = ...) -> None: ...

class Lot(_message.Message):
    __slots__ = ("lot_id", "open_quantity", "original_quantity", "terms", "opened_by", "relieved_by", "adjusted_by")
    LOT_ID_FIELD_NUMBER: _ClassVar[int]
    OPEN_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    TERMS_FIELD_NUMBER: _ClassVar[int]
    OPENED_BY_FIELD_NUMBER: _ClassVar[int]
    RELIEVED_BY_FIELD_NUMBER: _ClassVar[int]
    ADJUSTED_BY_FIELD_NUMBER: _ClassVar[int]
    lot_id: str
    open_quantity: Decimal
    original_quantity: Decimal
    terms: LotTerms
    opened_by: JournalRef
    relieved_by: _containers.RepeatedCompositeFieldContainer[JournalRef]
    adjusted_by: _containers.RepeatedCompositeFieldContainer[JournalRef]
    def __init__(self, lot_id: _Optional[str] = ..., open_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., original_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., terms: _Optional[_Union[LotTerms, _Mapping]] = ..., opened_by: _Optional[_Union[JournalRef, _Mapping]] = ..., relieved_by: _Optional[_Iterable[_Union[JournalRef, _Mapping]]] = ..., adjusted_by: _Optional[_Iterable[_Union[JournalRef, _Mapping]]] = ...) -> None: ...

class Encumbrance(_message.Message):
    __slots__ = ("kind", "quantity", "pledgee", "held_at", "agreement", "source_code", "detail", "source", "since_date", "set_by")
    KIND_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    PLEDGEE_FIELD_NUMBER: _ClassVar[int]
    HELD_AT_FIELD_NUMBER: _ClassVar[int]
    AGREEMENT_FIELD_NUMBER: _ClassVar[int]
    SOURCE_CODE_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    SINCE_DATE_FIELD_NUMBER: _ClassVar[int]
    SET_BY_FIELD_NUMBER: _ClassVar[int]
    kind: EncumbranceKind
    quantity: Decimal
    pledgee: str
    held_at: str
    agreement: MarginAgreementRef
    source_code: str
    detail: str
    source: StreetRecordRef
    since_date: str
    set_by: JournalRef
    def __init__(self, kind: _Optional[_Union[EncumbranceKind, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., pledgee: _Optional[str] = ..., held_at: _Optional[str] = ..., agreement: _Optional[_Union[MarginAgreementRef, _Mapping]] = ..., source_code: _Optional[str] = ..., detail: _Optional[str] = ..., source: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., since_date: _Optional[str] = ..., set_by: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class MarginAgreementRef(_message.Message):
    __slots__ = ("statement_segment",)
    STATEMENT_SEGMENT_FIELD_NUMBER: _ClassVar[int]
    statement_segment: StatementSegmentRef
    def __init__(self, statement_segment: _Optional[_Union[StatementSegmentRef, _Mapping]] = ...) -> None: ...

class StatementSegmentRef(_message.Message):
    __slots__ = ("external_account_id", "segment", "counterparty")
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SEGMENT_FIELD_NUMBER: _ClassVar[int]
    COUNTERPARTY_FIELD_NUMBER: _ClassVar[int]
    external_account_id: str
    segment: str
    counterparty: str
    def __init__(self, external_account_id: _Optional[str] = ..., segment: _Optional[str] = ..., counterparty: _Optional[str] = ...) -> None: ...

class Break(_message.Message):
    __slots__ = ("break_id", "account_id", "position", "figure", "category", "differences", "book_watermark", "street", "first_seen_date", "last_seen_date", "state", "candidate_causes", "confirmed_cause", "handling", "resolution", "recorded_by", "last_change")
    BREAK_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FIGURE_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    DIFFERENCES_FIELD_NUMBER: _ClassVar[int]
    BOOK_WATERMARK_FIELD_NUMBER: _ClassVar[int]
    STREET_FIELD_NUMBER: _ClassVar[int]
    FIRST_SEEN_DATE_FIELD_NUMBER: _ClassVar[int]
    LAST_SEEN_DATE_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CANDIDATE_CAUSES_FIELD_NUMBER: _ClassVar[int]
    CONFIRMED_CAUSE_FIELD_NUMBER: _ClassVar[int]
    HANDLING_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    RECORDED_BY_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    break_id: str
    account_id: str
    position: PositionKey
    figure: FigureKey
    category: BreakCategory
    differences: _containers.RepeatedCompositeFieldContainer[BreakDifference]
    book_watermark: Watermark
    street: StreetRecordRef
    first_seen_date: str
    last_seen_date: str
    state: BreakState
    candidate_causes: _containers.RepeatedCompositeFieldContainer[BreakCause]
    confirmed_cause: BreakCause
    handling: BreakHandling
    resolution: BreakResolution
    recorded_by: Actor
    last_change: JournalRef
    def __init__(self, break_id: _Optional[str] = ..., account_id: _Optional[str] = ..., position: _Optional[_Union[PositionKey, _Mapping]] = ..., figure: _Optional[_Union[FigureKey, _Mapping]] = ..., category: _Optional[_Union[BreakCategory, str]] = ..., differences: _Optional[_Iterable[_Union[BreakDifference, _Mapping]]] = ..., book_watermark: _Optional[_Union[Watermark, _Mapping]] = ..., street: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., first_seen_date: _Optional[str] = ..., last_seen_date: _Optional[str] = ..., state: _Optional[_Union[BreakState, str]] = ..., candidate_causes: _Optional[_Iterable[_Union[BreakCause, _Mapping]]] = ..., confirmed_cause: _Optional[_Union[BreakCause, _Mapping]] = ..., handling: _Optional[_Union[BreakHandling, _Mapping]] = ..., resolution: _Optional[_Union[BreakResolution, _Mapping]] = ..., recorded_by: _Optional[_Union[Actor, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class PositionKey(_message.Message):
    __slots__ = ("instrument_id", "side")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: HoldingSide
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ...) -> None: ...

class FigureKey(_message.Message):
    __slots__ = ("agreement", "figure", "instrument_id")
    AGREEMENT_FIELD_NUMBER: _ClassVar[int]
    FIGURE_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    agreement: MarginAgreementRef
    figure: str
    instrument_id: str
    def __init__(self, agreement: _Optional[_Union[MarginAgreementRef, _Mapping]] = ..., figure: _Optional[str] = ..., instrument_id: _Optional[str] = ...) -> None: ...

class BreakDifference(_message.Message):
    __slots__ = ("field", "book", "street")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    BOOK_FIELD_NUMBER: _ClassVar[int]
    STREET_FIELD_NUMBER: _ClassVar[int]
    field: str
    book: BreakValue
    street: BreakValue
    def __init__(self, field: _Optional[str] = ..., book: _Optional[_Union[BreakValue, _Mapping]] = ..., street: _Optional[_Union[BreakValue, _Mapping]] = ...) -> None: ...

class BreakValue(_message.Message):
    __slots__ = ("quantity", "amount", "text")
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    quantity: Decimal
    amount: Money
    text: str
    def __init__(self, quantity: _Optional[_Union[Decimal, _Mapping]] = ..., amount: _Optional[_Union[Money, _Mapping]] = ..., text: _Optional[str] = ...) -> None: ...

class BreakCause(_message.Message):
    __slots__ = ("category", "street_record", "book_entry", "pending_settlement", "event_reference", "none_found", "note")
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    STREET_RECORD_FIELD_NUMBER: _ClassVar[int]
    BOOK_ENTRY_FIELD_NUMBER: _ClassVar[int]
    PENDING_SETTLEMENT_FIELD_NUMBER: _ClassVar[int]
    EVENT_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    NONE_FOUND_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    category: BreakCauseCategory
    street_record: StreetRecordRef
    book_entry: JournalRef
    pending_settlement: PendingSettlementRef
    event_reference: str
    none_found: bool
    note: str
    def __init__(self, category: _Optional[_Union[BreakCauseCategory, str]] = ..., street_record: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., book_entry: _Optional[_Union[JournalRef, _Mapping]] = ..., pending_settlement: _Optional[_Union[PendingSettlementRef, _Mapping]] = ..., event_reference: _Optional[str] = ..., none_found: bool = ..., note: _Optional[str] = ...) -> None: ...

class PendingSettlementRef(_message.Message):
    __slots__ = ("instrument_id", "side", "value_date")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: HoldingSide
    value_date: str
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., value_date: _Optional[str] = ...) -> None: ...

class BreakHandling(_message.Message):
    __slots__ = ("owner_subject", "escalation_level", "due_date")
    OWNER_SUBJECT_FIELD_NUMBER: _ClassVar[int]
    ESCALATION_LEVEL_FIELD_NUMBER: _ClassVar[int]
    DUE_DATE_FIELD_NUMBER: _ClassVar[int]
    owner_subject: str
    escalation_level: int
    due_date: str
    def __init__(self, owner_subject: _Optional[str] = ..., escalation_level: _Optional[int] = ..., due_date: _Optional[str] = ...) -> None: ...

class BreakResolution(_message.Message):
    __slots__ = ("entries", "explanation", "actor", "reason", "cleared_at")
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    CLEARED_AT_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[JournalRef]
    explanation: str
    actor: Actor
    reason: str
    cleared_at: StreetRecordRef
    def __init__(self, entries: _Optional[_Iterable[_Union[JournalRef, _Mapping]]] = ..., explanation: _Optional[str] = ..., actor: _Optional[_Union[Actor, _Mapping]] = ..., reason: _Optional[str] = ..., cleared_at: _Optional[_Union[StreetRecordRef, _Mapping]] = ...) -> None: ...

class AccountFigures(_message.Message):
    __slots__ = ("account_id", "business_date", "agreement", "figures", "position_values", "source", "last_change")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    AGREEMENT_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    POSITION_VALUES_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    business_date: str
    agreement: MarginAgreementRef
    figures: StatementFigures
    position_values: _containers.RepeatedCompositeFieldContainer[ReportedPositionValue]
    source: StreetRecordRef
    last_change: JournalRef
    def __init__(self, account_id: _Optional[str] = ..., business_date: _Optional[str] = ..., agreement: _Optional[_Union[MarginAgreementRef, _Mapping]] = ..., figures: _Optional[_Union[StatementFigures, _Mapping]] = ..., position_values: _Optional[_Iterable[_Union[ReportedPositionValue, _Mapping]]] = ..., source: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ReportedPositionValue(_message.Message):
    __slots__ = ("instrument_id", "side", "market_value", "margin_requirement")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    MARGIN_REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: HoldingSide
    market_value: Money
    margin_requirement: Money
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., market_value: _Optional[_Union[Money, _Mapping]] = ..., margin_requirement: _Optional[_Union[Money, _Mapping]] = ...) -> None: ...

class AccountAttributes(_message.Message):
    __slots__ = ("account_id", "base_currency_code", "lot_relief_default", "last_change", "opening_balance")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BASE_CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    LOT_RELIEF_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    OPENING_BALANCE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    base_currency_code: str
    lot_relief_default: LotReliefMethod
    last_change: JournalRef
    opening_balance: OpeningBalance
    def __init__(self, account_id: _Optional[str] = ..., base_currency_code: _Optional[str] = ..., lot_relief_default: _Optional[_Union[LotReliefMethod, str]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., opening_balance: _Optional[_Union[OpeningBalance, _Mapping]] = ...) -> None: ...

class OpeningBalance(_message.Message):
    __slots__ = ("entry_id", "as_of_date", "sources", "recorded_by", "journal", "reason")
    ENTRY_ID_FIELD_NUMBER: _ClassVar[int]
    AS_OF_DATE_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    RECORDED_BY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    entry_id: str
    as_of_date: str
    sources: _containers.RepeatedCompositeFieldContainer[OpeningSource]
    recorded_by: Actor
    journal: JournalRef
    reason: str
    def __init__(self, entry_id: _Optional[str] = ..., as_of_date: _Optional[str] = ..., sources: _Optional[_Iterable[_Union[OpeningSource, _Mapping]]] = ..., recorded_by: _Optional[_Union[Actor, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., reason: _Optional[str] = ...) -> None: ...

class AgreementFigures(_message.Message):
    __slots__ = ("agreement", "figures", "position_values")
    AGREEMENT_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    POSITION_VALUES_FIELD_NUMBER: _ClassVar[int]
    agreement: MarginAgreementRef
    figures: StatementFigures
    position_values: _containers.RepeatedCompositeFieldContainer[ReportedPositionValue]
    def __init__(self, agreement: _Optional[_Union[MarginAgreementRef, _Mapping]] = ..., figures: _Optional[_Union[StatementFigures, _Mapping]] = ..., position_values: _Optional[_Iterable[_Union[ReportedPositionValue, _Mapping]]] = ...) -> None: ...

class PositionEncumbrances(_message.Message):
    __slots__ = ("instrument_id", "side", "encumbrances")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    ENCUMBRANCES_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: HoldingSide
    encumbrances: _containers.RepeatedCompositeFieldContainer[Encumbrance]
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., encumbrances: _Optional[_Iterable[_Union[Encumbrance, _Mapping]]] = ...) -> None: ...

class Adjustment(_message.Message):
    __slots__ = ("effective_date", "lines", "basis_adjustments", "event_reference")
    EFFECTIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    LINES_FIELD_NUMBER: _ClassVar[int]
    BASIS_ADJUSTMENTS_FIELD_NUMBER: _ClassVar[int]
    EVENT_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    effective_date: str
    lines: _containers.RepeatedCompositeFieldContainer[MovementLine]
    basis_adjustments: _containers.RepeatedCompositeFieldContainer[BasisAdjustment]
    event_reference: str
    def __init__(self, effective_date: _Optional[str] = ..., lines: _Optional[_Iterable[_Union[MovementLine, _Mapping]]] = ..., basis_adjustments: _Optional[_Iterable[_Union[BasisAdjustment, _Mapping]]] = ..., event_reference: _Optional[str] = ...) -> None: ...

class MovementLine(_message.Message):
    __slots__ = ("instrument_id", "side", "bucket", "value_date", "quantity", "lot_id", "opens_lot", "pending_state")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    LOT_ID_FIELD_NUMBER: _ClassVar[int]
    OPENS_LOT_FIELD_NUMBER: _ClassVar[int]
    PENDING_STATE_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: HoldingSide
    bucket: SettlementBucket
    value_date: str
    quantity: Decimal
    lot_id: str
    opens_lot: LotTerms
    pending_state: PendingState
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., bucket: _Optional[_Union[SettlementBucket, str]] = ..., value_date: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., lot_id: _Optional[str] = ..., opens_lot: _Optional[_Union[LotTerms, _Mapping]] = ..., pending_state: _Optional[_Union[PendingState, _Mapping]] = ...) -> None: ...

class BasisAdjustment(_message.Message):
    __slots__ = ("lot_id", "cost_change", "stated_cost", "holding_period_start")
    LOT_ID_FIELD_NUMBER: _ClassVar[int]
    COST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    STATED_COST_FIELD_NUMBER: _ClassVar[int]
    HOLDING_PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    lot_id: str
    cost_change: Money
    stated_cost: Money
    holding_period_start: str
    def __init__(self, lot_id: _Optional[str] = ..., cost_change: _Optional[_Union[Money, _Mapping]] = ..., stated_cost: _Optional[_Union[Money, _Mapping]] = ..., holding_period_start: _Optional[str] = ...) -> None: ...

class Reversal(_message.Message):
    __slots__ = ("entry_id",)
    ENTRY_ID_FIELD_NUMBER: _ClassVar[int]
    entry_id: str
    def __init__(self, entry_id: _Optional[str] = ...) -> None: ...

class ResolvedByEntries(_message.Message):
    __slots__ = ("entry_ids",)
    ENTRY_IDS_FIELD_NUMBER: _ClassVar[int]
    entry_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, entry_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class CustodialPositionUpdatedEvent(_message.Message):
    __slots__ = ("position", "statement_id", "previous_quantity", "journal", "cause")
    POSITION_FIELD_NUMBER: _ClassVar[int]
    STATEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    position: CustodialPosition
    statement_id: str
    previous_quantity: Decimal
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, position: _Optional[_Union[CustodialPosition, _Mapping]] = ..., statement_id: _Optional[str] = ..., previous_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class PositionChangedEvent(_message.Message):
    __slots__ = ("position", "previous_trade_date_quantity", "entry", "journal", "cause")
    POSITION_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_TRADE_DATE_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    position: BookPosition
    previous_trade_date_quantity: Decimal
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, position: _Optional[_Union[BookPosition, _Mapping]] = ..., previous_trade_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class BreakChangedEvent(_message.Message):
    __slots__ = ("break_record", "entry", "journal", "cause")
    BREAK_RECORD_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    break_record: Break
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, break_record: _Optional[_Union[Break, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class AccountFiguresRecordedEvent(_message.Message):
    __slots__ = ("figures", "entry", "journal", "cause")
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    figures: AccountFigures
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, figures: _Optional[_Union[AccountFigures, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class AccountAttributeChangedEvent(_message.Message):
    __slots__ = ("attributes", "entry", "journal", "cause")
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    attributes: AccountAttributes
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, attributes: _Optional[_Union[AccountAttributes, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...
