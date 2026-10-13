"""Bounded local navigation metadata; never a financial evidence packet (D08)."""
from dataclasses import dataclass
from langgraphagenticai.state.research_context import ResearchContext

SECTOR_ALIASES = {"Communication": "Communication Services", "Cons. Cyclical": "Consumer Cyclical", "Financials": "Financial Services", "Healthcare": "Healthcare", "Cons. Staples": "Consumer Defensive", "Materials": "Basic Materials"}


@dataclass(frozen=True)
class DiscoveryState:
    sector: str = "All sectors"
    period: str = "5D"
    direction: str = "Leaders"
    selected_ticker: str = ""
    origin: str = "Top Movers"

    def __post_init__(self):
        if self.period not in ("1D", "5D", "1M", "ytd") or self.direction not in ("Leaders", "Laggards"):
            raise ValueError("Unsupported discovery filters.")
        if not isinstance(self.sector, str) or len(self.sector) > 80 or self.origin not in ("Introduction", "Top Movers"):
            raise ValueError("Invalid discovery metadata.")
        if self.selected_ticker:
            context = ResearchContext((self.selected_ticker,), "Research", "analyze", self.origin)
            object.__setattr__(self, "selected_ticker", context.symbols[0])


def queue_discovery(state, sector):
    state["pending_discovery"] = DiscoveryState(sector=SECTOR_ALIASES.get(sector, sector), origin="Introduction")
    state["next_workspace"] = "Top Movers"


def apply_discovery(state):
    incoming = state.pop("pending_discovery", None)
    if incoming is not None:
        if not isinstance(incoming, DiscoveryState):
            raise ValueError("Invalid discovery handoff.")
        state.update(movers_sector_filter=incoming.sector, movers_period=incoming.period, movers_direction=incoming.direction)
        state["discovery_state"] = incoming
    return incoming


def queue_discovery_research(state, discovery):
    from langgraphagenticai.ui.workspace_handoff import queue_handoff
    state["discovery_state"] = discovery
    state["pending_discovery_request"] = (discovery.selected_ticker, f"Investigate {discovery.selected_ticker}, discovered among {discovery.sector} {discovery.direction.lower()} in the {discovery.period} screen. Collect dated evidence and assess business, financials, valuation and risks.")
    queue_handoff(state, ResearchContext((discovery.selected_ticker,), "Research", "analyze", "Top Movers"))
