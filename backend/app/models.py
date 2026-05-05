from typing import Any, Literal, Optional, Union
from pydantic import BaseModel


class AgentModel(BaseModel):
    model_name: str          # full id, e.g. "llama-3.1-8b-instant"
    display_name: str        # short label shown on map
    x: int
    y: int
    alive: bool = True
    allied_with: Optional[str] = None   # model_name of ally (if stacked)
    has_proposed_alliance: bool = False
    last_message: Optional[str] = None
    distance_to_fire: Optional[float] = None
    # New fields for fire/coalition mechanics
    water_collected: bool = False         # carrying water
    is_leader: bool = False               # elected coalition leader
    coalition_members: list[str] = []     # list of allied agent model_names
    mode: Literal["solo", "coalition"] = "coalition"  # agent's chosen path
    status: Literal["searching", "collecting_water", "extinguishing_fire", "escaping", "idle"] = "idle"
    vote_for: Optional[str] = None        # who this agent voted for as leader
    extinguish_score: float = 0.0         # total fire intensity reduced by this agent


class FireScenario(BaseModel):
    x: int
    y: int
    radius: float = 50.0         # current fire radius
    intensity: float = 100.0     # 0-100; when 0, fire is out
    growth_rate: float = 3.0     # px per tick


class WaterSource(BaseModel):
    id: str                   # unique id
    x: int
    y: int
    water_amount: float = 50.0  # how much water available


class SimulationState(BaseModel):
    simulation_id: str
    scenario: str                       # "fire" (was "volcano")
    map_width: int
    map_height: int
    agents: list[AgentModel]
    fire: Optional[FireScenario] = None
    water_sources: list[WaterSource] = []
    round: int = 0
    status: str = "waiting_for_scenario"
    winner_model: Optional[str] = None
    coalition_leader: Optional[str] = None  # elected leader
    coalition_members: list[str] = []       # all coalition members


# Event models
class DeathEvent(BaseModel):
    type: Literal["death"] = "death"
    model: str

class MessageEvent(BaseModel):
    type: Literal["message"] = "message"
    model: str
    content: str

class AllianceProposalEvent(BaseModel):
    type: Literal["alliance_proposal"] = "alliance_proposal"
    from_model: str
    to_model: str

class AllianceAcceptEvent(BaseModel):
    type: Literal["alliance_accept"] = "alliance_accept"
    model_a: str
    model_b: str
    stacked: bool = True

class AllianceRejectEvent(BaseModel):
    type: Literal["alliance_reject"] = "alliance_reject"
    from_model: str
    to_model: str

class LeadershipVoteEvent(BaseModel):
    type: Literal["leadership_vote"] = "leadership_vote"
    voter: str
    candidate: str

class LeaderElectedEvent(BaseModel):
    type: Literal["leader_elected"] = "leader_elected"
    leader: str
    coalition_members: list[str]

class WaterCollectedEvent(BaseModel):
    type: Literal["water_collected"] = "water_collected"
    model: str
    water_source_id: str

class FireExtinguishedEvent(BaseModel):
    type: Literal["fire_extinguished"] = "fire_extinguished"
    extinguished_by: list[str]  # models that contributed
    fire_intensity: float

class FireSpreadEvent(BaseModel):
    type: Literal["fire_spread"] = "fire_spread"
    new_radius: float
    new_intensity: float


class ChatEntry(BaseModel):
    agent_id: str
    message: str
    tick: int


class TickResponse(BaseModel):
    simulation_id: str
    round: int
    events: list[Union[DeathEvent, MessageEvent, AllianceProposalEvent, AllianceAcceptEvent, 
                       AllianceRejectEvent, LeadershipVoteEvent, LeaderElectedEvent, 
                       WaterCollectedEvent, FireExtinguishedEvent, FireSpreadEvent]]
    chat: list[ChatEntry]
    state: SimulationState
