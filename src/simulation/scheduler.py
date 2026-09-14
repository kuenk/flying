
from src.domain import connection
from src.domain.network import Network
from src.simulation.drone import Drone, DroneState


class Scheduler:
    """Runs the turn-based drone simulation over a network.

    Attributes:
        network: The network drones move through.
        drones: All drones participating in the simulation.
        max_turns: Safety limit on the number of turns, to detect
            unresolved deadlocks instead of looping forever.
        turn: The current turn number.
        available_zone_capacity: Free capacity per zone name, recomputed
            at the start of each turn.
        available_link_capacity: Free capacity per connection name,
            recomputed at the start of each turn.
    """
    def __init__(self, network: Network,
                 drones: list[Drone], max_turns: int) -> None:
        self.network = network
        self.drones = drones
        self.max_turns = max_turns
        self.turn: int = 0
        self.available_zone_capacity: dict[str, int] = {}
        self.available_link_capacity: dict[str, int] = {}

    def run(self) -> list[str]:
        """Execute the simulation turn by turn until all drones are delivered.
        Returns:
            The log lines for each turn, in order.

        Raises:
            RuntimeError: If the simulation exceeds max_turns without all
                drones reaching the end zone, indicating an unresolved deadlock.
        """
        turn_logs: list[str] = []
        while not self._all_delivered():
            self.turn += 1
            if self.turn > self.max_turns:
                raise RuntimeError(
                    f"Exceeded max turns ({self.max_turns}) without "
                    "delivering all packages.")
            self._recompute_available_capacity()
            turn_log = self._process_turn()
            turn_logs.append(turn_log)
        return turn_logs




    def _recompute_available_capacity(self) -> None:
        """Recompute free capacity for every zone and connection this turn.

        Accounts for drones physically at a zone, as well as drones in
        transit toward a restricted zone, which reserve their destination
        capacity and occupy their connection for the whole transit.
        """
        zone_occupancy: dict[str, int] = {name: 0 for name
                                          in self.network.zones}
        link_occupancy: dict[str, int] ={connection.name(): 0
                                         for connection
                                         in self.network.connections}
        for drone in self.drones:
            if drone.state == DroneState.AT_ZONE:
                zone_occupancy[drone.current_zone.name] += 1
            elif drone.state == DroneState.IN_TRANSIT:
                destination = drone.path.zones[drone.path_index + 1]
                zone_occupancy[destination.name] += 1
                link_occupancy[drone.transit_connection.name()] += 1

    def _process_turn(self):

    def _try_move_drone(drone: Drone) -> bool

    def _all_delivered(self) -> bool:
        """Check whether every drone has reached the end zone.

        Returns:
            True if all drones are in the DELIVERED state.
        """
        return all(drone.state == DroneState.DELIVERED for drone in self.drones)
