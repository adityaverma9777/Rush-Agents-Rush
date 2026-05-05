import asyncio
import math
from typing import Union

from .models import (
    AgentModel,
    DeathEvent,
    MessageEvent,
    LeadershipVoteEvent,
    LeaderElectedEvent,
    WaterCollectedEvent,
    FireExtinguishedEvent,
    FireSpreadEvent,
    SimulationState,
    TickResponse,
    ChatEntry,
)
from . import groq_client
from . import movement

FIRE_GROWTH_RATE = 1.0  # radius growth per tick
FIRE_INTENSITY_GROWTH = 0.9  # intensity per tick
BASE_EXTINGUISH_RATE = 15.0  # baseline intensity reduction per agent
MIN_EXTINGUISH_RATE = 8.0
MAX_EXTINGUISH_RATE = 28.0
TICK_INTERVAL_SECONDS = 3
WATER_PICKUP_RANGE = 40
EXTINGUISH_RANGE = 45
FIRE_SAFE_BUFFER = 10

class SimulationEngine:
    def __init__(self, state: SimulationState) -> None:
        self.state = state

    def _normalize_message(self, message: str | None) -> str:
        if not message:
            return "Staying focused and moving."
        cleaned = " ".join(str(message).strip().split())
        if not cleaned:
            return "Staying focused and moving."
        return cleaned[:220]

    def _move_toward(self, agent: AgentModel, target_x: float, target_y: float, stop_distance: float = 0) -> None:
        dx = target_x - agent.x
        dy = target_y - agent.y
        dist = math.sqrt(dx**2 + dy**2) or 1
        if dist <= stop_distance:
            return
        step = min(movement.MAX_AGENT_SPEED, dist - stop_distance)
        agent.x += int((dx / dist) * step)
        agent.y += int((dy / dist) * step)
        agent.x = max(0, min(agent.x, self.state.map_width))
        agent.y = max(0, min(agent.y, self.state.map_height))

    async def tick(self) -> TickResponse:
        """
        Main simulation loop:
        1. Get decisions from all living agents
        2. Handle coalition leadership voting
        3. Execute agent actions (search water, collect, extinguish, escape, etc.)
        4. Grow fire
        5. Extinguish fire if agents with water are present
        6. Kill agents in fire (but protect coalition members)
        7. Check win condition
        """
        if self.state.status != "running":
            raise ValueError(f"Cannot tick a simulation with status '{self.state.status}'.")

        fire = self.state.fire
        assert fire is not None, "Fire must be placed before ticking."

        events = []
        bounds = (self.state.map_width, self.state.map_height)
        living_agents = [a for a in self.state.agents if a.alive]
        recent_radio = [
            f"{a.display_name}: {a.last_message}"
            for a in living_agents
            if a.last_message
        ][-8:]

        # 1. Get decisions from all living agents
        decisions = await asyncio.gather(
            *[groq_client.generate_fire_decision(agent, fire, self.state.water_sources, living_agents, bounds, recent_radio)
              for agent in living_agents],
            return_exceptions=True
        )

        decision_map = {}
        for agent, decision in zip(living_agents, decisions):
            if isinstance(decision, Exception):
                decision = groq_client._fallback_escape(agent, fire)
            decision_map[agent.model_name] = decision

        # 2. Leadership voting phase (if coalition leader not elected)
        if not self.state.coalition_leader:
            vote_events = await self._voting_phase(living_agents, decision_map)
            events.extend(vote_events)

        # 3. Execute actions
        action_events = await self._execute_actions(living_agents, decision_map, fire)
        events.extend(action_events)

        # 4. Grow fire
        fire.radius += FIRE_GROWTH_RATE
        fire.intensity += FIRE_INTENSITY_GROWTH
        if fire.intensity > 100.0:
            fire.intensity = 100.0
        
        if fire.intensity > 0:
            events.append(FireSpreadEvent(new_radius=fire.radius, new_intensity=fire.intensity))

        # 5. Extinguish fire if agents with water are present
        extinguish_events = self._check_extinguish(living_agents, fire)
        events.extend(extinguish_events)

        # 6. Kill agents in fire
        death_events = self._kill_agents_in_fire(living_agents, fire)
        events.extend(death_events)

        # 7. Check win condition
        self.state.round += 1
        living_count = len([a for a in self.state.agents if a.alive])
        
        if fire.intensity <= 0:
            # Fire extinguished!
            self.state.status = "finished"
            top_score = max((a.extinguish_score for a in self.state.agents), default=0)
            top_agents = [a.model_name for a in self.state.agents if a.extinguish_score == top_score and top_score > 0]
            if top_agents:
                self.state.winner_model = f"Top extinguisher: {', '.join(top_agents)} ({top_score:.1f} impact)"
            else:
                self.state.winner_model = "Fire extinguished"
        elif living_count <= 1:
            # Only one agent left
            self.state.status = "finished"
            winner = next((a.model_name for a in self.state.agents if a.alive), None)
            self.state.winner_model = winner or "No survivors"

        return TickResponse(
            simulation_id=self.state.simulation_id,
            round=self.state.round,
            events=events,
            chat=[],
            state=self.state
        )

    async def _voting_phase(self, agents, decision_map):
        """
        Agents vote for a coalition leader.
        Get votes from LLM based on current situation.
        """
        events = []

        # Gather votes
        votes = {}  # candidate -> vote count
        for agent in agents:
            decision = decision_map.get(agent.model_name, {})
            vote_for = decision.get("vote_for")
            if vote_for:
                votes[vote_for] = votes.get(vote_for, 0) + 1
                events.append(LeadershipVoteEvent(voter=agent.model_name, candidate=vote_for))

        # Elect leader if there are votes
        if votes:
            leader_name = max(votes, key=votes.get)
            leader_agent = next((a for a in agents if a.model_name == leader_name), None)
            if leader_agent:
                for agent in agents:
                    agent.mode = "coalition"
                leader_agent.is_leader = True
                self.state.coalition_leader = leader_name
                coalition = [a.model_name for a in agents if a.mode == "coalition"]
                self.state.coalition_members = coalition
                events.append(LeaderElectedEvent(leader=leader_name, coalition_members=coalition))

        return events

    async def _execute_actions(self, agents, decision_map, fire):
        """
        Execute agent actions: search, collect water, extinguish, escape, vote, etc.
        """
        events = []
        chat_entries = []

        for agent in agents:
            decision = decision_map.get(agent.model_name, {})
            action = decision.get("action", "escape")
            message = self._normalize_message(decision.get("message"))

            nearest_water = self._find_nearest_water(agent, self.state.water_sources)
            dist_to_fire = math.dist((agent.x, agent.y), (fire.x, fire.y))
            dist_to_water = None
            if nearest_water:
                dist_to_water = math.dist((agent.x, agent.y), (nearest_water.x, nearest_water.y))

            # Guardrails to keep behavior consistent with visuals and objectives.
            if dist_to_fire <= fire.radius + FIRE_SAFE_BUFFER:
                action = "escape"
            elif agent.water_collected:
                action = "extinguish_fire"
            elif dist_to_water is not None and dist_to_water <= WATER_PICKUP_RANGE:
                action = "collect_water"
            else:
                action = "search_water"

            if action == "collect_water":
                water_source = nearest_water
                if water_source and dist_to_water is not None:
                    dist_to_water = math.dist((agent.x, agent.y), (water_source.x, water_source.y))
                    if dist_to_water <= WATER_PICKUP_RANGE:
                        agent.water_collected = True
                        agent.status = "collecting_water"
                        events.append(WaterCollectedEvent(model=agent.model_name, water_source_id=water_source.id))
                    else:
                        agent.status = "searching"
                        self._move_toward(agent, water_source.x, water_source.y)

            elif action == "extinguish_fire":
                if agent.water_collected:
                    agent.status = "extinguishing_fire"
                    dist_to_fire = math.dist((agent.x, agent.y), (fire.x, fire.y))
                    target_dist = max(fire.radius + FIRE_SAFE_BUFFER, 0)
                    self._move_toward(agent, fire.x, fire.y, stop_distance=target_dist)
                else:
                    agent.status = "searching"
                    message = self._normalize_message(decision.get("message"))

            elif action == "search_water":
                agent.status = "searching"
                water_source = nearest_water
                if water_source:
                    self._move_toward(agent, water_source.x, water_source.y)

            elif action == "escape":
                agent.status = "escaping"
                # Move away from fire
                dx = agent.x - fire.x
                dy = agent.y - fire.y
                dist = math.sqrt(dx**2 + dy**2) or 1
                agent.x += int((dx / dist) * movement.MAX_AGENT_SPEED)
                agent.y += int((dy / dist) * movement.MAX_AGENT_SPEED)
                agent.x = max(0, min(agent.x, self.state.map_width))
                agent.y = max(0, min(agent.y, self.state.map_height))

            agent.last_message = message
            events.append(MessageEvent(model=agent.model_name, content=message))
            chat_entries.append(ChatEntry(agent_id=agent.model_name, message=message, tick=self.state.round))

        return events

    def _find_nearest_water(self, agent, water_sources):
        """Find the closest water source to an agent."""
        if not water_sources:
            return None
        return min(water_sources, key=lambda w: math.dist((agent.x, agent.y), (w.x, w.y)))

    def _check_extinguish(self, agents, fire):
        """Check if agents with water are extinguishing the fire."""
        events = []
        agents_with_water = []
        for agent in agents:
            if not (agent.water_collected and agent.status == "extinguishing_fire"):
                continue
            dist_to_fire = math.dist((agent.x, agent.y), (fire.x, fire.y))
            if dist_to_fire <= fire.radius + EXTINGUISH_RANGE:
                agents_with_water.append(agent)
        
        if agents_with_water:
            living_count = len([a for a in agents if a.alive]) or 1
            scale = max(0.5, min(2.0, 2.0 / living_count))
            per_agent_rate = BASE_EXTINGUISH_RATE * scale
            per_agent_rate = max(MIN_EXTINGUISH_RATE, min(MAX_EXTINGUISH_RATE, per_agent_rate))
            reduction = len(agents_with_water) * per_agent_rate
            fire.intensity -= reduction
            if fire.intensity < 0:
                fire.intensity = 0
            
            extinguisher_names = [a.model_name for a in agents_with_water]
            events.append(FireExtinguishedEvent(extinguished_by=extinguisher_names, fire_intensity=fire.intensity))
            for agent in agents_with_water:
                agent.extinguish_score += per_agent_rate
                agent.water_collected = False

        return events

    def _kill_agents_in_fire(self, agents, fire):
        """Check if agents are consumed by fire."""
        events = []

        for agent in agents:
            if not agent.alive:
                continue

            dist_to_fire = math.dist((agent.x, agent.y), (fire.x, fire.y))
            
            # Agent dies if inside fire radius
            if dist_to_fire < fire.radius:
                agent.alive = False
                events.append(DeathEvent(model=agent.model_name))
                events.append(MessageEvent(model=agent.model_name, content="No!!! The fire got me..."))

        return events
