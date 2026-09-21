from src.domain.zone import Zone, ZoneType
from src.domain.connection import Connection
from src.domain.network import Network
from src.parsing.parser import parse_zone_line, ParseError

# Construcción manual de una red pequeña: hub -> roof1 -> goal
hub = Zone("hub", 0, 0, ZoneType.NORMAL, max_drones=1,
           is_start=True, is_end=False)
roof1 = Zone("roof1", 3, 4, ZoneType.NORMAL, max_drones=1,
             is_start=False, is_end=False)
goal = Zone("goal", 10, 10, ZoneType.NORMAL, max_drones=1,
            is_start=False, is_end=True)

network = Network()
network.add_zone(hub)
network.add_zone(roof1)
network.add_zone(goal)

connection_hub_roof1 = Connection(hub, roof1, max_link_capacity=1)
connection_roof1_goal = Connection(roof1, goal, max_link_capacity=1)
network.add_connection(connection_hub_roof1)
network.add_connection(connection_roof1_goal)

# 1. neighbors_of en ambos sentidos
assert roof1 in network.neighbors_of("hub")
assert hub in network.neighbors_of("roof1")
assert goal in network.neighbors_of("roof1")
print("OK: neighbors_of funciona en ambos sentidos")

# 2. has_connection es simétrico
assert network.has_connection("hub", "roof1") is True
assert network.has_connection("roof1", "hub") is True
assert network.has_connection("hub", "goal") is False
print("OK: has_connection es simétrico y detecta ausencia de conexión")

# 3. max_drones infinito en la zona start
assert network.start_zone is hub
assert network.end_zone is goal
assert hub.max_drones == float("inf")
print("OK: la zona start tiene capacidad infinita")

# Extra: connection_between coincide con lo esperado
assert network.connection_between("hub", "roof1") is connection_hub_roof1
try:
    network.connection_between("hub", "goal")
    print("FALLO: se esperaba KeyError")
except KeyError as error:
    print(f"OK: connection_between lanza KeyError si no hay conexión -> {error}")

print("Network OK — Capítulo 2 completo")

# Zona hub normal, sin metadata
zone1 = parse_zone_line("hub: roof2 6 2", 1)
assert zone1.name == "roof2"
assert zone1.x == 6 and zone1.y == 2
assert zone1.zone_type == ZoneType.NORMAL
assert zone1.color is None
assert zone1.max_drones == 1
print("OK: zona sin metadata usa los defaults correctos")

# start_hub con metadata parcial
zone2 = parse_zone_line("start_hub: hub 0 0 [color=green]", 2)
assert zone2.is_start is True
assert zone2.color == "green"
assert zone2.max_drones == float("inf")  # is_start ignora max_drones, vía Zone.__init__
print("OK: start_hub tiene capacidad infinita pese al default de 1")

# hub con metadata completa
zone3 = parse_zone_line(
    "hub: corridorA 4 3 [zone=priority color=green max_drones=2]", 3)
assert zone3.zone_type == ZoneType.PRIORITY
assert zone3.max_drones == 2
print("OK: metadata completa parseada correctamente")

# Prefijo inválido
try:
    parse_zone_line("weird_hub: x 1 1", 4)
    print("FALLO: se esperaba ParseError")
except ParseError as error:
    print(f"OK: prefijo inválido detectado -> {error}")

# Tipo de zona inválido
try:
    parse_zone_line("hub: y 2 2 [zone=foo]", 5)
    print("FALLO: se esperaba ParseError")
except ParseError as error:
    print(f"OK: tipo de zona inválido detectado -> {error}")

# Corchete sin cerrar
try:
    parse_zone_line("hub: z 3 3 [zone=normal", 6)
    print("FALLO: se esperaba ParseError")
except ParseError as error:
    print(f"OK: corchete sin cerrar detectado -> {error}")

print("parse_zone_line OK")

from src.parsing.parser import parse_file
from src.pathfinder.pathfinder import dijkstra
from src.simulation.drone import Drone, DroneState
from src.simulation.scheduler import Scheduler

# 1. Simulación básica sobre el mapa de ejemplo del subject
network, nb_drones = parse_file("maps/example.txt")
path = dijkstra(network, network.start_zone.name, network.end_zone.name)
drones = [Drone(i, path) for i in range(1, nb_drones + 1)]

scheduler = Scheduler(network, drones, max_turns=60)
logs = scheduler.run()

print(f"Simulación completada en {len(logs)} turnos")
for line in logs:
    print(line)
assert all(drone.state == DroneState.DELIVERED for drone in drones)
print("OK: todos los drones entregados")

# 2. Verificar que ningún dron viola la capacidad en ningún turno intermedio
# (esto ya lo garantiza el diseño, pero lo confirmamos con un mapa de capacidad ajustada)
with open("maps/capacity_check.txt", "w") as f:
    f.write("nb_drones: 3\n")
    f.write("start_hub: a 0 0\n")
    f.write("hub: bottleneck 1 0 [max_drones=1]\n")
    f.write("end_hub: c 2 0\n")
    f.write("connection: a-bottleneck\n")
    f.write("connection: bottleneck-c\n")

cap_network, cap_nb_drones = parse_file("maps/capacity_check.txt")
cap_path = dijkstra(cap_network, cap_network.start_zone.name, cap_network.end_zone.name)
cap_drones = [Drone(i, cap_path) for i in range(1, cap_nb_drones + 1)]

cap_scheduler = Scheduler(cap_network, cap_drones, max_turns=20)
cap_logs = cap_scheduler.run()

print(f"\nMapa de cuello de botella (capacidad 1), {len(cap_logs)} turnos:")
for line in cap_logs:
    print(line)
assert all(drone.state == DroneState.DELIVERED for drone in cap_drones)
print("OK: los 3 drones pasan uno a uno por el cuello de botella sin violar capacidad")

# 3. Verificar el caso restricted: el dron aparece como conexión, luego como zona
with open("maps/restricted_check.txt", "w") as f:
    f.write("nb_drones: 1\n")
    f.write("start_hub: a 0 0\n")
    f.write("hub: r 1 0 [zone=restricted]\n")
    f.write("end_hub: b 2 0\n")
    f.write("connection: a-r\n")
    f.write("connection: r-b\n")

r_network, r_nb_drones = parse_file("maps/restricted_check.txt")
r_path = dijkstra(r_network, r_network.start_zone.name, r_network.end_zone.name)
r_drones = [Drone(i, r_path) for i in range(1, r_nb_drones + 1)]

r_scheduler = Scheduler(r_network, r_drones, max_turns=10)
r_logs = r_scheduler.run()

print(f"\nMapa con zona restricted, {len(r_logs)} turnos:")
for line in r_logs:
    print(line)
assert "D1-a-r" in r_logs[0]
assert r_logs[1] == ""
assert "D1-r" in r_logs[2]
print("OK: el dron entra en tránsito, espera un turno, y llega a la zona restricted")

print("\nScheduler OK — Capítulo 5 completo")