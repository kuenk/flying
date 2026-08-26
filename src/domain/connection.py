from .zone import Zone

class Connection:
    """A bidirectional link between two zones.

    Attributes:
        zone_a: One endpoint of the connection.
        zone_b: The other endpoint of the connection.
        max_link_capacity: Maximum number of drones that can traverse this
            connection simultaneously.
    """
    def __init__(self, zone_a: Zone, zone_b: Zone,
                 max_link_capacity: int) -> None:
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity

    def other_side(self, zone: Zone) -> Zone:
        """Return the zone on the opposite end of the connection.
        Args:
            zone: One of the two zones this connection links.
        Returns:
            The zone at the other end of the connection.
        Raises:
            ValueError: If the given zone is not part of this connection.
        """
        if self.zone_a is zone:
            return self.zone_b
        elif self.zone_b is zone:
            return self.zone_a
        else:
            raise ValueError(f"Zone {zone.name} is not"
                             f" part of this connection.")

    def name(self) -> str:
        """Return the connection identifier, e.g. 'zoneA-zoneB'."""
        return f"{self.zone_a.name}-{self.zone_b.name}"