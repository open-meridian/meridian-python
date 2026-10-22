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
    PROVENANCE_KIND_COMPUTED: _ClassVar[ProvenanceKind]

class DateRuleKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATE_RULE_KIND_UNSPECIFIED: _ClassVar[DateRuleKind]
    DATE_RULE_KIND_SETTLEMENT: _ClassVar[DateRuleKind]
    DATE_RULE_KIND_SPOT: _ClassVar[DateRuleKind]

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

class ActivityKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACTIVITY_KIND_UNSPECIFIED: _ClassVar[ActivityKind]
    ACTIVITY_KIND_PURCHASE: _ClassVar[ActivityKind]
    ACTIVITY_KIND_SALE: _ClassVar[ActivityKind]
    ACTIVITY_KIND_REINVESTMENT: _ClassVar[ActivityKind]
    ACTIVITY_KIND_DIVIDEND: _ClassVar[ActivityKind]
    ACTIVITY_KIND_INTEREST: _ClassVar[ActivityKind]
    ACTIVITY_KIND_FEE: _ClassVar[ActivityKind]
    ACTIVITY_KIND_TAX: _ClassVar[ActivityKind]
    ACTIVITY_KIND_SPLIT: _ClassVar[ActivityKind]
    ACTIVITY_KIND_CORPORATE_ACTION: _ClassVar[ActivityKind]
    ACTIVITY_KIND_TRANSFER_IN: _ClassVar[ActivityKind]
    ACTIVITY_KIND_TRANSFER_OUT: _ClassVar[ActivityKind]
    ACTIVITY_KIND_CONTRIBUTION: _ClassVar[ActivityKind]
    ACTIVITY_KIND_WITHDRAWAL: _ClassVar[ActivityKind]
    ACTIVITY_KIND_JOURNAL: _ClassVar[ActivityKind]

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
    ASSET_CLASS_REFERENTIAL: _ClassVar[AssetClass]

class InstrumentType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    INSTRUMENT_TYPE_UNSPECIFIED: _ClassVar[InstrumentType]
    INSTRUMENT_TYPE_MONEY_MARKET_FUND: _ClassVar[InstrumentType]
    INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT: _ClassVar[InstrumentType]
    INSTRUMENT_TYPE_INTEREST_RATE: _ClassVar[InstrumentType]
    INSTRUMENT_TYPE_RATE_CURVE: _ClassVar[InstrumentType]
    INSTRUMENT_TYPE_INDEX: _ClassVar[InstrumentType]

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
    INSTRUMENT_FIELD_BINARY_EVENT_CONTRACT: _ClassVar[InstrumentField]

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
    LOT_SOURCE_EXECUTION: _ClassVar[LotSource]

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
    BREAK_CATEGORY_UNRECOGNIZED_SECURITY: _ClassVar[BreakCategory]

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
    BREAK_CAUSE_CATEGORY_INCOME_REINVESTED: _ClassVar[BreakCauseCategory]
    BREAK_CAUSE_CATEGORY_VALUE_DATE_NOT_BUSINESS_DAY: _ClassVar[BreakCauseCategory]

class DateCheckReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATE_CHECK_REASON_UNSPECIFIED: _ClassVar[DateCheckReason]
    DATE_CHECK_REASON_WEEKEND: _ClassVar[DateCheckReason]
    DATE_CHECK_REASON_HOLIDAY: _ClassVar[DateCheckReason]
    DATE_CHECK_REASON_OUTSIDE_COVERAGE: _ClassVar[DateCheckReason]

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

class Side(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SIDE_UNSPECIFIED: _ClassVar[Side]
    SIDE_BUY: _ClassVar[Side]
    SIDE_SELL: _ClassVar[Side]
    SIDE_SELL_SHORT: _ClassVar[Side]
    SIDE_SELL_SHORT_EXEMPT: _ClassVar[Side]

class OrderType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ORDER_TYPE_UNSPECIFIED: _ClassVar[OrderType]
    ORDER_TYPE_MARKET: _ClassVar[OrderType]
    ORDER_TYPE_LIMIT: _ClassVar[OrderType]
    ORDER_TYPE_STOP: _ClassVar[OrderType]
    ORDER_TYPE_STOP_LIMIT: _ClassVar[OrderType]
    ORDER_TYPE_REQUEST_FOR_QUOTE: _ClassVar[OrderType]

class TimeInForce(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TIME_IN_FORCE_UNSPECIFIED: _ClassVar[TimeInForce]
    TIME_IN_FORCE_DAY: _ClassVar[TimeInForce]
    TIME_IN_FORCE_GOOD_TILL_CANCELLED: _ClassVar[TimeInForce]
    TIME_IN_FORCE_GOOD_TILL_DATE: _ClassVar[TimeInForce]
    TIME_IN_FORCE_GOOD_TILL_TIME: _ClassVar[TimeInForce]
    TIME_IN_FORCE_IMMEDIATE_OR_CANCEL: _ClassVar[TimeInForce]
    TIME_IN_FORCE_FILL_OR_KILL: _ClassVar[TimeInForce]
    TIME_IN_FORCE_AT_THE_OPEN: _ClassVar[TimeInForce]
    TIME_IN_FORCE_AT_THE_CLOSE: _ClassVar[TimeInForce]

class Capacity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CAPACITY_UNSPECIFIED: _ClassVar[Capacity]
    CAPACITY_AGENCY: _ClassVar[Capacity]
    CAPACITY_PRINCIPAL: _ClassVar[Capacity]
    CAPACITY_RISKLESS_PRINCIPAL: _ClassVar[Capacity]
    CAPACITY_MIXED: _ClassVar[Capacity]

class OrderDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ORDER_DIRECTION_UNSPECIFIED: _ClassVar[OrderDirection]
    ORDER_DIRECTION_RECEIVED: _ClassVar[OrderDirection]

class PartyRole(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PARTY_ROLE_UNSPECIFIED: _ClassVar[PartyRole]
    PARTY_ROLE_CLIENT: _ClassVar[PartyRole]
    PARTY_ROLE_COUNTERPARTY: _ClassVar[PartyRole]

class TimePrecision(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TIME_PRECISION_UNSPECIFIED: _ClassVar[TimePrecision]
    TIME_PRECISION_SECOND: _ClassVar[TimePrecision]
    TIME_PRECISION_MILLISECOND: _ClassVar[TimePrecision]
    TIME_PRECISION_MICROSECOND: _ClassVar[TimePrecision]
    TIME_PRECISION_NANOSECOND: _ClassVar[TimePrecision]

class ReceiptQuoteSourceKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RECEIPT_QUOTE_SOURCE_KIND_UNSPECIFIED: _ClassVar[ReceiptQuoteSourceKind]
    RECEIPT_QUOTE_SOURCE_KIND_CONSOLIDATED: _ClassVar[ReceiptQuoteSourceKind]
    RECEIPT_QUOTE_SOURCE_KIND_VENUE: _ClassVar[ReceiptQuoteSourceKind]

class OrderLinkKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ORDER_LINK_KIND_UNSPECIFIED: _ClassVar[OrderLinkKind]
    ORDER_LINK_KIND_SPLIT: _ClassVar[OrderLinkKind]
    ORDER_LINK_KIND_NET: _ClassVar[OrderLinkKind]

class ExecutionInstruction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXECUTION_INSTRUCTION_UNSPECIFIED: _ClassVar[ExecutionInstruction]
    EXECUTION_INSTRUCTION_NOT_HELD: _ClassVar[ExecutionInstruction]
    EXECUTION_INSTRUCTION_DO_NOT_REDUCE: _ClassVar[ExecutionInstruction]
    EXECUTION_INSTRUCTION_DO_NOT_INCREASE: _ClassVar[ExecutionInstruction]
    EXECUTION_INSTRUCTION_REDUCE_ONLY: _ClassVar[ExecutionInstruction]
    EXECUTION_INSTRUCTION_SELF_MATCH_PREVENTION: _ClassVar[ExecutionInstruction]

class OrderOrigin(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ORDER_ORIGIN_UNSPECIFIED: _ClassVar[OrderOrigin]
    ORDER_ORIGIN_TELEPHONED: _ClassVar[OrderOrigin]
    ORDER_ORIGIN_ACCEPTED_EXECUTION: _ClassVar[OrderOrigin]

class OrderState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ORDER_STATE_UNSPECIFIED: _ClassVar[OrderState]
    ORDER_STATE_PROPOSED: _ClassVar[OrderState]
    ORDER_STATE_REFUSED: _ClassVar[OrderState]
    ORDER_STATE_RELEASED: _ClassVar[OrderState]
    ORDER_STATE_WORKING: _ClassVar[OrderState]
    ORDER_STATE_FILLED: _ClassVar[OrderState]
    ORDER_STATE_CANCELLED: _ClassVar[OrderState]
    ORDER_STATE_EXPIRED: _ClassVar[OrderState]

class OrderCondition(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ORDER_CONDITION_UNSPECIFIED: _ClassVar[OrderCondition]
    ORDER_CONDITION_CHANGE_REQUESTED: _ClassVar[OrderCondition]
    ORDER_CONDITION_APPROVAL_REQUIRED: _ClassVar[OrderCondition]
    ORDER_CONDITION_AWAITING_CHECK: _ClassVar[OrderCondition]
    ORDER_CONDITION_CLAIMED: _ClassVar[OrderCondition]
    ORDER_CONDITION_HELD: _ClassVar[OrderCondition]
    ORDER_CONDITION_PAUSED: _ClassVar[OrderCondition]
    ORDER_CONDITION_OUTCOME_UNKNOWN: _ClassVar[OrderCondition]
    ORDER_CONDITION_DOES_NOT_TIE_OUT: _ClassVar[OrderCondition]
    ORDER_CONDITION_LATE_FACT: _ClassVar[OrderCondition]

class TieOutReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TIE_OUT_REASON_UNSPECIFIED: _ClassVar[TieOutReason]
    TIE_OUT_REASON_OVERFILL: _ClassVar[TieOutReason]
    TIE_OUT_REASON_RESTATEMENT: _ClassVar[TieOutReason]

class HoldCause(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HOLD_CAUSE_UNSPECIFIED: _ClassVar[HoldCause]
    HOLD_CAUSE_REFERENCE_PRICE_STALE: _ClassVar[HoldCause]

class CheckVerdict(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CHECK_VERDICT_UNSPECIFIED: _ClassVar[CheckVerdict]
    CHECK_VERDICT_PASS: _ClassVar[CheckVerdict]
    CHECK_VERDICT_WARN: _ClassVar[CheckVerdict]
    CHECK_VERDICT_BLOCK: _ClassVar[CheckVerdict]
    CHECK_VERDICT_REFUSE: _ClassVar[CheckVerdict]

class OrderChangeKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ORDER_CHANGE_KIND_UNSPECIFIED: _ClassVar[OrderChangeKind]
    ORDER_CHANGE_KIND_CANCEL: _ClassVar[OrderChangeKind]
    ORDER_CHANGE_KIND_AMEND: _ClassVar[OrderChangeKind]
    ORDER_CHANGE_KIND_RECALL: _ClassVar[OrderChangeKind]
    ORDER_CHANGE_KIND_WITHDRAW: _ClassVar[OrderChangeKind]
    ORDER_CHANGE_KIND_QUANTITY: _ClassVar[OrderChangeKind]

class PlacementChangeKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLACEMENT_CHANGE_KIND_UNSPECIFIED: _ClassVar[PlacementChangeKind]
    PLACEMENT_CHANGE_KIND_CANCEL: _ClassVar[PlacementChangeKind]
    PLACEMENT_CHANGE_KIND_REPLACE: _ClassVar[PlacementChangeKind]

class ChangeRequestOutcome(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CHANGE_REQUEST_OUTCOME_UNSPECIFIED: _ClassVar[ChangeRequestOutcome]
    CHANGE_REQUEST_OUTCOME_PENDING: _ClassVar[ChangeRequestOutcome]
    CHANGE_REQUEST_OUTCOME_APPLIED: _ClassVar[ChangeRequestOutcome]
    CHANGE_REQUEST_OUTCOME_REJECTED: _ClassVar[ChangeRequestOutcome]

class StrategyKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STRATEGY_KIND_UNSPECIFIED: _ClassVar[StrategyKind]
    STRATEGY_KIND_VWAP: _ClassVar[StrategyKind]
    STRATEGY_KIND_TWAP: _ClassVar[StrategyKind]
    STRATEGY_KIND_POV: _ClassVar[StrategyKind]
    STRATEGY_KIND_IS: _ClassVar[StrategyKind]

class Urgency(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    URGENCY_UNSPECIFIED: _ClassVar[Urgency]
    URGENCY_LOW: _ClassVar[Urgency]
    URGENCY_MEDIUM: _ClassVar[Urgency]
    URGENCY_HIGH: _ClassVar[Urgency]

class RouteType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ROUTE_TYPE_UNSPECIFIED: _ClassVar[RouteType]
    ROUTE_TYPE_DIRECTED: _ClassVar[RouteType]
    ROUTE_TYPE_NOT_DIRECTED: _ClassVar[RouteType]

class PlacementState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLACEMENT_STATE_UNSPECIFIED: _ClassVar[PlacementState]
    PLACEMENT_STATE_QUEUED: _ClassVar[PlacementState]
    PLACEMENT_STATE_SENT: _ClassVar[PlacementState]
    PLACEMENT_STATE_WORKING: _ClassVar[PlacementState]
    PLACEMENT_STATE_DONE_FOR_DAY: _ClassVar[PlacementState]
    PLACEMENT_STATE_FILLED: _ClassVar[PlacementState]
    PLACEMENT_STATE_CANCELLED: _ClassVar[PlacementState]
    PLACEMENT_STATE_EXPIRED: _ClassVar[PlacementState]
    PLACEMENT_STATE_REJECTED: _ClassVar[PlacementState]

class PlacementCondition(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLACEMENT_CONDITION_UNSPECIFIED: _ClassVar[PlacementCondition]
    PLACEMENT_CONDITION_CHANGE_REQUESTED: _ClassVar[PlacementCondition]
    PLACEMENT_CONDITION_OUTCOME_UNKNOWN: _ClassVar[PlacementCondition]
    PLACEMENT_CONDITION_SUSPENDED: _ClassVar[PlacementCondition]
    PLACEMENT_CONDITION_AWAITING_TRIGGER: _ClassVar[PlacementCondition]
    PLACEMENT_CONDITION_SENT_ON_STALE_REFERENCE: _ClassVar[PlacementCondition]

class UnknownReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN_REASON_UNSPECIFIED: _ClassVar[UnknownReason]
    UNKNOWN_REASON_CONNECTION_LOST: _ClassVar[UnknownReason]
    UNKNOWN_REASON_REQUEST_UNANSWERED: _ClassVar[UnknownReason]
    UNKNOWN_REASON_VENUE_STATUS_NOT_MAPPED: _ClassVar[UnknownReason]

class RejectionReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REJECTION_REASON_UNSPECIFIED: _ClassVar[RejectionReason]
    REJECTION_REASON_UNSUPPORTED: _ClassVar[RejectionReason]
    REJECTION_REASON_VENUE_REJECTED: _ClassVar[RejectionReason]
    REJECTION_REASON_HELD_BY_PRE_TRADE_CHECK: _ClassVar[RejectionReason]

class PlacementType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLACEMENT_TYPE_UNSPECIFIED: _ClassVar[PlacementType]
    PLACEMENT_TYPE_DMA: _ClassVar[PlacementType]
    PLACEMENT_TYPE_ALGO: _ClassVar[PlacementType]
    PLACEMENT_TYPE_CARE: _ClassVar[PlacementType]
    PLACEMENT_TYPE_RFQ: _ClassVar[PlacementType]
    PLACEMENT_TYPE_MANUAL: _ClassVar[PlacementType]

class PlacementQuoteOutcome(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLACEMENT_QUOTE_OUTCOME_UNSPECIFIED: _ClassVar[PlacementQuoteOutcome]
    PLACEMENT_QUOTE_OUTCOME_OPEN: _ClassVar[PlacementQuoteOutcome]
    PLACEMENT_QUOTE_OUTCOME_PICKED: _ClassVar[PlacementQuoteOutcome]
    PLACEMENT_QUOTE_OUTCOME_ACCEPTED: _ClassVar[PlacementQuoteOutcome]
    PLACEMENT_QUOTE_OUTCOME_EXPIRED: _ClassVar[PlacementQuoteOutcome]
    PLACEMENT_QUOTE_OUTCOME_WITHDRAWN: _ClassVar[PlacementQuoteOutcome]
    PLACEMENT_QUOTE_OUTCOME_NOT_PICKED: _ClassVar[PlacementQuoteOutcome]

class ExecutionKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXECUTION_KIND_UNSPECIFIED: _ClassVar[ExecutionKind]
    EXECUTION_KIND_VENUE_REPORTED: _ClassVar[ExecutionKind]
    EXECUTION_KIND_MANUAL: _ClassVar[ExecutionKind]
    EXECUTION_KIND_FROM_INVENTORY: _ClassVar[ExecutionKind]
    EXECUTION_KIND_DONE_AWAY: _ClassVar[ExecutionKind]
    EXECUTION_KIND_FROM_CHILD_ORDERS: _ClassVar[ExecutionKind]
    EXECUTION_KIND_INTERNAL_CROSS: _ClassVar[ExecutionKind]
    EXECUTION_KIND_INFERRED: _ClassVar[ExecutionKind]

class ExecutionSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXECUTION_SOURCE_UNSPECIFIED: _ClassVar[ExecutionSource]
    EXECUTION_SOURCE_PRIMARY: _ClassVar[ExecutionSource]
    EXECUTION_SOURCE_DROP_COPY: _ClassVar[ExecutionSource]

class FinalityLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FINALITY_LEVEL_UNSPECIFIED: _ClassVar[FinalityLevel]
    FINALITY_LEVEL_AWAITING_ACCEPTANCE: _ClassVar[FinalityLevel]
    FINALITY_LEVEL_MATCHED: _ClassVar[FinalityLevel]
    FINALITY_LEVEL_INCLUDED: _ClassVar[FinalityLevel]
    FINALITY_LEVEL_FINAL: _ClassVar[FinalityLevel]
    FINALITY_LEVEL_FAILED: _ClassVar[FinalityLevel]

class FeeKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FEE_KIND_UNSPECIFIED: _ClassVar[FeeKind]
    FEE_KIND_EXCHANGE: _ClassVar[FeeKind]
    FEE_KIND_CANCEL: _ClassVar[FeeKind]
    FEE_KIND_NETWORK: _ClassVar[FeeKind]
    FEE_KIND_FINANCING: _ClassVar[FeeKind]
    FEE_KIND_COMMISSION: _ClassVar[FeeKind]

class LiquidityIndicator(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LIQUIDITY_INDICATOR_UNSPECIFIED: _ClassVar[LiquidityIndicator]
    LIQUIDITY_INDICATOR_MAKER: _ClassVar[LiquidityIndicator]
    LIQUIDITY_INDICATOR_TAKER: _ClassVar[LiquidityIndicator]

class ExecutionState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXECUTION_STATE_UNSPECIFIED: _ClassVar[ExecutionState]
    EXECUTION_STATE_UNMATCHED: _ClassVar[ExecutionState]
    EXECUTION_STATE_MATCHED: _ClassVar[ExecutionState]
    EXECUTION_STATE_DONT_KNOW: _ClassVar[ExecutionState]

class DkReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DK_REASON_UNSPECIFIED: _ClassVar[DkReason]
    DK_REASON_UNKNOWN_INSTRUMENT: _ClassVar[DkReason]
    DK_REASON_WRONG_SIDE: _ClassVar[DkReason]
    DK_REASON_QUANTITY_EXCEEDS_ORDER: _ClassVar[DkReason]
    DK_REASON_NO_MATCHING_ORDER: _ClassVar[DkReason]
    DK_REASON_PRICE_EXCEEDS_LIMIT: _ClassVar[DkReason]
    DK_REASON_CALCULATION_DIFFERENCE: _ClassVar[DkReason]
    DK_REASON_OTHER: _ClassVar[DkReason]

class GiveUpAnswer(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GIVE_UP_ANSWER_UNSPECIFIED: _ClassVar[GiveUpAnswer]
    GIVE_UP_ANSWER_ACCEPTED: _ClassVar[GiveUpAnswer]
    GIVE_UP_ANSWER_REJECTED: _ClassVar[GiveUpAnswer]

class CrossRateSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CROSS_RATE_SOURCE_UNSPECIFIED: _ClassVar[CrossRateSource]
    CROSS_RATE_SOURCE_NET_STREET_RATE: _ClassVar[CrossRateSource]
    CROSS_RATE_SOURCE_MID_AT_NETTING: _ClassVar[CrossRateSource]

class ApprovalDecision(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    APPROVAL_DECISION_UNSPECIFIED: _ClassVar[ApprovalDecision]
    APPROVAL_DECISION_REQUIRE: _ClassVar[ApprovalDecision]
    APPROVAL_DECISION_APPROVE: _ClassVar[ApprovalDecision]
    APPROVAL_DECISION_OVERRIDE: _ClassVar[ApprovalDecision]
    APPROVAL_DECISION_REJECT: _ClassVar[ApprovalDecision]

class PlacementEvent(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PLACEMENT_EVENT_UNSPECIFIED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_SENT: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_ACKNOWLEDGED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_REPLACED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_DONE_FOR_DAY: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_RESTATED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_SUSPENDED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_TRIGGERED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_CANCELLED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_EXPIRED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_REJECTED: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_OUTCOME_UNKNOWN: _ClassVar[PlacementEvent]
    PLACEMENT_EVENT_OUTCOME_RESOLVED: _ClassVar[PlacementEvent]

class RestatementReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESTATEMENT_REASON_UNSPECIFIED: _ClassVar[RestatementReason]
    RESTATEMENT_REASON_CORPORATE_ACTION: _ClassVar[RestatementReason]
    RESTATEMENT_REASON_RENEWAL: _ClassVar[RestatementReason]
    RESTATEMENT_REASON_REPRICING: _ClassVar[RestatementReason]
    RESTATEMENT_REASON_PARTIAL_DECLINE: _ClassVar[RestatementReason]
    RESTATEMENT_REASON_CANCEL_ON_HALT: _ClassVar[RestatementReason]
    RESTATEMENT_REASON_CANCEL_ON_SYSTEM_FAILURE: _ClassVar[RestatementReason]
    RESTATEMENT_REASON_VENUE_OPTION: _ClassVar[RestatementReason]
    RESTATEMENT_REASON_OTHER: _ClassVar[RestatementReason]

class UnplacedReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNPLACED_REASON_UNSPECIFIED: _ClassVar[UnplacedReason]
    UNPLACED_REASON_UNKNOWN_PLACEMENT: _ClassVar[UnplacedReason]
    UNPLACED_REASON_UNMAPPED_VENUE_ACCOUNT: _ClassVar[UnplacedReason]
    UNPLACED_REASON_NOTHING_PENDING: _ClassVar[UnplacedReason]
    UNPLACED_REASON_UNKNOWN_EXECUTION: _ClassVar[UnplacedReason]

class TradingInstructionValue(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRADING_INSTRUCTION_VALUE_UNSPECIFIED: _ClassVar[TradingInstructionValue]
    TRADING_INSTRUCTION_VALUE_ACTIVE: _ClassVar[TradingInstructionValue]
    TRADING_INSTRUCTION_VALUE_PAUSE: _ClassVar[TradingInstructionValue]
    TRADING_INSTRUCTION_VALUE_STOP: _ClassVar[TradingInstructionValue]

class SetterLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SETTER_LEVEL_UNSPECIFIED: _ClassVar[SetterLevel]
    SETTER_LEVEL_DEPLOYMENT_ADMIN: _ClassVar[SetterLevel]
    SETTER_LEVEL_PLUGIN_ADMIN: _ClassVar[SetterLevel]

class LocateUseKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOCATE_USE_KIND_UNSPECIFIED: _ClassVar[LocateUseKind]
    LOCATE_USE_KIND_RESERVE: _ClassVar[LocateUseKind]
    LOCATE_USE_KIND_GIVE_BACK: _ClassVar[LocateUseKind]
    LOCATE_USE_KIND_CONSUME: _ClassVar[LocateUseKind]

class StrategyParameterType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STRATEGY_PARAMETER_TYPE_UNSPECIFIED: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_INT: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_FLOAT: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_QTY: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_PRICE: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_PRICE_OFFSET: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_AMOUNT: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_PERCENTAGE: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_BOOLEAN: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_CHAR: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_STRING: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_UTC_TIMESTAMP: _ClassVar[StrategyParameterType]
    STRATEGY_PARAMETER_TYPE_LOCAL_MARKET_DATE: _ClassVar[StrategyParameterType]

class BorrowStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BORROW_STATUS_UNSPECIFIED: _ClassVar[BorrowStatus]
    BORROW_STATUS_EASY_TO_BORROW: _ClassVar[BorrowStatus]
    BORROW_STATUS_HARD_TO_BORROW: _ClassVar[BorrowStatus]

class ExecutionAcknowledgement(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXECUTION_ACKNOWLEDGEMENT_UNSPECIFIED: _ClassVar[ExecutionAcknowledgement]
    EXECUTION_ACKNOWLEDGEMENT_NONE: _ClassVar[ExecutionAcknowledgement]
    EXECUTION_ACKNOWLEDGEMENT_BN: _ClassVar[ExecutionAcknowledgement]
    EXECUTION_ACKNOWLEDGEMENT_DONT_KNOW_TRADE: _ClassVar[ExecutionAcknowledgement]

class ErrorCause(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_CAUSE_UNSPECIFIED: _ClassVar[ErrorCause]
    ERROR_CAUSE_OVERFILL: _ClassVar[ErrorCause]
    ERROR_CAUSE_CLIENT_RENEGED: _ClassVar[ErrorCause]
    ERROR_CAUSE_WRONG_ACCEPT: _ClassVar[ErrorCause]
    ERROR_CAUSE_BOOKING_ERROR: _ClassVar[ErrorCause]
    ERROR_CAUSE_OTHER: _ClassVar[ErrorCause]

class BookingState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BOOKING_STATE_UNSPECIFIED: _ClassVar[BookingState]
    BOOKING_STATE_BOOKED: _ClassVar[BookingState]
    BOOKING_STATE_HELD: _ClassVar[BookingState]
    BOOKING_STATE_HANDED_OFF: _ClassVar[BookingState]
    BOOKING_STATE_CLOSED: _ClassVar[BookingState]
    BOOKING_STATE_CANCELLED: _ClassVar[BookingState]

class BookingCorrectionKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BOOKING_CORRECTION_KIND_UNSPECIFIED: _ClassVar[BookingCorrectionKind]
    BOOKING_CORRECTION_KIND_CANCEL: _ClassVar[BookingCorrectionKind]
    BOOKING_CORRECTION_KIND_REPLACE: _ClassVar[BookingCorrectionKind]

class AlertKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ALERT_KIND_UNSPECIFIED: _ClassVar[AlertKind]
    ALERT_KIND_ERROR_ACCOUNT_BOOKING: _ClassVar[AlertKind]
    ALERT_KIND_BOOKING_HELD: _ClassVar[AlertKind]
    ALERT_KIND_COMPLIANCE: _ClassVar[AlertKind]

class AlertState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ALERT_STATE_UNSPECIFIED: _ClassVar[AlertState]
    ALERT_STATE_RAISED: _ClassVar[AlertState]
    ALERT_STATE_ACKNOWLEDGED: _ClassVar[AlertState]
    ALERT_STATE_CLEARED: _ClassVar[AlertState]

class VenueKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VENUE_KIND_UNSPECIFIED: _ClassVar[VenueKind]
    VENUE_KIND_EXCHANGE: _ClassVar[VenueKind]
    VENUE_KIND_ALTERNATIVE_TRADING_SYSTEM: _ClassVar[VenueKind]
    VENUE_KIND_CRYPTO_EXCHANGE: _ClassVar[VenueKind]
    VENUE_KIND_DEALER_NETWORK: _ClassVar[VenueKind]
    VENUE_KIND_REPORTING_FACILITY: _ClassVar[VenueKind]

class CalendarDayKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CALENDAR_DAY_KIND_UNSPECIFIED: _ClassVar[CalendarDayKind]
    CALENDAR_DAY_KIND_CLOSED: _ClassVar[CalendarDayKind]
    CALENDAR_DAY_KIND_OPEN: _ClassVar[CalendarDayKind]

class Weekday(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    WEEKDAY_UNSPECIFIED: _ClassVar[Weekday]
    WEEKDAY_MONDAY: _ClassVar[Weekday]
    WEEKDAY_TUESDAY: _ClassVar[Weekday]
    WEEKDAY_WEDNESDAY: _ClassVar[Weekday]
    WEEKDAY_THURSDAY: _ClassVar[Weekday]
    WEEKDAY_FRIDAY: _ClassVar[Weekday]
    WEEKDAY_SATURDAY: _ClassVar[Weekday]
    WEEKDAY_SUNDAY: _ClassVar[Weekday]

class TenorUnit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TENOR_UNIT_UNSPECIFIED: _ClassVar[TenorUnit]
    TENOR_UNIT_DAY: _ClassVar[TenorUnit]
    TENOR_UNIT_WEEK: _ClassVar[TenorUnit]
    TENOR_UNIT_MONTH: _ClassVar[TenorUnit]
    TENOR_UNIT_YEAR: _ClassVar[TenorUnit]
    TENOR_UNIT_OVERNIGHT: _ClassVar[TenorUnit]
    TENOR_UNIT_TOM_NEXT: _ClassVar[TenorUnit]
    TENOR_UNIT_SPOT_NEXT: _ClassVar[TenorUnit]

class BusinessDayConvention(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BUSINESS_DAY_CONVENTION_UNSPECIFIED: _ClassVar[BusinessDayConvention]
    BUSINESS_DAY_CONVENTION_FOLLOWING: _ClassVar[BusinessDayConvention]
    BUSINESS_DAY_CONVENTION_MODIFIED_FOLLOWING: _ClassVar[BusinessDayConvention]
    BUSINESS_DAY_CONVENTION_PRECEDING: _ClassVar[BusinessDayConvention]
    BUSINESS_DAY_CONVENTION_NONE: _ClassVar[BusinessDayConvention]

class DateOutcome(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATE_OUTCOME_UNSPECIFIED: _ClassVar[DateOutcome]
    DATE_OUTCOME_COMPUTED: _ClassVar[DateOutcome]
    DATE_OUTCOME_CALENDAR_NOT_HELD: _ClassVar[DateOutcome]
    DATE_OUTCOME_OUTSIDE_COVERAGE: _ClassVar[DateOutcome]
    DATE_OUTCOME_RULE_NOT_HELD: _ClassVar[DateOutcome]

class ReplacementCause(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REPLACEMENT_CAUSE_UNSPECIFIED: _ClassVar[ReplacementCause]
    REPLACEMENT_CAUSE_MERGED: _ClassVar[ReplacementCause]
    REPLACEMENT_CAUSE_RESOLVED: _ClassVar[ReplacementCause]
    REPLACEMENT_CAUSE_PLATFORM_MERGED: _ClassVar[ReplacementCause]

class SourceTimeKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SOURCE_TIME_KIND_UNSPECIFIED: _ClassVar[SourceTimeKind]
    SOURCE_TIME_KIND_EVENT: _ClassVar[SourceTimeKind]
    SOURCE_TIME_KIND_CONSOLIDATED: _ClassVar[SourceTimeKind]
    SOURCE_TIME_KIND_REPORTED: _ClassVar[SourceTimeKind]
    SOURCE_TIME_KIND_VENDOR_RECEIVED: _ClassVar[SourceTimeKind]
    SOURCE_TIME_KIND_PUBLISHED: _ClassVar[SourceTimeKind]

class PriceKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PRICE_KIND_UNSPECIFIED: _ClassVar[PriceKind]
    PRICE_KIND_CLOSE: _ClassVar[PriceKind]
    PRICE_KIND_LAST: _ClassVar[PriceKind]
    PRICE_KIND_NAV: _ClassVar[PriceKind]
    PRICE_KIND_SETTLEMENT: _ClassVar[PriceKind]
    PRICE_KIND_BID: _ClassVar[PriceKind]
    PRICE_KIND_ASK: _ClassVar[PriceKind]
    PRICE_KIND_MID: _ClassVar[PriceKind]

class PriceBasis(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PRICE_BASIS_UNSPECIFIED: _ClassVar[PriceBasis]
    PRICE_BASIS_PER_UNIT: _ClassVar[PriceBasis]

class Eligible(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ELIGIBLE_UNSPECIFIED: _ClassVar[Eligible]
    ELIGIBLE_ELIGIBLE: _ClassVar[Eligible]
    ELIGIBLE_NOT_ELIGIBLE: _ClassVar[Eligible]

class TradeCharacteristic(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRADE_CHARACTERISTIC_UNSPECIFIED: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_OPENING_AUCTION: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_CLOSING_AUCTION: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_OTHER_AUCTION: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_ODD_LOT: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_EXTENDED_HOURS: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_OUT_OF_SEQUENCE: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_LATE_REPORT: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_AVERAGE_PRICE: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_NON_REGULAR_SETTLEMENT: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_INTERMARKET_SWEEP: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_DERIVATIVELY_PRICED: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_PRIOR_REFERENCE_PRICE: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_CONTINGENT: _ClassVar[TradeCharacteristic]
    TRADE_CHARACTERISTIC_CROSS: _ClassVar[TradeCharacteristic]

class Aggressor(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AGGRESSOR_UNSPECIFIED: _ClassVar[Aggressor]
    AGGRESSOR_BUY: _ClassVar[Aggressor]
    AGGRESSOR_SELL: _ClassVar[Aggressor]

class QuoteCharacteristic(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    QUOTE_CHARACTERISTIC_UNSPECIFIED: _ClassVar[QuoteCharacteristic]
    QUOTE_CHARACTERISTIC_INDICATIVE: _ClassVar[QuoteCharacteristic]
    QUOTE_CHARACTERISTIC_HALTED: _ClassVar[QuoteCharacteristic]

class OutcomeDetermination(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OUTCOME_DETERMINATION_UNSPECIFIED: _ClassVar[OutcomeDetermination]
    OUTCOME_DETERMINATION_PAYS: _ClassVar[OutcomeDetermination]
    OUTCOME_DETERMINATION_PAYS_NOTHING: _ClassVar[OutcomeDetermination]
    OUTCOME_DETERMINATION_PAYS_PART: _ClassVar[OutcomeDetermination]

class OutcomeStage(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OUTCOME_STAGE_UNSPECIFIED: _ClassVar[OutcomeStage]
    OUTCOME_STAGE_PROPOSED: _ClassVar[OutcomeStage]
    OUTCOME_STAGE_DETERMINED: _ClassVar[OutcomeStage]
    OUTCOME_STAGE_DISPUTED: _ClassVar[OutcomeStage]
    OUTCOME_STAGE_FINAL: _ClassVar[OutcomeStage]

class UnansweredReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNANSWERED_REASON_UNSPECIFIED: _ClassVar[UnansweredReason]
    UNANSWERED_REASON_NOT_ENTITLED: _ClassVar[UnansweredReason]
    UNANSWERED_REASON_NOT_COVERED: _ClassVar[UnansweredReason]
    UNANSWERED_REASON_ASKED_SOURCE: _ClassVar[UnansweredReason]
    UNANSWERED_REASON_SOURCE_SILENT: _ClassVar[UnansweredReason]
    UNANSWERED_REASON_UNRESOLVED: _ClassVar[UnansweredReason]
    UNANSWERED_REASON_BEYOND_HISTORY: _ClassVar[UnansweredReason]
    UNANSWERED_REASON_NOT_KEPT: _ClassVar[UnansweredReason]

class ObservationMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OBSERVATION_MODE_UNSPECIFIED: _ClassVar[ObservationMode]
    OBSERVATION_MODE_PULL: _ClassVar[ObservationMode]
    OBSERVATION_MODE_PUSH: _ClassVar[ObservationMode]
    OBSERVATION_MODE_STREAM: _ClassVar[ObservationMode]

class AccessBasis(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACCESS_BASIS_UNSPECIFIED: _ClassVar[AccessBasis]
    ACCESS_BASIS_LICENSED: _ClassVar[AccessBasis]
    ACCESS_BASIS_OPEN: _ClassVar[AccessBasis]
    ACCESS_BASIS_PUBLIC_DOMAIN: _ClassVar[AccessBasis]

class Timeliness(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TIMELINESS_UNSPECIFIED: _ClassVar[Timeliness]
    TIMELINESS_REAL_TIME: _ClassVar[Timeliness]
    TIMELINESS_DELAYED: _ClassVar[Timeliness]
    TIMELINESS_END_OF_DAY: _ClassVar[Timeliness]
    TIMELINESS_HISTORICAL: _ClassVar[Timeliness]

class LicenceMeter(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LICENCE_METER_UNSPECIFIED: _ClassVar[LicenceMeter]
    LICENCE_METER_DISPLAY: _ClassVar[LicenceMeter]
    LICENCE_METER_NON_DISPLAY: _ClassVar[LicenceMeter]
    LICENCE_METER_ENTERPRISE: _ClassVar[LicenceMeter]

class DisplayUnit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DISPLAY_UNIT_UNSPECIFIED: _ClassVar[DisplayUnit]
    DISPLAY_UNIT_PERSON: _ClassVar[DisplayUnit]
    DISPLAY_UNIT_DEVICE: _ClassVar[DisplayUnit]

class CountBasis(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COUNT_BASIS_UNSPECIFIED: _ClassVar[CountBasis]
    COUNT_BASIS_SERVED: _ClassVar[CountBasis]
    COUNT_BASIS_ENTITLED: _ClassVar[CountBasis]

class ProfessionalDefinition(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROFESSIONAL_DEFINITION_UNSPECIFIED: _ClassVar[ProfessionalDefinition]
    PROFESSIONAL_DEFINITION_STANDARD: _ClassVar[ProfessionalDefinition]
    PROFESSIONAL_DEFINITION_VENDOR: _ClassVar[ProfessionalDefinition]

class NonDisplayCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NON_DISPLAY_CATEGORY_UNSPECIFIED: _ClassVar[NonDisplayCategory]
    NON_DISPLAY_CATEGORY_TRADING_PLATFORM: _ClassVar[NonDisplayCategory]
    NON_DISPLAY_CATEGORY_AUTOMATED_TRADING: _ClassVar[NonDisplayCategory]
    NON_DISPLAY_CATEGORY_INTERNAL: _ClassVar[NonDisplayCategory]
    NON_DISPLAY_CATEGORY_FOR_CLIENTS: _ClassVar[NonDisplayCategory]

class NonDisplayCount(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NON_DISPLAY_COUNT_UNSPECIFIED: _ClassVar[NonDisplayCount]
    NON_DISPLAY_COUNT_PER_PLUGIN: _ClassVar[NonDisplayCount]
    NON_DISPLAY_COUNT_PER_CATEGORY: _ClassVar[NonDisplayCount]

class EnterpriseReplaces(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ENTERPRISE_REPLACES_UNSPECIFIED: _ClassVar[EnterpriseReplaces]
    ENTERPRISE_REPLACES_DISPLAY_PROFESSIONAL: _ClassVar[EnterpriseReplaces]
    ENTERPRISE_REPLACES_DISPLAY_NON_PROFESSIONAL: _ClassVar[EnterpriseReplaces]
    ENTERPRISE_REPLACES_NON_DISPLAY: _ClassVar[EnterpriseReplaces]

class EnterpriseForm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ENTERPRISE_FORM_UNSPECIFIED: _ClassVar[EnterpriseForm]
    ENTERPRISE_FORM_FLAT: _ClassVar[EnterpriseForm]
    ENTERPRISE_FORM_CAP: _ClassVar[EnterpriseForm]

class EnterpriseScope(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ENTERPRISE_SCOPE_UNSPECIFIED: _ClassVar[EnterpriseScope]
    ENTERPRISE_SCOPE_DEPLOYMENT: _ClassVar[EnterpriseScope]

class DerivedUse(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DERIVED_USE_UNSPECIFIED: _ClassVar[DerivedUse]
    DERIVED_USE_NOT_RESTRICTED: _ClassVar[DerivedUse]
    DERIVED_USE_INTERNAL_ONLY: _ClassVar[DerivedUse]
    DERIVED_USE_REDISTRIBUTION_NEEDS_LICENCE: _ClassVar[DerivedUse]

class Redistribution(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REDISTRIBUTION_UNSPECIFIED: _ClassVar[Redistribution]
    REDISTRIBUTION_NOT_ALLOWED: _ClassVar[Redistribution]
    REDISTRIBUTION_LICENCE_REQUIRED: _ClassVar[Redistribution]
    REDISTRIBUTION_ALLOWED_WITH_ATTRIBUTION: _ClassVar[Redistribution]

class OutsideComputation(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OUTSIDE_COMPUTATION_UNSPECIFIED: _ClassVar[OutsideComputation]
    OUTSIDE_COMPUTATION_ALLOWED: _ClassVar[OutsideComputation]
    OUTSIDE_COMPUTATION_PER_REQUEST_NO_RETENTION: _ClassVar[OutsideComputation]
    OUTSIDE_COMPUTATION_NOT_ALLOWED: _ClassVar[OutsideComputation]

class ProhibitedUse(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROHIBITED_USE_UNSPECIFIED: _ClassVar[ProhibitedUse]
    PROHIBITED_USE_MODEL_TRAINING: _ClassVar[ProhibitedUse]
    PROHIBITED_USE_REPLICATE_SERVICE: _ClassVar[ProhibitedUse]
    PROHIBITED_USE_INDEX_CREATION: _ClassVar[ProhibitedUse]

class CopyrightClass(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COPYRIGHT_CLASS_UNSPECIFIED: _ClassVar[CopyrightClass]
    COPYRIGHT_CLASS_PUBLIC_DOMAIN: _ClassVar[CopyrightClass]
    COPYRIGHT_CLASS_COPYRIGHT_CITATION_REQUIRED: _ClassVar[CopyrightClass]
    COPYRIGHT_CLASS_COPYRIGHT_PREAPPROVAL_REQUIRED: _ClassVar[CopyrightClass]

class ReportCadence(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REPORT_CADENCE_UNSPECIFIED: _ClassVar[ReportCadence]
    REPORT_CADENCE_NONE: _ClassVar[ReportCadence]
    REPORT_CADENCE_MONTHLY: _ClassVar[ReportCadence]
    REPORT_CADENCE_ANNUAL_DECLARATION: _ClassVar[ReportCadence]
    REPORT_CADENCE_ON_CHANGE: _ClassVar[ReportCadence]

class ScenarioKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SCENARIO_KIND_UNSPECIFIED: _ClassVar[ScenarioKind]
    SCENARIO_KIND_BASE: _ClassVar[ScenarioKind]
    SCENARIO_KIND_WHAT_IF: _ClassVar[ScenarioKind]
    SCENARIO_KIND_HISTORICAL_DAY: _ClassVar[ScenarioKind]
    SCENARIO_KIND_OUTCOME: _ClassVar[ScenarioKind]
    SCENARIO_KIND_NONE_OF_THE_NAMED: _ClassVar[ScenarioKind]

class ComputedAs(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMPUTED_AS_UNSPECIFIED: _ClassVar[ComputedAs]
    COMPUTED_AS_EXACT: _ClassVar[ComputedAs]
    COMPUTED_AS_MODEL: _ClassVar[ComputedAs]

class NotEvaluatedReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOT_EVALUATED_REASON_UNSPECIFIED: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_PRICE_MISSING: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_PRICE_STALE: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_CONVERSION_MISSING: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_NOT_ENTITLED: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_LOCAL_RECORD: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_IMPLEMENTATION_UNAVAILABLE: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_SCHEME_NOT_HELD: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_GROUP_NOT_EXHAUSTIVE: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_HISTORY_INSUFFICIENT: _ClassVar[NotEvaluatedReason]
    NOT_EVALUATED_REASON_COST_MISSING: _ClassVar[NotEvaluatedReason]

class ConversionDerivation(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CONVERSION_DERIVATION_UNSPECIFIED: _ClassVar[ConversionDerivation]
    CONVERSION_DERIVATION_DIRECT: _ClassVar[ConversionDerivation]
    CONVERSION_DERIVATION_INVERTED: _ClassVar[ConversionDerivation]
    CONVERSION_DERIVATION_CROSSED: _ClassVar[ConversionDerivation]

class EventGroupFlag(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EVENT_GROUP_FLAG_UNSPECIFIED: _ClassVar[EventGroupFlag]
    EVENT_GROUP_FLAG_TRUE: _ClassVar[EventGroupFlag]
    EVENT_GROUP_FLAG_FALSE: _ClassVar[EventGroupFlag]
    EVENT_GROUP_FLAG_NOT_STATED: _ClassVar[EventGroupFlag]

class RateKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RATE_KIND_UNSPECIFIED: _ClassVar[RateKind]
    RATE_KIND_FIXING: _ClassVar[RateKind]
    RATE_KIND_AVERAGE: _ClassVar[RateKind]
    RATE_KIND_INDEX_LEVEL: _ClassVar[RateKind]
    RATE_KIND_PAR_YIELD: _ClassVar[RateKind]
    RATE_KIND_ZERO: _ClassVar[RateKind]
    RATE_KIND_DISCOUNT: _ClassVar[RateKind]
    RATE_KIND_COUPON_EQUIVALENT: _ClassVar[RateKind]

class ValueUnit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VALUE_UNIT_UNSPECIFIED: _ClassVar[ValueUnit]
    VALUE_UNIT_PERCENT: _ClassVar[ValueUnit]
    VALUE_UNIT_BASIS_POINTS: _ClassVar[ValueUnit]
    VALUE_UNIT_SHARES: _ClassVar[ValueUnit]
    VALUE_UNIT_CONTRACTS: _ClassVar[ValueUnit]
    VALUE_UNIT_PRINCIPAL: _ClassVar[ValueUnit]
    VALUE_UNIT_RATIO: _ClassVar[ValueUnit]
    VALUE_UNIT_COUNT: _ClassVar[ValueUnit]
    VALUE_UNIT_DAYS: _ClassVar[ValueUnit]
    VALUE_UNIT_INDEX: _ClassVar[ValueUnit]
    VALUE_UNIT_UCUM: _ClassVar[ValueUnit]

class DayCount(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DAY_COUNT_UNSPECIFIED: _ClassVar[DayCount]
    DAY_COUNT_ACT_360: _ClassVar[DayCount]
    DAY_COUNT_ACT_365_FIXED: _ClassVar[DayCount]
    DAY_COUNT_ACT_ACT: _ClassVar[DayCount]
    DAY_COUNT_THIRTY_360: _ClassVar[DayCount]
    DAY_COUNT_BUS_252: _ClassVar[DayCount]

class Compounding(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMPOUNDING_UNSPECIFIED: _ClassVar[Compounding]
    COMPOUNDING_SIMPLE: _ClassVar[Compounding]
    COMPOUNDING_COMPOUNDED: _ClassVar[Compounding]
    COMPOUNDING_CONTINUOUS: _ClassVar[Compounding]
    COMPOUNDING_DISCOUNT: _ClassVar[Compounding]

class AgeHop(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AGE_HOP_UNSPECIFIED: _ClassVar[AgeHop]
    AGE_HOP_EDGE: _ClassVar[AgeHop]
    AGE_HOP_SIDECAR: _ClassVar[AgeHop]
    AGE_HOP_LAKE: _ClassVar[AgeHop]
    AGE_HOP_BUS: _ClassVar[AgeHop]
    AGE_HOP_ANALYTICS: _ClassVar[AgeHop]
    AGE_HOP_EMS_CHECK: _ClassVar[AgeHop]
    AGE_HOP_PAGE: _ClassVar[AgeHop]

class LatencyMetric(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LATENCY_METRIC_UNSPECIFIED: _ClassVar[LatencyMetric]
    LATENCY_METRIC_RTT: _ClassVar[LatencyMetric]
    LATENCY_METRIC_ORDER_ACK: _ClassVar[LatencyMetric]
    LATENCY_METRIC_FILL_DELAY: _ClassVar[LatencyMetric]
    LATENCY_METRIC_AGE: _ClassVar[LatencyMetric]

class TcaBenchmark(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TCA_BENCHMARK_UNSPECIFIED: _ClassVar[TcaBenchmark]
    TCA_BENCHMARK_DECISION: _ClassVar[TcaBenchmark]
    TCA_BENCHMARK_ARRIVAL: _ClassVar[TcaBenchmark]
    TCA_BENCHMARK_PLACEMENT_ARRIVAL: _ClassVar[TcaBenchmark]
    TCA_BENCHMARK_MID_AT_FILL: _ClassVar[TcaBenchmark]
    TCA_BENCHMARK_INTERVAL_VWAP: _ClassVar[TcaBenchmark]
    TCA_BENCHMARK_FIX: _ClassVar[TcaBenchmark]

class TcaUnanswered(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TCA_UNANSWERED_UNSPECIFIED: _ClassVar[TcaUnanswered]
    TCA_UNANSWERED_NO_QUOTE: _ClassVar[TcaUnanswered]
    TCA_UNANSWERED_NOT_MEASURED: _ClassVar[TcaUnanswered]
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
PROVENANCE_KIND_COMPUTED: ProvenanceKind
DATE_RULE_KIND_UNSPECIFIED: DateRuleKind
DATE_RULE_KIND_SETTLEMENT: DateRuleKind
DATE_RULE_KIND_SPOT: DateRuleKind
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
ACTIVITY_KIND_UNSPECIFIED: ActivityKind
ACTIVITY_KIND_PURCHASE: ActivityKind
ACTIVITY_KIND_SALE: ActivityKind
ACTIVITY_KIND_REINVESTMENT: ActivityKind
ACTIVITY_KIND_DIVIDEND: ActivityKind
ACTIVITY_KIND_INTEREST: ActivityKind
ACTIVITY_KIND_FEE: ActivityKind
ACTIVITY_KIND_TAX: ActivityKind
ACTIVITY_KIND_SPLIT: ActivityKind
ACTIVITY_KIND_CORPORATE_ACTION: ActivityKind
ACTIVITY_KIND_TRANSFER_IN: ActivityKind
ACTIVITY_KIND_TRANSFER_OUT: ActivityKind
ACTIVITY_KIND_CONTRIBUTION: ActivityKind
ACTIVITY_KIND_WITHDRAWAL: ActivityKind
ACTIVITY_KIND_JOURNAL: ActivityKind
ASSET_CLASS_UNSPECIFIED: AssetClass
ASSET_CLASS_EQUITY: AssetClass
ASSET_CLASS_DEBT: AssetClass
ASSET_CLASS_FUND: AssetClass
ASSET_CLASS_DERIVATIVE: AssetClass
ASSET_CLASS_CRYPTO_ASSET: AssetClass
ASSET_CLASS_EVENT_CONTRACT: AssetClass
ASSET_CLASS_CASH: AssetClass
ASSET_CLASS_REFERENTIAL: AssetClass
INSTRUMENT_TYPE_UNSPECIFIED: InstrumentType
INSTRUMENT_TYPE_MONEY_MARKET_FUND: InstrumentType
INSTRUMENT_TYPE_BINARY_EVENT_CONTRACT: InstrumentType
INSTRUMENT_TYPE_INTEREST_RATE: InstrumentType
INSTRUMENT_TYPE_RATE_CURVE: InstrumentType
INSTRUMENT_TYPE_INDEX: InstrumentType
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
INSTRUMENT_FIELD_BINARY_EVENT_CONTRACT: InstrumentField
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
LOT_SOURCE_EXECUTION: LotSource
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
BREAK_CATEGORY_UNRECOGNIZED_SECURITY: BreakCategory
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
BREAK_CAUSE_CATEGORY_INCOME_REINVESTED: BreakCauseCategory
BREAK_CAUSE_CATEGORY_VALUE_DATE_NOT_BUSINESS_DAY: BreakCauseCategory
DATE_CHECK_REASON_UNSPECIFIED: DateCheckReason
DATE_CHECK_REASON_WEEKEND: DateCheckReason
DATE_CHECK_REASON_HOLIDAY: DateCheckReason
DATE_CHECK_REASON_OUTSIDE_COVERAGE: DateCheckReason
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
SIDE_UNSPECIFIED: Side
SIDE_BUY: Side
SIDE_SELL: Side
SIDE_SELL_SHORT: Side
SIDE_SELL_SHORT_EXEMPT: Side
ORDER_TYPE_UNSPECIFIED: OrderType
ORDER_TYPE_MARKET: OrderType
ORDER_TYPE_LIMIT: OrderType
ORDER_TYPE_STOP: OrderType
ORDER_TYPE_STOP_LIMIT: OrderType
ORDER_TYPE_REQUEST_FOR_QUOTE: OrderType
TIME_IN_FORCE_UNSPECIFIED: TimeInForce
TIME_IN_FORCE_DAY: TimeInForce
TIME_IN_FORCE_GOOD_TILL_CANCELLED: TimeInForce
TIME_IN_FORCE_GOOD_TILL_DATE: TimeInForce
TIME_IN_FORCE_GOOD_TILL_TIME: TimeInForce
TIME_IN_FORCE_IMMEDIATE_OR_CANCEL: TimeInForce
TIME_IN_FORCE_FILL_OR_KILL: TimeInForce
TIME_IN_FORCE_AT_THE_OPEN: TimeInForce
TIME_IN_FORCE_AT_THE_CLOSE: TimeInForce
CAPACITY_UNSPECIFIED: Capacity
CAPACITY_AGENCY: Capacity
CAPACITY_PRINCIPAL: Capacity
CAPACITY_RISKLESS_PRINCIPAL: Capacity
CAPACITY_MIXED: Capacity
ORDER_DIRECTION_UNSPECIFIED: OrderDirection
ORDER_DIRECTION_RECEIVED: OrderDirection
PARTY_ROLE_UNSPECIFIED: PartyRole
PARTY_ROLE_CLIENT: PartyRole
PARTY_ROLE_COUNTERPARTY: PartyRole
TIME_PRECISION_UNSPECIFIED: TimePrecision
TIME_PRECISION_SECOND: TimePrecision
TIME_PRECISION_MILLISECOND: TimePrecision
TIME_PRECISION_MICROSECOND: TimePrecision
TIME_PRECISION_NANOSECOND: TimePrecision
RECEIPT_QUOTE_SOURCE_KIND_UNSPECIFIED: ReceiptQuoteSourceKind
RECEIPT_QUOTE_SOURCE_KIND_CONSOLIDATED: ReceiptQuoteSourceKind
RECEIPT_QUOTE_SOURCE_KIND_VENUE: ReceiptQuoteSourceKind
ORDER_LINK_KIND_UNSPECIFIED: OrderLinkKind
ORDER_LINK_KIND_SPLIT: OrderLinkKind
ORDER_LINK_KIND_NET: OrderLinkKind
EXECUTION_INSTRUCTION_UNSPECIFIED: ExecutionInstruction
EXECUTION_INSTRUCTION_NOT_HELD: ExecutionInstruction
EXECUTION_INSTRUCTION_DO_NOT_REDUCE: ExecutionInstruction
EXECUTION_INSTRUCTION_DO_NOT_INCREASE: ExecutionInstruction
EXECUTION_INSTRUCTION_REDUCE_ONLY: ExecutionInstruction
EXECUTION_INSTRUCTION_SELF_MATCH_PREVENTION: ExecutionInstruction
ORDER_ORIGIN_UNSPECIFIED: OrderOrigin
ORDER_ORIGIN_TELEPHONED: OrderOrigin
ORDER_ORIGIN_ACCEPTED_EXECUTION: OrderOrigin
ORDER_STATE_UNSPECIFIED: OrderState
ORDER_STATE_PROPOSED: OrderState
ORDER_STATE_REFUSED: OrderState
ORDER_STATE_RELEASED: OrderState
ORDER_STATE_WORKING: OrderState
ORDER_STATE_FILLED: OrderState
ORDER_STATE_CANCELLED: OrderState
ORDER_STATE_EXPIRED: OrderState
ORDER_CONDITION_UNSPECIFIED: OrderCondition
ORDER_CONDITION_CHANGE_REQUESTED: OrderCondition
ORDER_CONDITION_APPROVAL_REQUIRED: OrderCondition
ORDER_CONDITION_AWAITING_CHECK: OrderCondition
ORDER_CONDITION_CLAIMED: OrderCondition
ORDER_CONDITION_HELD: OrderCondition
ORDER_CONDITION_PAUSED: OrderCondition
ORDER_CONDITION_OUTCOME_UNKNOWN: OrderCondition
ORDER_CONDITION_DOES_NOT_TIE_OUT: OrderCondition
ORDER_CONDITION_LATE_FACT: OrderCondition
TIE_OUT_REASON_UNSPECIFIED: TieOutReason
TIE_OUT_REASON_OVERFILL: TieOutReason
TIE_OUT_REASON_RESTATEMENT: TieOutReason
HOLD_CAUSE_UNSPECIFIED: HoldCause
HOLD_CAUSE_REFERENCE_PRICE_STALE: HoldCause
CHECK_VERDICT_UNSPECIFIED: CheckVerdict
CHECK_VERDICT_PASS: CheckVerdict
CHECK_VERDICT_WARN: CheckVerdict
CHECK_VERDICT_BLOCK: CheckVerdict
CHECK_VERDICT_REFUSE: CheckVerdict
ORDER_CHANGE_KIND_UNSPECIFIED: OrderChangeKind
ORDER_CHANGE_KIND_CANCEL: OrderChangeKind
ORDER_CHANGE_KIND_AMEND: OrderChangeKind
ORDER_CHANGE_KIND_RECALL: OrderChangeKind
ORDER_CHANGE_KIND_WITHDRAW: OrderChangeKind
ORDER_CHANGE_KIND_QUANTITY: OrderChangeKind
PLACEMENT_CHANGE_KIND_UNSPECIFIED: PlacementChangeKind
PLACEMENT_CHANGE_KIND_CANCEL: PlacementChangeKind
PLACEMENT_CHANGE_KIND_REPLACE: PlacementChangeKind
CHANGE_REQUEST_OUTCOME_UNSPECIFIED: ChangeRequestOutcome
CHANGE_REQUEST_OUTCOME_PENDING: ChangeRequestOutcome
CHANGE_REQUEST_OUTCOME_APPLIED: ChangeRequestOutcome
CHANGE_REQUEST_OUTCOME_REJECTED: ChangeRequestOutcome
STRATEGY_KIND_UNSPECIFIED: StrategyKind
STRATEGY_KIND_VWAP: StrategyKind
STRATEGY_KIND_TWAP: StrategyKind
STRATEGY_KIND_POV: StrategyKind
STRATEGY_KIND_IS: StrategyKind
URGENCY_UNSPECIFIED: Urgency
URGENCY_LOW: Urgency
URGENCY_MEDIUM: Urgency
URGENCY_HIGH: Urgency
ROUTE_TYPE_UNSPECIFIED: RouteType
ROUTE_TYPE_DIRECTED: RouteType
ROUTE_TYPE_NOT_DIRECTED: RouteType
PLACEMENT_STATE_UNSPECIFIED: PlacementState
PLACEMENT_STATE_QUEUED: PlacementState
PLACEMENT_STATE_SENT: PlacementState
PLACEMENT_STATE_WORKING: PlacementState
PLACEMENT_STATE_DONE_FOR_DAY: PlacementState
PLACEMENT_STATE_FILLED: PlacementState
PLACEMENT_STATE_CANCELLED: PlacementState
PLACEMENT_STATE_EXPIRED: PlacementState
PLACEMENT_STATE_REJECTED: PlacementState
PLACEMENT_CONDITION_UNSPECIFIED: PlacementCondition
PLACEMENT_CONDITION_CHANGE_REQUESTED: PlacementCondition
PLACEMENT_CONDITION_OUTCOME_UNKNOWN: PlacementCondition
PLACEMENT_CONDITION_SUSPENDED: PlacementCondition
PLACEMENT_CONDITION_AWAITING_TRIGGER: PlacementCondition
PLACEMENT_CONDITION_SENT_ON_STALE_REFERENCE: PlacementCondition
UNKNOWN_REASON_UNSPECIFIED: UnknownReason
UNKNOWN_REASON_CONNECTION_LOST: UnknownReason
UNKNOWN_REASON_REQUEST_UNANSWERED: UnknownReason
UNKNOWN_REASON_VENUE_STATUS_NOT_MAPPED: UnknownReason
REJECTION_REASON_UNSPECIFIED: RejectionReason
REJECTION_REASON_UNSUPPORTED: RejectionReason
REJECTION_REASON_VENUE_REJECTED: RejectionReason
REJECTION_REASON_HELD_BY_PRE_TRADE_CHECK: RejectionReason
PLACEMENT_TYPE_UNSPECIFIED: PlacementType
PLACEMENT_TYPE_DMA: PlacementType
PLACEMENT_TYPE_ALGO: PlacementType
PLACEMENT_TYPE_CARE: PlacementType
PLACEMENT_TYPE_RFQ: PlacementType
PLACEMENT_TYPE_MANUAL: PlacementType
PLACEMENT_QUOTE_OUTCOME_UNSPECIFIED: PlacementQuoteOutcome
PLACEMENT_QUOTE_OUTCOME_OPEN: PlacementQuoteOutcome
PLACEMENT_QUOTE_OUTCOME_PICKED: PlacementQuoteOutcome
PLACEMENT_QUOTE_OUTCOME_ACCEPTED: PlacementQuoteOutcome
PLACEMENT_QUOTE_OUTCOME_EXPIRED: PlacementQuoteOutcome
PLACEMENT_QUOTE_OUTCOME_WITHDRAWN: PlacementQuoteOutcome
PLACEMENT_QUOTE_OUTCOME_NOT_PICKED: PlacementQuoteOutcome
EXECUTION_KIND_UNSPECIFIED: ExecutionKind
EXECUTION_KIND_VENUE_REPORTED: ExecutionKind
EXECUTION_KIND_MANUAL: ExecutionKind
EXECUTION_KIND_FROM_INVENTORY: ExecutionKind
EXECUTION_KIND_DONE_AWAY: ExecutionKind
EXECUTION_KIND_FROM_CHILD_ORDERS: ExecutionKind
EXECUTION_KIND_INTERNAL_CROSS: ExecutionKind
EXECUTION_KIND_INFERRED: ExecutionKind
EXECUTION_SOURCE_UNSPECIFIED: ExecutionSource
EXECUTION_SOURCE_PRIMARY: ExecutionSource
EXECUTION_SOURCE_DROP_COPY: ExecutionSource
FINALITY_LEVEL_UNSPECIFIED: FinalityLevel
FINALITY_LEVEL_AWAITING_ACCEPTANCE: FinalityLevel
FINALITY_LEVEL_MATCHED: FinalityLevel
FINALITY_LEVEL_INCLUDED: FinalityLevel
FINALITY_LEVEL_FINAL: FinalityLevel
FINALITY_LEVEL_FAILED: FinalityLevel
FEE_KIND_UNSPECIFIED: FeeKind
FEE_KIND_EXCHANGE: FeeKind
FEE_KIND_CANCEL: FeeKind
FEE_KIND_NETWORK: FeeKind
FEE_KIND_FINANCING: FeeKind
FEE_KIND_COMMISSION: FeeKind
LIQUIDITY_INDICATOR_UNSPECIFIED: LiquidityIndicator
LIQUIDITY_INDICATOR_MAKER: LiquidityIndicator
LIQUIDITY_INDICATOR_TAKER: LiquidityIndicator
EXECUTION_STATE_UNSPECIFIED: ExecutionState
EXECUTION_STATE_UNMATCHED: ExecutionState
EXECUTION_STATE_MATCHED: ExecutionState
EXECUTION_STATE_DONT_KNOW: ExecutionState
DK_REASON_UNSPECIFIED: DkReason
DK_REASON_UNKNOWN_INSTRUMENT: DkReason
DK_REASON_WRONG_SIDE: DkReason
DK_REASON_QUANTITY_EXCEEDS_ORDER: DkReason
DK_REASON_NO_MATCHING_ORDER: DkReason
DK_REASON_PRICE_EXCEEDS_LIMIT: DkReason
DK_REASON_CALCULATION_DIFFERENCE: DkReason
DK_REASON_OTHER: DkReason
GIVE_UP_ANSWER_UNSPECIFIED: GiveUpAnswer
GIVE_UP_ANSWER_ACCEPTED: GiveUpAnswer
GIVE_UP_ANSWER_REJECTED: GiveUpAnswer
CROSS_RATE_SOURCE_UNSPECIFIED: CrossRateSource
CROSS_RATE_SOURCE_NET_STREET_RATE: CrossRateSource
CROSS_RATE_SOURCE_MID_AT_NETTING: CrossRateSource
APPROVAL_DECISION_UNSPECIFIED: ApprovalDecision
APPROVAL_DECISION_REQUIRE: ApprovalDecision
APPROVAL_DECISION_APPROVE: ApprovalDecision
APPROVAL_DECISION_OVERRIDE: ApprovalDecision
APPROVAL_DECISION_REJECT: ApprovalDecision
PLACEMENT_EVENT_UNSPECIFIED: PlacementEvent
PLACEMENT_EVENT_SENT: PlacementEvent
PLACEMENT_EVENT_ACKNOWLEDGED: PlacementEvent
PLACEMENT_EVENT_REPLACED: PlacementEvent
PLACEMENT_EVENT_DONE_FOR_DAY: PlacementEvent
PLACEMENT_EVENT_RESTATED: PlacementEvent
PLACEMENT_EVENT_SUSPENDED: PlacementEvent
PLACEMENT_EVENT_TRIGGERED: PlacementEvent
PLACEMENT_EVENT_CANCELLED: PlacementEvent
PLACEMENT_EVENT_EXPIRED: PlacementEvent
PLACEMENT_EVENT_REJECTED: PlacementEvent
PLACEMENT_EVENT_OUTCOME_UNKNOWN: PlacementEvent
PLACEMENT_EVENT_OUTCOME_RESOLVED: PlacementEvent
RESTATEMENT_REASON_UNSPECIFIED: RestatementReason
RESTATEMENT_REASON_CORPORATE_ACTION: RestatementReason
RESTATEMENT_REASON_RENEWAL: RestatementReason
RESTATEMENT_REASON_REPRICING: RestatementReason
RESTATEMENT_REASON_PARTIAL_DECLINE: RestatementReason
RESTATEMENT_REASON_CANCEL_ON_HALT: RestatementReason
RESTATEMENT_REASON_CANCEL_ON_SYSTEM_FAILURE: RestatementReason
RESTATEMENT_REASON_VENUE_OPTION: RestatementReason
RESTATEMENT_REASON_OTHER: RestatementReason
UNPLACED_REASON_UNSPECIFIED: UnplacedReason
UNPLACED_REASON_UNKNOWN_PLACEMENT: UnplacedReason
UNPLACED_REASON_UNMAPPED_VENUE_ACCOUNT: UnplacedReason
UNPLACED_REASON_NOTHING_PENDING: UnplacedReason
UNPLACED_REASON_UNKNOWN_EXECUTION: UnplacedReason
TRADING_INSTRUCTION_VALUE_UNSPECIFIED: TradingInstructionValue
TRADING_INSTRUCTION_VALUE_ACTIVE: TradingInstructionValue
TRADING_INSTRUCTION_VALUE_PAUSE: TradingInstructionValue
TRADING_INSTRUCTION_VALUE_STOP: TradingInstructionValue
SETTER_LEVEL_UNSPECIFIED: SetterLevel
SETTER_LEVEL_DEPLOYMENT_ADMIN: SetterLevel
SETTER_LEVEL_PLUGIN_ADMIN: SetterLevel
LOCATE_USE_KIND_UNSPECIFIED: LocateUseKind
LOCATE_USE_KIND_RESERVE: LocateUseKind
LOCATE_USE_KIND_GIVE_BACK: LocateUseKind
LOCATE_USE_KIND_CONSUME: LocateUseKind
STRATEGY_PARAMETER_TYPE_UNSPECIFIED: StrategyParameterType
STRATEGY_PARAMETER_TYPE_INT: StrategyParameterType
STRATEGY_PARAMETER_TYPE_FLOAT: StrategyParameterType
STRATEGY_PARAMETER_TYPE_QTY: StrategyParameterType
STRATEGY_PARAMETER_TYPE_PRICE: StrategyParameterType
STRATEGY_PARAMETER_TYPE_PRICE_OFFSET: StrategyParameterType
STRATEGY_PARAMETER_TYPE_AMOUNT: StrategyParameterType
STRATEGY_PARAMETER_TYPE_PERCENTAGE: StrategyParameterType
STRATEGY_PARAMETER_TYPE_BOOLEAN: StrategyParameterType
STRATEGY_PARAMETER_TYPE_CHAR: StrategyParameterType
STRATEGY_PARAMETER_TYPE_STRING: StrategyParameterType
STRATEGY_PARAMETER_TYPE_UTC_TIMESTAMP: StrategyParameterType
STRATEGY_PARAMETER_TYPE_LOCAL_MARKET_DATE: StrategyParameterType
BORROW_STATUS_UNSPECIFIED: BorrowStatus
BORROW_STATUS_EASY_TO_BORROW: BorrowStatus
BORROW_STATUS_HARD_TO_BORROW: BorrowStatus
EXECUTION_ACKNOWLEDGEMENT_UNSPECIFIED: ExecutionAcknowledgement
EXECUTION_ACKNOWLEDGEMENT_NONE: ExecutionAcknowledgement
EXECUTION_ACKNOWLEDGEMENT_BN: ExecutionAcknowledgement
EXECUTION_ACKNOWLEDGEMENT_DONT_KNOW_TRADE: ExecutionAcknowledgement
ERROR_CAUSE_UNSPECIFIED: ErrorCause
ERROR_CAUSE_OVERFILL: ErrorCause
ERROR_CAUSE_CLIENT_RENEGED: ErrorCause
ERROR_CAUSE_WRONG_ACCEPT: ErrorCause
ERROR_CAUSE_BOOKING_ERROR: ErrorCause
ERROR_CAUSE_OTHER: ErrorCause
BOOKING_STATE_UNSPECIFIED: BookingState
BOOKING_STATE_BOOKED: BookingState
BOOKING_STATE_HELD: BookingState
BOOKING_STATE_HANDED_OFF: BookingState
BOOKING_STATE_CLOSED: BookingState
BOOKING_STATE_CANCELLED: BookingState
BOOKING_CORRECTION_KIND_UNSPECIFIED: BookingCorrectionKind
BOOKING_CORRECTION_KIND_CANCEL: BookingCorrectionKind
BOOKING_CORRECTION_KIND_REPLACE: BookingCorrectionKind
ALERT_KIND_UNSPECIFIED: AlertKind
ALERT_KIND_ERROR_ACCOUNT_BOOKING: AlertKind
ALERT_KIND_BOOKING_HELD: AlertKind
ALERT_KIND_COMPLIANCE: AlertKind
ALERT_STATE_UNSPECIFIED: AlertState
ALERT_STATE_RAISED: AlertState
ALERT_STATE_ACKNOWLEDGED: AlertState
ALERT_STATE_CLEARED: AlertState
VENUE_KIND_UNSPECIFIED: VenueKind
VENUE_KIND_EXCHANGE: VenueKind
VENUE_KIND_ALTERNATIVE_TRADING_SYSTEM: VenueKind
VENUE_KIND_CRYPTO_EXCHANGE: VenueKind
VENUE_KIND_DEALER_NETWORK: VenueKind
VENUE_KIND_REPORTING_FACILITY: VenueKind
CALENDAR_DAY_KIND_UNSPECIFIED: CalendarDayKind
CALENDAR_DAY_KIND_CLOSED: CalendarDayKind
CALENDAR_DAY_KIND_OPEN: CalendarDayKind
WEEKDAY_UNSPECIFIED: Weekday
WEEKDAY_MONDAY: Weekday
WEEKDAY_TUESDAY: Weekday
WEEKDAY_WEDNESDAY: Weekday
WEEKDAY_THURSDAY: Weekday
WEEKDAY_FRIDAY: Weekday
WEEKDAY_SATURDAY: Weekday
WEEKDAY_SUNDAY: Weekday
TENOR_UNIT_UNSPECIFIED: TenorUnit
TENOR_UNIT_DAY: TenorUnit
TENOR_UNIT_WEEK: TenorUnit
TENOR_UNIT_MONTH: TenorUnit
TENOR_UNIT_YEAR: TenorUnit
TENOR_UNIT_OVERNIGHT: TenorUnit
TENOR_UNIT_TOM_NEXT: TenorUnit
TENOR_UNIT_SPOT_NEXT: TenorUnit
BUSINESS_DAY_CONVENTION_UNSPECIFIED: BusinessDayConvention
BUSINESS_DAY_CONVENTION_FOLLOWING: BusinessDayConvention
BUSINESS_DAY_CONVENTION_MODIFIED_FOLLOWING: BusinessDayConvention
BUSINESS_DAY_CONVENTION_PRECEDING: BusinessDayConvention
BUSINESS_DAY_CONVENTION_NONE: BusinessDayConvention
DATE_OUTCOME_UNSPECIFIED: DateOutcome
DATE_OUTCOME_COMPUTED: DateOutcome
DATE_OUTCOME_CALENDAR_NOT_HELD: DateOutcome
DATE_OUTCOME_OUTSIDE_COVERAGE: DateOutcome
DATE_OUTCOME_RULE_NOT_HELD: DateOutcome
REPLACEMENT_CAUSE_UNSPECIFIED: ReplacementCause
REPLACEMENT_CAUSE_MERGED: ReplacementCause
REPLACEMENT_CAUSE_RESOLVED: ReplacementCause
REPLACEMENT_CAUSE_PLATFORM_MERGED: ReplacementCause
SOURCE_TIME_KIND_UNSPECIFIED: SourceTimeKind
SOURCE_TIME_KIND_EVENT: SourceTimeKind
SOURCE_TIME_KIND_CONSOLIDATED: SourceTimeKind
SOURCE_TIME_KIND_REPORTED: SourceTimeKind
SOURCE_TIME_KIND_VENDOR_RECEIVED: SourceTimeKind
SOURCE_TIME_KIND_PUBLISHED: SourceTimeKind
PRICE_KIND_UNSPECIFIED: PriceKind
PRICE_KIND_CLOSE: PriceKind
PRICE_KIND_LAST: PriceKind
PRICE_KIND_NAV: PriceKind
PRICE_KIND_SETTLEMENT: PriceKind
PRICE_KIND_BID: PriceKind
PRICE_KIND_ASK: PriceKind
PRICE_KIND_MID: PriceKind
PRICE_BASIS_UNSPECIFIED: PriceBasis
PRICE_BASIS_PER_UNIT: PriceBasis
ELIGIBLE_UNSPECIFIED: Eligible
ELIGIBLE_ELIGIBLE: Eligible
ELIGIBLE_NOT_ELIGIBLE: Eligible
TRADE_CHARACTERISTIC_UNSPECIFIED: TradeCharacteristic
TRADE_CHARACTERISTIC_OPENING_AUCTION: TradeCharacteristic
TRADE_CHARACTERISTIC_CLOSING_AUCTION: TradeCharacteristic
TRADE_CHARACTERISTIC_OTHER_AUCTION: TradeCharacteristic
TRADE_CHARACTERISTIC_ODD_LOT: TradeCharacteristic
TRADE_CHARACTERISTIC_EXTENDED_HOURS: TradeCharacteristic
TRADE_CHARACTERISTIC_OUT_OF_SEQUENCE: TradeCharacteristic
TRADE_CHARACTERISTIC_LATE_REPORT: TradeCharacteristic
TRADE_CHARACTERISTIC_AVERAGE_PRICE: TradeCharacteristic
TRADE_CHARACTERISTIC_NON_REGULAR_SETTLEMENT: TradeCharacteristic
TRADE_CHARACTERISTIC_INTERMARKET_SWEEP: TradeCharacteristic
TRADE_CHARACTERISTIC_DERIVATIVELY_PRICED: TradeCharacteristic
TRADE_CHARACTERISTIC_PRIOR_REFERENCE_PRICE: TradeCharacteristic
TRADE_CHARACTERISTIC_CONTINGENT: TradeCharacteristic
TRADE_CHARACTERISTIC_CROSS: TradeCharacteristic
AGGRESSOR_UNSPECIFIED: Aggressor
AGGRESSOR_BUY: Aggressor
AGGRESSOR_SELL: Aggressor
QUOTE_CHARACTERISTIC_UNSPECIFIED: QuoteCharacteristic
QUOTE_CHARACTERISTIC_INDICATIVE: QuoteCharacteristic
QUOTE_CHARACTERISTIC_HALTED: QuoteCharacteristic
OUTCOME_DETERMINATION_UNSPECIFIED: OutcomeDetermination
OUTCOME_DETERMINATION_PAYS: OutcomeDetermination
OUTCOME_DETERMINATION_PAYS_NOTHING: OutcomeDetermination
OUTCOME_DETERMINATION_PAYS_PART: OutcomeDetermination
OUTCOME_STAGE_UNSPECIFIED: OutcomeStage
OUTCOME_STAGE_PROPOSED: OutcomeStage
OUTCOME_STAGE_DETERMINED: OutcomeStage
OUTCOME_STAGE_DISPUTED: OutcomeStage
OUTCOME_STAGE_FINAL: OutcomeStage
UNANSWERED_REASON_UNSPECIFIED: UnansweredReason
UNANSWERED_REASON_NOT_ENTITLED: UnansweredReason
UNANSWERED_REASON_NOT_COVERED: UnansweredReason
UNANSWERED_REASON_ASKED_SOURCE: UnansweredReason
UNANSWERED_REASON_SOURCE_SILENT: UnansweredReason
UNANSWERED_REASON_UNRESOLVED: UnansweredReason
UNANSWERED_REASON_BEYOND_HISTORY: UnansweredReason
UNANSWERED_REASON_NOT_KEPT: UnansweredReason
OBSERVATION_MODE_UNSPECIFIED: ObservationMode
OBSERVATION_MODE_PULL: ObservationMode
OBSERVATION_MODE_PUSH: ObservationMode
OBSERVATION_MODE_STREAM: ObservationMode
ACCESS_BASIS_UNSPECIFIED: AccessBasis
ACCESS_BASIS_LICENSED: AccessBasis
ACCESS_BASIS_OPEN: AccessBasis
ACCESS_BASIS_PUBLIC_DOMAIN: AccessBasis
TIMELINESS_UNSPECIFIED: Timeliness
TIMELINESS_REAL_TIME: Timeliness
TIMELINESS_DELAYED: Timeliness
TIMELINESS_END_OF_DAY: Timeliness
TIMELINESS_HISTORICAL: Timeliness
LICENCE_METER_UNSPECIFIED: LicenceMeter
LICENCE_METER_DISPLAY: LicenceMeter
LICENCE_METER_NON_DISPLAY: LicenceMeter
LICENCE_METER_ENTERPRISE: LicenceMeter
DISPLAY_UNIT_UNSPECIFIED: DisplayUnit
DISPLAY_UNIT_PERSON: DisplayUnit
DISPLAY_UNIT_DEVICE: DisplayUnit
COUNT_BASIS_UNSPECIFIED: CountBasis
COUNT_BASIS_SERVED: CountBasis
COUNT_BASIS_ENTITLED: CountBasis
PROFESSIONAL_DEFINITION_UNSPECIFIED: ProfessionalDefinition
PROFESSIONAL_DEFINITION_STANDARD: ProfessionalDefinition
PROFESSIONAL_DEFINITION_VENDOR: ProfessionalDefinition
NON_DISPLAY_CATEGORY_UNSPECIFIED: NonDisplayCategory
NON_DISPLAY_CATEGORY_TRADING_PLATFORM: NonDisplayCategory
NON_DISPLAY_CATEGORY_AUTOMATED_TRADING: NonDisplayCategory
NON_DISPLAY_CATEGORY_INTERNAL: NonDisplayCategory
NON_DISPLAY_CATEGORY_FOR_CLIENTS: NonDisplayCategory
NON_DISPLAY_COUNT_UNSPECIFIED: NonDisplayCount
NON_DISPLAY_COUNT_PER_PLUGIN: NonDisplayCount
NON_DISPLAY_COUNT_PER_CATEGORY: NonDisplayCount
ENTERPRISE_REPLACES_UNSPECIFIED: EnterpriseReplaces
ENTERPRISE_REPLACES_DISPLAY_PROFESSIONAL: EnterpriseReplaces
ENTERPRISE_REPLACES_DISPLAY_NON_PROFESSIONAL: EnterpriseReplaces
ENTERPRISE_REPLACES_NON_DISPLAY: EnterpriseReplaces
ENTERPRISE_FORM_UNSPECIFIED: EnterpriseForm
ENTERPRISE_FORM_FLAT: EnterpriseForm
ENTERPRISE_FORM_CAP: EnterpriseForm
ENTERPRISE_SCOPE_UNSPECIFIED: EnterpriseScope
ENTERPRISE_SCOPE_DEPLOYMENT: EnterpriseScope
DERIVED_USE_UNSPECIFIED: DerivedUse
DERIVED_USE_NOT_RESTRICTED: DerivedUse
DERIVED_USE_INTERNAL_ONLY: DerivedUse
DERIVED_USE_REDISTRIBUTION_NEEDS_LICENCE: DerivedUse
REDISTRIBUTION_UNSPECIFIED: Redistribution
REDISTRIBUTION_NOT_ALLOWED: Redistribution
REDISTRIBUTION_LICENCE_REQUIRED: Redistribution
REDISTRIBUTION_ALLOWED_WITH_ATTRIBUTION: Redistribution
OUTSIDE_COMPUTATION_UNSPECIFIED: OutsideComputation
OUTSIDE_COMPUTATION_ALLOWED: OutsideComputation
OUTSIDE_COMPUTATION_PER_REQUEST_NO_RETENTION: OutsideComputation
OUTSIDE_COMPUTATION_NOT_ALLOWED: OutsideComputation
PROHIBITED_USE_UNSPECIFIED: ProhibitedUse
PROHIBITED_USE_MODEL_TRAINING: ProhibitedUse
PROHIBITED_USE_REPLICATE_SERVICE: ProhibitedUse
PROHIBITED_USE_INDEX_CREATION: ProhibitedUse
COPYRIGHT_CLASS_UNSPECIFIED: CopyrightClass
COPYRIGHT_CLASS_PUBLIC_DOMAIN: CopyrightClass
COPYRIGHT_CLASS_COPYRIGHT_CITATION_REQUIRED: CopyrightClass
COPYRIGHT_CLASS_COPYRIGHT_PREAPPROVAL_REQUIRED: CopyrightClass
REPORT_CADENCE_UNSPECIFIED: ReportCadence
REPORT_CADENCE_NONE: ReportCadence
REPORT_CADENCE_MONTHLY: ReportCadence
REPORT_CADENCE_ANNUAL_DECLARATION: ReportCadence
REPORT_CADENCE_ON_CHANGE: ReportCadence
SCENARIO_KIND_UNSPECIFIED: ScenarioKind
SCENARIO_KIND_BASE: ScenarioKind
SCENARIO_KIND_WHAT_IF: ScenarioKind
SCENARIO_KIND_HISTORICAL_DAY: ScenarioKind
SCENARIO_KIND_OUTCOME: ScenarioKind
SCENARIO_KIND_NONE_OF_THE_NAMED: ScenarioKind
COMPUTED_AS_UNSPECIFIED: ComputedAs
COMPUTED_AS_EXACT: ComputedAs
COMPUTED_AS_MODEL: ComputedAs
NOT_EVALUATED_REASON_UNSPECIFIED: NotEvaluatedReason
NOT_EVALUATED_REASON_PRICE_MISSING: NotEvaluatedReason
NOT_EVALUATED_REASON_PRICE_STALE: NotEvaluatedReason
NOT_EVALUATED_REASON_CONVERSION_MISSING: NotEvaluatedReason
NOT_EVALUATED_REASON_NOT_ENTITLED: NotEvaluatedReason
NOT_EVALUATED_REASON_LOCAL_RECORD: NotEvaluatedReason
NOT_EVALUATED_REASON_IMPLEMENTATION_UNAVAILABLE: NotEvaluatedReason
NOT_EVALUATED_REASON_SCHEME_NOT_HELD: NotEvaluatedReason
NOT_EVALUATED_REASON_GROUP_NOT_EXHAUSTIVE: NotEvaluatedReason
NOT_EVALUATED_REASON_HISTORY_INSUFFICIENT: NotEvaluatedReason
NOT_EVALUATED_REASON_COST_MISSING: NotEvaluatedReason
CONVERSION_DERIVATION_UNSPECIFIED: ConversionDerivation
CONVERSION_DERIVATION_DIRECT: ConversionDerivation
CONVERSION_DERIVATION_INVERTED: ConversionDerivation
CONVERSION_DERIVATION_CROSSED: ConversionDerivation
EVENT_GROUP_FLAG_UNSPECIFIED: EventGroupFlag
EVENT_GROUP_FLAG_TRUE: EventGroupFlag
EVENT_GROUP_FLAG_FALSE: EventGroupFlag
EVENT_GROUP_FLAG_NOT_STATED: EventGroupFlag
RATE_KIND_UNSPECIFIED: RateKind
RATE_KIND_FIXING: RateKind
RATE_KIND_AVERAGE: RateKind
RATE_KIND_INDEX_LEVEL: RateKind
RATE_KIND_PAR_YIELD: RateKind
RATE_KIND_ZERO: RateKind
RATE_KIND_DISCOUNT: RateKind
RATE_KIND_COUPON_EQUIVALENT: RateKind
VALUE_UNIT_UNSPECIFIED: ValueUnit
VALUE_UNIT_PERCENT: ValueUnit
VALUE_UNIT_BASIS_POINTS: ValueUnit
VALUE_UNIT_SHARES: ValueUnit
VALUE_UNIT_CONTRACTS: ValueUnit
VALUE_UNIT_PRINCIPAL: ValueUnit
VALUE_UNIT_RATIO: ValueUnit
VALUE_UNIT_COUNT: ValueUnit
VALUE_UNIT_DAYS: ValueUnit
VALUE_UNIT_INDEX: ValueUnit
VALUE_UNIT_UCUM: ValueUnit
DAY_COUNT_UNSPECIFIED: DayCount
DAY_COUNT_ACT_360: DayCount
DAY_COUNT_ACT_365_FIXED: DayCount
DAY_COUNT_ACT_ACT: DayCount
DAY_COUNT_THIRTY_360: DayCount
DAY_COUNT_BUS_252: DayCount
COMPOUNDING_UNSPECIFIED: Compounding
COMPOUNDING_SIMPLE: Compounding
COMPOUNDING_COMPOUNDED: Compounding
COMPOUNDING_CONTINUOUS: Compounding
COMPOUNDING_DISCOUNT: Compounding
AGE_HOP_UNSPECIFIED: AgeHop
AGE_HOP_EDGE: AgeHop
AGE_HOP_SIDECAR: AgeHop
AGE_HOP_LAKE: AgeHop
AGE_HOP_BUS: AgeHop
AGE_HOP_ANALYTICS: AgeHop
AGE_HOP_EMS_CHECK: AgeHop
AGE_HOP_PAGE: AgeHop
LATENCY_METRIC_UNSPECIFIED: LatencyMetric
LATENCY_METRIC_RTT: LatencyMetric
LATENCY_METRIC_ORDER_ACK: LatencyMetric
LATENCY_METRIC_FILL_DELAY: LatencyMetric
LATENCY_METRIC_AGE: LatencyMetric
TCA_BENCHMARK_UNSPECIFIED: TcaBenchmark
TCA_BENCHMARK_DECISION: TcaBenchmark
TCA_BENCHMARK_ARRIVAL: TcaBenchmark
TCA_BENCHMARK_PLACEMENT_ARRIVAL: TcaBenchmark
TCA_BENCHMARK_MID_AT_FILL: TcaBenchmark
TCA_BENCHMARK_INTERVAL_VWAP: TcaBenchmark
TCA_BENCHMARK_FIX: TcaBenchmark
TCA_UNANSWERED_UNSPECIFIED: TcaUnanswered
TCA_UNANSWERED_NO_QUOTE: TcaUnanswered
TCA_UNANSWERED_NOT_MEASURED: TcaUnanswered

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
    __slots__ = ("source", "last_synced_at_ns", "connection_healthy", "status_detail", "observed_at_ns", "external_account_id", "state", "holdings_as_of_ns", "history_as_of_ns", "history_from")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CONNECTION_HEALTHY_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    HOLDINGS_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    HISTORY_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FROM_FIELD_NUMBER: _ClassVar[int]
    source: str
    last_synced_at_ns: int
    connection_healthy: bool
    status_detail: str
    observed_at_ns: int
    external_account_id: str
    state: SyncState
    holdings_as_of_ns: int
    history_as_of_ns: int
    history_from: str
    def __init__(self, source: _Optional[str] = ..., last_synced_at_ns: _Optional[int] = ..., connection_healthy: bool = ..., status_detail: _Optional[str] = ..., observed_at_ns: _Optional[int] = ..., external_account_id: _Optional[str] = ..., state: _Optional[_Union[SyncState, str]] = ..., holdings_as_of_ns: _Optional[int] = ..., history_as_of_ns: _Optional[int] = ..., history_from: _Optional[str] = ...) -> None: ...

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

class RecordActivityParams(_message.Message):
    __slots__ = ("external_account_id", "source", "activity", "acting_for")
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    external_account_id: str
    source: str
    activity: CustodialActivity
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, external_account_id: _Optional[str] = ..., source: _Optional[str] = ..., activity: _Optional[_Union[CustodialActivity, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordActivityResult(_message.Message):
    __slots__ = ("activity_id", "already_recorded")
    ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    ALREADY_RECORDED_FIELD_NUMBER: _ClassVar[int]
    activity_id: str
    already_recorded: bool
    def __init__(self, activity_id: _Optional[str] = ..., already_recorded: bool = ...) -> None: ...

class ListActivitiesParams(_message.Message):
    __slots__ = ("account_id", "trade_date_from", "trade_date_to", "since", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FROM_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_TO_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    trade_date_from: str
    trade_date_to: str
    since: Watermark
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., trade_date_from: _Optional[str] = ..., trade_date_to: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListActivitiesResult(_message.Message):
    __slots__ = ("activities", "next_cursor", "as_of", "history_from", "re_resolutions")
    ACTIVITIES_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FROM_FIELD_NUMBER: _ClassVar[int]
    RE_RESOLUTIONS_FIELD_NUMBER: _ClassVar[int]
    activities: _containers.RepeatedCompositeFieldContainer[ActivityRecordedEvent]
    next_cursor: str
    as_of: Watermark
    history_from: str
    re_resolutions: _containers.RepeatedCompositeFieldContainer[ActivityReResolution]
    def __init__(self, activities: _Optional[_Iterable[_Union[ActivityRecordedEvent, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ..., history_from: _Optional[str] = ..., re_resolutions: _Optional[_Iterable[_Union[ActivityReResolution, _Mapping]]] = ...) -> None: ...

class ReResolveActivityParams(_message.Message):
    __slots__ = ("external_account_id", "source", "external_activity_id", "instrument_id", "provenance", "resolved_at_ns", "acting_for")
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    external_account_id: str
    source: str
    external_activity_id: str
    instrument_id: str
    provenance: Provenance
    resolved_at_ns: int
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, external_account_id: _Optional[str] = ..., source: _Optional[str] = ..., external_activity_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., provenance: _Optional[_Union[Provenance, _Mapping]] = ..., resolved_at_ns: _Optional[int] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReResolveActivityResult(_message.Message):
    __slots__ = ("activity_id", "already_recorded")
    ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    ALREADY_RECORDED_FIELD_NUMBER: _ClassVar[int]
    activity_id: str
    already_recorded: bool
    def __init__(self, activity_id: _Optional[str] = ..., already_recorded: bool = ...) -> None: ...

class ListSyncStatusesParams(_message.Message):
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

class ListSyncStatusesResult(_message.Message):
    __slots__ = ("statuses", "next_cursor", "as_of")
    STATUSES_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    statuses: _containers.RepeatedCompositeFieldContainer[SyncStatusRecordedEvent]
    next_cursor: str
    as_of: Watermark
    def __init__(self, statuses: _Optional[_Iterable[_Union[SyncStatusRecordedEvent, _Mapping]]] = ..., next_cursor: _Optional[str] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ResolveIdentifierParams(_message.Message):
    __slots__ = ("identifiers", "as_of_ns", "exchange_mic", "currency", "stated_asset_class", "stated_currency", "stated_description", "stated_instrument_type", "provenance")
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    EXCHANGE_MIC_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    STATED_ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    STATED_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    STATED_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    STATED_INSTRUMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    as_of_ns: int
    exchange_mic: str
    currency: str
    stated_asset_class: AssetClass
    stated_currency: str
    stated_description: str
    stated_instrument_type: InstrumentType
    provenance: _containers.RepeatedCompositeFieldContainer[Provenance]
    def __init__(self, identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., as_of_ns: _Optional[int] = ..., exchange_mic: _Optional[str] = ..., currency: _Optional[str] = ..., stated_asset_class: _Optional[_Union[AssetClass, str]] = ..., stated_currency: _Optional[str] = ..., stated_description: _Optional[str] = ..., stated_instrument_type: _Optional[_Union[InstrumentType, str]] = ..., provenance: _Optional[_Iterable[_Union[Provenance, _Mapping]]] = ...) -> None: ...

class ResolveIdentifierResult(_message.Message):
    __slots__ = ("found", "instrument_id", "miss_reason", "minted", "provisional")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    MISS_REASON_FIELD_NUMBER: _ClassVar[int]
    MINTED_FIELD_NUMBER: _ClassVar[int]
    PROVISIONAL_FIELD_NUMBER: _ClassVar[int]
    found: bool
    instrument_id: str
    miss_reason: MissReason
    minted: bool
    provisional: bool
    def __init__(self, found: bool = ..., instrument_id: _Optional[str] = ..., miss_reason: _Optional[_Union[MissReason, str]] = ..., minted: bool = ..., provisional: bool = ...) -> None: ...

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
    __slots__ = ("account_id", "break_id", "position", "figure", "category", "differences", "book_watermark", "street", "business_date", "candidate_causes", "idempotency_key", "unresolved_identifiers", "acting_for")
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
    UNRESOLVED_IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
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
    unresolved_identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., break_id: _Optional[str] = ..., position: _Optional[_Union[PositionKey, _Mapping]] = ..., figure: _Optional[_Union[FigureKey, _Mapping]] = ..., category: _Optional[_Union[BreakCategory, str]] = ..., differences: _Optional[_Iterable[_Union[BreakDifference, _Mapping]]] = ..., book_watermark: _Optional[_Union[Watermark, _Mapping]] = ..., street: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., business_date: _Optional[str] = ..., candidate_causes: _Optional[_Iterable[_Union[BreakCause, _Mapping]]] = ..., idempotency_key: _Optional[str] = ..., unresolved_identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

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

class ProposeOrderParams(_message.Message):
    __slots__ = ("account_id", "instrument_id", "sleeve", "side", "locate_id", "quantity", "cash_quantity", "order_type", "limit_price", "dealt_currency", "legs", "allocation_instruction", "time_in_force", "lot_relief_method", "relieve_lot_ids", "capacity", "direction", "parties", "decided_by", "customer_id", "firm_designated_id", "handling_instructions", "received_at_ns", "received_precision", "quote_at_receipt", "represents_order_ids", "axe_source", "axe_counterparty_id", "link", "idempotency_key", "stop_price", "expire_date", "expire_time_ns", "execution_instructions", "quote_currency", "block_member_order_ids", "net_member_order_ids", "value_date", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    LOCATE_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    CASH_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    DEALT_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    LEGS_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_FORCE_FIELD_NUMBER: _ClassVar[int]
    LOT_RELIEF_METHOD_FIELD_NUMBER: _ClassVar[int]
    RELIEVE_LOT_IDS_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    PARTIES_FIELD_NUMBER: _ClassVar[int]
    DECIDED_BY_FIELD_NUMBER: _ClassVar[int]
    CUSTOMER_ID_FIELD_NUMBER: _ClassVar[int]
    FIRM_DESIGNATED_ID_FIELD_NUMBER: _ClassVar[int]
    HANDLING_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_PRECISION_FIELD_NUMBER: _ClassVar[int]
    QUOTE_AT_RECEIPT_FIELD_NUMBER: _ClassVar[int]
    REPRESENTS_ORDER_IDS_FIELD_NUMBER: _ClassVar[int]
    AXE_SOURCE_FIELD_NUMBER: _ClassVar[int]
    AXE_COUNTERPARTY_ID_FIELD_NUMBER: _ClassVar[int]
    LINK_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    STOP_PRICE_FIELD_NUMBER: _ClassVar[int]
    EXPIRE_DATE_FIELD_NUMBER: _ClassVar[int]
    EXPIRE_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    QUOTE_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    BLOCK_MEMBER_ORDER_IDS_FIELD_NUMBER: _ClassVar[int]
    NET_MEMBER_ORDER_IDS_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    instrument_id: str
    sleeve: str
    side: Side
    locate_id: str
    quantity: Decimal
    cash_quantity: Money
    order_type: OrderType
    limit_price: Money
    dealt_currency: str
    legs: _containers.RepeatedCompositeFieldContainer[Leg]
    allocation_instruction: AllocationInstruction
    time_in_force: TimeInForce
    lot_relief_method: LotReliefMethod
    relieve_lot_ids: _containers.RepeatedScalarFieldContainer[str]
    capacity: Capacity
    direction: OrderDirection
    parties: _containers.RepeatedCompositeFieldContainer[Party]
    decided_by: Actor
    customer_id: str
    firm_designated_id: str
    handling_instructions: _containers.RepeatedScalarFieldContainer[str]
    received_at_ns: int
    received_precision: TimePrecision
    quote_at_receipt: ReceiptQuote
    represents_order_ids: _containers.RepeatedScalarFieldContainer[str]
    axe_source: str
    axe_counterparty_id: str
    link: OrderLink
    idempotency_key: str
    stop_price: Money
    expire_date: str
    expire_time_ns: int
    execution_instructions: _containers.RepeatedScalarFieldContainer[ExecutionInstruction]
    quote_currency: str
    block_member_order_ids: _containers.RepeatedScalarFieldContainer[str]
    net_member_order_ids: _containers.RepeatedScalarFieldContainer[str]
    value_date: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., sleeve: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., locate_id: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., cash_quantity: _Optional[_Union[Money, _Mapping]] = ..., order_type: _Optional[_Union[OrderType, str]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., dealt_currency: _Optional[str] = ..., legs: _Optional[_Iterable[_Union[Leg, _Mapping]]] = ..., allocation_instruction: _Optional[_Union[AllocationInstruction, _Mapping]] = ..., time_in_force: _Optional[_Union[TimeInForce, str]] = ..., lot_relief_method: _Optional[_Union[LotReliefMethod, str]] = ..., relieve_lot_ids: _Optional[_Iterable[str]] = ..., capacity: _Optional[_Union[Capacity, str]] = ..., direction: _Optional[_Union[OrderDirection, str]] = ..., parties: _Optional[_Iterable[_Union[Party, _Mapping]]] = ..., decided_by: _Optional[_Union[Actor, _Mapping]] = ..., customer_id: _Optional[str] = ..., firm_designated_id: _Optional[str] = ..., handling_instructions: _Optional[_Iterable[str]] = ..., received_at_ns: _Optional[int] = ..., received_precision: _Optional[_Union[TimePrecision, str]] = ..., quote_at_receipt: _Optional[_Union[ReceiptQuote, _Mapping]] = ..., represents_order_ids: _Optional[_Iterable[str]] = ..., axe_source: _Optional[str] = ..., axe_counterparty_id: _Optional[str] = ..., link: _Optional[_Union[OrderLink, _Mapping]] = ..., idempotency_key: _Optional[str] = ..., stop_price: _Optional[_Union[Money, _Mapping]] = ..., expire_date: _Optional[str] = ..., expire_time_ns: _Optional[int] = ..., execution_instructions: _Optional[_Iterable[_Union[ExecutionInstruction, str]]] = ..., quote_currency: _Optional[str] = ..., block_member_order_ids: _Optional[_Iterable[str]] = ..., net_member_order_ids: _Optional[_Iterable[str]] = ..., value_date: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ProposeOrderResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class RecordOrderParams(_message.Message):
    __slots__ = ("account_id", "instrument_id", "sleeve", "side", "quantity", "order_type", "limit_price", "time_in_force", "venue_order_id", "origin", "idempotency_key", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_FORCE_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORIGIN_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    instrument_id: str
    sleeve: str
    side: Side
    quantity: Decimal
    order_type: OrderType
    limit_price: Money
    time_in_force: TimeInForce
    venue_order_id: str
    origin: OrderOrigin
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., sleeve: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., order_type: _Optional[_Union[OrderType, str]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., time_in_force: _Optional[_Union[TimeInForce, str]] = ..., venue_order_id: _Optional[str] = ..., origin: _Optional[_Union[OrderOrigin, str]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordOrderResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class RequestOrderChangeParams(_message.Message):
    __slots__ = ("order_id", "change", "reason", "idempotency_key", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CHANGE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    change: OrderChange
    reason: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., change: _Optional[_Union[OrderChange, _Mapping]] = ..., reason: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RequestOrderChangeResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class RecordCheckParams(_message.Message):
    __slots__ = ("order_id", "order_version", "placement_id", "verdict", "rule", "note", "idempotency_key", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_VERSION_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERDICT_FIELD_NUMBER: _ClassVar[int]
    RULE_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    order_version: int
    placement_id: str
    verdict: CheckVerdict
    rule: str
    note: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., order_version: _Optional[int] = ..., placement_id: _Optional[str] = ..., verdict: _Optional[_Union[CheckVerdict, str]] = ..., rule: _Optional[str] = ..., note: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordCheckResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class DecideApprovalParams(_message.Message):
    __slots__ = ("order_id", "decision", "reason", "idempotency_key", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    DECISION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    decision: ApprovalDecision
    reason: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., decision: _Optional[_Union[ApprovalDecision, str]] = ..., reason: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class DecideApprovalResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class ReleaseOrderParams(_message.Message):
    __slots__ = ("order_id", "idempotency_key", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReleaseOrderResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class SetWorkingConditionParams(_message.Message):
    __slots__ = ("order_id", "condition", "set", "reason", "idempotency_key", "hold_cause", "stale_reference", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    SET_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    HOLD_CAUSE_FIELD_NUMBER: _ClassVar[int]
    STALE_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    condition: OrderCondition
    set: bool
    reason: str
    idempotency_key: str
    hold_cause: HoldCause
    stale_reference: StaleReference
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., condition: _Optional[_Union[OrderCondition, str]] = ..., set: bool = ..., reason: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., hold_cause: _Optional[_Union[HoldCause, str]] = ..., stale_reference: _Optional[_Union[StaleReference, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class SetWorkingConditionResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class CreatePlacementParams(_message.Message):
    __slots__ = ("order_id", "connectivity_instance_id", "venue_account_code", "quantity", "limit_price", "time_in_force", "strategy", "destination", "route_type", "handling_instructions", "rfq_id", "axe_id", "idempotency_key", "placement_type", "counterparty_contact", "agreed_at_ns", "agreed_precision", "stale_reference", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CONNECTIVITY_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_FORCE_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    ROUTE_TYPE_FIELD_NUMBER: _ClassVar[int]
    HANDLING_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    RFQ_ID_FIELD_NUMBER: _ClassVar[int]
    AXE_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    COUNTERPARTY_CONTACT_FIELD_NUMBER: _ClassVar[int]
    AGREED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    AGREED_PRECISION_FIELD_NUMBER: _ClassVar[int]
    STALE_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    connectivity_instance_id: str
    venue_account_code: str
    quantity: Decimal
    limit_price: Money
    time_in_force: TimeInForce
    strategy: StrategyInstruction
    destination: str
    route_type: RouteType
    handling_instructions: _containers.RepeatedScalarFieldContainer[str]
    rfq_id: str
    axe_id: str
    idempotency_key: str
    placement_type: PlacementType
    counterparty_contact: str
    agreed_at_ns: int
    agreed_precision: TimePrecision
    stale_reference: StaleReference
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., connectivity_instance_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., time_in_force: _Optional[_Union[TimeInForce, str]] = ..., strategy: _Optional[_Union[StrategyInstruction, _Mapping]] = ..., destination: _Optional[str] = ..., route_type: _Optional[_Union[RouteType, str]] = ..., handling_instructions: _Optional[_Iterable[str]] = ..., rfq_id: _Optional[str] = ..., axe_id: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., placement_type: _Optional[_Union[PlacementType, str]] = ..., counterparty_contact: _Optional[str] = ..., agreed_at_ns: _Optional[int] = ..., agreed_precision: _Optional[_Union[TimePrecision, str]] = ..., stale_reference: _Optional[_Union[StaleReference, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class CreatePlacementResult(_message.Message):
    __slots__ = ("placement", "entry", "journal", "change_request_id")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class RequestPlacementChangeParams(_message.Message):
    __slots__ = ("placement_id", "change", "reason", "cause", "idempotency_key", "acting_for")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    CHANGE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    change: PlacementChange
    reason: str
    cause: EntryMeta
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, placement_id: _Optional[str] = ..., change: _Optional[_Union[PlacementChange, _Mapping]] = ..., reason: _Optional[str] = ..., cause: _Optional[_Union[EntryMeta, _Mapping]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RequestPlacementChangeResult(_message.Message):
    __slots__ = ("placement", "entry", "journal", "change_request_id")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class ReportPlacementParams(_message.Message):
    __slots__ = ("placement_id", "event", "venue_order_id", "routed_at_ns", "routed_precision", "rejection_reason", "rejection_as_reported", "unknown_reason", "status_as_reported", "restatement_reason", "quantity", "limit_price", "raw_record", "acting_for")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ROUTED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ROUTED_PRECISION_FIELD_NUMBER: _ClassVar[int]
    REJECTION_REASON_FIELD_NUMBER: _ClassVar[int]
    REJECTION_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_REASON_FIELD_NUMBER: _ClassVar[int]
    STATUS_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    RESTATEMENT_REASON_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    event: PlacementEvent
    venue_order_id: str
    routed_at_ns: int
    routed_precision: TimePrecision
    rejection_reason: RejectionReason
    rejection_as_reported: AsReported
    unknown_reason: UnknownReason
    status_as_reported: AsReported
    restatement_reason: RestatementReason
    quantity: Decimal
    limit_price: Money
    raw_record: RawRecordRef
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, placement_id: _Optional[str] = ..., event: _Optional[_Union[PlacementEvent, str]] = ..., venue_order_id: _Optional[str] = ..., routed_at_ns: _Optional[int] = ..., routed_precision: _Optional[_Union[TimePrecision, str]] = ..., rejection_reason: _Optional[_Union[RejectionReason, str]] = ..., rejection_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., unknown_reason: _Optional[_Union[UnknownReason, str]] = ..., status_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., restatement_reason: _Optional[_Union[RestatementReason, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReportPlacementResult(_message.Message):
    __slots__ = ("placement", "execution", "order", "charge", "unplaced", "entry", "journal")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    CHARGE_FIELD_NUMBER: _ClassVar[int]
    UNPLACED_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    execution: Execution
    order: Order
    charge: Charge
    unplaced: UnplacedFact
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., execution: _Optional[_Union[Execution, _Mapping]] = ..., order: _Optional[_Union[Order, _Mapping]] = ..., charge: _Optional[_Union[Charge, _Mapping]] = ..., unplaced: _Optional[_Union[UnplacedFact, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ReportExecutionParams(_message.Message):
    __slots__ = ("placement_id", "order_id", "account_id", "venue_account_code", "venue_execution_id", "kind", "source", "quantity", "price", "trade_time_ns", "trade_date", "finality", "settlement_date", "computed_settlement_date", "settlement_date_basis", "fees", "supersedes", "venue_id", "uti", "prior_uti", "upi", "given_up_to", "trade_chain_reference", "settlement_counterparty", "raw_record", "idempotency_key", "effective_date", "counterparty", "liquidity_indicator", "uti_generated_by", "instrument_id", "side", "venue_order_id", "venue_client_order_id", "cross_rate_source", "acting_for")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    VENUE_EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    TRADE_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    FINALITY_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    COMPUTED_SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_BASIS_FIELD_NUMBER: _ClassVar[int]
    FEES_FIELD_NUMBER: _ClassVar[int]
    SUPERSEDES_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    UTI_FIELD_NUMBER: _ClassVar[int]
    PRIOR_UTI_FIELD_NUMBER: _ClassVar[int]
    UPI_FIELD_NUMBER: _ClassVar[int]
    GIVEN_UP_TO_FIELD_NUMBER: _ClassVar[int]
    TRADE_CHAIN_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_COUNTERPARTY_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    COUNTERPARTY_FIELD_NUMBER: _ClassVar[int]
    LIQUIDITY_INDICATOR_FIELD_NUMBER: _ClassVar[int]
    UTI_GENERATED_BY_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_CLIENT_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CROSS_RATE_SOURCE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    order_id: str
    account_id: str
    venue_account_code: str
    venue_execution_id: str
    kind: ExecutionKind
    source: ExecutionSource
    quantity: Decimal
    price: Money
    trade_time_ns: int
    trade_date: str
    finality: Finality
    settlement_date: str
    computed_settlement_date: str
    settlement_date_basis: DateBasis
    fees: _containers.RepeatedCompositeFieldContainer[Fee]
    supersedes: str
    venue_id: str
    uti: str
    prior_uti: str
    upi: str
    given_up_to: str
    trade_chain_reference: str
    settlement_counterparty: str
    raw_record: RawRecordRef
    idempotency_key: str
    effective_date: str
    counterparty: Party
    liquidity_indicator: LiquidityIndicator
    uti_generated_by: str
    instrument_id: str
    side: Side
    venue_order_id: str
    venue_client_order_id: str
    cross_rate_source: CrossRateSource
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, placement_id: _Optional[str] = ..., order_id: _Optional[str] = ..., account_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., venue_execution_id: _Optional[str] = ..., kind: _Optional[_Union[ExecutionKind, str]] = ..., source: _Optional[_Union[ExecutionSource, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., trade_time_ns: _Optional[int] = ..., trade_date: _Optional[str] = ..., finality: _Optional[_Union[Finality, _Mapping]] = ..., settlement_date: _Optional[str] = ..., computed_settlement_date: _Optional[str] = ..., settlement_date_basis: _Optional[_Union[DateBasis, _Mapping]] = ..., fees: _Optional[_Iterable[_Union[Fee, _Mapping]]] = ..., supersedes: _Optional[str] = ..., venue_id: _Optional[str] = ..., uti: _Optional[str] = ..., prior_uti: _Optional[str] = ..., upi: _Optional[str] = ..., given_up_to: _Optional[str] = ..., trade_chain_reference: _Optional[str] = ..., settlement_counterparty: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., idempotency_key: _Optional[str] = ..., effective_date: _Optional[str] = ..., counterparty: _Optional[_Union[Party, _Mapping]] = ..., liquidity_indicator: _Optional[_Union[LiquidityIndicator, str]] = ..., uti_generated_by: _Optional[str] = ..., instrument_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., venue_order_id: _Optional[str] = ..., venue_client_order_id: _Optional[str] = ..., cross_rate_source: _Optional[_Union[CrossRateSource, str]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReportExecutionResult(_message.Message):
    __slots__ = ("placement", "execution", "order", "charge", "unplaced", "entry", "journal")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    CHARGE_FIELD_NUMBER: _ClassVar[int]
    UNPLACED_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    execution: Execution
    order: Order
    charge: Charge
    unplaced: UnplacedFact
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., execution: _Optional[_Union[Execution, _Mapping]] = ..., order: _Optional[_Union[Order, _Mapping]] = ..., charge: _Optional[_Union[Charge, _Mapping]] = ..., unplaced: _Optional[_Union[UnplacedFact, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ReportChargeParams(_message.Message):
    __slots__ = ("placement_id", "fee", "trade_date", "settlement_date", "raw_record", "acting_for")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    FEE_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    fee: Fee
    trade_date: str
    settlement_date: str
    raw_record: RawRecordRef
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, placement_id: _Optional[str] = ..., fee: _Optional[_Union[Fee, _Mapping]] = ..., trade_date: _Optional[str] = ..., settlement_date: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReportChargeResult(_message.Message):
    __slots__ = ("placement", "execution", "order", "charge", "unplaced", "entry", "journal")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    CHARGE_FIELD_NUMBER: _ClassVar[int]
    UNPLACED_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    execution: Execution
    order: Order
    charge: Charge
    unplaced: UnplacedFact
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., execution: _Optional[_Union[Execution, _Mapping]] = ..., order: _Optional[_Union[Order, _Mapping]] = ..., charge: _Optional[_Union[Charge, _Mapping]] = ..., unplaced: _Optional[_Union[UnplacedFact, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class AcknowledgeFlagParams(_message.Message):
    __slots__ = ("order_id", "condition", "reason", "idempotency_key", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    condition: OrderCondition
    reason: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., condition: _Optional[_Union[OrderCondition, str]] = ..., reason: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class AcknowledgeFlagResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class ListTradingInstructionsParams(_message.Message):
    __slots__ = ("since", "page_size", "cursor")
    SINCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    since: Watermark
    page_size: int
    cursor: str
    def __init__(self, since: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListTradingInstructionsResult(_message.Message):
    __slots__ = ("instructions", "control_sequence", "as_of", "next_cursor")
    INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    CONTROL_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    instructions: _containers.RepeatedCompositeFieldContainer[TradingInstruction]
    control_sequence: int
    as_of: Watermark
    next_cursor: str
    def __init__(self, instructions: _Optional[_Iterable[_Union[TradingInstruction, _Mapping]]] = ..., control_sequence: _Optional[int] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ListOrdersParams(_message.Message):
    __slots__ = ("account_id", "since", "page_size", "cursor", "execution_state")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_STATE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    since: Watermark
    page_size: int
    cursor: str
    execution_state: ExecutionState
    def __init__(self, account_id: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ..., execution_state: _Optional[_Union[ExecutionState, str]] = ...) -> None: ...

class ListOrdersResult(_message.Message):
    __slots__ = ("orders", "as_of", "next_cursor", "placements", "executions", "unplaced_facts")
    ORDERS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    PLACEMENTS_FIELD_NUMBER: _ClassVar[int]
    EXECUTIONS_FIELD_NUMBER: _ClassVar[int]
    UNPLACED_FACTS_FIELD_NUMBER: _ClassVar[int]
    orders: _containers.RepeatedCompositeFieldContainer[Order]
    as_of: Watermark
    next_cursor: str
    placements: _containers.RepeatedCompositeFieldContainer[Placement]
    executions: _containers.RepeatedCompositeFieldContainer[Execution]
    unplaced_facts: _containers.RepeatedCompositeFieldContainer[UnplacedFact]
    def __init__(self, orders: _Optional[_Iterable[_Union[Order, _Mapping]]] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ..., placements: _Optional[_Iterable[_Union[Placement, _Mapping]]] = ..., executions: _Optional[_Iterable[_Union[Execution, _Mapping]]] = ..., unplaced_facts: _Optional[_Iterable[_Union[UnplacedFact, _Mapping]]] = ...) -> None: ...

class ReadOrderHistoryParams(_message.Message):
    __slots__ = ("account_id", "order_id", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    order_id: str
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., order_id: _Optional[str] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ReadOrderHistoryResult(_message.Message):
    __slots__ = ("entries", "next_cursor")
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[EntryMeta]
    next_cursor: str
    def __init__(self, entries: _Optional[_Iterable[_Union[EntryMeta, _Mapping]]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class RecordLocateParams(_message.Message):
    __slots__ = ("venue_account_code", "instrument_id", "quantity_requested", "answer", "locate_record_id", "raw_record", "idempotency_key", "acting_for")
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_REQUESTED_FIELD_NUMBER: _ClassVar[int]
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    LOCATE_RECORD_ID_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    venue_account_code: str
    instrument_id: str
    quantity_requested: Decimal
    answer: LocateAnswer
    locate_record_id: str
    raw_record: RawRecordRef
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, venue_account_code: _Optional[str] = ..., instrument_id: _Optional[str] = ..., quantity_requested: _Optional[_Union[Decimal, _Mapping]] = ..., answer: _Optional[_Union[LocateAnswer, _Mapping]] = ..., locate_record_id: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordLocateResult(_message.Message):
    __slots__ = ("locate", "entry", "journal")
    LOCATE_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    locate: Locate
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, locate: _Optional[_Union[Locate, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ListLocatesParams(_message.Message):
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

class ListLocatesResult(_message.Message):
    __slots__ = ("locates", "as_of", "next_cursor")
    LOCATES_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    locates: _containers.RepeatedCompositeFieldContainer[Locate]
    as_of: Watermark
    next_cursor: str
    def __init__(self, locates: _Optional[_Iterable[_Union[Locate, _Mapping]]] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class RecordLocateUseParams(_message.Message):
    __slots__ = ("locate_record_id", "use", "idempotency_key", "acting_for")
    LOCATE_RECORD_ID_FIELD_NUMBER: _ClassVar[int]
    USE_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    locate_record_id: str
    use: LocateUse
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, locate_record_id: _Optional[str] = ..., use: _Optional[_Union[LocateUse, _Mapping]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordLocateUseResult(_message.Message):
    __slots__ = ("locate", "entry", "journal")
    LOCATE_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    locate: Locate
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, locate: _Optional[_Union[Locate, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ReportVenueCatalogueParams(_message.Message):
    __slots__ = ("catalogue",)
    CATALOGUE_FIELD_NUMBER: _ClassVar[int]
    catalogue: VenueCatalogue
    def __init__(self, catalogue: _Optional[_Union[VenueCatalogue, _Mapping]] = ...) -> None: ...

class ReadVenueCatalogueParams(_message.Message):
    __slots__ = ("connectivity_instance_id", "venue_account_code", "acting_for")
    CONNECTIVITY_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    connectivity_instance_id: str
    venue_account_code: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, connectivity_instance_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReadVenueCatalogueResult(_message.Message):
    __slots__ = ("catalogue",)
    CATALOGUE_FIELD_NUMBER: _ClassVar[int]
    catalogue: VenueCatalogue
    def __init__(self, catalogue: _Optional[_Union[VenueCatalogue, _Mapping]] = ...) -> None: ...

class MapVenueAccountParams(_message.Message):
    __slots__ = ("connectivity_instance_id", "venue_account_code", "account_id", "acting_for")
    CONNECTIVITY_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    connectivity_instance_id: str
    venue_account_code: str
    account_id: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, connectivity_instance_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., account_id: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class MapVenueAccountResult(_message.Message):
    __slots__ = ("ems_instance_id", "mappings")
    EMS_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    MAPPINGS_FIELD_NUMBER: _ClassVar[int]
    ems_instance_id: str
    mappings: _containers.RepeatedCompositeFieldContainer[VenueAccountMapping]
    def __init__(self, ems_instance_id: _Optional[str] = ..., mappings: _Optional[_Iterable[_Union[VenueAccountMapping, _Mapping]]] = ...) -> None: ...

class AcceptExecutionParams(_message.Message):
    __slots__ = ("execution_ids", "order_id", "new_order", "note", "acting_for")
    EXECUTION_IDS_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_ORDER_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    execution_ids: _containers.RepeatedScalarFieldContainer[str]
    order_id: str
    new_order: NewOrderFromExecutions
    note: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, execution_ids: _Optional[_Iterable[str]] = ..., order_id: _Optional[str] = ..., new_order: _Optional[_Union[NewOrderFromExecutions, _Mapping]] = ..., note: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class AcceptExecutionResult(_message.Message):
    __slots__ = ("executions", "order", "placement", "journal")
    EXECUTIONS_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    executions: _containers.RepeatedCompositeFieldContainer[Execution]
    order: Order
    placement: Placement
    journal: JournalRef
    def __init__(self, executions: _Optional[_Iterable[_Union[Execution, _Mapping]]] = ..., order: _Optional[_Union[Order, _Mapping]] = ..., placement: _Optional[_Union[Placement, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class DontKnowExecutionParams(_message.Message):
    __slots__ = ("execution_ids", "reason", "text", "acting_for")
    EXECUTION_IDS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    execution_ids: _containers.RepeatedScalarFieldContainer[str]
    reason: DkReason
    text: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, execution_ids: _Optional[_Iterable[str]] = ..., reason: _Optional[_Union[DkReason, str]] = ..., text: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class DontKnowExecutionResult(_message.Message):
    __slots__ = ("executions", "journal")
    EXECUTIONS_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    executions: _containers.RepeatedCompositeFieldContainer[Execution]
    journal: JournalRef
    def __init__(self, executions: _Optional[_Iterable[_Union[Execution, _Mapping]]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ReportValueDateRollParams(_message.Message):
    __slots__ = ("venue_account_code", "pair", "from_value_date", "to_value_date", "value_date_basis", "rolled_at_ns", "charge_ids", "raw_record", "idempotency_key", "acting_for")
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    PAIR_FIELD_NUMBER: _ClassVar[int]
    FROM_VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    TO_VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_BASIS_FIELD_NUMBER: _ClassVar[int]
    ROLLED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CHARGE_IDS_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    venue_account_code: str
    pair: _containers.RepeatedScalarFieldContainer[str]
    from_value_date: str
    to_value_date: str
    value_date_basis: DateBasis
    rolled_at_ns: int
    charge_ids: _containers.RepeatedScalarFieldContainer[str]
    raw_record: RawRecordRef
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, venue_account_code: _Optional[str] = ..., pair: _Optional[_Iterable[str]] = ..., from_value_date: _Optional[str] = ..., to_value_date: _Optional[str] = ..., value_date_basis: _Optional[_Union[DateBasis, _Mapping]] = ..., rolled_at_ns: _Optional[int] = ..., charge_ids: _Optional[_Iterable[str]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReportValueDateRollResult(_message.Message):
    __slots__ = ("placement", "execution", "order", "charge", "unplaced", "entry", "journal")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    CHARGE_FIELD_NUMBER: _ClassVar[int]
    UNPLACED_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    execution: Execution
    order: Order
    charge: Charge
    unplaced: UnplacedFact
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., execution: _Optional[_Union[Execution, _Mapping]] = ..., order: _Optional[_Union[Order, _Mapping]] = ..., charge: _Optional[_Union[Charge, _Mapping]] = ..., unplaced: _Optional[_Union[UnplacedFact, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class SetAllocationInstructionParams(_message.Message):
    __slots__ = ("order_id", "allocation_instruction", "reason", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    allocation_instruction: AllocationInstruction
    reason: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., allocation_instruction: _Optional[_Union[AllocationInstruction, _Mapping]] = ..., reason: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class SetAllocationInstructionResult(_message.Message):
    __slots__ = ("order", "entry", "journal", "change_request_id")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    order: Order
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class BookOrderParams(_message.Message):
    __slots__ = ("order_id", "execution_ids", "allocations", "hand_off", "acting_for")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_IDS_FIELD_NUMBER: _ClassVar[int]
    ALLOCATIONS_FIELD_NUMBER: _ClassVar[int]
    HAND_OFF_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    execution_ids: _containers.RepeatedScalarFieldContainer[str]
    allocations: _containers.RepeatedCompositeFieldContainer[Allocation]
    hand_off: bool
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, order_id: _Optional[str] = ..., execution_ids: _Optional[_Iterable[str]] = ..., allocations: _Optional[_Iterable[_Union[Allocation, _Mapping]]] = ..., hand_off: bool = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class BookOrderResult(_message.Message):
    __slots__ = ("booking", "entry", "journal")
    BOOKING_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    booking: Booking
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, booking: _Optional[_Union[Booking, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class HandOffBookingParams(_message.Message):
    __slots__ = ("booking_id", "close", "acting_for")
    BOOKING_ID_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    booking_id: str
    close: bool
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, booking_id: _Optional[str] = ..., close: bool = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class HandOffBookingResult(_message.Message):
    __slots__ = ("booking", "entry", "journal")
    BOOKING_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    booking: Booking
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, booking: _Optional[_Union[Booking, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class CorrectBookingParams(_message.Message):
    __slots__ = ("booking_id", "kind", "allocations", "effective_date", "reason", "acting_for")
    BOOKING_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    ALLOCATIONS_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    booking_id: str
    kind: BookingCorrectionKind
    allocations: _containers.RepeatedCompositeFieldContainer[Allocation]
    effective_date: str
    reason: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, booking_id: _Optional[str] = ..., kind: _Optional[_Union[BookingCorrectionKind, str]] = ..., allocations: _Optional[_Iterable[_Union[Allocation, _Mapping]]] = ..., effective_date: _Optional[str] = ..., reason: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class CorrectBookingResult(_message.Message):
    __slots__ = ("booking", "entry", "journal")
    BOOKING_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    booking: Booking
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, booking: _Optional[_Union[Booking, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ListBookingsParams(_message.Message):
    __slots__ = ("account_id", "since", "state", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    since: Watermark
    state: BookingState
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., state: _Optional[_Union[BookingState, str]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListBookingsResult(_message.Message):
    __slots__ = ("bookings", "as_of", "next_cursor")
    BOOKINGS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    bookings: _containers.RepeatedCompositeFieldContainer[Booking]
    as_of: Watermark
    next_cursor: str
    def __init__(self, bookings: _Optional[_Iterable[_Union[Booking, _Mapping]]] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ReportGiveUpParams(_message.Message):
    __slots__ = ("execution_id", "allocation_id", "answer", "prime_reference", "reason", "raw_record", "acting_for")
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    PRIME_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    execution_id: str
    allocation_id: str
    answer: GiveUpAnswer
    prime_reference: str
    reason: str
    raw_record: RawRecordRef
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, execution_id: _Optional[str] = ..., allocation_id: _Optional[str] = ..., answer: _Optional[_Union[GiveUpAnswer, str]] = ..., prime_reference: _Optional[str] = ..., reason: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReportGiveUpResult(_message.Message):
    __slots__ = ("placement", "execution", "order", "charge", "unplaced", "entry", "journal")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    CHARGE_FIELD_NUMBER: _ClassVar[int]
    UNPLACED_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    execution: Execution
    order: Order
    charge: Charge
    unplaced: UnplacedFact
    entry: EntryMeta
    journal: JournalRef
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., execution: _Optional[_Union[Execution, _Mapping]] = ..., order: _Optional[_Union[Order, _Mapping]] = ..., charge: _Optional[_Union[Charge, _Mapping]] = ..., unplaced: _Optional[_Union[UnplacedFact, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class RecordSleeveCrossParams(_message.Message):
    __slots__ = ("sleeve_cross", "acting_for")
    SLEEVE_CROSS_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    sleeve_cross: SleeveCross
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, sleeve_cross: _Optional[_Union[SleeveCross, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordSleeveCrossResult(_message.Message):
    __slots__ = ("sleeve_cross", "journal")
    SLEEVE_CROSS_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    sleeve_cross: SleeveCross
    journal: JournalRef
    def __init__(self, sleeve_cross: _Optional[_Union[SleeveCross, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class RaiseAlertParams(_message.Message):
    __slots__ = ("account_id", "kind", "reason", "subject", "acting_for")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    kind: AlertKind
    reason: str
    subject: AlertSubject
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, account_id: _Optional[str] = ..., kind: _Optional[_Union[AlertKind, str]] = ..., reason: _Optional[str] = ..., subject: _Optional[_Union[AlertSubject, _Mapping]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RaiseAlertResult(_message.Message):
    __slots__ = ("alert", "journal")
    ALERT_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    alert: Alert
    journal: JournalRef
    def __init__(self, alert: _Optional[_Union[Alert, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class AcknowledgeAlertParams(_message.Message):
    __slots__ = ("alert_id", "reason", "acting_for")
    ALERT_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    alert_id: str
    reason: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, alert_id: _Optional[str] = ..., reason: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class AcknowledgeAlertResult(_message.Message):
    __slots__ = ("alert", "journal")
    ALERT_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    alert: Alert
    journal: JournalRef
    def __init__(self, alert: _Optional[_Union[Alert, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ListAlertsParams(_message.Message):
    __slots__ = ("account_id", "state", "since", "page_size", "cursor", "kind")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    SINCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    state: AlertState
    since: Watermark
    page_size: int
    cursor: str
    kind: AlertKind
    def __init__(self, account_id: _Optional[str] = ..., state: _Optional[_Union[AlertState, str]] = ..., since: _Optional[_Union[Watermark, _Mapping]] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ..., kind: _Optional[_Union[AlertKind, str]] = ...) -> None: ...

class ListAlertsResult(_message.Message):
    __slots__ = ("alerts", "as_of", "next_cursor")
    ALERTS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    alerts: _containers.RepeatedCompositeFieldContainer[Alert]
    as_of: Watermark
    next_cursor: str
    def __init__(self, alerts: _Optional[_Iterable[_Union[Alert, _Mapping]]] = ..., as_of: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ReadLocalRecordOrdersParams(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ReadLocalRecordOrdersResult(_message.Message):
    __slots__ = ("allows_local_record_orders", "open_order_count")
    ALLOWS_LOCAL_RECORD_ORDERS_FIELD_NUMBER: _ClassVar[int]
    OPEN_ORDER_COUNT_FIELD_NUMBER: _ClassVar[int]
    allows_local_record_orders: bool
    open_order_count: int
    def __init__(self, allows_local_record_orders: bool = ..., open_order_count: _Optional[int] = ...) -> None: ...

class ResolveVenueParams(_message.Message):
    __slots__ = ("identifiers", "as_of_ns", "venue_id")
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    as_of_ns: int
    venue_id: str
    def __init__(self, identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., as_of_ns: _Optional[int] = ..., venue_id: _Optional[str] = ...) -> None: ...

class ResolveVenueResult(_message.Message):
    __slots__ = ("found", "venue", "miss_reason")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    VENUE_FIELD_NUMBER: _ClassVar[int]
    MISS_REASON_FIELD_NUMBER: _ClassVar[int]
    found: bool
    venue: VenueRecord
    miss_reason: MissReason
    def __init__(self, found: bool = ..., venue: _Optional[_Union[VenueRecord, _Mapping]] = ..., miss_reason: _Optional[_Union[MissReason, str]] = ...) -> None: ...

class ReportMissingVenueParams(_message.Message):
    __slots__ = ("source", "identifiers", "as_of_ns", "reason", "observed_at_ns")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    source: str
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    as_of_ns: int
    reason: MissReason
    observed_at_ns: int
    def __init__(self, source: _Optional[str] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., as_of_ns: _Optional[int] = ..., reason: _Optional[_Union[MissReason, str]] = ..., observed_at_ns: _Optional[int] = ...) -> None: ...

class ReadCalendarParams(_message.Message):
    __slots__ = ("calendar_id", "from_date", "to_date", "as_of_ns")
    CALENDAR_ID_FIELD_NUMBER: _ClassVar[int]
    FROM_DATE_FIELD_NUMBER: _ClassVar[int]
    TO_DATE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    calendar_id: str
    from_date: str
    to_date: str
    as_of_ns: int
    def __init__(self, calendar_id: _Optional[str] = ..., from_date: _Optional[str] = ..., to_date: _Optional[str] = ..., as_of_ns: _Optional[int] = ...) -> None: ...

class ReadCalendarResult(_message.Message):
    __slots__ = ("found", "calendar_id", "version", "days", "weekends", "coverage", "sources", "trading_sessions")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    CALENDAR_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    DAYS_FIELD_NUMBER: _ClassVar[int]
    WEEKENDS_FIELD_NUMBER: _ClassVar[int]
    COVERAGE_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    TRADING_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    found: bool
    calendar_id: str
    version: int
    days: _containers.RepeatedCompositeFieldContainer[CalendarDay]
    weekends: _containers.RepeatedCompositeFieldContainer[CalendarWeekend]
    coverage: CalendarCoverage
    sources: _containers.RepeatedCompositeFieldContainer[CalendarSource]
    trading_sessions: TradingSessions
    def __init__(self, found: bool = ..., calendar_id: _Optional[str] = ..., version: _Optional[int] = ..., days: _Optional[_Iterable[_Union[CalendarDay, _Mapping]]] = ..., weekends: _Optional[_Iterable[_Union[CalendarWeekend, _Mapping]]] = ..., coverage: _Optional[_Union[CalendarCoverage, _Mapping]] = ..., sources: _Optional[_Iterable[_Union[CalendarSource, _Mapping]]] = ..., trading_sessions: _Optional[_Union[TradingSessions, _Mapping]] = ...) -> None: ...

class ComputeDateParams(_message.Message):
    __slots__ = ("settlement", "spot", "tenor", "roll", "business_day", "as_of_ns")
    SETTLEMENT_FIELD_NUMBER: _ClassVar[int]
    SPOT_FIELD_NUMBER: _ClassVar[int]
    TENOR_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DAY_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    settlement: SettlementDateInputs
    spot: SpotDateInputs
    tenor: TenorDateInputs
    roll: RollInputs
    business_day: BusinessDayInputs
    as_of_ns: int
    def __init__(self, settlement: _Optional[_Union[SettlementDateInputs, _Mapping]] = ..., spot: _Optional[_Union[SpotDateInputs, _Mapping]] = ..., tenor: _Optional[_Union[TenorDateInputs, _Mapping]] = ..., roll: _Optional[_Union[RollInputs, _Mapping]] = ..., business_day: _Optional[_Union[BusinessDayInputs, _Mapping]] = ..., as_of_ns: _Optional[int] = ...) -> None: ...

class ComputeDateResult(_message.Message):
    __slots__ = ("date", "outcome", "basis", "business_day")
    DATE_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    BASIS_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DAY_FIELD_NUMBER: _ClassVar[int]
    date: str
    outcome: DateOutcome
    basis: DateBasis
    business_day: bool
    def __init__(self, date: _Optional[str] = ..., outcome: _Optional[_Union[DateOutcome, str]] = ..., basis: _Optional[_Union[DateBasis, _Mapping]] = ..., business_day: bool = ...) -> None: ...

class ListReplacementsParams(_message.Message):
    __slots__ = ("after_sequence",)
    AFTER_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    after_sequence: int
    def __init__(self, after_sequence: _Optional[int] = ...) -> None: ...

class ListReplacementsResult(_message.Message):
    __slots__ = ("replacements", "sequence")
    REPLACEMENTS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    replacements: _containers.RepeatedCompositeFieldContainer[InstrumentReplacedEvent]
    sequence: int
    def __init__(self, replacements: _Optional[_Iterable[_Union[InstrumentReplacedEvent, _Mapping]]] = ..., sequence: _Optional[int] = ...) -> None: ...

class OfferTemplateFieldsParams(_message.Message):
    __slots__ = ("instrument_id", "template_id", "template_version", "fields", "acting_for")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    template_id: str
    template_version: str
    fields: _containers.RepeatedCompositeFieldContainer[TemplateFieldValue]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, instrument_id: _Optional[str] = ..., template_id: _Optional[str] = ..., template_version: _Optional[str] = ..., fields: _Optional[_Iterable[_Union[TemplateFieldValue, _Mapping]]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class OfferTemplateFieldsResult(_message.Message):
    __slots__ = ("instrument",)
    INSTRUMENT_FIELD_NUMBER: _ClassVar[int]
    instrument: InstrumentRecord
    def __init__(self, instrument: _Optional[_Union[InstrumentRecord, _Mapping]] = ...) -> None: ...

class ListTemplatesParams(_message.Message):
    __slots__ = ("asset_class",)
    ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    asset_class: AssetClass
    def __init__(self, asset_class: _Optional[_Union[AssetClass, str]] = ...) -> None: ...

class ListTemplatesResult(_message.Message):
    __slots__ = ("templates",)
    TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    templates: _containers.RepeatedCompositeFieldContainer[SecurityTemplate]
    def __init__(self, templates: _Optional[_Iterable[_Union[SecurityTemplate, _Mapping]]] = ...) -> None: ...

class ReadTemplateParams(_message.Message):
    __slots__ = ("template_id", "template_version")
    TEMPLATE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    template_id: str
    template_version: str
    def __init__(self, template_id: _Optional[str] = ..., template_version: _Optional[str] = ...) -> None: ...

class ReadTemplateResult(_message.Message):
    __slots__ = ("template",)
    TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    template: SecurityTemplate
    def __init__(self, template: _Optional[_Union[SecurityTemplate, _Mapping]] = ...) -> None: ...

class RecordPricesParams(_message.Message):
    __slots__ = ("prices", "want_id", "acting_for")
    PRICES_FIELD_NUMBER: _ClassVar[int]
    WANT_ID_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    prices: _containers.RepeatedCompositeFieldContainer[Price]
    want_id: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, prices: _Optional[_Iterable[_Union[Price, _Mapping]]] = ..., want_id: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordPricesResult(_message.Message):
    __slots__ = ("recorded", "restated", "unchanged", "watermark")
    RECORDED_FIELD_NUMBER: _ClassVar[int]
    RESTATED_FIELD_NUMBER: _ClassVar[int]
    UNCHANGED_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    recorded: int
    restated: int
    unchanged: int
    watermark: Watermark
    def __init__(self, recorded: _Optional[int] = ..., restated: _Optional[int] = ..., unchanged: _Optional[int] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class RecordBarsParams(_message.Message):
    __slots__ = ("bars", "want_id", "acting_for")
    BARS_FIELD_NUMBER: _ClassVar[int]
    WANT_ID_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    bars: _containers.RepeatedCompositeFieldContainer[Bar]
    want_id: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, bars: _Optional[_Iterable[_Union[Bar, _Mapping]]] = ..., want_id: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordBarsResult(_message.Message):
    __slots__ = ("recorded", "restated", "unchanged", "watermark")
    RECORDED_FIELD_NUMBER: _ClassVar[int]
    RESTATED_FIELD_NUMBER: _ClassVar[int]
    UNCHANGED_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    recorded: int
    restated: int
    unchanged: int
    watermark: Watermark
    def __init__(self, recorded: _Optional[int] = ..., restated: _Optional[int] = ..., unchanged: _Optional[int] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class RecordTradesParams(_message.Message):
    __slots__ = ("trades", "want_id", "acting_for")
    TRADES_FIELD_NUMBER: _ClassVar[int]
    WANT_ID_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    trades: _containers.RepeatedCompositeFieldContainer[Trade]
    want_id: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, trades: _Optional[_Iterable[_Union[Trade, _Mapping]]] = ..., want_id: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordTradesResult(_message.Message):
    __slots__ = ("recorded", "restated", "unchanged", "watermark")
    RECORDED_FIELD_NUMBER: _ClassVar[int]
    RESTATED_FIELD_NUMBER: _ClassVar[int]
    UNCHANGED_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    recorded: int
    restated: int
    unchanged: int
    watermark: Watermark
    def __init__(self, recorded: _Optional[int] = ..., restated: _Optional[int] = ..., unchanged: _Optional[int] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class RecordQuotesParams(_message.Message):
    __slots__ = ("quotes", "want_id", "acting_for")
    QUOTES_FIELD_NUMBER: _ClassVar[int]
    WANT_ID_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    quotes: _containers.RepeatedCompositeFieldContainer[Quote]
    want_id: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, quotes: _Optional[_Iterable[_Union[Quote, _Mapping]]] = ..., want_id: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordQuotesResult(_message.Message):
    __slots__ = ("recorded", "restated", "unchanged", "watermark")
    RECORDED_FIELD_NUMBER: _ClassVar[int]
    RESTATED_FIELD_NUMBER: _ClassVar[int]
    UNCHANGED_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    recorded: int
    restated: int
    unchanged: int
    watermark: Watermark
    def __init__(self, recorded: _Optional[int] = ..., restated: _Optional[int] = ..., unchanged: _Optional[int] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class RecordOutcomesParams(_message.Message):
    __slots__ = ("outcomes", "acting_for")
    OUTCOMES_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    outcomes: _containers.RepeatedCompositeFieldContainer[Outcome]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, outcomes: _Optional[_Iterable[_Union[Outcome, _Mapping]]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordOutcomesResult(_message.Message):
    __slots__ = ("recorded", "restated", "unchanged", "watermark")
    RECORDED_FIELD_NUMBER: _ClassVar[int]
    RESTATED_FIELD_NUMBER: _ClassVar[int]
    UNCHANGED_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    recorded: int
    restated: int
    unchanged: int
    watermark: Watermark
    def __init__(self, recorded: _Optional[int] = ..., restated: _Optional[int] = ..., unchanged: _Optional[int] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListPricesParams(_message.Message):
    __slots__ = ("subjects", "kinds", "sources", "at_ns", "business_date", "valid_from_ns", "valid_until_ns", "as_of_ns", "page_size", "cursor")
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    KINDS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    kinds: _containers.RepeatedScalarFieldContainer[PriceKind]
    sources: SourceChoice
    at_ns: int
    business_date: str
    valid_from_ns: int
    valid_until_ns: int
    as_of_ns: int
    page_size: int
    cursor: str
    def __init__(self, subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., kinds: _Optional[_Iterable[_Union[PriceKind, str]]] = ..., sources: _Optional[_Union[SourceChoice, _Mapping]] = ..., at_ns: _Optional[int] = ..., business_date: _Optional[str] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., as_of_ns: _Optional[int] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListPricesResult(_message.Message):
    __slots__ = ("prices", "unanswered", "datasets", "watermark", "next_cursor")
    PRICES_FIELD_NUMBER: _ClassVar[int]
    UNANSWERED_FIELD_NUMBER: _ClassVar[int]
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    prices: _containers.RepeatedCompositeFieldContainer[Price]
    unanswered: _containers.RepeatedCompositeFieldContainer[Unanswered]
    datasets: _containers.RepeatedCompositeFieldContainer[DatasetRef]
    watermark: Watermark
    next_cursor: str
    def __init__(self, prices: _Optional[_Iterable[_Union[Price, _Mapping]]] = ..., unanswered: _Optional[_Iterable[_Union[Unanswered, _Mapping]]] = ..., datasets: _Optional[_Iterable[_Union[DatasetRef, _Mapping]]] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ListBarsParams(_message.Message):
    __slots__ = ("subjects", "interval_ns", "sources", "at_ns", "business_date", "valid_from_ns", "valid_until_ns", "as_of_ns", "page_size", "cursor")
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_NS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    interval_ns: int
    sources: SourceChoice
    at_ns: int
    business_date: str
    valid_from_ns: int
    valid_until_ns: int
    as_of_ns: int
    page_size: int
    cursor: str
    def __init__(self, subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., interval_ns: _Optional[int] = ..., sources: _Optional[_Union[SourceChoice, _Mapping]] = ..., at_ns: _Optional[int] = ..., business_date: _Optional[str] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., as_of_ns: _Optional[int] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListBarsResult(_message.Message):
    __slots__ = ("bars", "unanswered", "datasets", "watermark", "next_cursor")
    BARS_FIELD_NUMBER: _ClassVar[int]
    UNANSWERED_FIELD_NUMBER: _ClassVar[int]
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    bars: _containers.RepeatedCompositeFieldContainer[Bar]
    unanswered: _containers.RepeatedCompositeFieldContainer[Unanswered]
    datasets: _containers.RepeatedCompositeFieldContainer[DatasetRef]
    watermark: Watermark
    next_cursor: str
    def __init__(self, bars: _Optional[_Iterable[_Union[Bar, _Mapping]]] = ..., unanswered: _Optional[_Iterable[_Union[Unanswered, _Mapping]]] = ..., datasets: _Optional[_Iterable[_Union[DatasetRef, _Mapping]]] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ListTradesParams(_message.Message):
    __slots__ = ("subjects", "sources", "valid_from_ns", "valid_until_ns", "after_watermark", "as_of_ns", "page_size", "cursor", "latest_recorded")
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    AFTER_WATERMARK_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    LATEST_RECORDED_FIELD_NUMBER: _ClassVar[int]
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    sources: SourceChoice
    valid_from_ns: int
    valid_until_ns: int
    after_watermark: Watermark
    as_of_ns: int
    page_size: int
    cursor: str
    latest_recorded: bool
    def __init__(self, subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., sources: _Optional[_Union[SourceChoice, _Mapping]] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., after_watermark: _Optional[_Union[Watermark, _Mapping]] = ..., as_of_ns: _Optional[int] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ..., latest_recorded: bool = ...) -> None: ...

class ListTradesResult(_message.Message):
    __slots__ = ("trades", "unanswered", "datasets", "watermark", "next_cursor")
    TRADES_FIELD_NUMBER: _ClassVar[int]
    UNANSWERED_FIELD_NUMBER: _ClassVar[int]
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    trades: _containers.RepeatedCompositeFieldContainer[Trade]
    unanswered: _containers.RepeatedCompositeFieldContainer[Unanswered]
    datasets: _containers.RepeatedCompositeFieldContainer[DatasetRef]
    watermark: Watermark
    next_cursor: str
    def __init__(self, trades: _Optional[_Iterable[_Union[Trade, _Mapping]]] = ..., unanswered: _Optional[_Iterable[_Union[Unanswered, _Mapping]]] = ..., datasets: _Optional[_Iterable[_Union[DatasetRef, _Mapping]]] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ListQuotesParams(_message.Message):
    __slots__ = ("subjects", "sources", "at_ns", "valid_from_ns", "valid_until_ns", "as_of_ns", "page_size", "cursor")
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    sources: SourceChoice
    at_ns: int
    valid_from_ns: int
    valid_until_ns: int
    as_of_ns: int
    page_size: int
    cursor: str
    def __init__(self, subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., sources: _Optional[_Union[SourceChoice, _Mapping]] = ..., at_ns: _Optional[int] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., as_of_ns: _Optional[int] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListQuotesResult(_message.Message):
    __slots__ = ("quotes", "unanswered", "datasets", "watermark", "next_cursor")
    QUOTES_FIELD_NUMBER: _ClassVar[int]
    UNANSWERED_FIELD_NUMBER: _ClassVar[int]
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    quotes: _containers.RepeatedCompositeFieldContainer[Quote]
    unanswered: _containers.RepeatedCompositeFieldContainer[Unanswered]
    datasets: _containers.RepeatedCompositeFieldContainer[DatasetRef]
    watermark: Watermark
    next_cursor: str
    def __init__(self, quotes: _Optional[_Iterable[_Union[Quote, _Mapping]]] = ..., unanswered: _Optional[_Iterable[_Union[Unanswered, _Mapping]]] = ..., datasets: _Optional[_Iterable[_Union[DatasetRef, _Mapping]]] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ListOutcomesParams(_message.Message):
    __slots__ = ("subjects", "after_watermark", "as_of_ns")
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    AFTER_WATERMARK_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    after_watermark: Watermark
    as_of_ns: int
    def __init__(self, subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., after_watermark: _Optional[_Union[Watermark, _Mapping]] = ..., as_of_ns: _Optional[int] = ...) -> None: ...

class ListOutcomesResult(_message.Message):
    __slots__ = ("outcomes", "watermark")
    OUTCOMES_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    outcomes: _containers.RepeatedCompositeFieldContainer[Outcome]
    watermark: Watermark
    def __init__(self, outcomes: _Optional[_Iterable[_Union[Outcome, _Mapping]]] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class DeclineWantParams(_message.Message):
    __slots__ = ("want_id", "subjects", "reason", "acting_for")
    WANT_ID_FIELD_NUMBER: _ClassVar[int]
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    want_id: str
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    reason: UnansweredReason
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, want_id: _Optional[str] = ..., subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., reason: _Optional[_Union[UnansweredReason, str]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class DeclineWantResult(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListDatasetsParams(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListDatasetsResult(_message.Message):
    __slots__ = ("datasets", "licences", "entitlements")
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    LICENCES_FIELD_NUMBER: _ClassVar[int]
    ENTITLEMENTS_FIELD_NUMBER: _ClassVar[int]
    datasets: _containers.RepeatedCompositeFieldContainer[DatasetRef]
    licences: _containers.RepeatedCompositeFieldContainer[DatasetLicence]
    entitlements: _containers.RepeatedCompositeFieldContainer[DatasetEntitlement]
    def __init__(self, datasets: _Optional[_Iterable[_Union[DatasetRef, _Mapping]]] = ..., licences: _Optional[_Iterable[_Union[DatasetLicence, _Mapping]]] = ..., entitlements: _Optional[_Iterable[_Union[DatasetEntitlement, _Mapping]]] = ...) -> None: ...

class RunJobParams(_message.Message):
    __slots__ = ("job",)
    JOB_FIELD_NUMBER: _ClassVar[int]
    job: Job
    def __init__(self, job: _Optional[_Union[Job, _Mapping]] = ...) -> None: ...

class RunJobResult(_message.Message):
    __slots__ = ("answered_inline", "job_id", "answer")
    ANSWERED_INLINE_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    answered_inline: bool
    job_id: str
    answer: JobAnswer
    def __init__(self, answered_inline: bool = ..., job_id: _Optional[str] = ..., answer: _Optional[_Union[JobAnswer, _Mapping]] = ...) -> None: ...

class ListMeasureDefinitionsParams(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListMeasureDefinitionsResult(_message.Message):
    __slots__ = ("definitions",)
    DEFINITIONS_FIELD_NUMBER: _ClassVar[int]
    definitions: _containers.RepeatedCompositeFieldContainer[MeasureDefinition]
    def __init__(self, definitions: _Optional[_Iterable[_Union[MeasureDefinition, _Mapping]]] = ...) -> None: ...

class ListPriceBatchesParams(_message.Message):
    __slots__ = ("after_sequence",)
    AFTER_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    after_sequence: int
    def __init__(self, after_sequence: _Optional[int] = ...) -> None: ...

class ListPriceBatchesResult(_message.Message):
    __slots__ = ("batches", "sequence")
    BATCHES_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    batches: _containers.RepeatedCompositeFieldContainer[PriceBatchRequest]
    sequence: int
    def __init__(self, batches: _Optional[_Iterable[_Union[PriceBatchRequest, _Mapping]]] = ..., sequence: _Optional[int] = ...) -> None: ...

class AnswerPriceBatchParams(_message.Message):
    __slots__ = ("batch_id", "values", "sensitivities", "acting_for")
    BATCH_ID_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    SENSITIVITIES_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    batch_id: str
    values: _containers.RepeatedCompositeFieldContainer[PricedUnit]
    sensitivities: _containers.RepeatedCompositeFieldContainer[Sensitivity]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, batch_id: _Optional[str] = ..., values: _Optional[_Iterable[_Union[PricedUnit, _Mapping]]] = ..., sensitivities: _Optional[_Iterable[_Union[Sensitivity, _Mapping]]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class AnswerPriceBatchResult(_message.Message):
    __slots__ = ("batch_id",)
    BATCH_ID_FIELD_NUMBER: _ClassVar[int]
    batch_id: str
    def __init__(self, batch_id: _Optional[str] = ...) -> None: ...

class ListFinishedJobsParams(_message.Message):
    __slots__ = ("after_sequence",)
    AFTER_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    after_sequence: int
    def __init__(self, after_sequence: _Optional[int] = ...) -> None: ...

class ListFinishedJobsResult(_message.Message):
    __slots__ = ("finished", "sequence")
    FINISHED_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    finished: _containers.RepeatedCompositeFieldContainer[JobFinishedEvent]
    sequence: int
    def __init__(self, finished: _Optional[_Iterable[_Union[JobFinishedEvent, _Mapping]]] = ..., sequence: _Optional[int] = ...) -> None: ...

class ReadJobAnswerParams(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class ReadJobAnswerResult(_message.Message):
    __slots__ = ("job_id", "figures", "not_evaluated", "provenance")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    NOT_EVALUATED_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    figures: _containers.RepeatedCompositeFieldContainer[Figure]
    not_evaluated: _containers.RepeatedCompositeFieldContainer[NotEvaluated]
    provenance: AnswerProvenance
    def __init__(self, job_id: _Optional[str] = ..., figures: _Optional[_Iterable[_Union[Figure, _Mapping]]] = ..., not_evaluated: _Optional[_Iterable[_Union[NotEvaluated, _Mapping]]] = ..., provenance: _Optional[_Union[AnswerProvenance, _Mapping]] = ...) -> None: ...

class ReportEventGroupParams(_message.Message):
    __slots__ = ("venue_id", "venue_event_ref", "title", "member_instrument_ids", "mutually_exclusive", "exhaustive", "series_id", "valid_from_ns", "raw_record", "member_bounds", "acting_for")
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_EVENT_REF_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    MEMBER_INSTRUMENT_IDS_FIELD_NUMBER: _ClassVar[int]
    MUTUALLY_EXCLUSIVE_FIELD_NUMBER: _ClassVar[int]
    EXHAUSTIVE_FIELD_NUMBER: _ClassVar[int]
    SERIES_ID_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    MEMBER_BOUNDS_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    venue_id: str
    venue_event_ref: str
    title: str
    member_instrument_ids: _containers.RepeatedScalarFieldContainer[str]
    mutually_exclusive: EventGroupFlag
    exhaustive: EventGroupFlag
    series_id: str
    valid_from_ns: int
    raw_record: RawRecordRef
    member_bounds: _containers.RepeatedCompositeFieldContainer[EventGroupMemberBound]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, venue_id: _Optional[str] = ..., venue_event_ref: _Optional[str] = ..., title: _Optional[str] = ..., member_instrument_ids: _Optional[_Iterable[str]] = ..., mutually_exclusive: _Optional[_Union[EventGroupFlag, str]] = ..., exhaustive: _Optional[_Union[EventGroupFlag, str]] = ..., series_id: _Optional[str] = ..., valid_from_ns: _Optional[int] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., member_bounds: _Optional[_Iterable[_Union[EventGroupMemberBound, _Mapping]]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReportEventGroupResult(_message.Message):
    __slots__ = ("event_group", "pending_review")
    EVENT_GROUP_FIELD_NUMBER: _ClassVar[int]
    PENDING_REVIEW_FIELD_NUMBER: _ClassVar[int]
    event_group: EventGroup
    pending_review: bool
    def __init__(self, event_group: _Optional[_Union[EventGroup, _Mapping]] = ..., pending_review: bool = ...) -> None: ...

class ListEventGroupsParams(_message.Message):
    __slots__ = ("instrument_ids", "event_group_ids", "as_of_ns", "after_sequence", "page_size", "cursor")
    INSTRUMENT_IDS_FIELD_NUMBER: _ClassVar[int]
    EVENT_GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    AFTER_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    instrument_ids: _containers.RepeatedScalarFieldContainer[str]
    event_group_ids: _containers.RepeatedScalarFieldContainer[str]
    as_of_ns: int
    after_sequence: int
    page_size: int
    cursor: str
    def __init__(self, instrument_ids: _Optional[_Iterable[str]] = ..., event_group_ids: _Optional[_Iterable[str]] = ..., as_of_ns: _Optional[int] = ..., after_sequence: _Optional[int] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListEventGroupsResult(_message.Message):
    __slots__ = ("event_groups", "sequence", "next_cursor")
    EVENT_GROUPS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    event_groups: _containers.RepeatedCompositeFieldContainer[EventGroup]
    sequence: int
    next_cursor: str
    def __init__(self, event_groups: _Optional[_Iterable[_Union[EventGroup, _Mapping]]] = ..., sequence: _Optional[int] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ReadAgentOrdersDemoOnlyParams(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ReadAgentOrdersDemoOnlyResult(_message.Message):
    __slots__ = ("agent_orders_demo_only",)
    AGENT_ORDERS_DEMO_ONLY_FIELD_NUMBER: _ClassVar[int]
    agent_orders_demo_only: bool
    def __init__(self, agent_orders_demo_only: bool = ...) -> None: ...

class QueryLakeParams(_message.Message):
    __slots__ = ("kind", "subjects", "sources", "valid_from_ns", "valid_until_ns", "from_date", "to_date", "as_of_ns", "fields", "row_limit")
    KIND_FIELD_NUMBER: _ClassVar[int]
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    FROM_DATE_FIELD_NUMBER: _ClassVar[int]
    TO_DATE_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    ROW_LIMIT_FIELD_NUMBER: _ClassVar[int]
    kind: str
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    sources: SourceChoice
    valid_from_ns: int
    valid_until_ns: int
    from_date: str
    to_date: str
    as_of_ns: int
    fields: _containers.RepeatedScalarFieldContainer[str]
    row_limit: int
    def __init__(self, kind: _Optional[str] = ..., subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., sources: _Optional[_Union[SourceChoice, _Mapping]] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., from_date: _Optional[str] = ..., to_date: _Optional[str] = ..., as_of_ns: _Optional[int] = ..., fields: _Optional[_Iterable[str]] = ..., row_limit: _Optional[int] = ...) -> None: ...

class QueryLakeResult(_message.Message):
    __slots__ = ("prices", "bars", "trades", "quotes", "outcomes", "unanswered", "datasets", "watermark", "truncated", "rates")
    PRICES_FIELD_NUMBER: _ClassVar[int]
    BARS_FIELD_NUMBER: _ClassVar[int]
    TRADES_FIELD_NUMBER: _ClassVar[int]
    QUOTES_FIELD_NUMBER: _ClassVar[int]
    OUTCOMES_FIELD_NUMBER: _ClassVar[int]
    UNANSWERED_FIELD_NUMBER: _ClassVar[int]
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    RATES_FIELD_NUMBER: _ClassVar[int]
    prices: _containers.RepeatedCompositeFieldContainer[Price]
    bars: _containers.RepeatedCompositeFieldContainer[Bar]
    trades: _containers.RepeatedCompositeFieldContainer[Trade]
    quotes: _containers.RepeatedCompositeFieldContainer[Quote]
    outcomes: _containers.RepeatedCompositeFieldContainer[Outcome]
    unanswered: _containers.RepeatedCompositeFieldContainer[Unanswered]
    datasets: _containers.RepeatedCompositeFieldContainer[DatasetRef]
    watermark: Watermark
    truncated: bool
    rates: _containers.RepeatedCompositeFieldContainer[Rate]
    def __init__(self, prices: _Optional[_Iterable[_Union[Price, _Mapping]]] = ..., bars: _Optional[_Iterable[_Union[Bar, _Mapping]]] = ..., trades: _Optional[_Iterable[_Union[Trade, _Mapping]]] = ..., quotes: _Optional[_Iterable[_Union[Quote, _Mapping]]] = ..., outcomes: _Optional[_Iterable[_Union[Outcome, _Mapping]]] = ..., unanswered: _Optional[_Iterable[_Union[Unanswered, _Mapping]]] = ..., datasets: _Optional[_Iterable[_Union[DatasetRef, _Mapping]]] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ..., truncated: bool = ..., rates: _Optional[_Iterable[_Union[Rate, _Mapping]]] = ...) -> None: ...

class ReportLatencyParams(_message.Message):
    __slots__ = ("snapshots", "acting_for")
    SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    snapshots: _containers.RepeatedCompositeFieldContainer[LatencySnapshot]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, snapshots: _Optional[_Iterable[_Union[LatencySnapshot, _Mapping]]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReportLatencyResult(_message.Message):
    __slots__ = ("accepted",)
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    accepted: int
    def __init__(self, accepted: _Optional[int] = ...) -> None: ...

class RecordRatesParams(_message.Message):
    __slots__ = ("rates", "want_id", "acting_for")
    RATES_FIELD_NUMBER: _ClassVar[int]
    WANT_ID_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    rates: _containers.RepeatedCompositeFieldContainer[Rate]
    want_id: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, rates: _Optional[_Iterable[_Union[Rate, _Mapping]]] = ..., want_id: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordRatesResult(_message.Message):
    __slots__ = ("recorded", "restated", "unchanged", "watermark")
    RECORDED_FIELD_NUMBER: _ClassVar[int]
    RESTATED_FIELD_NUMBER: _ClassVar[int]
    UNCHANGED_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    recorded: int
    restated: int
    unchanged: int
    watermark: Watermark
    def __init__(self, recorded: _Optional[int] = ..., restated: _Optional[int] = ..., unchanged: _Optional[int] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ...) -> None: ...

class ListRatesParams(_message.Message):
    __slots__ = ("subjects", "kinds", "tenors", "sources", "at_ns", "business_date", "valid_from_ns", "valid_until_ns", "as_of_ns", "published_as_of_ns", "page_size", "cursor")
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    KINDS_FIELD_NUMBER: _ClassVar[int]
    TENORS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    kinds: _containers.RepeatedScalarFieldContainer[RateKind]
    tenors: _containers.RepeatedCompositeFieldContainer[Tenor]
    sources: SourceChoice
    at_ns: int
    business_date: str
    valid_from_ns: int
    valid_until_ns: int
    as_of_ns: int
    published_as_of_ns: int
    page_size: int
    cursor: str
    def __init__(self, subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., kinds: _Optional[_Iterable[_Union[RateKind, str]]] = ..., tenors: _Optional[_Iterable[_Union[Tenor, _Mapping]]] = ..., sources: _Optional[_Union[SourceChoice, _Mapping]] = ..., at_ns: _Optional[int] = ..., business_date: _Optional[str] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., as_of_ns: _Optional[int] = ..., published_as_of_ns: _Optional[int] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListRatesResult(_message.Message):
    __slots__ = ("rates", "unanswered", "datasets", "watermark", "next_cursor")
    RATES_FIELD_NUMBER: _ClassVar[int]
    UNANSWERED_FIELD_NUMBER: _ClassVar[int]
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    WATERMARK_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    rates: _containers.RepeatedCompositeFieldContainer[Rate]
    unanswered: _containers.RepeatedCompositeFieldContainer[Unanswered]
    datasets: _containers.RepeatedCompositeFieldContainer[DatasetRef]
    watermark: Watermark
    next_cursor: str
    def __init__(self, rates: _Optional[_Iterable[_Union[Rate, _Mapping]]] = ..., unanswered: _Optional[_Iterable[_Union[Unanswered, _Mapping]]] = ..., datasets: _Optional[_Iterable[_Union[DatasetRef, _Mapping]]] = ..., watermark: _Optional[_Union[Watermark, _Mapping]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class RecordLivenessParams(_message.Message):
    __slots__ = ("liveness", "acting_for")
    LIVENESS_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    liveness: _containers.RepeatedCompositeFieldContainer[DatasetLiveness]
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, liveness: _Optional[_Iterable[_Union[DatasetLiveness, _Mapping]]] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class RecordLivenessResult(_message.Message):
    __slots__ = ("kept",)
    KEPT_FIELD_NUMBER: _ClassVar[int]
    kept: int
    def __init__(self, kept: _Optional[int] = ...) -> None: ...

class ListExecutionCostsParams(_message.Message):
    __slots__ = ("account_id", "execution_ids", "order_id", "trade_date", "benchmarks", "as_of_ns", "page_size", "cursor")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_IDS_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    BENCHMARKS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    execution_ids: _containers.RepeatedScalarFieldContainer[str]
    order_id: str
    trade_date: str
    benchmarks: _containers.RepeatedScalarFieldContainer[TcaBenchmark]
    as_of_ns: int
    page_size: int
    cursor: str
    def __init__(self, account_id: _Optional[str] = ..., execution_ids: _Optional[_Iterable[str]] = ..., order_id: _Optional[str] = ..., trade_date: _Optional[str] = ..., benchmarks: _Optional[_Iterable[_Union[TcaBenchmark, str]]] = ..., as_of_ns: _Optional[int] = ..., page_size: _Optional[int] = ..., cursor: _Optional[str] = ...) -> None: ...

class ListExecutionCostsResult(_message.Message):
    __slots__ = ("costs", "next_cursor")
    COSTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    costs: _containers.RepeatedCompositeFieldContainer[ExecutionCost]
    next_cursor: str
    def __init__(self, costs: _Optional[_Iterable[_Union[ExecutionCost, _Mapping]]] = ..., next_cursor: _Optional[str] = ...) -> None: ...

class ReportPlacementQuoteParams(_message.Message):
    __slots__ = ("placement_id", "quote_id", "dealer_id", "dealer_quote_id", "side", "price", "quantity", "received_at_ns", "valid_until_ns", "outcome", "raw_record", "idempotency_key", "acting_for")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    QUOTE_ID_FIELD_NUMBER: _ClassVar[int]
    DEALER_ID_FIELD_NUMBER: _ClassVar[int]
    DEALER_QUOTE_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    quote_id: str
    dealer_id: str
    dealer_quote_id: str
    side: Side
    price: Money
    quantity: Decimal
    received_at_ns: int
    valid_until_ns: int
    outcome: PlacementQuoteOutcome
    raw_record: RawRecordRef
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, placement_id: _Optional[str] = ..., quote_id: _Optional[str] = ..., dealer_id: _Optional[str] = ..., dealer_quote_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., received_at_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., outcome: _Optional[_Union[PlacementQuoteOutcome, str]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class ReportPlacementQuoteResult(_message.Message):
    __slots__ = ("placement", "entry", "journal", "change_request_id")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class PickPlacementQuoteParams(_message.Message):
    __slots__ = ("placement_id", "quote_id", "reason", "idempotency_key", "acting_for")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    QUOTE_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ACTING_FOR_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    quote_id: str
    reason: str
    idempotency_key: str
    acting_for: _sidecar_pb2.CallerAssertion
    def __init__(self, placement_id: _Optional[str] = ..., quote_id: _Optional[str] = ..., reason: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., acting_for: _Optional[_Union[_sidecar_pb2.CallerAssertion, _Mapping]] = ...) -> None: ...

class PickPlacementQuoteResult(_message.Message):
    __slots__ = ("placement", "entry", "journal", "change_request_id")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    entry: EntryMeta
    journal: JournalRef
    change_request_id: str
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., change_request_id: _Optional[str] = ...) -> None: ...

class ReceiveRequest(_message.Message):
    __slots__ = ("rows", "subjects")
    ROWS_FIELD_NUMBER: _ClassVar[int]
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedScalarFieldContainer[str]
    subjects: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, rows: _Optional[_Iterable[str]] = ..., subjects: _Optional[_Iterable[str]] = ...) -> None: ...

class Delivery(_message.Message):
    __slots__ = ("meta", "lost", "statement_recorded", "custodial_position_updated", "position_changed", "break_changed", "account_figures_recorded", "account_attribute_changed", "activity_recorded", "sync_status_recorded", "activity_re_resolved", "prices_recorded", "bars_recorded", "observations_wanted", "want_withdrawn", "trades_recorded", "quotes_recorded", "order_updated", "placement_updated", "execution_recorded", "unplaced_fact_recorded", "trading_instruction_changed", "locate_updated", "report_venue_catalogue", "outcomes_recorded", "replace_merged_instrument", "booking_updated", "alert_changed", "price_batch", "job_finished", "event_group_changed", "rates_recorded", "liveness_recorded")
    META_FIELD_NUMBER: _ClassVar[int]
    LOST_FIELD_NUMBER: _ClassVar[int]
    STATEMENT_RECORDED_FIELD_NUMBER: _ClassVar[int]
    CUSTODIAL_POSITION_UPDATED_FIELD_NUMBER: _ClassVar[int]
    POSITION_CHANGED_FIELD_NUMBER: _ClassVar[int]
    BREAK_CHANGED_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_FIGURES_RECORDED_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ATTRIBUTE_CHANGED_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_RECORDED_FIELD_NUMBER: _ClassVar[int]
    SYNC_STATUS_RECORDED_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_RE_RESOLVED_FIELD_NUMBER: _ClassVar[int]
    PRICES_RECORDED_FIELD_NUMBER: _ClassVar[int]
    BARS_RECORDED_FIELD_NUMBER: _ClassVar[int]
    OBSERVATIONS_WANTED_FIELD_NUMBER: _ClassVar[int]
    WANT_WITHDRAWN_FIELD_NUMBER: _ClassVar[int]
    TRADES_RECORDED_FIELD_NUMBER: _ClassVar[int]
    QUOTES_RECORDED_FIELD_NUMBER: _ClassVar[int]
    ORDER_UPDATED_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_UPDATED_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_RECORDED_FIELD_NUMBER: _ClassVar[int]
    UNPLACED_FACT_RECORDED_FIELD_NUMBER: _ClassVar[int]
    TRADING_INSTRUCTION_CHANGED_FIELD_NUMBER: _ClassVar[int]
    LOCATE_UPDATED_FIELD_NUMBER: _ClassVar[int]
    REPORT_VENUE_CATALOGUE_FIELD_NUMBER: _ClassVar[int]
    OUTCOMES_RECORDED_FIELD_NUMBER: _ClassVar[int]
    REPLACE_MERGED_INSTRUMENT_FIELD_NUMBER: _ClassVar[int]
    BOOKING_UPDATED_FIELD_NUMBER: _ClassVar[int]
    ALERT_CHANGED_FIELD_NUMBER: _ClassVar[int]
    PRICE_BATCH_FIELD_NUMBER: _ClassVar[int]
    JOB_FINISHED_FIELD_NUMBER: _ClassVar[int]
    EVENT_GROUP_CHANGED_FIELD_NUMBER: _ClassVar[int]
    RATES_RECORDED_FIELD_NUMBER: _ClassVar[int]
    LIVENESS_RECORDED_FIELD_NUMBER: _ClassVar[int]
    meta: DeliveryMeta
    lost: Lost
    statement_recorded: StatementRecordedEvent
    custodial_position_updated: CustodialPositionUpdatedEvent
    position_changed: PositionChangedEvent
    break_changed: BreakChangedEvent
    account_figures_recorded: AccountFiguresRecordedEvent
    account_attribute_changed: AccountAttributeChangedEvent
    activity_recorded: ActivityRecordedEvent
    sync_status_recorded: SyncStatusRecordedEvent
    activity_re_resolved: ActivityReResolvedEvent
    prices_recorded: PricesRecordedEvent
    bars_recorded: BarsRecordedEvent
    observations_wanted: ObservationsWantedEvent
    want_withdrawn: WantWithdrawnEvent
    trades_recorded: TradesRecordedEvent
    quotes_recorded: QuotesRecordedEvent
    order_updated: OrderUpdatedEvent
    placement_updated: PlacementUpdatedEvent
    execution_recorded: ExecutionRecordedEvent
    unplaced_fact_recorded: UnplacedFactRecordedEvent
    trading_instruction_changed: TradingInstructionChangedEvent
    locate_updated: LocateUpdatedEvent
    report_venue_catalogue: VenueCatalogueEvent
    outcomes_recorded: OutcomesRecordedEvent
    replace_merged_instrument: InstrumentReplacedEvent
    booking_updated: BookingUpdatedEvent
    alert_changed: AlertChangedEvent
    price_batch: PriceBatchRequest
    job_finished: JobFinishedEvent
    event_group_changed: EventGroup
    rates_recorded: RatesRecordedEvent
    liveness_recorded: LivenessRecordedEvent
    def __init__(self, meta: _Optional[_Union[DeliveryMeta, _Mapping]] = ..., lost: _Optional[_Union[Lost, _Mapping]] = ..., statement_recorded: _Optional[_Union[StatementRecordedEvent, _Mapping]] = ..., custodial_position_updated: _Optional[_Union[CustodialPositionUpdatedEvent, _Mapping]] = ..., position_changed: _Optional[_Union[PositionChangedEvent, _Mapping]] = ..., break_changed: _Optional[_Union[BreakChangedEvent, _Mapping]] = ..., account_figures_recorded: _Optional[_Union[AccountFiguresRecordedEvent, _Mapping]] = ..., account_attribute_changed: _Optional[_Union[AccountAttributeChangedEvent, _Mapping]] = ..., activity_recorded: _Optional[_Union[ActivityRecordedEvent, _Mapping]] = ..., sync_status_recorded: _Optional[_Union[SyncStatusRecordedEvent, _Mapping]] = ..., activity_re_resolved: _Optional[_Union[ActivityReResolvedEvent, _Mapping]] = ..., prices_recorded: _Optional[_Union[PricesRecordedEvent, _Mapping]] = ..., bars_recorded: _Optional[_Union[BarsRecordedEvent, _Mapping]] = ..., observations_wanted: _Optional[_Union[ObservationsWantedEvent, _Mapping]] = ..., want_withdrawn: _Optional[_Union[WantWithdrawnEvent, _Mapping]] = ..., trades_recorded: _Optional[_Union[TradesRecordedEvent, _Mapping]] = ..., quotes_recorded: _Optional[_Union[QuotesRecordedEvent, _Mapping]] = ..., order_updated: _Optional[_Union[OrderUpdatedEvent, _Mapping]] = ..., placement_updated: _Optional[_Union[PlacementUpdatedEvent, _Mapping]] = ..., execution_recorded: _Optional[_Union[ExecutionRecordedEvent, _Mapping]] = ..., unplaced_fact_recorded: _Optional[_Union[UnplacedFactRecordedEvent, _Mapping]] = ..., trading_instruction_changed: _Optional[_Union[TradingInstructionChangedEvent, _Mapping]] = ..., locate_updated: _Optional[_Union[LocateUpdatedEvent, _Mapping]] = ..., report_venue_catalogue: _Optional[_Union[VenueCatalogueEvent, _Mapping]] = ..., outcomes_recorded: _Optional[_Union[OutcomesRecordedEvent, _Mapping]] = ..., replace_merged_instrument: _Optional[_Union[InstrumentReplacedEvent, _Mapping]] = ..., booking_updated: _Optional[_Union[BookingUpdatedEvent, _Mapping]] = ..., alert_changed: _Optional[_Union[AlertChangedEvent, _Mapping]] = ..., price_batch: _Optional[_Union[PriceBatchRequest, _Mapping]] = ..., job_finished: _Optional[_Union[JobFinishedEvent, _Mapping]] = ..., event_group_changed: _Optional[_Union[EventGroup, _Mapping]] = ..., rates_recorded: _Optional[_Union[RatesRecordedEvent, _Mapping]] = ..., liveness_recorded: _Optional[_Union[LivenessRecordedEvent, _Mapping]] = ...) -> None: ...

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
    __slots__ = ("amount", "currency_code", "instrument_id")
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    amount: Decimal
    currency_code: str
    instrument_id: str
    def __init__(self, amount: _Optional[_Union[Decimal, _Mapping]] = ..., currency_code: _Optional[str] = ..., instrument_id: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("scheme", "value", "source", "valid_from_ns", "valid_until_ns", "trading_currency")
    SCHEME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    TRADING_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    scheme: str
    value: str
    source: str
    valid_from_ns: int
    valid_until_ns: int
    trading_currency: str
    def __init__(self, scheme: _Optional[str] = ..., value: _Optional[str] = ..., source: _Optional[str] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., trading_currency: _Optional[str] = ...) -> None: ...

class RawRecordRef(_message.Message):
    __slots__ = ("instance_id", "key")
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    key: str
    def __init__(self, instance_id: _Optional[str] = ..., key: _Optional[str] = ...) -> None: ...

class Provenance(_message.Message):
    __slots__ = ("field", "kind", "raw_record", "source", "person", "rule", "date_basis")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    PERSON_FIELD_NUMBER: _ClassVar[int]
    RULE_FIELD_NUMBER: _ClassVar[int]
    DATE_BASIS_FIELD_NUMBER: _ClassVar[int]
    field: str
    kind: ProvenanceKind
    raw_record: RawRecordRef
    source: str
    person: str
    rule: str
    date_basis: DateBasis
    def __init__(self, field: _Optional[str] = ..., kind: _Optional[_Union[ProvenanceKind, str]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., source: _Optional[str] = ..., person: _Optional[str] = ..., rule: _Optional[str] = ..., date_basis: _Optional[_Union[DateBasis, _Mapping]] = ...) -> None: ...

class DateBasis(_message.Message):
    __slots__ = ("rule", "calendars")
    RULE_FIELD_NUMBER: _ClassVar[int]
    CALENDARS_FIELD_NUMBER: _ClassVar[int]
    rule: DateRuleRef
    calendars: _containers.RepeatedCompositeFieldContainer[CalendarRef]
    def __init__(self, rule: _Optional[_Union[DateRuleRef, _Mapping]] = ..., calendars: _Optional[_Iterable[_Union[CalendarRef, _Mapping]]] = ...) -> None: ...

class DateRuleRef(_message.Message):
    __slots__ = ("kind", "subject", "version")
    KIND_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    kind: DateRuleKind
    subject: str
    version: int
    def __init__(self, kind: _Optional[_Union[DateRuleKind, str]] = ..., subject: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class CalendarRef(_message.Message):
    __slots__ = ("calendar_id", "version")
    CALENDAR_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    calendar_id: str
    version: int
    def __init__(self, calendar_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

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

class CustodialActivity(_message.Message):
    __slots__ = ("external_activity_id", "kind", "kind_as_reported", "instrument_id", "instrument_as_reported", "trade_date", "settlement_date", "units", "price", "amount", "description", "raw_record", "provenance")
    EXTERNAL_ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    KIND_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    UNITS_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    external_activity_id: str
    kind: ActivityKind
    kind_as_reported: AsReported
    instrument_id: str
    instrument_as_reported: AsReported
    trade_date: str
    settlement_date: str
    units: Decimal
    price: Money
    amount: Money
    description: str
    raw_record: RawRecordRef
    provenance: _containers.RepeatedCompositeFieldContainer[Provenance]
    def __init__(self, external_activity_id: _Optional[str] = ..., kind: _Optional[_Union[ActivityKind, str]] = ..., kind_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., instrument_id: _Optional[str] = ..., instrument_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., trade_date: _Optional[str] = ..., settlement_date: _Optional[str] = ..., units: _Optional[_Union[Decimal, _Mapping]] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., amount: _Optional[_Union[Money, _Mapping]] = ..., description: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., provenance: _Optional[_Iterable[_Union[Provenance, _Mapping]]] = ...) -> None: ...

class ActivityRecordedEvent(_message.Message):
    __slots__ = ("activity_id", "account_id", "external_account_id", "source", "activity", "recorded_at_ns", "journal", "cause")
    ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    activity_id: str
    account_id: str
    external_account_id: str
    source: str
    activity: CustodialActivity
    recorded_at_ns: int
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, activity_id: _Optional[str] = ..., account_id: _Optional[str] = ..., external_account_id: _Optional[str] = ..., source: _Optional[str] = ..., activity: _Optional[_Union[CustodialActivity, _Mapping]] = ..., recorded_at_ns: _Optional[int] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class ActivityReResolution(_message.Message):
    __slots__ = ("activity_id", "account_id", "instrument_id", "provenance", "resolved_at_ns", "recorded_at_ns", "journal")
    ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    activity_id: str
    account_id: str
    instrument_id: str
    provenance: Provenance
    resolved_at_ns: int
    recorded_at_ns: int
    journal: JournalRef
    def __init__(self, activity_id: _Optional[str] = ..., account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., provenance: _Optional[_Union[Provenance, _Mapping]] = ..., resolved_at_ns: _Optional[int] = ..., recorded_at_ns: _Optional[int] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class SyncStatusRecordedEvent(_message.Message):
    __slots__ = ("status", "recorded_at_ns", "journal", "cause")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    status: SyncStatusEvent
    recorded_at_ns: int
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, status: _Optional[_Union[SyncStatusEvent, _Mapping]] = ..., recorded_at_ns: _Optional[int] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class SyncStatusEvent(_message.Message):
    __slots__ = ("source", "account_id", "last_synced_at_ns", "connection_healthy", "status_detail", "observed_at_ns", "external_account_id", "state", "holdings_as_of_ns", "history_as_of_ns", "history_from")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CONNECTION_HEALTHY_FIELD_NUMBER: _ClassVar[int]
    STATUS_DETAIL_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    HOLDINGS_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    HISTORY_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FROM_FIELD_NUMBER: _ClassVar[int]
    source: str
    account_id: str
    last_synced_at_ns: int
    connection_healthy: bool
    status_detail: str
    observed_at_ns: int
    external_account_id: str
    state: SyncState
    holdings_as_of_ns: int
    history_as_of_ns: int
    history_from: str
    def __init__(self, source: _Optional[str] = ..., account_id: _Optional[str] = ..., last_synced_at_ns: _Optional[int] = ..., connection_healthy: bool = ..., status_detail: _Optional[str] = ..., observed_at_ns: _Optional[int] = ..., external_account_id: _Optional[str] = ..., state: _Optional[_Union[SyncState, str]] = ..., holdings_as_of_ns: _Optional[int] = ..., history_as_of_ns: _Optional[int] = ..., history_from: _Optional[str] = ...) -> None: ...

class InstrumentRecord(_message.Message):
    __slots__ = ("instrument_id", "identifiers", "asset_class", "currency", "exchange_mic", "description", "lifecycle_state", "version", "valid_from_ns", "record_time_ns", "sources", "offers", "instrument_type", "money_market_fund", "listing_venue_id", "binary_event_contract", "provisional", "template_id", "template_version", "missing_fields")
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
    LISTING_VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    BINARY_EVENT_CONTRACT_FIELD_NUMBER: _ClassVar[int]
    PROVISIONAL_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    MISSING_FIELDS_FIELD_NUMBER: _ClassVar[int]
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
    listing_venue_id: str
    binary_event_contract: BinaryEventContract
    provisional: bool
    template_id: str
    template_version: str
    missing_fields: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, instrument_id: _Optional[str] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., asset_class: _Optional[_Union[AssetClass, str]] = ..., currency: _Optional[str] = ..., exchange_mic: _Optional[str] = ..., description: _Optional[str] = ..., lifecycle_state: _Optional[_Union[InstrumentLifecycleState, str]] = ..., version: _Optional[int] = ..., valid_from_ns: _Optional[int] = ..., record_time_ns: _Optional[int] = ..., sources: _Optional[_Iterable[_Union[InstrumentValueSource, _Mapping]]] = ..., offers: _Optional[_Iterable[_Union[OfferedValue, _Mapping]]] = ..., instrument_type: _Optional[_Union[InstrumentType, str]] = ..., money_market_fund: _Optional[_Union[MoneyMarketFund, _Mapping]] = ..., listing_venue_id: _Optional[str] = ..., binary_event_contract: _Optional[_Union[BinaryEventContract, _Mapping]] = ..., provisional: bool = ..., template_id: _Optional[str] = ..., template_version: _Optional[str] = ..., missing_fields: _Optional[_Iterable[str]] = ...) -> None: ...

class InstrumentValueSource(_message.Message):
    __slots__ = ("field", "identifier", "source", "person", "instance_id", "recorded_at_ns", "note", "acting_through_delegation", "client_name", "prepared_call_id")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    PERSON_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    ACTING_THROUGH_DELEGATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    PREPARED_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    field: InstrumentField
    identifier: Identifier
    source: str
    person: str
    instance_id: str
    recorded_at_ns: int
    note: str
    acting_through_delegation: str
    client_name: str
    prepared_call_id: str
    def __init__(self, field: _Optional[_Union[InstrumentField, str]] = ..., identifier: _Optional[_Union[Identifier, _Mapping]] = ..., source: _Optional[str] = ..., person: _Optional[str] = ..., instance_id: _Optional[str] = ..., recorded_at_ns: _Optional[int] = ..., note: _Optional[str] = ..., acting_through_delegation: _Optional[str] = ..., client_name: _Optional[str] = ..., prepared_call_id: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("asset_class", "currency", "description", "identifier", "instrument_type", "money_market_fund", "binary_event_contract", "source")
    ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    MONEY_MARKET_FUND_FIELD_NUMBER: _ClassVar[int]
    BINARY_EVENT_CONTRACT_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    asset_class: AssetClass
    currency: str
    description: str
    identifier: Identifier
    instrument_type: InstrumentType
    money_market_fund: MoneyMarketFund
    binary_event_contract: BinaryEventContract
    source: str
    def __init__(self, asset_class: _Optional[_Union[AssetClass, str]] = ..., currency: _Optional[str] = ..., description: _Optional[str] = ..., identifier: _Optional[_Union[Identifier, _Mapping]] = ..., instrument_type: _Optional[_Union[InstrumentType, str]] = ..., money_market_fund: _Optional[_Union[MoneyMarketFund, _Mapping]] = ..., binary_event_contract: _Optional[_Union[BinaryEventContract, _Mapping]] = ..., source: _Optional[str] = ...) -> None: ...

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

class BinaryEventContract(_message.Message):
    __slots__ = ("payout", "closes_at_ns", "floor", "cap", "bound_unit")
    PAYOUT_FIELD_NUMBER: _ClassVar[int]
    CLOSES_AT_NS_FIELD_NUMBER: _ClassVar[int]
    FLOOR_FIELD_NUMBER: _ClassVar[int]
    CAP_FIELD_NUMBER: _ClassVar[int]
    BOUND_UNIT_FIELD_NUMBER: _ClassVar[int]
    payout: Money
    closes_at_ns: int
    floor: EventContractBound
    cap: EventContractBound
    bound_unit: str
    def __init__(self, payout: _Optional[_Union[Money, _Mapping]] = ..., closes_at_ns: _Optional[int] = ..., floor: _Optional[_Union[EventContractBound, _Mapping]] = ..., cap: _Optional[_Union[EventContractBound, _Mapping]] = ..., bound_unit: _Optional[str] = ...) -> None: ...

class EventContractBound(_message.Message):
    __slots__ = ("value", "inclusive")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    INCLUSIVE_FIELD_NUMBER: _ClassVar[int]
    value: Decimal
    inclusive: bool
    def __init__(self, value: _Optional[_Union[Decimal, _Mapping]] = ..., inclusive: bool = ...) -> None: ...

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
    __slots__ = ("person", "system", "service_account", "venue")
    PERSON_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    VENUE_FIELD_NUMBER: _ClassVar[int]
    person: PersonActor
    system: SystemActor
    service_account: ServiceAccountActor
    venue: VenueActor
    def __init__(self, person: _Optional[_Union[PersonActor, _Mapping]] = ..., system: _Optional[_Union[SystemActor, _Mapping]] = ..., service_account: _Optional[_Union[ServiceAccountActor, _Mapping]] = ..., venue: _Optional[_Union[VenueActor, _Mapping]] = ...) -> None: ...

class PersonActor(_message.Message):
    __slots__ = ("subject", "delegation_id", "client_name", "prepared_call_id")
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    DELEGATION_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    PREPARED_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    subject: str
    delegation_id: str
    client_name: str
    prepared_call_id: str
    def __init__(self, subject: _Optional[str] = ..., delegation_id: _Optional[str] = ..., client_name: _Optional[str] = ..., prepared_call_id: _Optional[str] = ...) -> None: ...

class SystemActor(_message.Message):
    __slots__ = ("instance_id",)
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    def __init__(self, instance_id: _Optional[str] = ...) -> None: ...

class ServiceAccountActor(_message.Message):
    __slots__ = ("subject", "owner_subject", "algorithm_id")
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    OWNER_SUBJECT_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_ID_FIELD_NUMBER: _ClassVar[int]
    subject: str
    owner_subject: str
    algorithm_id: str
    def __init__(self, subject: _Optional[str] = ..., owner_subject: _Optional[str] = ..., algorithm_id: _Optional[str] = ...) -> None: ...

class VenueActor(_message.Message):
    __slots__ = ("instance_id", "venue_id")
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    venue_id: str
    def __init__(self, instance_id: _Optional[str] = ..., venue_id: _Optional[str] = ...) -> None: ...

class ReferenceVersion(_message.Message):
    __slots__ = ("instrument_id", "version")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    version: int
    def __init__(self, instrument_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class BookPosition(_message.Message):
    __slots__ = ("account_id", "instrument_id", "side", "trade_date_quantity", "settled_quantity", "not_stated_quantity", "pending", "lots", "opened_from", "effective_date", "last_change", "removed", "encumbrances", "free_quantity", "free_basis", "sleeve")
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
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
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
    sleeve: str
    def __init__(self, account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., trade_date_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., settled_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., not_stated_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., pending: _Optional[_Iterable[_Union[PendingSettlement, _Mapping]]] = ..., lots: _Optional[_Iterable[_Union[Lot, _Mapping]]] = ..., opened_from: _Optional[_Iterable[_Union[OpeningSource, _Mapping]]] = ..., effective_date: _Optional[str] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., removed: bool = ..., encumbrances: _Optional[_Iterable[_Union[Encumbrance, _Mapping]]] = ..., free_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., free_basis: _Optional[_Union[FreeBasis, str]] = ..., sleeve: _Optional[str] = ...) -> None: ...

class Lot(_message.Message):
    __slots__ = ("lot_id", "open_quantity", "original_quantity", "terms", "opened_by", "relieved_by", "adjusted_by", "sleeve", "reliefs")
    LOT_ID_FIELD_NUMBER: _ClassVar[int]
    OPEN_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    TERMS_FIELD_NUMBER: _ClassVar[int]
    OPENED_BY_FIELD_NUMBER: _ClassVar[int]
    RELIEVED_BY_FIELD_NUMBER: _ClassVar[int]
    ADJUSTED_BY_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    RELIEFS_FIELD_NUMBER: _ClassVar[int]
    lot_id: str
    open_quantity: Decimal
    original_quantity: Decimal
    terms: LotTerms
    opened_by: JournalRef
    relieved_by: _containers.RepeatedCompositeFieldContainer[JournalRef]
    adjusted_by: _containers.RepeatedCompositeFieldContainer[JournalRef]
    sleeve: str
    reliefs: _containers.RepeatedCompositeFieldContainer[LotRelief]
    def __init__(self, lot_id: _Optional[str] = ..., open_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., original_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., terms: _Optional[_Union[LotTerms, _Mapping]] = ..., opened_by: _Optional[_Union[JournalRef, _Mapping]] = ..., relieved_by: _Optional[_Iterable[_Union[JournalRef, _Mapping]]] = ..., adjusted_by: _Optional[_Iterable[_Union[JournalRef, _Mapping]]] = ..., sleeve: _Optional[str] = ..., reliefs: _Optional[_Iterable[_Union[LotRelief, _Mapping]]] = ...) -> None: ...

class LotRelief(_message.Message):
    __slots__ = ("relieved_by", "quantity", "proceeds", "trade_date")
    RELIEVED_BY_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    PROCEEDS_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    relieved_by: JournalRef
    quantity: Decimal
    proceeds: Money
    trade_date: str
    def __init__(self, relieved_by: _Optional[_Union[JournalRef, _Mapping]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., proceeds: _Optional[_Union[Money, _Mapping]] = ..., trade_date: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("break_id", "account_id", "position", "figure", "category", "differences", "book_watermark", "street", "first_seen_date", "last_seen_date", "state", "candidate_causes", "confirmed_cause", "handling", "resolution", "recorded_by", "last_change", "unresolved_identifiers")
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
    UNRESOLVED_IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
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
    unresolved_identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    def __init__(self, break_id: _Optional[str] = ..., account_id: _Optional[str] = ..., position: _Optional[_Union[PositionKey, _Mapping]] = ..., figure: _Optional[_Union[FigureKey, _Mapping]] = ..., category: _Optional[_Union[BreakCategory, str]] = ..., differences: _Optional[_Iterable[_Union[BreakDifference, _Mapping]]] = ..., book_watermark: _Optional[_Union[Watermark, _Mapping]] = ..., street: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., first_seen_date: _Optional[str] = ..., last_seen_date: _Optional[str] = ..., state: _Optional[_Union[BreakState, str]] = ..., candidate_causes: _Optional[_Iterable[_Union[BreakCause, _Mapping]]] = ..., confirmed_cause: _Optional[_Union[BreakCause, _Mapping]] = ..., handling: _Optional[_Union[BreakHandling, _Mapping]] = ..., resolution: _Optional[_Union[BreakResolution, _Mapping]] = ..., recorded_by: _Optional[_Union[Actor, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., unresolved_identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ...) -> None: ...

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
    __slots__ = ("category", "street_record", "book_entry", "pending_settlement", "event_reference", "none_found", "activity", "date_check", "note")
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    STREET_RECORD_FIELD_NUMBER: _ClassVar[int]
    BOOK_ENTRY_FIELD_NUMBER: _ClassVar[int]
    PENDING_SETTLEMENT_FIELD_NUMBER: _ClassVar[int]
    EVENT_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    NONE_FOUND_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_FIELD_NUMBER: _ClassVar[int]
    DATE_CHECK_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    category: BreakCauseCategory
    street_record: StreetRecordRef
    book_entry: JournalRef
    pending_settlement: PendingSettlementRef
    event_reference: str
    none_found: bool
    activity: ActivityRef
    date_check: DateCheck
    note: str
    def __init__(self, category: _Optional[_Union[BreakCauseCategory, str]] = ..., street_record: _Optional[_Union[StreetRecordRef, _Mapping]] = ..., book_entry: _Optional[_Union[JournalRef, _Mapping]] = ..., pending_settlement: _Optional[_Union[PendingSettlementRef, _Mapping]] = ..., event_reference: _Optional[str] = ..., none_found: bool = ..., activity: _Optional[_Union[ActivityRef, _Mapping]] = ..., date_check: _Optional[_Union[DateCheck, _Mapping]] = ..., note: _Optional[str] = ...) -> None: ...

class PendingSettlementRef(_message.Message):
    __slots__ = ("instrument_id", "side", "value_date")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: HoldingSide
    value_date: str
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., value_date: _Optional[str] = ...) -> None: ...

class ActivityRef(_message.Message):
    __slots__ = ("activity_id", "change", "trade_date")
    ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    CHANGE_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    activity_id: str
    change: JournalRef
    trade_date: str
    def __init__(self, activity_id: _Optional[str] = ..., change: _Optional[_Union[JournalRef, _Mapping]] = ..., trade_date: _Optional[str] = ...) -> None: ...

class DateCheck(_message.Message):
    __slots__ = ("date", "calendars", "reason", "holiday_name")
    DATE_FIELD_NUMBER: _ClassVar[int]
    CALENDARS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    HOLIDAY_NAME_FIELD_NUMBER: _ClassVar[int]
    date: str
    calendars: _containers.RepeatedCompositeFieldContainer[CalendarRef]
    reason: DateCheckReason
    holiday_name: str
    def __init__(self, date: _Optional[str] = ..., calendars: _Optional[_Iterable[_Union[CalendarRef, _Mapping]]] = ..., reason: _Optional[_Union[DateCheckReason, str]] = ..., holiday_name: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("account_id", "base_currency_code", "lot_relief_default", "last_change", "opening_balance", "waits_for_compliance", "error_account", "allocation_account", "base_cash_instrument_id")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BASE_CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    LOT_RELIEF_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    OPENING_BALANCE_FIELD_NUMBER: _ClassVar[int]
    WAITS_FOR_COMPLIANCE_FIELD_NUMBER: _ClassVar[int]
    ERROR_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    BASE_CASH_INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    base_currency_code: str
    lot_relief_default: LotReliefMethod
    last_change: JournalRef
    opening_balance: OpeningBalance
    waits_for_compliance: bool
    error_account: bool
    allocation_account: bool
    base_cash_instrument_id: str
    def __init__(self, account_id: _Optional[str] = ..., base_currency_code: _Optional[str] = ..., lot_relief_default: _Optional[_Union[LotReliefMethod, str]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., opening_balance: _Optional[_Union[OpeningBalance, _Mapping]] = ..., waits_for_compliance: bool = ..., error_account: bool = ..., allocation_account: bool = ..., base_cash_instrument_id: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("instrument_id", "side", "bucket", "value_date", "quantity", "lot_id", "opens_lot", "pending_state", "sleeve")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    LOT_ID_FIELD_NUMBER: _ClassVar[int]
    OPENS_LOT_FIELD_NUMBER: _ClassVar[int]
    PENDING_STATE_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: HoldingSide
    bucket: SettlementBucket
    value_date: str
    quantity: Decimal
    lot_id: str
    opens_lot: LotTerms
    pending_state: PendingState
    sleeve: str
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[HoldingSide, str]] = ..., bucket: _Optional[_Union[SettlementBucket, str]] = ..., value_date: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., lot_id: _Optional[str] = ..., opens_lot: _Optional[_Union[LotTerms, _Mapping]] = ..., pending_state: _Optional[_Union[PendingState, _Mapping]] = ..., sleeve: _Optional[str] = ...) -> None: ...

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

class Leg(_message.Message):
    __slots__ = ("instrument_id", "side", "ratio")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    RATIO_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: Side
    ratio: Decimal
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., ratio: _Optional[_Union[Decimal, _Mapping]] = ...) -> None: ...

class AllocationInstruction(_message.Message):
    __slots__ = ("lines",)
    LINES_FIELD_NUMBER: _ClassVar[int]
    lines: _containers.RepeatedCompositeFieldContainer[AllocationLine]
    def __init__(self, lines: _Optional[_Iterable[_Union[AllocationLine, _Mapping]]] = ...) -> None: ...

class AllocationLine(_message.Message):
    __slots__ = ("account_id", "quantity", "weight", "sleeve")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    WEIGHT_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    quantity: Decimal
    weight: Decimal
    sleeve: str
    def __init__(self, account_id: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., weight: _Optional[_Union[Decimal, _Mapping]] = ..., sleeve: _Optional[str] = ...) -> None: ...

class Party(_message.Message):
    __slots__ = ("identifiers", "lei", "party_role", "contact")
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    LEI_FIELD_NUMBER: _ClassVar[int]
    PARTY_ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    lei: str
    party_role: PartyRole
    contact: str
    def __init__(self, identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., lei: _Optional[str] = ..., party_role: _Optional[_Union[PartyRole, str]] = ..., contact: _Optional[str] = ...) -> None: ...

class ReceiptQuote(_message.Message):
    __slots__ = ("bid", "ask", "source_kind", "venue_id", "quoted_at_ns", "bid_size", "ask_size", "dataset", "row_key")
    BID_FIELD_NUMBER: _ClassVar[int]
    ASK_FIELD_NUMBER: _ClassVar[int]
    SOURCE_KIND_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    QUOTED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    BID_SIZE_FIELD_NUMBER: _ClassVar[int]
    ASK_SIZE_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    ROW_KEY_FIELD_NUMBER: _ClassVar[int]
    bid: Money
    ask: Money
    source_kind: ReceiptQuoteSourceKind
    venue_id: str
    quoted_at_ns: int
    bid_size: Decimal
    ask_size: Decimal
    dataset: str
    row_key: str
    def __init__(self, bid: _Optional[_Union[Money, _Mapping]] = ..., ask: _Optional[_Union[Money, _Mapping]] = ..., source_kind: _Optional[_Union[ReceiptQuoteSourceKind, str]] = ..., venue_id: _Optional[str] = ..., quoted_at_ns: _Optional[int] = ..., bid_size: _Optional[_Union[Decimal, _Mapping]] = ..., ask_size: _Optional[_Union[Decimal, _Mapping]] = ..., dataset: _Optional[str] = ..., row_key: _Optional[str] = ...) -> None: ...

class OrderLink(_message.Message):
    __slots__ = ("kind", "parent_order_id")
    KIND_FIELD_NUMBER: _ClassVar[int]
    PARENT_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    kind: OrderLinkKind
    parent_order_id: str
    def __init__(self, kind: _Optional[_Union[OrderLinkKind, str]] = ..., parent_order_id: _Optional[str] = ...) -> None: ...

class Order(_message.Message):
    __slots__ = ("order_id", "account_id", "instrument_id", "sleeve", "side", "locate_id", "quantity", "cash_quantity", "order_type", "limit_price", "stop_price", "dealt_currency", "quote_currency", "legs", "allocation_instruction", "time_in_force", "expire_date", "expire_time_ns", "execution_instructions", "lot_relief_method", "relieve_lot_ids", "capacity", "direction", "parties", "person_roles", "customer_id", "firm_designated_id", "handling_instructions", "received_at_ns", "received_precision", "quote_at_receipt", "represents_order_ids", "axe_source", "axe_counterparty_id", "link", "origin", "venue_order_id", "status", "checks", "change_requests", "placements", "executions", "charges", "last_change", "block_member_order_ids", "sleeve_cross_ids", "net_member_order_ids", "value_date")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    LOCATE_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    CASH_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    STOP_PRICE_FIELD_NUMBER: _ClassVar[int]
    DEALT_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    QUOTE_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    LEGS_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_FORCE_FIELD_NUMBER: _ClassVar[int]
    EXPIRE_DATE_FIELD_NUMBER: _ClassVar[int]
    EXPIRE_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    LOT_RELIEF_METHOD_FIELD_NUMBER: _ClassVar[int]
    RELIEVE_LOT_IDS_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    PARTIES_FIELD_NUMBER: _ClassVar[int]
    PERSON_ROLES_FIELD_NUMBER: _ClassVar[int]
    CUSTOMER_ID_FIELD_NUMBER: _ClassVar[int]
    FIRM_DESIGNATED_ID_FIELD_NUMBER: _ClassVar[int]
    HANDLING_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_PRECISION_FIELD_NUMBER: _ClassVar[int]
    QUOTE_AT_RECEIPT_FIELD_NUMBER: _ClassVar[int]
    REPRESENTS_ORDER_IDS_FIELD_NUMBER: _ClassVar[int]
    AXE_SOURCE_FIELD_NUMBER: _ClassVar[int]
    AXE_COUNTERPARTY_ID_FIELD_NUMBER: _ClassVar[int]
    LINK_FIELD_NUMBER: _ClassVar[int]
    ORIGIN_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CHECKS_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    PLACEMENTS_FIELD_NUMBER: _ClassVar[int]
    EXECUTIONS_FIELD_NUMBER: _ClassVar[int]
    CHARGES_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    BLOCK_MEMBER_ORDER_IDS_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_CROSS_IDS_FIELD_NUMBER: _ClassVar[int]
    NET_MEMBER_ORDER_IDS_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    account_id: str
    instrument_id: str
    sleeve: str
    side: Side
    locate_id: str
    quantity: Decimal
    cash_quantity: Money
    order_type: OrderType
    limit_price: Money
    stop_price: Money
    dealt_currency: str
    quote_currency: str
    legs: _containers.RepeatedCompositeFieldContainer[Leg]
    allocation_instruction: AllocationInstruction
    time_in_force: TimeInForce
    expire_date: str
    expire_time_ns: int
    execution_instructions: _containers.RepeatedScalarFieldContainer[ExecutionInstruction]
    lot_relief_method: LotReliefMethod
    relieve_lot_ids: _containers.RepeatedScalarFieldContainer[str]
    capacity: Capacity
    direction: OrderDirection
    parties: _containers.RepeatedCompositeFieldContainer[Party]
    person_roles: PersonRoles
    customer_id: str
    firm_designated_id: str
    handling_instructions: _containers.RepeatedScalarFieldContainer[str]
    received_at_ns: int
    received_precision: TimePrecision
    quote_at_receipt: ReceiptQuote
    represents_order_ids: _containers.RepeatedScalarFieldContainer[str]
    axe_source: str
    axe_counterparty_id: str
    link: OrderLink
    origin: OrderOrigin
    venue_order_id: str
    status: OrderStatus
    checks: _containers.RepeatedCompositeFieldContainer[Check]
    change_requests: _containers.RepeatedCompositeFieldContainer[ChangeRequest]
    placements: _containers.RepeatedCompositeFieldContainer[Placement]
    executions: _containers.RepeatedCompositeFieldContainer[Execution]
    charges: _containers.RepeatedCompositeFieldContainer[Charge]
    last_change: JournalRef
    block_member_order_ids: _containers.RepeatedScalarFieldContainer[str]
    sleeve_cross_ids: _containers.RepeatedScalarFieldContainer[str]
    net_member_order_ids: _containers.RepeatedScalarFieldContainer[str]
    value_date: str
    def __init__(self, order_id: _Optional[str] = ..., account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., sleeve: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., locate_id: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., cash_quantity: _Optional[_Union[Money, _Mapping]] = ..., order_type: _Optional[_Union[OrderType, str]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., stop_price: _Optional[_Union[Money, _Mapping]] = ..., dealt_currency: _Optional[str] = ..., quote_currency: _Optional[str] = ..., legs: _Optional[_Iterable[_Union[Leg, _Mapping]]] = ..., allocation_instruction: _Optional[_Union[AllocationInstruction, _Mapping]] = ..., time_in_force: _Optional[_Union[TimeInForce, str]] = ..., expire_date: _Optional[str] = ..., expire_time_ns: _Optional[int] = ..., execution_instructions: _Optional[_Iterable[_Union[ExecutionInstruction, str]]] = ..., lot_relief_method: _Optional[_Union[LotReliefMethod, str]] = ..., relieve_lot_ids: _Optional[_Iterable[str]] = ..., capacity: _Optional[_Union[Capacity, str]] = ..., direction: _Optional[_Union[OrderDirection, str]] = ..., parties: _Optional[_Iterable[_Union[Party, _Mapping]]] = ..., person_roles: _Optional[_Union[PersonRoles, _Mapping]] = ..., customer_id: _Optional[str] = ..., firm_designated_id: _Optional[str] = ..., handling_instructions: _Optional[_Iterable[str]] = ..., received_at_ns: _Optional[int] = ..., received_precision: _Optional[_Union[TimePrecision, str]] = ..., quote_at_receipt: _Optional[_Union[ReceiptQuote, _Mapping]] = ..., represents_order_ids: _Optional[_Iterable[str]] = ..., axe_source: _Optional[str] = ..., axe_counterparty_id: _Optional[str] = ..., link: _Optional[_Union[OrderLink, _Mapping]] = ..., origin: _Optional[_Union[OrderOrigin, str]] = ..., venue_order_id: _Optional[str] = ..., status: _Optional[_Union[OrderStatus, _Mapping]] = ..., checks: _Optional[_Iterable[_Union[Check, _Mapping]]] = ..., change_requests: _Optional[_Iterable[_Union[ChangeRequest, _Mapping]]] = ..., placements: _Optional[_Iterable[_Union[Placement, _Mapping]]] = ..., executions: _Optional[_Iterable[_Union[Execution, _Mapping]]] = ..., charges: _Optional[_Iterable[_Union[Charge, _Mapping]]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., block_member_order_ids: _Optional[_Iterable[str]] = ..., sleeve_cross_ids: _Optional[_Iterable[str]] = ..., net_member_order_ids: _Optional[_Iterable[str]] = ..., value_date: _Optional[str] = ...) -> None: ...

class PersonRoles(_message.Message):
    __slots__ = ("entered_by", "executed_by", "decided_by")
    ENTERED_BY_FIELD_NUMBER: _ClassVar[int]
    EXECUTED_BY_FIELD_NUMBER: _ClassVar[int]
    DECIDED_BY_FIELD_NUMBER: _ClassVar[int]
    entered_by: Actor
    executed_by: Actor
    decided_by: Actor
    def __init__(self, entered_by: _Optional[_Union[Actor, _Mapping]] = ..., executed_by: _Optional[_Union[Actor, _Mapping]] = ..., decided_by: _Optional[_Union[Actor, _Mapping]] = ...) -> None: ...

class OrderStatus(_message.Message):
    __slots__ = ("state", "conditions", "quantities")
    STATE_FIELD_NUMBER: _ClassVar[int]
    CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    QUANTITIES_FIELD_NUMBER: _ClassVar[int]
    state: OrderState
    conditions: _containers.RepeatedCompositeFieldContainer[StandingOrderCondition]
    quantities: OrderQuantities
    def __init__(self, state: _Optional[_Union[OrderState, str]] = ..., conditions: _Optional[_Iterable[_Union[StandingOrderCondition, _Mapping]]] = ..., quantities: _Optional[_Union[OrderQuantities, _Mapping]] = ...) -> None: ...

class StandingOrderCondition(_message.Message):
    __slots__ = ("condition", "reason", "actor", "claimant", "tie_out_reason", "hold_cause", "stale_reference")
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    CLAIMANT_FIELD_NUMBER: _ClassVar[int]
    TIE_OUT_REASON_FIELD_NUMBER: _ClassVar[int]
    HOLD_CAUSE_FIELD_NUMBER: _ClassVar[int]
    STALE_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    condition: OrderCondition
    reason: str
    actor: Actor
    claimant: Claimant
    tie_out_reason: TieOutReason
    hold_cause: HoldCause
    stale_reference: StaleReference
    def __init__(self, condition: _Optional[_Union[OrderCondition, str]] = ..., reason: _Optional[str] = ..., actor: _Optional[_Union[Actor, _Mapping]] = ..., claimant: _Optional[_Union[Claimant, _Mapping]] = ..., tie_out_reason: _Optional[_Union[TieOutReason, str]] = ..., hold_cause: _Optional[_Union[HoldCause, str]] = ..., stale_reference: _Optional[_Union[StaleReference, _Mapping]] = ...) -> None: ...

class Claimant(_message.Message):
    __slots__ = ("instance_id", "person", "service_account")
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    PERSON_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    person: PersonActor
    service_account: ServiceAccountActor
    def __init__(self, instance_id: _Optional[str] = ..., person: _Optional[_Union[PersonActor, _Mapping]] = ..., service_account: _Optional[_Union[ServiceAccountActor, _Mapping]] = ...) -> None: ...

class StaleReference(_message.Message):
    __slots__ = ("dataset", "age_ns", "ceiling_ns")
    DATASET_FIELD_NUMBER: _ClassVar[int]
    AGE_NS_FIELD_NUMBER: _ClassVar[int]
    CEILING_NS_FIELD_NUMBER: _ClassVar[int]
    dataset: str
    age_ns: int
    ceiling_ns: int
    def __init__(self, dataset: _Optional[str] = ..., age_ns: _Optional[int] = ..., ceiling_ns: _Optional[int] = ...) -> None: ...

class OrderQuantities(_message.Message):
    __slots__ = ("ordered", "reported_filled", "final_filled", "awaiting_acceptance", "committed", "idle", "leaves")
    ORDERED_FIELD_NUMBER: _ClassVar[int]
    REPORTED_FILLED_FIELD_NUMBER: _ClassVar[int]
    FINAL_FILLED_FIELD_NUMBER: _ClassVar[int]
    AWAITING_ACCEPTANCE_FIELD_NUMBER: _ClassVar[int]
    COMMITTED_FIELD_NUMBER: _ClassVar[int]
    IDLE_FIELD_NUMBER: _ClassVar[int]
    LEAVES_FIELD_NUMBER: _ClassVar[int]
    ordered: Decimal
    reported_filled: Decimal
    final_filled: Decimal
    awaiting_acceptance: Decimal
    committed: Decimal
    idle: Decimal
    leaves: Decimal
    def __init__(self, ordered: _Optional[_Union[Decimal, _Mapping]] = ..., reported_filled: _Optional[_Union[Decimal, _Mapping]] = ..., final_filled: _Optional[_Union[Decimal, _Mapping]] = ..., awaiting_acceptance: _Optional[_Union[Decimal, _Mapping]] = ..., committed: _Optional[_Union[Decimal, _Mapping]] = ..., idle: _Optional[_Union[Decimal, _Mapping]] = ..., leaves: _Optional[_Union[Decimal, _Mapping]] = ...) -> None: ...

class Check(_message.Message):
    __slots__ = ("verdict", "order_version", "placement_id", "rule", "note", "instance_id", "recorded_by")
    VERDICT_FIELD_NUMBER: _ClassVar[int]
    ORDER_VERSION_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    RULE_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    RECORDED_BY_FIELD_NUMBER: _ClassVar[int]
    verdict: CheckVerdict
    order_version: int
    placement_id: str
    rule: str
    note: str
    instance_id: str
    recorded_by: Actor
    def __init__(self, verdict: _Optional[_Union[CheckVerdict, str]] = ..., order_version: _Optional[int] = ..., placement_id: _Optional[str] = ..., rule: _Optional[str] = ..., note: _Optional[str] = ..., instance_id: _Optional[str] = ..., recorded_by: _Optional[_Union[Actor, _Mapping]] = ...) -> None: ...

class ChangeRequest(_message.Message):
    __slots__ = ("change_request_id", "order_id", "placement_id", "order_change", "placement_change", "reason", "entry", "outcome")
    CHANGE_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_CHANGE_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_CHANGE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    change_request_id: str
    order_id: str
    placement_id: str
    order_change: OrderChange
    placement_change: PlacementChange
    reason: str
    entry: EntryMeta
    outcome: ChangeRequestOutcome
    def __init__(self, change_request_id: _Optional[str] = ..., order_id: _Optional[str] = ..., placement_id: _Optional[str] = ..., order_change: _Optional[_Union[OrderChange, _Mapping]] = ..., placement_change: _Optional[_Union[PlacementChange, _Mapping]] = ..., reason: _Optional[str] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., outcome: _Optional[_Union[ChangeRequestOutcome, str]] = ...) -> None: ...

class OrderChange(_message.Message):
    __slots__ = ("kind", "quantity", "limit_price", "time_in_force", "allocation_instruction", "execution_instructions")
    KIND_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_FORCE_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    kind: OrderChangeKind
    quantity: Decimal
    limit_price: Money
    time_in_force: TimeInForce
    allocation_instruction: AllocationInstruction
    execution_instructions: _containers.RepeatedScalarFieldContainer[ExecutionInstruction]
    def __init__(self, kind: _Optional[_Union[OrderChangeKind, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., time_in_force: _Optional[_Union[TimeInForce, str]] = ..., allocation_instruction: _Optional[_Union[AllocationInstruction, _Mapping]] = ..., execution_instructions: _Optional[_Iterable[_Union[ExecutionInstruction, str]]] = ...) -> None: ...

class PlacementChange(_message.Message):
    __slots__ = ("kind", "quantity", "limit_price", "time_in_force")
    KIND_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_FORCE_FIELD_NUMBER: _ClassVar[int]
    kind: PlacementChangeKind
    quantity: Decimal
    limit_price: Money
    time_in_force: TimeInForce
    def __init__(self, kind: _Optional[_Union[PlacementChangeKind, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., time_in_force: _Optional[_Union[TimeInForce, str]] = ...) -> None: ...

class Placement(_message.Message):
    __slots__ = ("placement_id", "order_id", "account_id", "ems_instance_id", "connectivity_instance_id", "venue_account_code", "quantity", "limit_price", "time_in_force", "strategy", "destination", "route_type", "routed_at_ns", "routed_precision", "handling_instructions", "rfq_id", "axe_id", "venue_order_id", "status", "person_roles", "checks", "rejection_reason", "rejection_as_reported", "last_change", "venue_order_ids", "change_requests", "placement_type", "counterparty_contact", "agreed_at_ns", "agreed_precision", "quotes", "picked_quote_id")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    EMS_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    CONNECTIVITY_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    TIME_IN_FORCE_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    ROUTE_TYPE_FIELD_NUMBER: _ClassVar[int]
    ROUTED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ROUTED_PRECISION_FIELD_NUMBER: _ClassVar[int]
    HANDLING_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    RFQ_ID_FIELD_NUMBER: _ClassVar[int]
    AXE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PERSON_ROLES_FIELD_NUMBER: _ClassVar[int]
    CHECKS_FIELD_NUMBER: _ClassVar[int]
    REJECTION_REASON_FIELD_NUMBER: _ClassVar[int]
    REJECTION_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_IDS_FIELD_NUMBER: _ClassVar[int]
    CHANGE_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    COUNTERPARTY_CONTACT_FIELD_NUMBER: _ClassVar[int]
    AGREED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    AGREED_PRECISION_FIELD_NUMBER: _ClassVar[int]
    QUOTES_FIELD_NUMBER: _ClassVar[int]
    PICKED_QUOTE_ID_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    order_id: str
    account_id: str
    ems_instance_id: str
    connectivity_instance_id: str
    venue_account_code: str
    quantity: Decimal
    limit_price: Money
    time_in_force: TimeInForce
    strategy: StrategyInstruction
    destination: str
    route_type: RouteType
    routed_at_ns: int
    routed_precision: TimePrecision
    handling_instructions: _containers.RepeatedScalarFieldContainer[str]
    rfq_id: str
    axe_id: str
    venue_order_id: str
    status: PlacementStatus
    person_roles: PersonRoles
    checks: _containers.RepeatedCompositeFieldContainer[Check]
    rejection_reason: RejectionReason
    rejection_as_reported: AsReported
    last_change: JournalRef
    venue_order_ids: _containers.RepeatedScalarFieldContainer[str]
    change_requests: _containers.RepeatedCompositeFieldContainer[ChangeRequest]
    placement_type: PlacementType
    counterparty_contact: str
    agreed_at_ns: int
    agreed_precision: TimePrecision
    quotes: _containers.RepeatedCompositeFieldContainer[PlacementQuote]
    picked_quote_id: str
    def __init__(self, placement_id: _Optional[str] = ..., order_id: _Optional[str] = ..., account_id: _Optional[str] = ..., ems_instance_id: _Optional[str] = ..., connectivity_instance_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., time_in_force: _Optional[_Union[TimeInForce, str]] = ..., strategy: _Optional[_Union[StrategyInstruction, _Mapping]] = ..., destination: _Optional[str] = ..., route_type: _Optional[_Union[RouteType, str]] = ..., routed_at_ns: _Optional[int] = ..., routed_precision: _Optional[_Union[TimePrecision, str]] = ..., handling_instructions: _Optional[_Iterable[str]] = ..., rfq_id: _Optional[str] = ..., axe_id: _Optional[str] = ..., venue_order_id: _Optional[str] = ..., status: _Optional[_Union[PlacementStatus, _Mapping]] = ..., person_roles: _Optional[_Union[PersonRoles, _Mapping]] = ..., checks: _Optional[_Iterable[_Union[Check, _Mapping]]] = ..., rejection_reason: _Optional[_Union[RejectionReason, str]] = ..., rejection_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., venue_order_ids: _Optional[_Iterable[str]] = ..., change_requests: _Optional[_Iterable[_Union[ChangeRequest, _Mapping]]] = ..., placement_type: _Optional[_Union[PlacementType, str]] = ..., counterparty_contact: _Optional[str] = ..., agreed_at_ns: _Optional[int] = ..., agreed_precision: _Optional[_Union[TimePrecision, str]] = ..., quotes: _Optional[_Iterable[_Union[PlacementQuote, _Mapping]]] = ..., picked_quote_id: _Optional[str] = ...) -> None: ...

class StrategyInstruction(_message.Message):
    __slots__ = ("kind", "start_ns", "end_ns", "participation", "urgency", "max_participation", "price_limit")
    KIND_FIELD_NUMBER: _ClassVar[int]
    START_NS_FIELD_NUMBER: _ClassVar[int]
    END_NS_FIELD_NUMBER: _ClassVar[int]
    PARTICIPATION_FIELD_NUMBER: _ClassVar[int]
    URGENCY_FIELD_NUMBER: _ClassVar[int]
    MAX_PARTICIPATION_FIELD_NUMBER: _ClassVar[int]
    PRICE_LIMIT_FIELD_NUMBER: _ClassVar[int]
    kind: StrategyKind
    start_ns: int
    end_ns: int
    participation: Decimal
    urgency: Urgency
    max_participation: Decimal
    price_limit: Money
    def __init__(self, kind: _Optional[_Union[StrategyKind, str]] = ..., start_ns: _Optional[int] = ..., end_ns: _Optional[int] = ..., participation: _Optional[_Union[Decimal, _Mapping]] = ..., urgency: _Optional[_Union[Urgency, str]] = ..., max_participation: _Optional[_Union[Decimal, _Mapping]] = ..., price_limit: _Optional[_Union[Money, _Mapping]] = ...) -> None: ...

class PlacementStatus(_message.Message):
    __slots__ = ("state", "conditions")
    STATE_FIELD_NUMBER: _ClassVar[int]
    CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    state: PlacementState
    conditions: _containers.RepeatedCompositeFieldContainer[StandingPlacementCondition]
    def __init__(self, state: _Optional[_Union[PlacementState, str]] = ..., conditions: _Optional[_Iterable[_Union[StandingPlacementCondition, _Mapping]]] = ...) -> None: ...

class StandingPlacementCondition(_message.Message):
    __slots__ = ("condition", "reason", "actor", "unknown_reason", "status_as_reported", "stale_reference")
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_REASON_FIELD_NUMBER: _ClassVar[int]
    STATUS_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    STALE_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    condition: PlacementCondition
    reason: str
    actor: Actor
    unknown_reason: UnknownReason
    status_as_reported: AsReported
    stale_reference: StaleReference
    def __init__(self, condition: _Optional[_Union[PlacementCondition, str]] = ..., reason: _Optional[str] = ..., actor: _Optional[_Union[Actor, _Mapping]] = ..., unknown_reason: _Optional[_Union[UnknownReason, str]] = ..., status_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., stale_reference: _Optional[_Union[StaleReference, _Mapping]] = ...) -> None: ...

class PlacementQuote(_message.Message):
    __slots__ = ("quote_id", "dealer_id", "dealer_quote_id", "side", "price", "quantity", "received_at_ns", "valid_until_ns", "outcome", "raw_record")
    QUOTE_ID_FIELD_NUMBER: _ClassVar[int]
    DEALER_ID_FIELD_NUMBER: _ClassVar[int]
    DEALER_QUOTE_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    quote_id: str
    dealer_id: str
    dealer_quote_id: str
    side: Side
    price: Money
    quantity: Decimal
    received_at_ns: int
    valid_until_ns: int
    outcome: PlacementQuoteOutcome
    raw_record: RawRecordRef
    def __init__(self, quote_id: _Optional[str] = ..., dealer_id: _Optional[str] = ..., dealer_quote_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., received_at_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., outcome: _Optional[_Union[PlacementQuoteOutcome, str]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ...) -> None: ...

class Execution(_message.Message):
    __slots__ = ("execution_id", "order_id", "placement_id", "account_id", "instrument_id", "sleeve", "side", "quantity", "price", "trade_time_ns", "trade_date", "venue_execution_id", "kind", "source", "finality", "fees", "settlement_date", "computed_settlement_date", "settlement_date_basis", "supersedes", "venue_id", "uti", "prior_uti", "upi", "given_up_to", "trade_chain_reference", "settlement_counterparty", "person_roles", "raw_record", "last_change", "effective_date", "counterparty", "liquidity_indicator", "uti_generated_by", "state", "venue_order_id", "dk_reason", "dk_text", "venue_client_order_id", "give_up_answers", "cross_rate_source")
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    TRADE_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    VENUE_EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    FINALITY_FIELD_NUMBER: _ClassVar[int]
    FEES_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    COMPUTED_SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_BASIS_FIELD_NUMBER: _ClassVar[int]
    SUPERSEDES_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    UTI_FIELD_NUMBER: _ClassVar[int]
    PRIOR_UTI_FIELD_NUMBER: _ClassVar[int]
    UPI_FIELD_NUMBER: _ClassVar[int]
    GIVEN_UP_TO_FIELD_NUMBER: _ClassVar[int]
    TRADE_CHAIN_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_COUNTERPARTY_FIELD_NUMBER: _ClassVar[int]
    PERSON_ROLES_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    COUNTERPARTY_FIELD_NUMBER: _ClassVar[int]
    LIQUIDITY_INDICATOR_FIELD_NUMBER: _ClassVar[int]
    UTI_GENERATED_BY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    DK_REASON_FIELD_NUMBER: _ClassVar[int]
    DK_TEXT_FIELD_NUMBER: _ClassVar[int]
    VENUE_CLIENT_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    GIVE_UP_ANSWERS_FIELD_NUMBER: _ClassVar[int]
    CROSS_RATE_SOURCE_FIELD_NUMBER: _ClassVar[int]
    execution_id: str
    order_id: str
    placement_id: str
    account_id: str
    instrument_id: str
    sleeve: str
    side: Side
    quantity: Decimal
    price: Money
    trade_time_ns: int
    trade_date: str
    venue_execution_id: str
    kind: ExecutionKind
    source: ExecutionSource
    finality: Finality
    fees: _containers.RepeatedCompositeFieldContainer[Fee]
    settlement_date: str
    computed_settlement_date: str
    settlement_date_basis: DateBasis
    supersedes: str
    venue_id: str
    uti: str
    prior_uti: str
    upi: str
    given_up_to: str
    trade_chain_reference: str
    settlement_counterparty: str
    person_roles: PersonRoles
    raw_record: RawRecordRef
    last_change: JournalRef
    effective_date: str
    counterparty: Party
    liquidity_indicator: LiquidityIndicator
    uti_generated_by: str
    state: ExecutionState
    venue_order_id: str
    dk_reason: DkReason
    dk_text: str
    venue_client_order_id: str
    give_up_answers: _containers.RepeatedCompositeFieldContainer[GiveUpRecord]
    cross_rate_source: CrossRateSource
    def __init__(self, execution_id: _Optional[str] = ..., order_id: _Optional[str] = ..., placement_id: _Optional[str] = ..., account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., sleeve: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., trade_time_ns: _Optional[int] = ..., trade_date: _Optional[str] = ..., venue_execution_id: _Optional[str] = ..., kind: _Optional[_Union[ExecutionKind, str]] = ..., source: _Optional[_Union[ExecutionSource, str]] = ..., finality: _Optional[_Union[Finality, _Mapping]] = ..., fees: _Optional[_Iterable[_Union[Fee, _Mapping]]] = ..., settlement_date: _Optional[str] = ..., computed_settlement_date: _Optional[str] = ..., settlement_date_basis: _Optional[_Union[DateBasis, _Mapping]] = ..., supersedes: _Optional[str] = ..., venue_id: _Optional[str] = ..., uti: _Optional[str] = ..., prior_uti: _Optional[str] = ..., upi: _Optional[str] = ..., given_up_to: _Optional[str] = ..., trade_chain_reference: _Optional[str] = ..., settlement_counterparty: _Optional[str] = ..., person_roles: _Optional[_Union[PersonRoles, _Mapping]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ..., effective_date: _Optional[str] = ..., counterparty: _Optional[_Union[Party, _Mapping]] = ..., liquidity_indicator: _Optional[_Union[LiquidityIndicator, str]] = ..., uti_generated_by: _Optional[str] = ..., state: _Optional[_Union[ExecutionState, str]] = ..., venue_order_id: _Optional[str] = ..., dk_reason: _Optional[_Union[DkReason, str]] = ..., dk_text: _Optional[str] = ..., venue_client_order_id: _Optional[str] = ..., give_up_answers: _Optional[_Iterable[_Union[GiveUpRecord, _Mapping]]] = ..., cross_rate_source: _Optional[_Union[CrossRateSource, str]] = ...) -> None: ...

class Finality(_message.Message):
    __slots__ = ("level", "at_ns")
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    level: FinalityLevel
    at_ns: int
    def __init__(self, level: _Optional[_Union[FinalityLevel, str]] = ..., at_ns: _Optional[int] = ...) -> None: ...

class Fee(_message.Message):
    __slots__ = ("kind", "amount", "capitalised")
    KIND_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    CAPITALISED_FIELD_NUMBER: _ClassVar[int]
    kind: FeeKind
    amount: Money
    capitalised: bool
    def __init__(self, kind: _Optional[_Union[FeeKind, str]] = ..., amount: _Optional[_Union[Money, _Mapping]] = ..., capitalised: bool = ...) -> None: ...

class GiveUpRecord(_message.Message):
    __slots__ = ("answer", "prime_reference", "reason", "entry")
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    PRIME_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    answer: GiveUpAnswer
    prime_reference: str
    reason: str
    entry: EntryMeta
    def __init__(self, answer: _Optional[_Union[GiveUpAnswer, str]] = ..., prime_reference: _Optional[str] = ..., reason: _Optional[str] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ...) -> None: ...

class Charge(_message.Message):
    __slots__ = ("charge_id", "placement_id", "order_id", "account_id", "fee", "trade_date", "settlement_date", "raw_record")
    CHARGE_ID_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    FEE_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    charge_id: str
    placement_id: str
    order_id: str
    account_id: str
    fee: Fee
    trade_date: str
    settlement_date: str
    raw_record: RawRecordRef
    def __init__(self, charge_id: _Optional[str] = ..., placement_id: _Optional[str] = ..., order_id: _Optional[str] = ..., account_id: _Optional[str] = ..., fee: _Optional[_Union[Fee, _Mapping]] = ..., trade_date: _Optional[str] = ..., settlement_date: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ...) -> None: ...

class UnplacedFact(_message.Message):
    __slots__ = ("unplaced_id", "account_id", "fact_kind", "reason", "raw_record", "venue_account_code", "execution", "placement", "charge", "locate", "value_date_roll", "give_up", "placed_by", "last_change")
    UNPLACED_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    FACT_KIND_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    CHARGE_FIELD_NUMBER: _ClassVar[int]
    LOCATE_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_ROLL_FIELD_NUMBER: _ClassVar[int]
    GIVE_UP_FIELD_NUMBER: _ClassVar[int]
    PLACED_BY_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    unplaced_id: str
    account_id: str
    fact_kind: str
    reason: UnplacedReason
    raw_record: RawRecordRef
    venue_account_code: str
    execution: ReportExecutionRequest
    placement: ReportPlacementRequest
    charge: ReportChargeRequest
    locate: RecordLocateRequest
    value_date_roll: ReportValueDateRollRequest
    give_up: ReportGiveUpRequest
    placed_by: JournalRef
    last_change: JournalRef
    def __init__(self, unplaced_id: _Optional[str] = ..., account_id: _Optional[str] = ..., fact_kind: _Optional[str] = ..., reason: _Optional[_Union[UnplacedReason, str]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., venue_account_code: _Optional[str] = ..., execution: _Optional[_Union[ReportExecutionRequest, _Mapping]] = ..., placement: _Optional[_Union[ReportPlacementRequest, _Mapping]] = ..., charge: _Optional[_Union[ReportChargeRequest, _Mapping]] = ..., locate: _Optional[_Union[RecordLocateRequest, _Mapping]] = ..., value_date_roll: _Optional[_Union[ReportValueDateRollRequest, _Mapping]] = ..., give_up: _Optional[_Union[ReportGiveUpRequest, _Mapping]] = ..., placed_by: _Optional[_Union[JournalRef, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class ReportExecutionRequest(_message.Message):
    __slots__ = ("placement_id", "order_id", "account_id", "venue_account_code", "venue_execution_id", "kind", "source", "quantity", "price", "trade_time_ns", "trade_date", "finality", "settlement_date", "computed_settlement_date", "settlement_date_basis", "fees", "supersedes", "venue_id", "uti", "prior_uti", "upi", "given_up_to", "trade_chain_reference", "settlement_counterparty", "raw_record", "idempotency_key", "effective_date", "counterparty", "liquidity_indicator", "uti_generated_by", "instrument_id", "side", "venue_order_id", "venue_client_order_id", "cross_rate_source")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    VENUE_EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    TRADE_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    FINALITY_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    COMPUTED_SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_BASIS_FIELD_NUMBER: _ClassVar[int]
    FEES_FIELD_NUMBER: _ClassVar[int]
    SUPERSEDES_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    UTI_FIELD_NUMBER: _ClassVar[int]
    PRIOR_UTI_FIELD_NUMBER: _ClassVar[int]
    UPI_FIELD_NUMBER: _ClassVar[int]
    GIVEN_UP_TO_FIELD_NUMBER: _ClassVar[int]
    TRADE_CHAIN_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_COUNTERPARTY_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    COUNTERPARTY_FIELD_NUMBER: _ClassVar[int]
    LIQUIDITY_INDICATOR_FIELD_NUMBER: _ClassVar[int]
    UTI_GENERATED_BY_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_CLIENT_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    CROSS_RATE_SOURCE_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    order_id: str
    account_id: str
    venue_account_code: str
    venue_execution_id: str
    kind: ExecutionKind
    source: ExecutionSource
    quantity: Decimal
    price: Money
    trade_time_ns: int
    trade_date: str
    finality: Finality
    settlement_date: str
    computed_settlement_date: str
    settlement_date_basis: DateBasis
    fees: _containers.RepeatedCompositeFieldContainer[Fee]
    supersedes: str
    venue_id: str
    uti: str
    prior_uti: str
    upi: str
    given_up_to: str
    trade_chain_reference: str
    settlement_counterparty: str
    raw_record: RawRecordRef
    idempotency_key: str
    effective_date: str
    counterparty: Party
    liquidity_indicator: LiquidityIndicator
    uti_generated_by: str
    instrument_id: str
    side: Side
    venue_order_id: str
    venue_client_order_id: str
    cross_rate_source: CrossRateSource
    def __init__(self, placement_id: _Optional[str] = ..., order_id: _Optional[str] = ..., account_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., venue_execution_id: _Optional[str] = ..., kind: _Optional[_Union[ExecutionKind, str]] = ..., source: _Optional[_Union[ExecutionSource, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., trade_time_ns: _Optional[int] = ..., trade_date: _Optional[str] = ..., finality: _Optional[_Union[Finality, _Mapping]] = ..., settlement_date: _Optional[str] = ..., computed_settlement_date: _Optional[str] = ..., settlement_date_basis: _Optional[_Union[DateBasis, _Mapping]] = ..., fees: _Optional[_Iterable[_Union[Fee, _Mapping]]] = ..., supersedes: _Optional[str] = ..., venue_id: _Optional[str] = ..., uti: _Optional[str] = ..., prior_uti: _Optional[str] = ..., upi: _Optional[str] = ..., given_up_to: _Optional[str] = ..., trade_chain_reference: _Optional[str] = ..., settlement_counterparty: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., idempotency_key: _Optional[str] = ..., effective_date: _Optional[str] = ..., counterparty: _Optional[_Union[Party, _Mapping]] = ..., liquidity_indicator: _Optional[_Union[LiquidityIndicator, str]] = ..., uti_generated_by: _Optional[str] = ..., instrument_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., venue_order_id: _Optional[str] = ..., venue_client_order_id: _Optional[str] = ..., cross_rate_source: _Optional[_Union[CrossRateSource, str]] = ...) -> None: ...

class ReportPlacementRequest(_message.Message):
    __slots__ = ("placement_id", "event", "venue_order_id", "routed_at_ns", "routed_precision", "rejection_reason", "rejection_as_reported", "unknown_reason", "status_as_reported", "restatement_reason", "quantity", "limit_price", "raw_record")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_FIELD_NUMBER: _ClassVar[int]
    VENUE_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ROUTED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ROUTED_PRECISION_FIELD_NUMBER: _ClassVar[int]
    REJECTION_REASON_FIELD_NUMBER: _ClassVar[int]
    REJECTION_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_REASON_FIELD_NUMBER: _ClassVar[int]
    STATUS_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    RESTATEMENT_REASON_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_PRICE_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    event: PlacementEvent
    venue_order_id: str
    routed_at_ns: int
    routed_precision: TimePrecision
    rejection_reason: RejectionReason
    rejection_as_reported: AsReported
    unknown_reason: UnknownReason
    status_as_reported: AsReported
    restatement_reason: RestatementReason
    quantity: Decimal
    limit_price: Money
    raw_record: RawRecordRef
    def __init__(self, placement_id: _Optional[str] = ..., event: _Optional[_Union[PlacementEvent, str]] = ..., venue_order_id: _Optional[str] = ..., routed_at_ns: _Optional[int] = ..., routed_precision: _Optional[_Union[TimePrecision, str]] = ..., rejection_reason: _Optional[_Union[RejectionReason, str]] = ..., rejection_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., unknown_reason: _Optional[_Union[UnknownReason, str]] = ..., status_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., restatement_reason: _Optional[_Union[RestatementReason, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., limit_price: _Optional[_Union[Money, _Mapping]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ...) -> None: ...

class ReportChargeRequest(_message.Message):
    __slots__ = ("placement_id", "fee", "trade_date", "settlement_date", "raw_record")
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    FEE_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    placement_id: str
    fee: Fee
    trade_date: str
    settlement_date: str
    raw_record: RawRecordRef
    def __init__(self, placement_id: _Optional[str] = ..., fee: _Optional[_Union[Fee, _Mapping]] = ..., trade_date: _Optional[str] = ..., settlement_date: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ...) -> None: ...

class RecordLocateRequest(_message.Message):
    __slots__ = ("account_id", "venue_account_code", "instrument_id", "quantity_requested", "answer", "locate_record_id", "raw_record", "idempotency_key")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_REQUESTED_FIELD_NUMBER: _ClassVar[int]
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    LOCATE_RECORD_ID_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    venue_account_code: str
    instrument_id: str
    quantity_requested: Decimal
    answer: LocateAnswer
    locate_record_id: str
    raw_record: RawRecordRef
    idempotency_key: str
    def __init__(self, account_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., instrument_id: _Optional[str] = ..., quantity_requested: _Optional[_Union[Decimal, _Mapping]] = ..., answer: _Optional[_Union[LocateAnswer, _Mapping]] = ..., locate_record_id: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class LocateAnswer(_message.Message):
    __slots__ = ("quantity_approved", "rate", "expires_at_ns", "locate_id")
    QUANTITY_APPROVED_FIELD_NUMBER: _ClassVar[int]
    RATE_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_NS_FIELD_NUMBER: _ClassVar[int]
    LOCATE_ID_FIELD_NUMBER: _ClassVar[int]
    quantity_approved: Decimal
    rate: Decimal
    expires_at_ns: int
    locate_id: str
    def __init__(self, quantity_approved: _Optional[_Union[Decimal, _Mapping]] = ..., rate: _Optional[_Union[Decimal, _Mapping]] = ..., expires_at_ns: _Optional[int] = ..., locate_id: _Optional[str] = ...) -> None: ...

class ReportValueDateRollRequest(_message.Message):
    __slots__ = ("account_id", "venue_account_code", "pair", "from_value_date", "to_value_date", "value_date_basis", "rolled_at_ns", "charge_ids", "raw_record", "idempotency_key")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    PAIR_FIELD_NUMBER: _ClassVar[int]
    FROM_VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    TO_VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_BASIS_FIELD_NUMBER: _ClassVar[int]
    ROLLED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CHARGE_IDS_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    venue_account_code: str
    pair: _containers.RepeatedScalarFieldContainer[str]
    from_value_date: str
    to_value_date: str
    value_date_basis: DateBasis
    rolled_at_ns: int
    charge_ids: _containers.RepeatedScalarFieldContainer[str]
    raw_record: RawRecordRef
    idempotency_key: str
    def __init__(self, account_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., pair: _Optional[_Iterable[str]] = ..., from_value_date: _Optional[str] = ..., to_value_date: _Optional[str] = ..., value_date_basis: _Optional[_Union[DateBasis, _Mapping]] = ..., rolled_at_ns: _Optional[int] = ..., charge_ids: _Optional[_Iterable[str]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class ReportGiveUpRequest(_message.Message):
    __slots__ = ("execution_id", "allocation_id", "answer", "prime_reference", "reason", "raw_record")
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    PRIME_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    execution_id: str
    allocation_id: str
    answer: GiveUpAnswer
    prime_reference: str
    reason: str
    raw_record: RawRecordRef
    def __init__(self, execution_id: _Optional[str] = ..., allocation_id: _Optional[str] = ..., answer: _Optional[_Union[GiveUpAnswer, str]] = ..., prime_reference: _Optional[str] = ..., reason: _Optional[str] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ...) -> None: ...

class TradingInstruction(_message.Message):
    __slots__ = ("target", "value", "setter_level", "covers", "reason", "entry", "last_change")
    TARGET_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SETTER_LEVEL_FIELD_NUMBER: _ClassVar[int]
    COVERS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    target: TradingInstructionTarget
    value: TradingInstructionValue
    setter_level: SetterLevel
    covers: _containers.RepeatedScalarFieldContainer[str]
    reason: str
    entry: EntryMeta
    last_change: JournalRef
    def __init__(self, target: _Optional[_Union[TradingInstructionTarget, _Mapping]] = ..., value: _Optional[_Union[TradingInstructionValue, str]] = ..., setter_level: _Optional[_Union[SetterLevel, str]] = ..., covers: _Optional[_Iterable[str]] = ..., reason: _Optional[str] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class TradingInstructionTarget(_message.Message):
    __slots__ = ("all_accounts", "account_id", "instance_id", "subject", "service_account_id", "user_group_id")
    ALL_ACCOUNTS_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    all_accounts: bool
    account_id: str
    instance_id: str
    subject: str
    service_account_id: str
    user_group_id: str
    def __init__(self, all_accounts: bool = ..., account_id: _Optional[str] = ..., instance_id: _Optional[str] = ..., subject: _Optional[str] = ..., service_account_id: _Optional[str] = ..., user_group_id: _Optional[str] = ...) -> None: ...

class Locate(_message.Message):
    __slots__ = ("locate_record_id", "account_id", "instrument_id", "quantity_requested", "answer", "locate_id", "remaining", "uses", "raw_record", "last_change")
    LOCATE_RECORD_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_REQUESTED_FIELD_NUMBER: _ClassVar[int]
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    LOCATE_ID_FIELD_NUMBER: _ClassVar[int]
    REMAINING_FIELD_NUMBER: _ClassVar[int]
    USES_FIELD_NUMBER: _ClassVar[int]
    RAW_RECORD_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    locate_record_id: str
    account_id: str
    instrument_id: str
    quantity_requested: Decimal
    answer: LocateAnswer
    locate_id: str
    remaining: Decimal
    uses: _containers.RepeatedCompositeFieldContainer[LocateUse]
    raw_record: RawRecordRef
    last_change: JournalRef
    def __init__(self, locate_record_id: _Optional[str] = ..., account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., quantity_requested: _Optional[_Union[Decimal, _Mapping]] = ..., answer: _Optional[_Union[LocateAnswer, _Mapping]] = ..., locate_id: _Optional[str] = ..., remaining: _Optional[_Union[Decimal, _Mapping]] = ..., uses: _Optional[_Iterable[_Union[LocateUse, _Mapping]]] = ..., raw_record: _Optional[_Union[RawRecordRef, _Mapping]] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class LocateUse(_message.Message):
    __slots__ = ("kind", "quantity", "order_id")
    KIND_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    kind: LocateUseKind
    quantity: Decimal
    order_id: str
    def __init__(self, kind: _Optional[_Union[LocateUseKind, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., order_id: _Optional[str] = ...) -> None: ...

class VenueCatalogue(_message.Message):
    __slots__ = ("connectivity_instance_id", "venue_account_code", "order_types", "strategies", "eligibility", "execution_acknowledgement", "environment", "placement_types")
    CONNECTIVITY_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPES_FIELD_NUMBER: _ClassVar[int]
    STRATEGIES_FIELD_NUMBER: _ClassVar[int]
    ELIGIBILITY_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_ACKNOWLEDGEMENT_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_TYPES_FIELD_NUMBER: _ClassVar[int]
    connectivity_instance_id: str
    venue_account_code: str
    order_types: _containers.RepeatedCompositeFieldContainer[VenueOrderType]
    strategies: _containers.RepeatedCompositeFieldContainer[VenueStrategy]
    eligibility: _containers.RepeatedCompositeFieldContainer[VenueEligibility]
    execution_acknowledgement: ExecutionAcknowledgement
    environment: str
    placement_types: _containers.RepeatedScalarFieldContainer[PlacementType]
    def __init__(self, connectivity_instance_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., order_types: _Optional[_Iterable[_Union[VenueOrderType, _Mapping]]] = ..., strategies: _Optional[_Iterable[_Union[VenueStrategy, _Mapping]]] = ..., eligibility: _Optional[_Iterable[_Union[VenueEligibility, _Mapping]]] = ..., execution_acknowledgement: _Optional[_Union[ExecutionAcknowledgement, str]] = ..., environment: _Optional[str] = ..., placement_types: _Optional[_Iterable[_Union[PlacementType, str]]] = ...) -> None: ...

class VenueOrderType(_message.Message):
    __slots__ = ("order_type", "times_in_force", "stated_at_ns")
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    TIMES_IN_FORCE_FIELD_NUMBER: _ClassVar[int]
    STATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    order_type: OrderType
    times_in_force: _containers.RepeatedScalarFieldContainer[TimeInForce]
    stated_at_ns: int
    def __init__(self, order_type: _Optional[_Union[OrderType, str]] = ..., times_in_force: _Optional[_Iterable[_Union[TimeInForce, str]]] = ..., stated_at_ns: _Optional[int] = ...) -> None: ...

class VenueStrategy(_message.Message):
    __slots__ = ("kind", "name", "stated_at_ns", "parameters")
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    kind: StrategyKind
    name: str
    stated_at_ns: int
    parameters: _containers.RepeatedCompositeFieldContainer[StrategyParameter]
    def __init__(self, kind: _Optional[_Union[StrategyKind, str]] = ..., name: _Optional[str] = ..., stated_at_ns: _Optional[int] = ..., parameters: _Optional[_Iterable[_Union[StrategyParameter, _Mapping]]] = ...) -> None: ...

class StrategyParameter(_message.Message):
    __slots__ = ("name", "type", "required", "min_value", "max_value", "allowed_values", "default_value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    MIN_VALUE_FIELD_NUMBER: _ClassVar[int]
    MAX_VALUE_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_VALUES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: StrategyParameterType
    required: bool
    min_value: str
    max_value: str
    allowed_values: _containers.RepeatedScalarFieldContainer[str]
    default_value: str
    def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[StrategyParameterType, str]] = ..., required: bool = ..., min_value: _Optional[str] = ..., max_value: _Optional[str] = ..., allowed_values: _Optional[_Iterable[str]] = ..., default_value: _Optional[str] = ...) -> None: ...

class VenueEligibility(_message.Message):
    __slots__ = ("instrument_id", "fractionable", "shortable", "stated_at_ns", "borrow_status", "options_level")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    FRACTIONABLE_FIELD_NUMBER: _ClassVar[int]
    SHORTABLE_FIELD_NUMBER: _ClassVar[int]
    STATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    BORROW_STATUS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_LEVEL_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    fractionable: bool
    shortable: bool
    stated_at_ns: int
    borrow_status: BorrowStatus
    options_level: int
    def __init__(self, instrument_id: _Optional[str] = ..., fractionable: bool = ..., shortable: bool = ..., stated_at_ns: _Optional[int] = ..., borrow_status: _Optional[_Union[BorrowStatus, str]] = ..., options_level: _Optional[int] = ...) -> None: ...

class VenueAccountMapping(_message.Message):
    __slots__ = ("connectivity_instance_id", "venue_account_code", "account_id")
    CONNECTIVITY_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ACCOUNT_CODE_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    connectivity_instance_id: str
    venue_account_code: str
    account_id: str
    def __init__(self, connectivity_instance_id: _Optional[str] = ..., venue_account_code: _Optional[str] = ..., account_id: _Optional[str] = ...) -> None: ...

class NewOrderFromExecutions(_message.Message):
    __slots__ = ("sleeve", "note")
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    sleeve: str
    note: str
    def __init__(self, sleeve: _Optional[str] = ..., note: _Optional[str] = ...) -> None: ...

class Allocation(_message.Message):
    __slots__ = ("allocation_id", "account_id", "sleeve", "quantity", "average_price", "gross_amount", "fees", "net_amount", "intended_settlement_date", "average_priced", "relieve_lot_ids", "reason", "error_cause", "error_text", "give_up_answers")
    ALLOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SLEEVE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_PRICE_FIELD_NUMBER: _ClassVar[int]
    GROSS_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    FEES_FIELD_NUMBER: _ClassVar[int]
    NET_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    INTENDED_SETTLEMENT_DATE_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_PRICED_FIELD_NUMBER: _ClassVar[int]
    RELIEVE_LOT_IDS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ERROR_CAUSE_FIELD_NUMBER: _ClassVar[int]
    ERROR_TEXT_FIELD_NUMBER: _ClassVar[int]
    GIVE_UP_ANSWERS_FIELD_NUMBER: _ClassVar[int]
    allocation_id: str
    account_id: str
    sleeve: str
    quantity: Decimal
    average_price: Money
    gross_amount: Money
    fees: _containers.RepeatedCompositeFieldContainer[Fee]
    net_amount: Money
    intended_settlement_date: str
    average_priced: bool
    relieve_lot_ids: _containers.RepeatedScalarFieldContainer[str]
    reason: str
    error_cause: ErrorCause
    error_text: str
    give_up_answers: _containers.RepeatedCompositeFieldContainer[GiveUpRecord]
    def __init__(self, allocation_id: _Optional[str] = ..., account_id: _Optional[str] = ..., sleeve: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., average_price: _Optional[_Union[Money, _Mapping]] = ..., gross_amount: _Optional[_Union[Money, _Mapping]] = ..., fees: _Optional[_Iterable[_Union[Fee, _Mapping]]] = ..., net_amount: _Optional[_Union[Money, _Mapping]] = ..., intended_settlement_date: _Optional[str] = ..., average_priced: bool = ..., relieve_lot_ids: _Optional[_Iterable[str]] = ..., reason: _Optional[str] = ..., error_cause: _Optional[_Union[ErrorCause, str]] = ..., error_text: _Optional[str] = ..., give_up_answers: _Optional[_Iterable[_Union[GiveUpRecord, _Mapping]]] = ...) -> None: ...

class Booking(_message.Message):
    __slots__ = ("booking_id", "order_id", "account_id", "execution_ids", "allocations", "state", "held_reason", "last_change")
    BOOKING_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_IDS_FIELD_NUMBER: _ClassVar[int]
    ALLOCATIONS_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    HELD_REASON_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    booking_id: str
    order_id: str
    account_id: str
    execution_ids: _containers.RepeatedScalarFieldContainer[str]
    allocations: _containers.RepeatedCompositeFieldContainer[Allocation]
    state: BookingState
    held_reason: str
    last_change: JournalRef
    def __init__(self, booking_id: _Optional[str] = ..., order_id: _Optional[str] = ..., account_id: _Optional[str] = ..., execution_ids: _Optional[_Iterable[str]] = ..., allocations: _Optional[_Iterable[_Union[Allocation, _Mapping]]] = ..., state: _Optional[_Union[BookingState, str]] = ..., held_reason: _Optional[str] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class SleeveCross(_message.Message):
    __slots__ = ("sleeve_cross_id", "account_id", "instrument_id", "giving_sleeve", "receiving_sleeve", "quantity", "cross_price", "price_source", "order_ids", "reason")
    SLEEVE_CROSS_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    GIVING_SLEEVE_FIELD_NUMBER: _ClassVar[int]
    RECEIVING_SLEEVE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    CROSS_PRICE_FIELD_NUMBER: _ClassVar[int]
    PRICE_SOURCE_FIELD_NUMBER: _ClassVar[int]
    ORDER_IDS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    sleeve_cross_id: str
    account_id: str
    instrument_id: str
    giving_sleeve: str
    receiving_sleeve: str
    quantity: Decimal
    cross_price: Money
    price_source: str
    order_ids: _containers.RepeatedScalarFieldContainer[str]
    reason: str
    def __init__(self, sleeve_cross_id: _Optional[str] = ..., account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., giving_sleeve: _Optional[str] = ..., receiving_sleeve: _Optional[str] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., cross_price: _Optional[_Union[Money, _Mapping]] = ..., price_source: _Optional[str] = ..., order_ids: _Optional[_Iterable[str]] = ..., reason: _Optional[str] = ...) -> None: ...

class AlertSubject(_message.Message):
    __slots__ = ("order_id", "booking_id", "allocation_id", "position")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    BOOKING_ID_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    booking_id: str
    allocation_id: str
    position: PositionKey
    def __init__(self, order_id: _Optional[str] = ..., booking_id: _Optional[str] = ..., allocation_id: _Optional[str] = ..., position: _Optional[_Union[PositionKey, _Mapping]] = ...) -> None: ...

class Alert(_message.Message):
    __slots__ = ("alert_id", "account_id", "kind", "state", "reason", "subject", "due_by", "last_change")
    ALERT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    DUE_BY_FIELD_NUMBER: _ClassVar[int]
    LAST_CHANGE_FIELD_NUMBER: _ClassVar[int]
    alert_id: str
    account_id: str
    kind: AlertKind
    state: AlertState
    reason: str
    subject: AlertSubject
    due_by: int
    last_change: JournalRef
    def __init__(self, alert_id: _Optional[str] = ..., account_id: _Optional[str] = ..., kind: _Optional[_Union[AlertKind, str]] = ..., state: _Optional[_Union[AlertState, str]] = ..., reason: _Optional[str] = ..., subject: _Optional[_Union[AlertSubject, _Mapping]] = ..., due_by: _Optional[int] = ..., last_change: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class VenueRecord(_message.Message):
    __slots__ = ("venue_id", "name", "country_code", "kind", "identifiers", "operating_venue_id", "time_zone", "version", "valid_from_ns", "record_time_ns", "lifecycle_state")
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_CODE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    OPERATING_VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    TIME_ZONE_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    RECORD_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    LIFECYCLE_STATE_FIELD_NUMBER: _ClassVar[int]
    venue_id: str
    name: str
    country_code: str
    kind: VenueKind
    identifiers: _containers.RepeatedCompositeFieldContainer[Identifier]
    operating_venue_id: str
    time_zone: str
    version: int
    valid_from_ns: int
    record_time_ns: int
    lifecycle_state: InstrumentLifecycleState
    def __init__(self, venue_id: _Optional[str] = ..., name: _Optional[str] = ..., country_code: _Optional[str] = ..., kind: _Optional[_Union[VenueKind, str]] = ..., identifiers: _Optional[_Iterable[_Union[Identifier, _Mapping]]] = ..., operating_venue_id: _Optional[str] = ..., time_zone: _Optional[str] = ..., version: _Optional[int] = ..., valid_from_ns: _Optional[int] = ..., record_time_ns: _Optional[int] = ..., lifecycle_state: _Optional[_Union[InstrumentLifecycleState, str]] = ...) -> None: ...

class CalendarDay(_message.Message):
    __slots__ = ("date", "kind", "name", "source")
    DATE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    date: str
    kind: CalendarDayKind
    name: str
    source: str
    def __init__(self, date: _Optional[str] = ..., kind: _Optional[_Union[CalendarDayKind, str]] = ..., name: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...

class CalendarWeekend(_message.Message):
    __slots__ = ("weekdays", "valid_from_date")
    WEEKDAYS_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_DATE_FIELD_NUMBER: _ClassVar[int]
    weekdays: _containers.RepeatedScalarFieldContainer[Weekday]
    valid_from_date: str
    def __init__(self, weekdays: _Optional[_Iterable[_Union[Weekday, str]]] = ..., valid_from_date: _Optional[str] = ...) -> None: ...

class CalendarCoverage(_message.Message):
    __slots__ = ("from_date", "to_date")
    FROM_DATE_FIELD_NUMBER: _ClassVar[int]
    TO_DATE_FIELD_NUMBER: _ClassVar[int]
    from_date: str
    to_date: str
    def __init__(self, from_date: _Optional[str] = ..., to_date: _Optional[str] = ...) -> None: ...

class CalendarSource(_message.Message):
    __slots__ = ("source_id", "name", "address", "read_at_ns")
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    READ_AT_NS_FIELD_NUMBER: _ClassVar[int]
    source_id: str
    name: str
    address: str
    read_at_ns: int
    def __init__(self, source_id: _Optional[str] = ..., name: _Optional[str] = ..., address: _Optional[str] = ..., read_at_ns: _Optional[int] = ...) -> None: ...

class TradingSessions(_message.Message):
    __slots__ = ("time_zone", "sessions", "early_closes")
    TIME_ZONE_FIELD_NUMBER: _ClassVar[int]
    SESSIONS_FIELD_NUMBER: _ClassVar[int]
    EARLY_CLOSES_FIELD_NUMBER: _ClassVar[int]
    time_zone: str
    sessions: _containers.RepeatedCompositeFieldContainer[TradingSession]
    early_closes: _containers.RepeatedCompositeFieldContainer[TradingSessionDay]
    def __init__(self, time_zone: _Optional[str] = ..., sessions: _Optional[_Iterable[_Union[TradingSession, _Mapping]]] = ..., early_closes: _Optional[_Iterable[_Union[TradingSessionDay, _Mapping]]] = ...) -> None: ...

class TradingSession(_message.Message):
    __slots__ = ("weekdays", "start_minute", "end_minute", "extended")
    WEEKDAYS_FIELD_NUMBER: _ClassVar[int]
    START_MINUTE_FIELD_NUMBER: _ClassVar[int]
    END_MINUTE_FIELD_NUMBER: _ClassVar[int]
    EXTENDED_FIELD_NUMBER: _ClassVar[int]
    weekdays: _containers.RepeatedScalarFieldContainer[Weekday]
    start_minute: int
    end_minute: int
    extended: bool
    def __init__(self, weekdays: _Optional[_Iterable[_Union[Weekday, str]]] = ..., start_minute: _Optional[int] = ..., end_minute: _Optional[int] = ..., extended: bool = ...) -> None: ...

class TradingSessionDay(_message.Message):
    __slots__ = ("date", "sessions", "source")
    DATE_FIELD_NUMBER: _ClassVar[int]
    SESSIONS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    date: str
    sessions: _containers.RepeatedCompositeFieldContainer[TradingSession]
    source: str
    def __init__(self, date: _Optional[str] = ..., sessions: _Optional[_Iterable[_Union[TradingSession, _Mapping]]] = ..., source: _Optional[str] = ...) -> None: ...

class SettlementDateInputs(_message.Message):
    __slots__ = ("instrument_id", "trade_date")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    trade_date: str
    def __init__(self, instrument_id: _Optional[str] = ..., trade_date: _Optional[str] = ...) -> None: ...

class SpotDateInputs(_message.Message):
    __slots__ = ("pair", "trade_date", "at_ns")
    PAIR_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    pair: _containers.RepeatedScalarFieldContainer[str]
    trade_date: str
    at_ns: int
    def __init__(self, pair: _Optional[_Iterable[str]] = ..., trade_date: _Optional[str] = ..., at_ns: _Optional[int] = ...) -> None: ...

class TenorDateInputs(_message.Message):
    __slots__ = ("pair", "tenor", "trade_date")
    PAIR_FIELD_NUMBER: _ClassVar[int]
    TENOR_FIELD_NUMBER: _ClassVar[int]
    TRADE_DATE_FIELD_NUMBER: _ClassVar[int]
    pair: _containers.RepeatedScalarFieldContainer[str]
    tenor: Tenor
    trade_date: str
    def __init__(self, pair: _Optional[_Iterable[str]] = ..., tenor: _Optional[_Union[Tenor, _Mapping]] = ..., trade_date: _Optional[str] = ...) -> None: ...

class Tenor(_message.Message):
    __slots__ = ("count", "unit")
    COUNT_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    count: int
    unit: TenorUnit
    def __init__(self, count: _Optional[int] = ..., unit: _Optional[_Union[TenorUnit, str]] = ...) -> None: ...

class RollInputs(_message.Message):
    __slots__ = ("date", "convention", "calendars")
    DATE_FIELD_NUMBER: _ClassVar[int]
    CONVENTION_FIELD_NUMBER: _ClassVar[int]
    CALENDARS_FIELD_NUMBER: _ClassVar[int]
    date: str
    convention: BusinessDayConvention
    calendars: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, date: _Optional[str] = ..., convention: _Optional[_Union[BusinessDayConvention, str]] = ..., calendars: _Optional[_Iterable[str]] = ...) -> None: ...

class BusinessDayInputs(_message.Message):
    __slots__ = ("date", "calendars")
    DATE_FIELD_NUMBER: _ClassVar[int]
    CALENDARS_FIELD_NUMBER: _ClassVar[int]
    date: str
    calendars: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, date: _Optional[str] = ..., calendars: _Optional[_Iterable[str]] = ...) -> None: ...

class InstrumentReplacedEvent(_message.Message):
    __slots__ = ("replaced_instrument_id", "instrument", "replaced_at_ns", "cause", "sequence")
    REPLACED_INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_FIELD_NUMBER: _ClassVar[int]
    REPLACED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    replaced_instrument_id: str
    instrument: InstrumentRecord
    replaced_at_ns: int
    cause: ReplacementCause
    sequence: int
    def __init__(self, replaced_instrument_id: _Optional[str] = ..., instrument: _Optional[_Union[InstrumentRecord, _Mapping]] = ..., replaced_at_ns: _Optional[int] = ..., cause: _Optional[_Union[ReplacementCause, str]] = ..., sequence: _Optional[int] = ...) -> None: ...

class TemplateFieldValue(_message.Message):
    __slots__ = ("path", "value", "provenance")
    PATH_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    path: str
    value: str
    provenance: Provenance
    def __init__(self, path: _Optional[str] = ..., value: _Optional[str] = ..., provenance: _Optional[_Union[Provenance, _Mapping]] = ...) -> None: ...

class SecurityTemplate(_message.Message):
    __slots__ = ("template_id", "template_version", "name", "asset_class", "instrument_type", "base", "calculation", "fields", "match_rule", "calculation_package")
    TEMPLATE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ASSET_CLASS_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    CALCULATION_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    MATCH_RULE_FIELD_NUMBER: _ClassVar[int]
    CALCULATION_PACKAGE_FIELD_NUMBER: _ClassVar[int]
    template_id: str
    template_version: str
    name: str
    asset_class: AssetClass
    instrument_type: InstrumentType
    base: bool
    calculation: str
    fields: _containers.RepeatedCompositeFieldContainer[TemplateField]
    match_rule: _containers.RepeatedScalarFieldContainer[str]
    calculation_package: CalculationPackage
    def __init__(self, template_id: _Optional[str] = ..., template_version: _Optional[str] = ..., name: _Optional[str] = ..., asset_class: _Optional[_Union[AssetClass, str]] = ..., instrument_type: _Optional[_Union[InstrumentType, str]] = ..., base: bool = ..., calculation: _Optional[str] = ..., fields: _Optional[_Iterable[_Union[TemplateField, _Mapping]]] = ..., match_rule: _Optional[_Iterable[str]] = ..., calculation_package: _Optional[_Union[CalculationPackage, _Mapping]] = ...) -> None: ...

class TemplateField(_message.Message):
    __slots__ = ("path", "type", "required")
    PATH_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    path: str
    type: str
    required: bool
    def __init__(self, path: _Optional[str] = ..., type: _Optional[str] = ..., required: bool = ...) -> None: ...

class CalculationPackage(_message.Message):
    __slots__ = ("model_id", "model_version", "pricing_inputs", "corporate_action_factors", "calculation_version", "test_cases")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    PRICING_INPUTS_FIELD_NUMBER: _ClassVar[int]
    CORPORATE_ACTION_FACTORS_FIELD_NUMBER: _ClassVar[int]
    CALCULATION_VERSION_FIELD_NUMBER: _ClassVar[int]
    TEST_CASES_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    model_version: int
    pricing_inputs: _containers.RepeatedScalarFieldContainer[str]
    corporate_action_factors: str
    calculation_version: str
    test_cases: _containers.RepeatedCompositeFieldContainer[CalculationTestCase]
    def __init__(self, model_id: _Optional[str] = ..., model_version: _Optional[int] = ..., pricing_inputs: _Optional[_Iterable[str]] = ..., corporate_action_factors: _Optional[str] = ..., calculation_version: _Optional[str] = ..., test_cases: _Optional[_Iterable[_Union[CalculationTestCase, _Mapping]]] = ...) -> None: ...

class CalculationTestCase(_message.Message):
    __slots__ = ("name", "inputs", "expected")
    NAME_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_FIELD_NUMBER: _ClassVar[int]
    name: str
    inputs: str
    expected: str
    def __init__(self, name: _Optional[str] = ..., inputs: _Optional[str] = ..., expected: _Optional[str] = ...) -> None: ...

class Price(_message.Message):
    __slots__ = ("meta", "kind", "price", "basis")
    META_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    BASIS_FIELD_NUMBER: _ClassVar[int]
    meta: ObservationMeta
    kind: PriceKind
    price: Money
    basis: PriceBasis
    def __init__(self, meta: _Optional[_Union[ObservationMeta, _Mapping]] = ..., kind: _Optional[_Union[PriceKind, str]] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., basis: _Optional[_Union[PriceBasis, str]] = ...) -> None: ...

class ObservationMeta(_message.Message):
    __slots__ = ("row_key", "subjects", "source", "valid_from_ns", "valid_until_ns", "business_date", "source_times", "sent_at_ns", "recorded_at_ns", "version", "sequence", "previous_sequence", "raw", "unconverted", "closed_day")
    ROW_KEY_FIELD_NUMBER: _ClassVar[int]
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TIMES_FIELD_NUMBER: _ClassVar[int]
    SENT_AT_NS_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    RAW_FIELD_NUMBER: _ClassVar[int]
    UNCONVERTED_FIELD_NUMBER: _ClassVar[int]
    CLOSED_DAY_FIELD_NUMBER: _ClassVar[int]
    row_key: str
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    source: Source
    valid_from_ns: int
    valid_until_ns: int
    business_date: str
    source_times: _containers.RepeatedCompositeFieldContainer[SourceTime]
    sent_at_ns: int
    recorded_at_ns: int
    version: int
    sequence: int
    previous_sequence: int
    raw: RawRecordRef
    unconverted: _containers.RepeatedCompositeFieldContainer[AsReported]
    closed_day: DateCheck
    def __init__(self, row_key: _Optional[str] = ..., subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., source: _Optional[_Union[Source, _Mapping]] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., business_date: _Optional[str] = ..., source_times: _Optional[_Iterable[_Union[SourceTime, _Mapping]]] = ..., sent_at_ns: _Optional[int] = ..., recorded_at_ns: _Optional[int] = ..., version: _Optional[int] = ..., sequence: _Optional[int] = ..., previous_sequence: _Optional[int] = ..., raw: _Optional[_Union[RawRecordRef, _Mapping]] = ..., unconverted: _Optional[_Iterable[_Union[AsReported, _Mapping]]] = ..., closed_day: _Optional[_Union[DateCheck, _Mapping]] = ...) -> None: ...

class SubjectRef(_message.Message):
    __slots__ = ("entity_id",)
    ENTITY_ID_FIELD_NUMBER: _ClassVar[int]
    entity_id: str
    def __init__(self, entity_id: _Optional[str] = ...) -> None: ...

class Source(_message.Message):
    __slots__ = ("instance", "plugin_version", "dataset", "venue_id")
    INSTANCE_FIELD_NUMBER: _ClassVar[int]
    PLUGIN_VERSION_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    instance: str
    plugin_version: str
    dataset: str
    venue_id: str
    def __init__(self, instance: _Optional[str] = ..., plugin_version: _Optional[str] = ..., dataset: _Optional[str] = ..., venue_id: _Optional[str] = ...) -> None: ...

class SourceTime(_message.Message):
    __slots__ = ("kind", "at_ns")
    KIND_FIELD_NUMBER: _ClassVar[int]
    AT_NS_FIELD_NUMBER: _ClassVar[int]
    kind: SourceTimeKind
    at_ns: int
    def __init__(self, kind: _Optional[_Union[SourceTimeKind, str]] = ..., at_ns: _Optional[int] = ...) -> None: ...

class Bar(_message.Message):
    __slots__ = ("meta", "open", "high", "low", "close", "volume", "vwap", "trade_count")
    META_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    VWAP_FIELD_NUMBER: _ClassVar[int]
    TRADE_COUNT_FIELD_NUMBER: _ClassVar[int]
    meta: ObservationMeta
    open: Money
    high: Money
    low: Money
    close: Money
    volume: Decimal
    vwap: Money
    trade_count: int
    def __init__(self, meta: _Optional[_Union[ObservationMeta, _Mapping]] = ..., open: _Optional[_Union[Money, _Mapping]] = ..., high: _Optional[_Union[Money, _Mapping]] = ..., low: _Optional[_Union[Money, _Mapping]] = ..., close: _Optional[_Union[Money, _Mapping]] = ..., volume: _Optional[_Union[Decimal, _Mapping]] = ..., vwap: _Optional[_Union[Money, _Mapping]] = ..., trade_count: _Optional[int] = ...) -> None: ...

class Trade(_message.Message):
    __slots__ = ("meta", "price", "quantity", "attributes", "aggressor", "source_sequence", "cancelled")
    META_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    AGGRESSOR_FIELD_NUMBER: _ClassVar[int]
    SOURCE_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    CANCELLED_FIELD_NUMBER: _ClassVar[int]
    meta: ObservationMeta
    price: Money
    quantity: Decimal
    attributes: TradeAttributes
    aggressor: Aggressor
    source_sequence: int
    cancelled: bool
    def __init__(self, meta: _Optional[_Union[ObservationMeta, _Mapping]] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., attributes: _Optional[_Union[TradeAttributes, _Mapping]] = ..., aggressor: _Optional[_Union[Aggressor, str]] = ..., source_sequence: _Optional[int] = ..., cancelled: bool = ...) -> None: ...

class TradeAttributes(_message.Message):
    __slots__ = ("consolidated", "market_centre", "characteristics")
    CONSOLIDATED_FIELD_NUMBER: _ClassVar[int]
    MARKET_CENTRE_FIELD_NUMBER: _ClassVar[int]
    CHARACTERISTICS_FIELD_NUMBER: _ClassVar[int]
    consolidated: Eligibility
    market_centre: Eligibility
    characteristics: _containers.RepeatedScalarFieldContainer[TradeCharacteristic]
    def __init__(self, consolidated: _Optional[_Union[Eligibility, _Mapping]] = ..., market_centre: _Optional[_Union[Eligibility, _Mapping]] = ..., characteristics: _Optional[_Iterable[_Union[TradeCharacteristic, str]]] = ...) -> None: ...

class Eligibility(_message.Message):
    __slots__ = ("high_low", "open", "close", "volume")
    HIGH_LOW_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    high_low: Eligible
    open: Eligible
    close: Eligible
    volume: Eligible
    def __init__(self, high_low: _Optional[_Union[Eligible, str]] = ..., open: _Optional[_Union[Eligible, str]] = ..., close: _Optional[_Union[Eligible, str]] = ..., volume: _Optional[_Union[Eligible, str]] = ...) -> None: ...

class Quote(_message.Message):
    __slots__ = ("meta", "bid", "ask", "bid_quantity", "ask_quantity", "characteristics")
    META_FIELD_NUMBER: _ClassVar[int]
    BID_FIELD_NUMBER: _ClassVar[int]
    ASK_FIELD_NUMBER: _ClassVar[int]
    BID_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    ASK_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    CHARACTERISTICS_FIELD_NUMBER: _ClassVar[int]
    meta: ObservationMeta
    bid: Money
    ask: Money
    bid_quantity: Decimal
    ask_quantity: Decimal
    characteristics: _containers.RepeatedScalarFieldContainer[QuoteCharacteristic]
    def __init__(self, meta: _Optional[_Union[ObservationMeta, _Mapping]] = ..., bid: _Optional[_Union[Money, _Mapping]] = ..., ask: _Optional[_Union[Money, _Mapping]] = ..., bid_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., ask_quantity: _Optional[_Union[Decimal, _Mapping]] = ..., characteristics: _Optional[_Iterable[_Union[QuoteCharacteristic, str]]] = ...) -> None: ...

class Outcome(_message.Message):
    __slots__ = ("meta", "determination", "stage", "settlement_value", "settled_at_ns", "determination_as_reported", "challenge_ends_at_ns")
    META_FIELD_NUMBER: _ClassVar[int]
    DETERMINATION_FIELD_NUMBER: _ClassVar[int]
    STAGE_FIELD_NUMBER: _ClassVar[int]
    SETTLEMENT_VALUE_FIELD_NUMBER: _ClassVar[int]
    SETTLED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    DETERMINATION_AS_REPORTED_FIELD_NUMBER: _ClassVar[int]
    CHALLENGE_ENDS_AT_NS_FIELD_NUMBER: _ClassVar[int]
    meta: ObservationMeta
    determination: OutcomeDetermination
    stage: OutcomeStage
    settlement_value: Money
    settled_at_ns: int
    determination_as_reported: AsReported
    challenge_ends_at_ns: int
    def __init__(self, meta: _Optional[_Union[ObservationMeta, _Mapping]] = ..., determination: _Optional[_Union[OutcomeDetermination, str]] = ..., stage: _Optional[_Union[OutcomeStage, str]] = ..., settlement_value: _Optional[_Union[Money, _Mapping]] = ..., settled_at_ns: _Optional[int] = ..., determination_as_reported: _Optional[_Union[AsReported, _Mapping]] = ..., challenge_ends_at_ns: _Optional[int] = ...) -> None: ...

class SourceChoice(_message.Message):
    __slots__ = ("default", "named", "side_by_side")
    DEFAULT_FIELD_NUMBER: _ClassVar[int]
    NAMED_FIELD_NUMBER: _ClassVar[int]
    SIDE_BY_SIDE_FIELD_NUMBER: _ClassVar[int]
    default: bool
    named: _containers.RepeatedScalarFieldContainer[str]
    side_by_side: bool
    def __init__(self, default: bool = ..., named: _Optional[_Iterable[str]] = ..., side_by_side: bool = ...) -> None: ...

class Unanswered(_message.Message):
    __slots__ = ("subject", "dataset", "field", "reason")
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    subject: SubjectRef
    dataset: str
    field: str
    reason: UnansweredReason
    def __init__(self, subject: _Optional[_Union[SubjectRef, _Mapping]] = ..., dataset: _Optional[str] = ..., field: _Optional[str] = ..., reason: _Optional[_Union[UnansweredReason, str]] = ...) -> None: ...

class DatasetRef(_message.Message):
    __slots__ = ("dataset", "instance", "vendor", "aggregator", "declaration", "unconverted_count", "miss_count", "closed_day_count", "outside_coverage_count", "declared_delay_ns", "stale_after_ns", "liveness")
    DATASET_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_FIELD_NUMBER: _ClassVar[int]
    VENDOR_FIELD_NUMBER: _ClassVar[int]
    AGGREGATOR_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    UNCONVERTED_COUNT_FIELD_NUMBER: _ClassVar[int]
    MISS_COUNT_FIELD_NUMBER: _ClassVar[int]
    CLOSED_DAY_COUNT_FIELD_NUMBER: _ClassVar[int]
    OUTSIDE_COVERAGE_COUNT_FIELD_NUMBER: _ClassVar[int]
    DECLARED_DELAY_NS_FIELD_NUMBER: _ClassVar[int]
    STALE_AFTER_NS_FIELD_NUMBER: _ClassVar[int]
    LIVENESS_FIELD_NUMBER: _ClassVar[int]
    dataset: str
    instance: str
    vendor: str
    aggregator: str
    declaration: DatasetDeclaration
    unconverted_count: int
    miss_count: int
    closed_day_count: int
    outside_coverage_count: int
    declared_delay_ns: int
    stale_after_ns: int
    liveness: _containers.RepeatedCompositeFieldContainer[DatasetLiveness]
    def __init__(self, dataset: _Optional[str] = ..., instance: _Optional[str] = ..., vendor: _Optional[str] = ..., aggregator: _Optional[str] = ..., declaration: _Optional[_Union[DatasetDeclaration, _Mapping]] = ..., unconverted_count: _Optional[int] = ..., miss_count: _Optional[int] = ..., closed_day_count: _Optional[int] = ..., outside_coverage_count: _Optional[int] = ..., declared_delay_ns: _Optional[int] = ..., stale_after_ns: _Optional[int] = ..., liveness: _Optional[_Iterable[_Union[DatasetLiveness, _Mapping]]] = ...) -> None: ...

class DatasetDeclaration(_message.Message):
    __slots__ = ("key", "vendor", "aggregator", "data_types", "modes", "cadence", "history", "licence_default", "day_time_zone", "day_end_minute", "venue_id", "calendar_id", "declared_delay_ns")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VENDOR_FIELD_NUMBER: _ClassVar[int]
    AGGREGATOR_FIELD_NUMBER: _ClassVar[int]
    DATA_TYPES_FIELD_NUMBER: _ClassVar[int]
    MODES_FIELD_NUMBER: _ClassVar[int]
    CADENCE_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FIELD_NUMBER: _ClassVar[int]
    LICENCE_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    DAY_TIME_ZONE_FIELD_NUMBER: _ClassVar[int]
    DAY_END_MINUTE_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    CALENDAR_ID_FIELD_NUMBER: _ClassVar[int]
    DECLARED_DELAY_NS_FIELD_NUMBER: _ClassVar[int]
    key: str
    vendor: str
    aggregator: str
    data_types: _containers.RepeatedScalarFieldContainer[str]
    modes: _containers.RepeatedScalarFieldContainer[ObservationMode]
    cadence: int
    history: int
    licence_default: DatasetLicence
    day_time_zone: str
    day_end_minute: int
    venue_id: str
    calendar_id: str
    declared_delay_ns: int
    def __init__(self, key: _Optional[str] = ..., vendor: _Optional[str] = ..., aggregator: _Optional[str] = ..., data_types: _Optional[_Iterable[str]] = ..., modes: _Optional[_Iterable[_Union[ObservationMode, str]]] = ..., cadence: _Optional[int] = ..., history: _Optional[int] = ..., licence_default: _Optional[_Union[DatasetLicence, _Mapping]] = ..., day_time_zone: _Optional[str] = ..., day_end_minute: _Optional[int] = ..., venue_id: _Optional[str] = ..., calendar_id: _Optional[str] = ..., declared_delay_ns: _Optional[int] = ...) -> None: ...

class DatasetLicence(_message.Message):
    __slots__ = ("dataset", "kept", "retention_days", "derived_use", "display", "default_fields", "personal_use", "updated_by", "updated_at_ns", "acting_through_delegation", "client_name", "note", "prepared_call_id", "terms_version", "access_basis", "timeliness", "delay_minutes", "delay_label", "underlying_source", "meters", "display_terms", "non_display", "enterprise", "derived_use_terms", "derived_multi_instrument_free", "derived_creation_is_non_display", "redistribution", "outside_computation", "prohibited_uses", "attribution_required", "attribution_text", "copyright_class", "no_more_restrictive_terms", "not_affiliated_notice", "report_cadence", "report_due_day")
    DATASET_FIELD_NUMBER: _ClassVar[int]
    KEPT_FIELD_NUMBER: _ClassVar[int]
    RETENTION_DAYS_FIELD_NUMBER: _ClassVar[int]
    DERIVED_USE_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_FIELDS_FIELD_NUMBER: _ClassVar[int]
    PERSONAL_USE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ACTING_THROUGH_DELEGATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    PREPARED_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    TERMS_VERSION_FIELD_NUMBER: _ClassVar[int]
    ACCESS_BASIS_FIELD_NUMBER: _ClassVar[int]
    TIMELINESS_FIELD_NUMBER: _ClassVar[int]
    DELAY_MINUTES_FIELD_NUMBER: _ClassVar[int]
    DELAY_LABEL_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_SOURCE_FIELD_NUMBER: _ClassVar[int]
    METERS_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_TERMS_FIELD_NUMBER: _ClassVar[int]
    NON_DISPLAY_FIELD_NUMBER: _ClassVar[int]
    ENTERPRISE_FIELD_NUMBER: _ClassVar[int]
    DERIVED_USE_TERMS_FIELD_NUMBER: _ClassVar[int]
    DERIVED_MULTI_INSTRUMENT_FREE_FIELD_NUMBER: _ClassVar[int]
    DERIVED_CREATION_IS_NON_DISPLAY_FIELD_NUMBER: _ClassVar[int]
    REDISTRIBUTION_FIELD_NUMBER: _ClassVar[int]
    OUTSIDE_COMPUTATION_FIELD_NUMBER: _ClassVar[int]
    PROHIBITED_USES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_REQUIRED_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTION_TEXT_FIELD_NUMBER: _ClassVar[int]
    COPYRIGHT_CLASS_FIELD_NUMBER: _ClassVar[int]
    NO_MORE_RESTRICTIVE_TERMS_FIELD_NUMBER: _ClassVar[int]
    NOT_AFFILIATED_NOTICE_FIELD_NUMBER: _ClassVar[int]
    REPORT_CADENCE_FIELD_NUMBER: _ClassVar[int]
    REPORT_DUE_DAY_FIELD_NUMBER: _ClassVar[int]
    dataset: str
    kept: bool
    retention_days: int
    derived_use: bool
    display: bool
    default_fields: _containers.RepeatedScalarFieldContainer[str]
    personal_use: bool
    updated_by: str
    updated_at_ns: int
    acting_through_delegation: str
    client_name: str
    note: str
    prepared_call_id: str
    terms_version: str
    access_basis: AccessBasis
    timeliness: Timeliness
    delay_minutes: int
    delay_label: str
    underlying_source: str
    meters: _containers.RepeatedScalarFieldContainer[LicenceMeter]
    display_terms: DisplayTerms
    non_display: NonDisplayTerms
    enterprise: EnterpriseTerms
    derived_use_terms: DerivedUse
    derived_multi_instrument_free: bool
    derived_creation_is_non_display: bool
    redistribution: Redistribution
    outside_computation: OutsideComputation
    prohibited_uses: _containers.RepeatedScalarFieldContainer[ProhibitedUse]
    attribution_required: bool
    attribution_text: str
    copyright_class: CopyrightClass
    no_more_restrictive_terms: bool
    not_affiliated_notice: str
    report_cadence: ReportCadence
    report_due_day: int
    def __init__(self, dataset: _Optional[str] = ..., kept: bool = ..., retention_days: _Optional[int] = ..., derived_use: bool = ..., display: bool = ..., default_fields: _Optional[_Iterable[str]] = ..., personal_use: bool = ..., updated_by: _Optional[str] = ..., updated_at_ns: _Optional[int] = ..., acting_through_delegation: _Optional[str] = ..., client_name: _Optional[str] = ..., note: _Optional[str] = ..., prepared_call_id: _Optional[str] = ..., terms_version: _Optional[str] = ..., access_basis: _Optional[_Union[AccessBasis, str]] = ..., timeliness: _Optional[_Union[Timeliness, str]] = ..., delay_minutes: _Optional[int] = ..., delay_label: _Optional[str] = ..., underlying_source: _Optional[str] = ..., meters: _Optional[_Iterable[_Union[LicenceMeter, str]]] = ..., display_terms: _Optional[_Union[DisplayTerms, _Mapping]] = ..., non_display: _Optional[_Union[NonDisplayTerms, _Mapping]] = ..., enterprise: _Optional[_Union[EnterpriseTerms, _Mapping]] = ..., derived_use_terms: _Optional[_Union[DerivedUse, str]] = ..., derived_multi_instrument_free: bool = ..., derived_creation_is_non_display: bool = ..., redistribution: _Optional[_Union[Redistribution, str]] = ..., outside_computation: _Optional[_Union[OutsideComputation, str]] = ..., prohibited_uses: _Optional[_Iterable[_Union[ProhibitedUse, str]]] = ..., attribution_required: bool = ..., attribution_text: _Optional[str] = ..., copyright_class: _Optional[_Union[CopyrightClass, str]] = ..., no_more_restrictive_terms: bool = ..., not_affiliated_notice: _Optional[str] = ..., report_cadence: _Optional[_Union[ReportCadence, str]] = ..., report_due_day: _Optional[int] = ...) -> None: ...

class DisplayTerms(_message.Message):
    __slots__ = ("unit", "count_basis", "professional_split", "professional_definition")
    UNIT_FIELD_NUMBER: _ClassVar[int]
    COUNT_BASIS_FIELD_NUMBER: _ClassVar[int]
    PROFESSIONAL_SPLIT_FIELD_NUMBER: _ClassVar[int]
    PROFESSIONAL_DEFINITION_FIELD_NUMBER: _ClassVar[int]
    unit: DisplayUnit
    count_basis: CountBasis
    professional_split: bool
    professional_definition: ProfessionalDefinition
    def __init__(self, unit: _Optional[_Union[DisplayUnit, str]] = ..., count_basis: _Optional[_Union[CountBasis, str]] = ..., professional_split: bool = ..., professional_definition: _Optional[_Union[ProfessionalDefinition, str]] = ...) -> None: ...

class NonDisplayTerms(_message.Message):
    __slots__ = ("categories", "counts", "personal_exempt")
    CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    COUNTS_FIELD_NUMBER: _ClassVar[int]
    PERSONAL_EXEMPT_FIELD_NUMBER: _ClassVar[int]
    categories: _containers.RepeatedScalarFieldContainer[NonDisplayCategory]
    counts: NonDisplayCount
    personal_exempt: bool
    def __init__(self, categories: _Optional[_Iterable[_Union[NonDisplayCategory, str]]] = ..., counts: _Optional[_Union[NonDisplayCount, str]] = ..., personal_exempt: bool = ...) -> None: ...

class EnterpriseTerms(_message.Message):
    __slots__ = ("replaces", "form", "scope", "reporting_waived")
    REPLACES_FIELD_NUMBER: _ClassVar[int]
    FORM_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    REPORTING_WAIVED_FIELD_NUMBER: _ClassVar[int]
    replaces: _containers.RepeatedScalarFieldContainer[EnterpriseReplaces]
    form: EnterpriseForm
    scope: EnterpriseScope
    reporting_waived: bool
    def __init__(self, replaces: _Optional[_Iterable[_Union[EnterpriseReplaces, str]]] = ..., form: _Optional[_Union[EnterpriseForm, str]] = ..., scope: _Optional[_Union[EnterpriseScope, str]] = ..., reporting_waived: bool = ...) -> None: ...

class DatasetLiveness(_message.Message):
    __slots__ = ("dataset", "venue_id", "alive_at_ns", "instance")
    DATASET_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    ALIVE_AT_NS_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_FIELD_NUMBER: _ClassVar[int]
    dataset: str
    venue_id: str
    alive_at_ns: int
    instance: str
    def __init__(self, dataset: _Optional[str] = ..., venue_id: _Optional[str] = ..., alive_at_ns: _Optional[int] = ..., instance: _Optional[str] = ...) -> None: ...

class DatasetEntitlement(_message.Message):
    __slots__ = ("dataset", "instance", "allowed", "fields", "updated_by", "updated_at_ns", "acting_through_delegation", "client_name", "note", "prepared_call_id")
    DATASET_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    ACTING_THROUGH_DELEGATION_FIELD_NUMBER: _ClassVar[int]
    CLIENT_NAME_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    PREPARED_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    dataset: str
    instance: str
    allowed: bool
    fields: _containers.RepeatedScalarFieldContainer[str]
    updated_by: str
    updated_at_ns: int
    acting_through_delegation: str
    client_name: str
    note: str
    prepared_call_id: str
    def __init__(self, dataset: _Optional[str] = ..., instance: _Optional[str] = ..., allowed: bool = ..., fields: _Optional[_Iterable[str]] = ..., updated_by: _Optional[str] = ..., updated_at_ns: _Optional[int] = ..., acting_through_delegation: _Optional[str] = ..., client_name: _Optional[str] = ..., note: _Optional[str] = ..., prepared_call_id: _Optional[str] = ...) -> None: ...

class Job(_message.Message):
    __slots__ = ("account_ids", "inputs", "measures", "what_if", "business_date", "reporting_currency")
    ACCOUNT_IDS_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    MEASURES_FIELD_NUMBER: _ClassVar[int]
    WHAT_IF_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    REPORTING_CURRENCY_FIELD_NUMBER: _ClassVar[int]
    account_ids: _containers.RepeatedScalarFieldContainer[str]
    inputs: InputRefs
    measures: _containers.RepeatedCompositeFieldContainer[MeasureRef]
    what_if: WhatIf
    business_date: str
    reporting_currency: str
    def __init__(self, account_ids: _Optional[_Iterable[str]] = ..., inputs: _Optional[_Union[InputRefs, _Mapping]] = ..., measures: _Optional[_Iterable[_Union[MeasureRef, _Mapping]]] = ..., what_if: _Optional[_Union[WhatIf, _Mapping]] = ..., business_date: _Optional[str] = ..., reporting_currency: _Optional[str] = ...) -> None: ...

class InputRefs(_message.Message):
    __slots__ = ("book_at", "lake_as_of_ns", "sources")
    BOOK_AT_FIELD_NUMBER: _ClassVar[int]
    LAKE_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    book_at: Watermark
    lake_as_of_ns: int
    sources: SourceChoice
    def __init__(self, book_at: _Optional[_Union[Watermark, _Mapping]] = ..., lake_as_of_ns: _Optional[int] = ..., sources: _Optional[_Union[SourceChoice, _Mapping]] = ...) -> None: ...

class MeasureRef(_message.Message):
    __slots__ = ("definition", "version", "breakdowns", "event_group_id")
    DEFINITION_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    BREAKDOWNS_FIELD_NUMBER: _ClassVar[int]
    EVENT_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    definition: str
    version: int
    breakdowns: _containers.RepeatedScalarFieldContainer[str]
    event_group_id: str
    def __init__(self, definition: _Optional[str] = ..., version: _Optional[int] = ..., breakdowns: _Optional[_Iterable[str]] = ..., event_group_id: _Optional[str] = ...) -> None: ...

class WhatIf(_message.Message):
    __slots__ = ("account_id", "trades")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    TRADES_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    trades: _containers.RepeatedCompositeFieldContainer[WhatIfTrade]
    def __init__(self, account_id: _Optional[str] = ..., trades: _Optional[_Iterable[_Union[WhatIfTrade, _Mapping]]] = ...) -> None: ...

class WhatIfTrade(_message.Message):
    __slots__ = ("instrument_id", "side", "quantity", "price")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    side: Side
    quantity: Decimal
    price: Money
    def __init__(self, instrument_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., quantity: _Optional[_Union[Decimal, _Mapping]] = ..., price: _Optional[_Union[Money, _Mapping]] = ...) -> None: ...

class JobAnswer(_message.Message):
    __slots__ = ("job_id", "figures", "not_evaluated", "provenance")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    FIGURES_FIELD_NUMBER: _ClassVar[int]
    NOT_EVALUATED_FIELD_NUMBER: _ClassVar[int]
    PROVENANCE_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    figures: _containers.RepeatedCompositeFieldContainer[Figure]
    not_evaluated: _containers.RepeatedCompositeFieldContainer[NotEvaluated]
    provenance: AnswerProvenance
    def __init__(self, job_id: _Optional[str] = ..., figures: _Optional[_Iterable[_Union[Figure, _Mapping]]] = ..., not_evaluated: _Optional[_Iterable[_Union[NotEvaluated, _Mapping]]] = ..., provenance: _Optional[_Union[AnswerProvenance, _Mapping]] = ...) -> None: ...

class Figure(_message.Message):
    __slots__ = ("measure", "account_id", "breakdown", "scenario_key", "value", "numerator", "denominator", "currency_instrument_id", "computed_as", "oldest_input_source_ns")
    MEASURE_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BREAKDOWN_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    NUMERATOR_FIELD_NUMBER: _ClassVar[int]
    DENOMINATOR_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    COMPUTED_AS_FIELD_NUMBER: _ClassVar[int]
    OLDEST_INPUT_SOURCE_NS_FIELD_NUMBER: _ClassVar[int]
    measure: MeasureRef
    account_id: str
    breakdown: _containers.RepeatedCompositeFieldContainer[BreakdownValue]
    scenario_key: ScenarioKey
    value: Decimal
    numerator: Decimal
    denominator: Decimal
    currency_instrument_id: str
    computed_as: ComputedAs
    oldest_input_source_ns: int
    def __init__(self, measure: _Optional[_Union[MeasureRef, _Mapping]] = ..., account_id: _Optional[str] = ..., breakdown: _Optional[_Iterable[_Union[BreakdownValue, _Mapping]]] = ..., scenario_key: _Optional[_Union[ScenarioKey, _Mapping]] = ..., value: _Optional[_Union[Decimal, _Mapping]] = ..., numerator: _Optional[_Union[Decimal, _Mapping]] = ..., denominator: _Optional[_Union[Decimal, _Mapping]] = ..., currency_instrument_id: _Optional[str] = ..., computed_as: _Optional[_Union[ComputedAs, str]] = ..., oldest_input_source_ns: _Optional[int] = ...) -> None: ...

class BreakdownValue(_message.Message):
    __slots__ = ("breakdown", "value")
    BREAKDOWN_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    breakdown: str
    value: str
    def __init__(self, breakdown: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class ScenarioKey(_message.Message):
    __slots__ = ("kind", "business_date", "outcome_instrument_id")
    KIND_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    kind: ScenarioKind
    business_date: str
    outcome_instrument_id: str
    def __init__(self, kind: _Optional[_Union[ScenarioKind, str]] = ..., business_date: _Optional[str] = ..., outcome_instrument_id: _Optional[str] = ...) -> None: ...

class NotEvaluated(_message.Message):
    __slots__ = ("account_id", "instrument_id", "measure", "reason", "detail", "age_ns", "ceiling_ns")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    MEASURE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    AGE_NS_FIELD_NUMBER: _ClassVar[int]
    CEILING_NS_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    instrument_id: str
    measure: MeasureRef
    reason: NotEvaluatedReason
    detail: str
    age_ns: int
    ceiling_ns: int
    def __init__(self, account_id: _Optional[str] = ..., instrument_id: _Optional[str] = ..., measure: _Optional[_Union[MeasureRef, _Mapping]] = ..., reason: _Optional[_Union[NotEvaluatedReason, str]] = ..., detail: _Optional[str] = ..., age_ns: _Optional[int] = ..., ceiling_ns: _Optional[int] = ...) -> None: ...

class AnswerProvenance(_message.Message):
    __slots__ = ("book_watermark", "lake_as_of_ns", "datasets", "instruments", "models", "measures", "event_groups", "routing_version", "engine_version", "answer_hash", "business_date", "input_prices", "conversion_legs")
    BOOK_WATERMARK_FIELD_NUMBER: _ClassVar[int]
    LAKE_AS_OF_NS_FIELD_NUMBER: _ClassVar[int]
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENTS_FIELD_NUMBER: _ClassVar[int]
    MODELS_FIELD_NUMBER: _ClassVar[int]
    MEASURES_FIELD_NUMBER: _ClassVar[int]
    EVENT_GROUPS_FIELD_NUMBER: _ClassVar[int]
    ROUTING_VERSION_FIELD_NUMBER: _ClassVar[int]
    ENGINE_VERSION_FIELD_NUMBER: _ClassVar[int]
    ANSWER_HASH_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    INPUT_PRICES_FIELD_NUMBER: _ClassVar[int]
    CONVERSION_LEGS_FIELD_NUMBER: _ClassVar[int]
    book_watermark: Watermark
    lake_as_of_ns: int
    datasets: _containers.RepeatedScalarFieldContainer[str]
    instruments: _containers.RepeatedCompositeFieldContainer[InstrumentInput]
    models: _containers.RepeatedCompositeFieldContainer[ModelRef]
    measures: _containers.RepeatedCompositeFieldContainer[MeasureRef]
    event_groups: _containers.RepeatedCompositeFieldContainer[EventGroupInput]
    routing_version: int
    engine_version: str
    answer_hash: str
    business_date: str
    input_prices: _containers.RepeatedCompositeFieldContainer[InputPrice]
    conversion_legs: _containers.RepeatedCompositeFieldContainer[ConversionLeg]
    def __init__(self, book_watermark: _Optional[_Union[Watermark, _Mapping]] = ..., lake_as_of_ns: _Optional[int] = ..., datasets: _Optional[_Iterable[str]] = ..., instruments: _Optional[_Iterable[_Union[InstrumentInput, _Mapping]]] = ..., models: _Optional[_Iterable[_Union[ModelRef, _Mapping]]] = ..., measures: _Optional[_Iterable[_Union[MeasureRef, _Mapping]]] = ..., event_groups: _Optional[_Iterable[_Union[EventGroupInput, _Mapping]]] = ..., routing_version: _Optional[int] = ..., engine_version: _Optional[str] = ..., answer_hash: _Optional[str] = ..., business_date: _Optional[str] = ..., input_prices: _Optional[_Iterable[_Union[InputPrice, _Mapping]]] = ..., conversion_legs: _Optional[_Iterable[_Union[ConversionLeg, _Mapping]]] = ...) -> None: ...

class InstrumentInput(_message.Message):
    __slots__ = ("instrument_id", "record_version", "template_id", "template_version", "calculation_version")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    RECORD_VERSION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    CALCULATION_VERSION_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    record_version: int
    template_id: str
    template_version: str
    calculation_version: str
    def __init__(self, instrument_id: _Optional[str] = ..., record_version: _Optional[int] = ..., template_id: _Optional[str] = ..., template_version: _Optional[str] = ..., calculation_version: _Optional[str] = ...) -> None: ...

class ModelRef(_message.Message):
    __slots__ = ("model_id", "model_version", "implementation", "implementation_version")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    IMPLEMENTATION_FIELD_NUMBER: _ClassVar[int]
    IMPLEMENTATION_VERSION_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    model_version: int
    implementation: str
    implementation_version: str
    def __init__(self, model_id: _Optional[str] = ..., model_version: _Optional[int] = ..., implementation: _Optional[str] = ..., implementation_version: _Optional[str] = ...) -> None: ...

class EventGroupInput(_message.Message):
    __slots__ = ("event_group_id", "version")
    EVENT_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    event_group_id: str
    version: int
    def __init__(self, event_group_id: _Optional[str] = ..., version: _Optional[int] = ...) -> None: ...

class InputPrice(_message.Message):
    __slots__ = ("instrument_id", "price", "dataset", "row_key", "version", "source_ns")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    ROW_KEY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_NS_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    price: Money
    dataset: str
    row_key: str
    version: int
    source_ns: int
    def __init__(self, instrument_id: _Optional[str] = ..., price: _Optional[_Union[Money, _Mapping]] = ..., dataset: _Optional[str] = ..., row_key: _Optional[str] = ..., version: _Optional[int] = ..., source_ns: _Optional[int] = ...) -> None: ...

class ConversionLeg(_message.Message):
    __slots__ = ("from_instrument_id", "to_instrument_id", "rate", "derivation", "via_instrument_id", "dataset")
    FROM_INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TO_INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    RATE_FIELD_NUMBER: _ClassVar[int]
    DERIVATION_FIELD_NUMBER: _ClassVar[int]
    VIA_INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    from_instrument_id: str
    to_instrument_id: str
    rate: Decimal
    derivation: ConversionDerivation
    via_instrument_id: str
    dataset: str
    def __init__(self, from_instrument_id: _Optional[str] = ..., to_instrument_id: _Optional[str] = ..., rate: _Optional[_Union[Decimal, _Mapping]] = ..., derivation: _Optional[_Union[ConversionDerivation, str]] = ..., via_instrument_id: _Optional[str] = ..., dataset: _Optional[str] = ...) -> None: ...

class MeasureDefinition(_message.Message):
    __slots__ = ("definition", "version", "parameters", "breakdowns", "scale", "description")
    DEFINITION_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    BREAKDOWNS_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    definition: str
    version: int
    parameters: _containers.RepeatedCompositeFieldContainer[MeasureParameter]
    breakdowns: _containers.RepeatedScalarFieldContainer[str]
    scale: int
    description: str
    def __init__(self, definition: _Optional[str] = ..., version: _Optional[int] = ..., parameters: _Optional[_Iterable[_Union[MeasureParameter, _Mapping]]] = ..., breakdowns: _Optional[_Iterable[str]] = ..., scale: _Optional[int] = ..., description: _Optional[str] = ...) -> None: ...

class MeasureParameter(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: str
    def __init__(self, name: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class PriceBatchRequest(_message.Message):
    __slots__ = ("batch_id", "pricing_instance_id", "model_id", "model_version", "units", "deadline_ns", "batch_hash", "sequence")
    BATCH_ID_FIELD_NUMBER: _ClassVar[int]
    PRICING_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    UNITS_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_NS_FIELD_NUMBER: _ClassVar[int]
    BATCH_HASH_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    batch_id: str
    pricing_instance_id: str
    model_id: str
    model_version: int
    units: _containers.RepeatedCompositeFieldContainer[PricingUnit]
    deadline_ns: int
    batch_hash: str
    sequence: int
    def __init__(self, batch_id: _Optional[str] = ..., pricing_instance_id: _Optional[str] = ..., model_id: _Optional[str] = ..., model_version: _Optional[int] = ..., units: _Optional[_Iterable[_Union[PricingUnit, _Mapping]]] = ..., deadline_ns: _Optional[int] = ..., batch_hash: _Optional[str] = ..., sequence: _Optional[int] = ...) -> None: ...

class PricingUnit(_message.Message):
    __slots__ = ("instrument_id", "template_version", "scenario_key", "inputs")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_KEY_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    template_version: str
    scenario_key: ScenarioKey
    inputs: _containers.RepeatedCompositeFieldContainer[MarketObjectValue]
    def __init__(self, instrument_id: _Optional[str] = ..., template_version: _Optional[str] = ..., scenario_key: _Optional[_Union[ScenarioKey, _Mapping]] = ..., inputs: _Optional[_Iterable[_Union[MarketObjectValue, _Mapping]]] = ...) -> None: ...

class MarketObjectValue(_message.Message):
    __slots__ = ("subject_id", "kind", "value", "dataset")
    SUBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    subject_id: str
    kind: str
    value: Money
    dataset: str
    def __init__(self, subject_id: _Optional[str] = ..., kind: _Optional[str] = ..., value: _Optional[_Union[Money, _Mapping]] = ..., dataset: _Optional[str] = ...) -> None: ...

class PricedUnit(_message.Message):
    __slots__ = ("instrument_id", "scenario_key", "value_per_unit")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_PER_UNIT_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    scenario_key: ScenarioKey
    value_per_unit: Money
    def __init__(self, instrument_id: _Optional[str] = ..., scenario_key: _Optional[_Union[ScenarioKey, _Mapping]] = ..., value_per_unit: _Optional[_Union[Money, _Mapping]] = ...) -> None: ...

class Sensitivity(_message.Message):
    __slots__ = ("instrument_id", "scenario_key", "name", "value")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_KEY_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    scenario_key: ScenarioKey
    name: str
    value: Decimal
    def __init__(self, instrument_id: _Optional[str] = ..., scenario_key: _Optional[_Union[ScenarioKey, _Mapping]] = ..., name: _Optional[str] = ..., value: _Optional[_Union[Decimal, _Mapping]] = ...) -> None: ...

class JobFinishedEvent(_message.Message):
    __slots__ = ("job_id", "client_instance_id", "answer_hash", "finished_at_ns", "sequence")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    ANSWER_HASH_FIELD_NUMBER: _ClassVar[int]
    FINISHED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    client_instance_id: str
    answer_hash: str
    finished_at_ns: int
    sequence: int
    def __init__(self, job_id: _Optional[str] = ..., client_instance_id: _Optional[str] = ..., answer_hash: _Optional[str] = ..., finished_at_ns: _Optional[int] = ..., sequence: _Optional[int] = ...) -> None: ...

class EventGroupMemberBound(_message.Message):
    __slots__ = ("instrument_id", "floor", "cap", "bound_unit")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    FLOOR_FIELD_NUMBER: _ClassVar[int]
    CAP_FIELD_NUMBER: _ClassVar[int]
    BOUND_UNIT_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    floor: EventContractBound
    cap: EventContractBound
    bound_unit: str
    def __init__(self, instrument_id: _Optional[str] = ..., floor: _Optional[_Union[EventContractBound, _Mapping]] = ..., cap: _Optional[_Union[EventContractBound, _Mapping]] = ..., bound_unit: _Optional[str] = ...) -> None: ...

class EventGroup(_message.Message):
    __slots__ = ("event_group_id", "venue_id", "venue_event_ref", "title", "member_instrument_ids", "mutually_exclusive", "exhaustive", "series_id", "version", "valid_from_ns", "record_time_ns", "provisional", "sequence")
    EVENT_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    VENUE_EVENT_REF_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    MEMBER_INSTRUMENT_IDS_FIELD_NUMBER: _ClassVar[int]
    MUTUALLY_EXCLUSIVE_FIELD_NUMBER: _ClassVar[int]
    EXHAUSTIVE_FIELD_NUMBER: _ClassVar[int]
    SERIES_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    RECORD_TIME_NS_FIELD_NUMBER: _ClassVar[int]
    PROVISIONAL_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    event_group_id: str
    venue_id: str
    venue_event_ref: str
    title: str
    member_instrument_ids: _containers.RepeatedScalarFieldContainer[str]
    mutually_exclusive: EventGroupFlag
    exhaustive: EventGroupFlag
    series_id: str
    version: int
    valid_from_ns: int
    record_time_ns: int
    provisional: bool
    sequence: int
    def __init__(self, event_group_id: _Optional[str] = ..., venue_id: _Optional[str] = ..., venue_event_ref: _Optional[str] = ..., title: _Optional[str] = ..., member_instrument_ids: _Optional[_Iterable[str]] = ..., mutually_exclusive: _Optional[_Union[EventGroupFlag, str]] = ..., exhaustive: _Optional[_Union[EventGroupFlag, str]] = ..., series_id: _Optional[str] = ..., version: _Optional[int] = ..., valid_from_ns: _Optional[int] = ..., record_time_ns: _Optional[int] = ..., provisional: bool = ..., sequence: _Optional[int] = ...) -> None: ...

class Rate(_message.Message):
    __slots__ = ("meta", "kind", "value", "convention", "tenor", "maturity_date", "preliminary", "volume", "transaction_count", "percentiles")
    META_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    CONVENTION_FIELD_NUMBER: _ClassVar[int]
    TENOR_FIELD_NUMBER: _ClassVar[int]
    MATURITY_DATE_FIELD_NUMBER: _ClassVar[int]
    PRELIMINARY_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_COUNT_FIELD_NUMBER: _ClassVar[int]
    PERCENTILES_FIELD_NUMBER: _ClassVar[int]
    meta: ObservationMeta
    kind: RateKind
    value: UnitValue
    convention: RateConvention
    tenor: Tenor
    maturity_date: str
    preliminary: bool
    volume: Money
    transaction_count: int
    percentiles: _containers.RepeatedCompositeFieldContainer[RatePercentile]
    def __init__(self, meta: _Optional[_Union[ObservationMeta, _Mapping]] = ..., kind: _Optional[_Union[RateKind, str]] = ..., value: _Optional[_Union[UnitValue, _Mapping]] = ..., convention: _Optional[_Union[RateConvention, _Mapping]] = ..., tenor: _Optional[_Union[Tenor, _Mapping]] = ..., maturity_date: _Optional[str] = ..., preliminary: bool = ..., volume: _Optional[_Union[Money, _Mapping]] = ..., transaction_count: _Optional[int] = ..., percentiles: _Optional[_Iterable[_Union[RatePercentile, _Mapping]]] = ...) -> None: ...

class UnitValue(_message.Message):
    __slots__ = ("value", "unit", "index_base", "ucum_code")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    INDEX_BASE_FIELD_NUMBER: _ClassVar[int]
    UCUM_CODE_FIELD_NUMBER: _ClassVar[int]
    value: Decimal
    unit: ValueUnit
    index_base: str
    ucum_code: str
    def __init__(self, value: _Optional[_Union[Decimal, _Mapping]] = ..., unit: _Optional[_Union[ValueUnit, str]] = ..., index_base: _Optional[str] = ..., ucum_code: _Optional[str] = ...) -> None: ...

class RateConvention(_message.Message):
    __slots__ = ("day_count", "compounding", "periods_per_year")
    DAY_COUNT_FIELD_NUMBER: _ClassVar[int]
    COMPOUNDING_FIELD_NUMBER: _ClassVar[int]
    PERIODS_PER_YEAR_FIELD_NUMBER: _ClassVar[int]
    day_count: DayCount
    compounding: Compounding
    periods_per_year: int
    def __init__(self, day_count: _Optional[_Union[DayCount, str]] = ..., compounding: _Optional[_Union[Compounding, str]] = ..., periods_per_year: _Optional[int] = ...) -> None: ...

class RatePercentile(_message.Message):
    __slots__ = ("percentile", "value")
    PERCENTILE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    percentile: int
    value: Decimal
    def __init__(self, percentile: _Optional[int] = ..., value: _Optional[_Union[Decimal, _Mapping]] = ...) -> None: ...

class LatencySnapshot(_message.Message):
    __slots__ = ("interval_start_ns", "interval_ns", "session", "dataset", "hop", "metric", "histogram", "counters", "clock_skew_ns", "alive_at_ns", "ceilings", "instance_id")
    INTERVAL_START_NS_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_NS_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    HOP_FIELD_NUMBER: _ClassVar[int]
    METRIC_FIELD_NUMBER: _ClassVar[int]
    HISTOGRAM_FIELD_NUMBER: _ClassVar[int]
    COUNTERS_FIELD_NUMBER: _ClassVar[int]
    CLOCK_SKEW_NS_FIELD_NUMBER: _ClassVar[int]
    ALIVE_AT_NS_FIELD_NUMBER: _ClassVar[int]
    CEILINGS_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    interval_start_ns: int
    interval_ns: int
    session: str
    dataset: str
    hop: AgeHop
    metric: LatencyMetric
    histogram: LatencyHistogram
    counters: LatencyCounters
    clock_skew_ns: int
    alive_at_ns: int
    ceilings: LatencyCeilings
    instance_id: str
    def __init__(self, interval_start_ns: _Optional[int] = ..., interval_ns: _Optional[int] = ..., session: _Optional[str] = ..., dataset: _Optional[str] = ..., hop: _Optional[_Union[AgeHop, str]] = ..., metric: _Optional[_Union[LatencyMetric, str]] = ..., histogram: _Optional[_Union[LatencyHistogram, _Mapping]] = ..., counters: _Optional[_Union[LatencyCounters, _Mapping]] = ..., clock_skew_ns: _Optional[int] = ..., alive_at_ns: _Optional[int] = ..., ceilings: _Optional[_Union[LatencyCeilings, _Mapping]] = ..., instance_id: _Optional[str] = ...) -> None: ...

class LatencyHistogram(_message.Message):
    __slots__ = ("lowest_ns", "significant_digits", "buckets", "min_ns", "max_ns", "total")
    LOWEST_NS_FIELD_NUMBER: _ClassVar[int]
    SIGNIFICANT_DIGITS_FIELD_NUMBER: _ClassVar[int]
    BUCKETS_FIELD_NUMBER: _ClassVar[int]
    MIN_NS_FIELD_NUMBER: _ClassVar[int]
    MAX_NS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    lowest_ns: int
    significant_digits: int
    buckets: _containers.RepeatedCompositeFieldContainer[LatencyBucket]
    min_ns: int
    max_ns: int
    total: int
    def __init__(self, lowest_ns: _Optional[int] = ..., significant_digits: _Optional[int] = ..., buckets: _Optional[_Iterable[_Union[LatencyBucket, _Mapping]]] = ..., min_ns: _Optional[int] = ..., max_ns: _Optional[int] = ..., total: _Optional[int] = ...) -> None: ...

class LatencyBucket(_message.Message):
    __slots__ = ("bucket", "count")
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    bucket: int
    count: int
    def __init__(self, bucket: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class LatencyCounters(_message.Message):
    __slots__ = ("gaps", "resends", "reconnects", "rate_limited", "backlog_peak")
    GAPS_FIELD_NUMBER: _ClassVar[int]
    RESENDS_FIELD_NUMBER: _ClassVar[int]
    RECONNECTS_FIELD_NUMBER: _ClassVar[int]
    RATE_LIMITED_FIELD_NUMBER: _ClassVar[int]
    BACKLOG_PEAK_FIELD_NUMBER: _ClassVar[int]
    gaps: int
    resends: int
    reconnects: int
    rate_limited: int
    backlog_peak: int
    def __init__(self, gaps: _Optional[int] = ..., resends: _Optional[int] = ..., reconnects: _Optional[int] = ..., rate_limited: _Optional[int] = ..., backlog_peak: _Optional[int] = ...) -> None: ...

class LatencyCeilings(_message.Message):
    __slots__ = ("rtt_p99_ns", "order_ack_p99_ns", "fill_delay_p99_ns", "feed_delay_p99_ns", "clock_skew_max_ns", "gaps_per_hour", "reconnects_per_hour", "backlog_max")
    RTT_P99_NS_FIELD_NUMBER: _ClassVar[int]
    ORDER_ACK_P99_NS_FIELD_NUMBER: _ClassVar[int]
    FILL_DELAY_P99_NS_FIELD_NUMBER: _ClassVar[int]
    FEED_DELAY_P99_NS_FIELD_NUMBER: _ClassVar[int]
    CLOCK_SKEW_MAX_NS_FIELD_NUMBER: _ClassVar[int]
    GAPS_PER_HOUR_FIELD_NUMBER: _ClassVar[int]
    RECONNECTS_PER_HOUR_FIELD_NUMBER: _ClassVar[int]
    BACKLOG_MAX_FIELD_NUMBER: _ClassVar[int]
    rtt_p99_ns: int
    order_ack_p99_ns: int
    fill_delay_p99_ns: int
    feed_delay_p99_ns: int
    clock_skew_max_ns: int
    gaps_per_hour: int
    reconnects_per_hour: int
    backlog_max: int
    def __init__(self, rtt_p99_ns: _Optional[int] = ..., order_ack_p99_ns: _Optional[int] = ..., fill_delay_p99_ns: _Optional[int] = ..., feed_delay_p99_ns: _Optional[int] = ..., clock_skew_max_ns: _Optional[int] = ..., gaps_per_hour: _Optional[int] = ..., reconnects_per_hour: _Optional[int] = ..., backlog_max: _Optional[int] = ...) -> None: ...

class ExecutionCost(_message.Message):
    __slots__ = ("meta", "execution_id", "order_id", "placement_id", "account_id", "benchmark", "benchmark_price", "benchmark_at_ns", "benchmark_dataset", "benchmark_row_key", "fixing_id", "execution_price", "side", "notional", "cost_bps", "fees_bps", "financing_bps", "liquidity_indicator", "venue_id", "unanswered", "staleness_bound_ns", "time_precision", "reject_count", "time_to_fill_ns")
    META_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_PRICE_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_AT_NS_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_DATASET_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_ROW_KEY_FIELD_NUMBER: _ClassVar[int]
    FIXING_ID_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_PRICE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    NOTIONAL_FIELD_NUMBER: _ClassVar[int]
    COST_BPS_FIELD_NUMBER: _ClassVar[int]
    FEES_BPS_FIELD_NUMBER: _ClassVar[int]
    FINANCING_BPS_FIELD_NUMBER: _ClassVar[int]
    LIQUIDITY_INDICATOR_FIELD_NUMBER: _ClassVar[int]
    VENUE_ID_FIELD_NUMBER: _ClassVar[int]
    UNANSWERED_FIELD_NUMBER: _ClassVar[int]
    STALENESS_BOUND_NS_FIELD_NUMBER: _ClassVar[int]
    TIME_PRECISION_FIELD_NUMBER: _ClassVar[int]
    REJECT_COUNT_FIELD_NUMBER: _ClassVar[int]
    TIME_TO_FILL_NS_FIELD_NUMBER: _ClassVar[int]
    meta: ObservationMeta
    execution_id: str
    order_id: str
    placement_id: str
    account_id: str
    benchmark: TcaBenchmark
    benchmark_price: Money
    benchmark_at_ns: int
    benchmark_dataset: str
    benchmark_row_key: str
    fixing_id: str
    execution_price: Money
    side: Side
    notional: Money
    cost_bps: Decimal
    fees_bps: Decimal
    financing_bps: Decimal
    liquidity_indicator: LiquidityIndicator
    venue_id: str
    unanswered: TcaUnanswered
    staleness_bound_ns: int
    time_precision: TimePrecision
    reject_count: int
    time_to_fill_ns: int
    def __init__(self, meta: _Optional[_Union[ObservationMeta, _Mapping]] = ..., execution_id: _Optional[str] = ..., order_id: _Optional[str] = ..., placement_id: _Optional[str] = ..., account_id: _Optional[str] = ..., benchmark: _Optional[_Union[TcaBenchmark, str]] = ..., benchmark_price: _Optional[_Union[Money, _Mapping]] = ..., benchmark_at_ns: _Optional[int] = ..., benchmark_dataset: _Optional[str] = ..., benchmark_row_key: _Optional[str] = ..., fixing_id: _Optional[str] = ..., execution_price: _Optional[_Union[Money, _Mapping]] = ..., side: _Optional[_Union[Side, str]] = ..., notional: _Optional[_Union[Money, _Mapping]] = ..., cost_bps: _Optional[_Union[Decimal, _Mapping]] = ..., fees_bps: _Optional[_Union[Decimal, _Mapping]] = ..., financing_bps: _Optional[_Union[Decimal, _Mapping]] = ..., liquidity_indicator: _Optional[_Union[LiquidityIndicator, str]] = ..., venue_id: _Optional[str] = ..., unanswered: _Optional[_Union[TcaUnanswered, str]] = ..., staleness_bound_ns: _Optional[int] = ..., time_precision: _Optional[_Union[TimePrecision, str]] = ..., reject_count: _Optional[int] = ..., time_to_fill_ns: _Optional[int] = ...) -> None: ...

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

class ActivityReResolvedEvent(_message.Message):
    __slots__ = ("account_id", "re_resolution", "cause", "journal")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    RE_RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    re_resolution: ActivityReResolution
    cause: ChangeCause
    journal: JournalRef
    def __init__(self, account_id: _Optional[str] = ..., re_resolution: _Optional[_Union[ActivityReResolution, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ...) -> None: ...

class PricesRecordedEvent(_message.Message):
    __slots__ = ("price",)
    PRICE_FIELD_NUMBER: _ClassVar[int]
    price: Price
    def __init__(self, price: _Optional[_Union[Price, _Mapping]] = ...) -> None: ...

class BarsRecordedEvent(_message.Message):
    __slots__ = ("bar",)
    BAR_FIELD_NUMBER: _ClassVar[int]
    bar: Bar
    def __init__(self, bar: _Optional[_Union[Bar, _Mapping]] = ...) -> None: ...

class ObservationsWantedEvent(_message.Message):
    __slots__ = ("want_id", "dataset", "data_type", "subjects", "kinds", "interval_ns", "business_date", "valid_from_ns", "valid_until_ns", "standing")
    WANT_ID_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    DATA_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBJECTS_FIELD_NUMBER: _ClassVar[int]
    KINDS_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_NS_FIELD_NUMBER: _ClassVar[int]
    BUSINESS_DATE_FIELD_NUMBER: _ClassVar[int]
    VALID_FROM_NS_FIELD_NUMBER: _ClassVar[int]
    VALID_UNTIL_NS_FIELD_NUMBER: _ClassVar[int]
    STANDING_FIELD_NUMBER: _ClassVar[int]
    want_id: str
    dataset: str
    data_type: str
    subjects: _containers.RepeatedCompositeFieldContainer[SubjectRef]
    kinds: _containers.RepeatedScalarFieldContainer[PriceKind]
    interval_ns: int
    business_date: str
    valid_from_ns: int
    valid_until_ns: int
    standing: bool
    def __init__(self, want_id: _Optional[str] = ..., dataset: _Optional[str] = ..., data_type: _Optional[str] = ..., subjects: _Optional[_Iterable[_Union[SubjectRef, _Mapping]]] = ..., kinds: _Optional[_Iterable[_Union[PriceKind, str]]] = ..., interval_ns: _Optional[int] = ..., business_date: _Optional[str] = ..., valid_from_ns: _Optional[int] = ..., valid_until_ns: _Optional[int] = ..., standing: bool = ...) -> None: ...

class WantWithdrawnEvent(_message.Message):
    __slots__ = ("want_id", "dataset")
    WANT_ID_FIELD_NUMBER: _ClassVar[int]
    DATASET_FIELD_NUMBER: _ClassVar[int]
    want_id: str
    dataset: str
    def __init__(self, want_id: _Optional[str] = ..., dataset: _Optional[str] = ...) -> None: ...

class TradesRecordedEvent(_message.Message):
    __slots__ = ("trade",)
    TRADE_FIELD_NUMBER: _ClassVar[int]
    trade: Trade
    def __init__(self, trade: _Optional[_Union[Trade, _Mapping]] = ...) -> None: ...

class QuotesRecordedEvent(_message.Message):
    __slots__ = ("quote",)
    QUOTE_FIELD_NUMBER: _ClassVar[int]
    quote: Quote
    def __init__(self, quote: _Optional[_Union[Quote, _Mapping]] = ...) -> None: ...

class OrderUpdatedEvent(_message.Message):
    __slots__ = ("order", "changed", "entry", "journal", "cause")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    CHANGED_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    order: Order
    changed: _containers.RepeatedScalarFieldContainer[str]
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, order: _Optional[_Union[Order, _Mapping]] = ..., changed: _Optional[_Iterable[str]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class PlacementUpdatedEvent(_message.Message):
    __slots__ = ("placement", "changed", "entry", "journal", "cause")
    PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    CHANGED_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    placement: Placement
    changed: _containers.RepeatedScalarFieldContainer[str]
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, placement: _Optional[_Union[Placement, _Mapping]] = ..., changed: _Optional[_Iterable[str]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class ExecutionRecordedEvent(_message.Message):
    __slots__ = ("execution", "entry", "journal", "cause")
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    execution: Execution
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, execution: _Optional[_Union[Execution, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class UnplacedFactRecordedEvent(_message.Message):
    __slots__ = ("unplaced", "entry", "journal", "cause")
    UNPLACED_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    unplaced: UnplacedFact
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, unplaced: _Optional[_Union[UnplacedFact, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class TradingInstructionChangedEvent(_message.Message):
    __slots__ = ("instruction", "journal", "cause")
    INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    instruction: TradingInstruction
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, instruction: _Optional[_Union[TradingInstruction, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class LocateUpdatedEvent(_message.Message):
    __slots__ = ("locate", "entry", "journal", "cause")
    LOCATE_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    locate: Locate
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, locate: _Optional[_Union[Locate, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class VenueCatalogueEvent(_message.Message):
    __slots__ = ("catalogue", "publisher_instance_id")
    CATALOGUE_FIELD_NUMBER: _ClassVar[int]
    PUBLISHER_INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    catalogue: VenueCatalogue
    publisher_instance_id: str
    def __init__(self, catalogue: _Optional[_Union[VenueCatalogue, _Mapping]] = ..., publisher_instance_id: _Optional[str] = ...) -> None: ...

class OutcomesRecordedEvent(_message.Message):
    __slots__ = ("outcome",)
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    outcome: Outcome
    def __init__(self, outcome: _Optional[_Union[Outcome, _Mapping]] = ...) -> None: ...

class BookingUpdatedEvent(_message.Message):
    __slots__ = ("booking", "entry", "journal", "cause")
    BOOKING_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    booking: Booking
    entry: EntryMeta
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, booking: _Optional[_Union[Booking, _Mapping]] = ..., entry: _Optional[_Union[EntryMeta, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class AlertChangedEvent(_message.Message):
    __slots__ = ("alert", "journal", "cause")
    ALERT_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    CAUSE_FIELD_NUMBER: _ClassVar[int]
    alert: Alert
    journal: JournalRef
    cause: ChangeCause
    def __init__(self, alert: _Optional[_Union[Alert, _Mapping]] = ..., journal: _Optional[_Union[JournalRef, _Mapping]] = ..., cause: _Optional[_Union[ChangeCause, _Mapping]] = ...) -> None: ...

class RatesRecordedEvent(_message.Message):
    __slots__ = ("rate",)
    RATE_FIELD_NUMBER: _ClassVar[int]
    rate: Rate
    def __init__(self, rate: _Optional[_Union[Rate, _Mapping]] = ...) -> None: ...

class LivenessRecordedEvent(_message.Message):
    __slots__ = ("liveness",)
    LIVENESS_FIELD_NUMBER: _ClassVar[int]
    liveness: DatasetLiveness
    def __init__(self, liveness: _Optional[_Union[DatasetLiveness, _Mapping]] = ...) -> None: ...
