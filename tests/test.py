from src.domain.zone import Zone, ZoneType
from src.domain.connection import Connection
from src.domain.network import Network
from src.parsing.parser import MapStructureError, parse_file, parse_zone_line, ParseError

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








network, nb_drones = parse_file("maps/maps.txt")

assert nb_drones == 5
assert len(network.zones) == 7
assert len(network.connections) == 6
assert network.start_zone is network.zones["hub"]
assert network.end_zone is network.zones["goal"]
print("OK: fichero de ejemplo parseado correctamente")

# Tipo de zona inválido
with open("maps/bad_zone_type.txt", "w") as file:
    file.write("nb_drones: 1\n")
    file.write("start_hub: a 0 0\n")
    file.write("end_hub: b 1 1\n")
    file.write("hub: c 2 2 [zone=foo]\n")
try:
    parse_file("maps/bad_zone_type.txt")
    print("FALLO: se esperaba ParseError")
except ParseError as error:
    print(f"OK: tipo de zona inválido detectado -> {error}")

# Conexión duplicada
with open("maps/duplicate_connection.txt", "w") as file:
    file.write("nb_drones: 1\n")
    file.write("start_hub: a 0 0\n")
    file.write("end_hub: b 1 1\n")
    file.write("connection: a-b\n")
    file.write("connection: b-a\n")
try:
    parse_file("maps/duplicate_connection.txt")
    print("FALLO: se esperaba ParseError")
except ParseError as error:
    print(f"OK: conexión duplicada detectada -> {error}")

# Conexión a zona no definida
with open("maps/undefined_zone.txt", "w") as file:
    file.write("nb_drones: 1\n")
    file.write("start_hub: a 0 0\n")
    file.write("end_hub: b 1 1\n")
    file.write("connection: a-ghost\n")
try:
    parse_file("maps/undefined_zone.txt")
    print("FALLO: se esperaba ParseError")
except ParseError as error:
    print(f"OK: zona no definida detectada -> {error}")

# Falta start_hub -> ahora es MapStructureError, no ParseError
with open("maps/missing_start.txt", "w") as file:
    file.write("nb_drones: 1\n")
    file.write("end_hub: b 1 1\n")
try:
    parse_file("maps/missing_start.txt")
    print("FALLO: se esperaba MapStructureError")
except MapStructureError as error:
    print(f"OK: start_hub ausente detectado -> {error}")

print("parse_file OK — Capítulo 3 completo")