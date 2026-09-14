from src.domain.network import Network
from src.domain.zone import Zone, ZoneType
import heapq


class Path:
    """A sequence of zones to traverse, with its total movement cost.

    Attributes:
        zones: The ordered sequence of zones from origin to destination.
        total_cost: The total number of turns required to traverse this
            path, according to each zone's movement cost.
    """

    def __init__(self, zones: list[Zone], total_cost: int) -> None:
        self.zones = zones
        self.total_cost = total_cost


def dijkstra(network: Network, start_name: str, end_name: str) -> Path:
    """Find the minimum-cost path between two zones, preferring priority zones.

    Uses Dijkstra's algorithm, where the cost of entering each zone is given
    by its movement cost. Ties in total cost are broken in favor of paths
    that pass through more priority zones.

    Args:
        network: The network to search.
        start_name: Name of the starting zone.
        end_name: Name of the destination zone.

    Returns:
        The lowest-cost path from start to end, including its total cost.

    Raises:
        ValueError: If no path exists between the two zones.
    """
    
    best_cost: dict[str, float] = {zone_name: float('inf')
                                    for zone_name in network.zones}
    best_cost[start_name] = 0
    best_priority_count: dict[str, int] = {zone_name: 0
                                            for zone_name in network.zones}
    previous: dict[str, str] = {}
    queue: list[tuple[float, int, str]] = [(0, 0, start_name)]

    while queue:
        cost, neg_priority_count, current_name = heapq.heappop(queue)
        if current_name == end_name:
            break
        if cost > best_cost[current_name]:
            continue

        for neighbor in network.neighbors_of(current_name):
            if neighbor.zone_type == ZoneType.BLOCKED:
                continue
                
            new_cost = cost + neighbor.movement_cost
            priority_bonus = 0
            if neighbor.zone_type == ZoneType.PRIORITY:
                priority_bonus = 1

            new_priority_count = -neg_priority_count + priority_bonus
            if new_cost < best_cost[neighbor.name] or (
                new_cost == best_cost[neighbor.name] and
                new_priority_count > best_priority_count[neighbor.name]
            ):
                best_cost[neighbor.name] = new_cost
                best_priority_count[neighbor.name] = new_priority_count
                previous[neighbor.name] = current_name
                heapq.heappush(queue, (new_cost, -new_priority_count, neighbor.name))

    if best_cost[end_name] == float('inf'):
        raise ValueError(f"No path exists from {start_name} to {end_name}")
    current = end_name
    path_names = [end_name]
    while current != start_name:
        current = previous[current]
        path_names.append(current)
    path_names.reverse()

    path_zones: list[Zone] = []
    for name in path_names:
        path_zones.append(network.zones[name])

    return Path(path_zones, best_cost[end_name])

        
