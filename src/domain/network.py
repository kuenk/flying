from .zone import Zone
from .connection import Connection
from src.domain import zone

class Network:
    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self._adjacency: dict[str, list[Connection]] = {}
        self.start_zone: Zone|None = None
        self.end_zone: Zone|None = None

    def add_zone(self, zone: Zone) -> None:
        """Register a zone in the network.
        Args:
            zone: The zone to add. If it is the start or end zone, it is
                also stored as such for quick access.
        """
        self.zones[zone.name] = zone
        self._adjacency[zone.name] = []
        if zone.is_start:
            self.start_zone = zone
        if zone.is_end:
            self.end_zone = zone

    

    def add_connection(self, connection: Connection) -> None:
        """Register a connection and update the adjacency index for both ends.
        Args:
            connection: The connection to add. Both zones it links must
                already be registered in the network.
        """
        self.connections.append(connection)
        self._adjacency[connection.zone_a.name].append(connection)
        self._adjacency[connection.zone_b.name].append(connection)


    def neighbors_of(self, zone_name: str) -> list[Zone]:
        """Return the zones directly reachable from the given zone.
        Args:
            zone_name: Name of the zone whose neighbors are requested.
        Returns:
            A list of zones connected to the given zone by a direct connection.
        """
        zone = self.zones[zone_name]
        res: list[Zone] = []
        for connection in self._adjacency[zone_name]:
            res.append(connection.other_side(zone))
        return res


    def connection_between(self, zone_a_name: str,
                           zone_b_name: str)-> Connection:    
        """Return the connection linking two zones by name.
        Args:
            zone_a_name: Name of one of the two zones.
            zone_b_name: Name of the other zone.
        Returns:
            The connection linking both zones.
        Raises:
            KeyError: If no connection exists between the two given zones.
        """
        zone_a = self.zones[zone_a_name]
        for connection in self._adjacency[zone_a_name]:
            if connection.other_side(zone_a).name == zone_b_name:
                return connection
        raise KeyError(f"No connection found between {zone_a_name}"
                       f" and {zone_b_name}.")


    def has_connection(self, zone_a_name: str, zone_b_name: str) -> bool:
        """Check whether a connection already exists between two zones.
        Args:
            zone_a_name: Name of one of the two zones.
            zone_b_name: Name of the other zone.

        Returns:
            True if a connection exists between both zones, False otherwise.
        """
        zone_a = self.zones[zone_a_name]
        for connection in self._adjacency[zone_a_name]:
            if connection.other_side(zone_a).name == zone_b_name:
                return True
        return False