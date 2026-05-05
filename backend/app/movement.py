import math

MAX_AGENT_SPEED = 80

def apply_movement(agent, dx: int, dy: int, bounds: tuple) -> tuple[int, int]:
    # 1. Clamp dx/dy to [-MAX_AGENT_SPEED, MAX_AGENT_SPEED]
    dx = max(-MAX_AGENT_SPEED, min(MAX_AGENT_SPEED, dx))
    dy = max(-MAX_AGENT_SPEED, min(MAX_AGENT_SPEED, dy))
    
    # 2. Calculate new_x, new_y
    new_x = agent.x + dx
    new_y = agent.y + dy
    
    # 3. Clamp to canvas bounds
    new_x = max(0, min(new_x, bounds[0]))
    new_y = max(0, min(new_y, bounds[1]))
    
    # 4. Return (new_x, new_y)
    return (int(new_x), int(new_y))

def is_in_lava(agent, volcano) -> bool:
    if not volcano:
        return False
    return math.dist((agent.x, agent.y), (volcano.x, volcano.y)) <= volcano.radius

def distance_to_lava_edge(agent, volcano) -> float:
    if not volcano:
        return 1000.0
    return math.dist((agent.x, agent.y), (volcano.x, volcano.y)) - volcano.radius
