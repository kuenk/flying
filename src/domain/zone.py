from enum import Enum
from math import inf

class ZoneType(Enum):
    """Type of a zone, determining its movement cost and accessibility.
        Attributes:
            NORMAL: Standard zone, costs 1 turn to enter.
            BLOCKED: Inaccessible zone, cannot be entered.
            RESTRICTED: Costs 2 turns to enter, entry must complete in a single transit.
            PRIORITY: Costs 1 turn but should be preferred by pathfinding.
    """
    NORMAL = "normal"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
    BLOCKED = "blocked"

MOVEMENT_COST: dict[ZoneType, int] = {
    ZoneType.NORMAL: 1,
    ZoneType.RESTRICTED: 2,
    ZoneType.PRIORITY: 1
}

class Zone:
    """A single zone in the drone network.
        Attributes:
            name: Unique identifier of the zone.
            x: X coordinate of the zone.
            y: Y coordinate of the zone.
            zone_type: The ZoneType determining movement cost and accessibility.
            is_start: Whether this zone is the unique starting zone.
            is_end: Whether this zone is the unique end zone.
            max_drones: Maximum number of drones allowed simultaneously in this
                zone. Infinite for the start and end zones, regardless of the
                value provided at construction.
            color: Optional color used for visual representation.
    """
    def __init__(self, name: str, x: int, y: int, zone_type: ZoneType,
                 max_drones: int, is_start: bool, is_end: bool,
                 color: str|None = None) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.is_start = is_start
        self.is_end = is_end
        if is_start or is_end:
            self.max_drones: float = inf
        else:
            self.max_drones = max_drones
        self.color = color


    @property
    def movement_cost(self) -> int:
        """Return the turn cost to move into this zone.
        Raises:
            ValueError: If the zone is blocked and therefore
            cannot be entered.
        """
        if self.zone_type == ZoneType.BLOCKED:
            raise ValueError(f"Zone {self.name} is blocked and"
                             f"cannot be entered.")
        return MOVEMENT_COST[self.zone_type]