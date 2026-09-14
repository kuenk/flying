from enum import Enum

from src.domain.zone import Zone
from src.pathfinder.pathfinder import Path
from src.domain.connection import Connection


class DroneState(Enum):
    """Lifecycle state of a drone during the simulation.

    Attributes:
        AT_ZONE: The drone is stationed at a zone, able to decide its
            next move.
        IN_TRANSIT: The drone is traversing a connection toward a
            restricted zone, committed to arrive in a fixed number of turns.
        DELIVERED: The drone has reached the end zone and is no longer
            tracked.
    """
    AT_ZONE = "at_zone"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class Drone:
    """A drone navigating the network from start to end.

    Attributes:
        id: Unique identifier of the drone.
        state: Current lifecycle state of the drone.
        current_zone: The zone the drone is currently stationed at, if any.
        transit_connection: The connection the drone is currently
            traversing, if any.
        transit_turns_remaining: Turns left before completing a transit
            toward a restricted zone.
        path: The drone's currently planned route, which may be replaced
            by the scheduler if it becomes unviable.
        path_index: Index into path.zones marking the drone's current
            position along its planned route.
    """
    def __init__(self, drone_id: int,
                 path: Path) -> None:

        self.id = drone_id
        self.state = DroneState.AT_ZONE
        self.current_zone: Zone | None = path.zones[0]
        self.transit_connection: Connection | None = None
        self.transit_turns_remaining = 0
        self.path = path
        self.path_index = 0
