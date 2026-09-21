
from src.domain import connection
from src.domain.network import Network
from src.simulation.drone import Drone, DroneState
from src.domain.zone import Zone, ZoneType


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
            if turn_log != "":
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
        
        for name, zone in self.network.zones.items():
            self.available_zone_capacity[name] = (
                zone.max_drones - zone_occupancy[name])
        for connection in self.network.connections:
            self.available_link_capacity[connection.name()] = (
                connection.max_link_capacity -
                link_occupancy[connection.name()])

    def _process_turn(self) -> str:
        """Process one simulation turn, moving drones in order of ID.

        Returns:
            The formatted log line for this turn (movements space-separated,
            empty string if no drone moved).
        """
        
        transit = self._advance_transits()
        ordered_drones = sorted(self.drones, key=lambda d: d.id)
        moved_drones: list[str] = transit
        for drone in ordered_drones:
            if drone.state == DroneState.AT_ZONE:
                movement = self._try_move_drone(drone)
                if movement is not None:
                    moved_drones.append(movement)
                    
        return " ".join(moved_drones)

    def _advance_transits(self) -> list[str]:
        """Advance drones currently in transit toward a restricted zone.

        Decrements each transiting drone's remaining turns; drones that
        complete their transit arrive at their destination zone (or are
        delivered if it is the end zone).

        Returns:
            The log entries for drones that completed their transit this turn.
        """
        log_entries: list[str] = []
        for drone in self.drones:
            if drone.state == DroneState.IN_TRANSIT:
                drone.transit_turns_remaining -= 1
                if drone.transit_turns_remaining == 0:
                    drone.path_index += 1
                    drone.current_zone = drone.path.zones[drone.path_index]
                    if drone.current_zone.is_end:
                        drone.state = DroneState.DELIVERED
                    else:
                        drone.state = DroneState.AT_ZONE
                    log_entries.append(f"D{drone.id}-"
                                       f"{drone.current_zone.name}")

        return log_entries


    def _try_move_drone(self, drone: Drone) -> str | None:
        """Attempt to move a drone one step along its planned path.

        Checks destination zone and connection capacity before committing.
        Handles both normal moves (completed this turn) and restricted zones
        (drone enters transit for two turns, reserving capacity immediately).

        Args:
            drone: The drone to move. Must be in the AT_ZONE state.

        Returns:
            The log entry for this drone's movement, or None if it could not
            move this turn due to insufficient capacity.
        """
        next_zone = drone.path.zones[drone.path_index + 1]
        connection = self.network.connection_between(drone.current_zone.name,
                                                     next_zone.name)
        has_capacity: bool = True
        if self.available_link_capacity[connection.name()] <= 0:
            has_capacity = False
        if self.available_zone_capacity[next_zone.name] <= 0:
            has_capacity = False

        origin_zone_name = drone.current_zone.name
        if has_capacity:
            if next_zone.zone_type == ZoneType.RESTRICTED:
                drone.state = DroneState.IN_TRANSIT
                self.available_zone_capacity[origin_zone_name] += 1
                self.available_zone_capacity[next_zone.name] -= 1
                self.available_link_capacity[connection.name()] -= 1
                drone.transit_connection = connection
                drone.transit_turns_remaining = 2
                drone.current_zone = None
                return f"D{drone.id}-{connection.name()}"
            
            else:
                if next_zone.is_end:
                    drone.state = DroneState.DELIVERED
                else:
                    drone.state = DroneState.AT_ZONE
                self.available_zone_capacity[origin_zone_name] += 1
                self.available_zone_capacity[next_zone.name] -= 1
                self.available_link_capacity[connection.name()] -= 1
                drone.current_zone = next_zone
                drone.path_index += 1
                return f"D{drone.id}-{next_zone.name}"
        else:
            return None


    def _all_delivered(self) -> bool:
        """Check whether every drone has reached the end zone.

        Returns:
            True if all drones are in the DELIVERED state.
        """
        return all(drone.state == DroneState.DELIVERED
                   for drone in self.drones)
