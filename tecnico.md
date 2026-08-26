# Fly-in — Guía técnica de desarrollo

> Documento de acompañamiento para implementar Fly-in en orden de ejecución real:
> cada capítulo construye sobre el anterior, sin piezas sueltas que haya que
> ensamblar al final. El código mostrado es **pseudocódigo o esqueletos de clase**
> — la implementación completa la escribes tú.

---

## Cómo usar este documento

Cada capítulo tiene tres partes:

- **Objetivo** — qué problema resuelve esta pieza dentro del flujo completo.
- **Diseño** — decisiones técnicas y pseudocódigo de las estructuras/algoritmos.
- **Checkpoint** — cómo comprobar que la pieza funciona antes de pasar a la siguiente.

No avances de capítulo sin pasar su checkpoint. El objetivo es que en ningún
momento tengas "código huérfano" que no sepas si funciona.

---

## Capítulo 0 — Setup del proyecto

### Objetivo
Tener el esqueleto del repo listo antes de escribir lógica, para no interrumpir
el desarrollo más adelante con configuración.

### Diseño

Estructura de carpetas sugerida:

```
fly-in/
├── Makefile
├── .gitignore
├── README.md
├── requirements.txt (si aplica)
├── src/
│   ├── __init__.py
│   ├── domain/          # Capítulo 2
│   │   ├── zone.py
│   │   ├── connection.py
│   │   └── network.py
│   ├── parsing/         # Capítulo 3
│   │   └── parser.py
│   ├── pathfinding/     # Capítulo 4
│   │   └── pathfinder.py
│   ├── simulation/      # Capítulo 5
│   │   ├── drone.py
│   │   └── scheduler.py
│   ├── output/          # Capítulo 6
│   │   └── formatter.py
│   ├── visualization/   # Capítulo 7
│   │   └── terminal_view.py
│   └── main.py
├── maps/                 # tus propios ficheros de mapa
└── tests/
```

Makefile: implementa ya los targets obligatorios (`install`, `run`, `debug`,
`clean`, `lint`, `lint-strict`) aunque `run` todavía no haga nada útil —
apuntando a `src/main.py`. Así el pipeline de lint/mypy está activo desde el
primer commit y detectas problemas de tipado desde ya.

### Checkpoint
- `make lint` pasa sin errores sobre un `main.py` vacío con un `print("Fly-in")`.
- `make clean` elimina `__pycache__` y `.mypy_cache` correctamente.

---

## Capítulo 1 — Excepciones del dominio

### Objetivo
Antes de escribir cualquier clase, define cómo va a fallar el sistema. Todo
el parser (Capítulo 3) va a depender de esto.

### Diseño

Una única excepción base es suficiente — el subject pide "mensaje claro
indicando línea y causa", no un manejo diferenciado por tipo de error:

```
class ParseError(Exception):
    line_number: int
    message: str
    # __init__ construye el mensaje final como "Line {n}: {message}"
```

Colócala en `src/parsing/errors.py` (o en `domain/` si prefieres verla como
parte del dominio — es una decisión menor).

### Checkpoint
- Lanza `ParseError(3, "invalid zone type")` en una prueba suelta y confirma
  que `str(error)` da un mensaje legible con número de línea.

---

## Capítulo 2 — Modelo de dominio

### Objetivo
Estas son las estructuras que el parser va a ir rellenando. Tienen que existir
**antes** del parser porque este las instancia mientras lee.

### Diseño

Decisión ya tomada: **Network centralizada** (no grafo distribuido). `Zone` y
`Connection` son estructuras de datos; `Network` concentra la lógica de grafo
(adyacencia, búsqueda, detección de duplicados).

```
enum ZoneType: NORMAL, BLOCKED, RESTRICTED, PRIORITY

MOVEMENT_COST = {
    NORMAL: 1, RESTRICTED: 2, PRIORITY: 1, BLOCKED: unreachable
}

class Zone:
    name, x, y, zone_type, color, max_drones, is_start, is_end
    # si is_start o is_end -> max_drones se ignora (capacidad infinita)
    method movement_cost() -> int

class Connection:
    zone_a, zone_b, max_link_capacity
    method other_side(zone) -> Zone
    method name() -> str   # "zoneA-zoneB"

class Network:
    zones: dict[name -> Zone]
    connections: list[Connection]
    _adjacency: dict[name -> list[Connection]]   # índice para O(grado) en vez de O(n)
    start_zone, end_zone

    method add_zone(zone)
    method add_connection(connection)
    method neighbors_of(zone_name) -> list[Zone]
    method connection_between(name_a, name_b) -> Connection
    method has_connection(name_a, name_b) -> bool   # usado por el parser para detectar duplicados
```

**Por qué `_adjacency` como índice aparte:** si `neighbors_of` recorriera
`self.connections` cada vez, sería O(número total de conexiones) por consulta.
Con un diccionario de listas es O(grado del nodo), lo cual importa en los
mapas "hard" con muchas conexiones y llamadas repetidas durante el pathfinding
y la simulación turno a turno.

### Checkpoint
- Construye a mano (sin parser) un `Network` pequeño de 3 zonas y 2 conexiones.
- Verifica `neighbors_of` en ambos sentidos (las conexiones son bidireccionales).
- Verifica que `has_connection("a", "b")` y `has_connection("b", "a")` devuelven
  lo mismo — esto es exactamente la regla anti-duplicados que usará el parser.
- Verifica que una `Zone` con `is_start=True` tiene `max_drones` infinito
  aunque se le pase `max_drones=1` en el constructor.

---

## Capítulo 3 — Parser

### Objetivo
Convertir el fichero de texto en un `Network` completamente poblado y
validado. Es la primera pieza que se ejecuta realmente cuando corre el programa.

### Diseño

El parser procesa el fichero en **dos pasadas lógicas** (no necesariamente dos
bucles físicos, pero sí dos fases):

1. **Fase de zonas**: `nb_drones`, `start_hub`, `end_hub`, `hub` — todas deben
   procesarse antes de la fase de conexiones, porque una conexión solo es
   válida si ambos extremos ya existen.
2. **Fase de conexiones**: cada `connection:` se resuelve contra el `Network`
   ya construido.

Esto no exige literalmente "dos loops" — puedes procesar línea a línea y
simplemente lanzar `ParseError` si una `connection:` referencia una zona que
aún no existe (equivalente a decir "las conexiones deben ir después de sus
zonas en el fichero", que es lo que implica el propio formato de ejemplo).

Pseudocódigo del flujo principal:

```
function parse_file(path) -> Network:
    network = Network()
    nb_drones = None
    seen_start = False
    seen_end = False

    for line_number, raw_line in enumerate(lines, start=1):
        line = strip_comment_and_whitespace(raw_line)
        if line is empty: continue

        if line starts with "nb_drones:":
            nb_drones = parse_positive_int(line, line_number)

        elif line starts with "start_hub:" or "end_hub:" or "hub:":
            zone = parse_zone_line(line, line_number)
            validate_unique_name(zone, network, line_number)
            network.add_zone(zone)
            track seen_start / seen_end

        elif line starts with "connection:":
            connection = parse_connection_line(line, network, line_number)
            # aquí se valida: ambos extremos existen, no es duplicado
            network.add_connection(connection)

        else:
            raise ParseError(line_number, "unrecognized line format")

    if nb_drones is None: raise ParseError(...)
    if not seen_start or not seen_end: raise ParseError(...)

    return network, nb_drones
```

Sub-parsers a considerar (cada uno con su propia función, para que el
`flake8`/longitud por función del 42-norm no se dispare):

```
function parse_metadata_block(raw: str) -> dict[str, str]:
    # extrae lo que hay entre [ ... ], separado por espacios,
    # cada tag como key=value. Orden libre (el subject lo permite).

function parse_zone_line(line, line_number) -> Zone:
    # separa prefijo (start_hub/end_hub/hub), nombre, x, y, metadata
    # valida: nombre sin espacios/guiones, x/y enteros, zone_type válido,
    # max_drones entero positivo (ignorado si start/end)

function parse_connection_line(line, network, line_number) -> Connection:
    # separa "name1-name2" — ¡cuidado! los nombres de zona no llevan guion,
    # así que el separador "-" es no ambiguo
    # valida: ambos existen en network, no hay conexión duplicada,
    # max_link_capacity entero positivo si está presente
```

**Punto delicado:** el subject dice "connection: <zone1>-<zone2>" y que los
nombres de zona no permiten guiones — eso es precisamente lo que hace que
`split("-", 1)` sea seguro para separar `name1` de `name2` sin ambigüedad.

### Checkpoint
- Parsea el fichero de ejemplo del subject (Capítulo VI del PDF) y verifica
  que `network.zones` tiene 6 zonas y `network.connections` tiene 6 conexiones.
- Prueba casos de error explícitamente, uno por uno, y confirma que cada uno
  lanza `ParseError` con el número de línea correcto:
  - tipo de zona inválido (`zone=foo`)
  - conexión duplicada (`a-b` seguido de `b-a`)
  - conexión a una zona no definida
  - dos `start_hub:`
  - `max_drones` en `start_hub` (debe ignorarse, **no** debe fallar)
  - `nb_drones` ausente o no positivo

---

## Capítulo 4 — Pathfinding

### Objetivo
Antes de simular turnos con múltiples drones, necesitas saber **qué caminos
son buenos** desde `start` a `end`. Esta pieza calcula rutas (o un conjunto de
rutas candidatas) que luego el scheduler (Capítulo 5) va a repartir entre
drones turno a turno.

### Diseño — tres opciones con trade-offs

**Opción A — BFS puro (número de saltos, ignorando coste de zona)**

```
function bfs(network, start, end) -> path:
    # exploración por niveles, todas las aristas "cuestan" lo mismo
```

*Pros:* trivial de implementar, O(V+E).
*Contras:* **no vale para este proyecto**. El subject exige que el algoritmo
tenga en cuenta explícitamente que `restricted` cuesta 2 turnos y `priority`
debe preferirse. BFS no distingue coste, así que puede devolver una ruta que
pase por una zona restricted cuando había una alternativa normal igual de
corta en saltos pero más barata en turnos. Lo incluyo solo como punto de
partida conceptual, no como candidata real.

**Opción B — Dijkstra (camino de coste mínimo)**

```
function dijkstra(network, start, end) -> path:
    distances = {zone: infinity for all zones}
    distances[start] = 0
    priority_queue = [(0, start)]
    previous = {}

    while priority_queue not empty:
        current_dist, current_zone = pop_min(priority_queue)
        if current_zone == end: break
        if current_zone.zone_type == BLOCKED: continue  # nunca se expande

        for neighbor in network.neighbors_of(current_zone):
            if neighbor.zone_type == BLOCKED: continue
            new_dist = current_dist + neighbor.movement_cost()
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                previous[neighbor] = current_zone
                push(priority_queue, (new_dist, neighbor))

    return reconstruct_path(previous, end)
```

*Pros:* resuelve exactamente lo que pide el subject — coste real en turnos,
respeta `blocked` como intransitable, y es fácil de sesgar hacia `priority`
bajándole artificialmente el coste (p. ej. tratarlo como 0.9 en el desempate,
o como criterio de desempate a igualdad de coste). Complejidad O((V+E) log V)
con heap — perfectamente asumible incluso en el mapa de 25 drones.
*Contras:* por sí solo, Dijkstra te da **un solo camino óptimo** entre dos
zonas. No resuelve el reparto de múltiples drones por caminos distintos para
maximizar throughput — eso es responsabilidad del scheduler, no del
pathfinder. Dijkstra es el bloque que el scheduler va a invocar
(posiblemente varias veces, con distintos pesos, o con aristas "penalizadas"
si ya están saturadas por otros drones).

**Opción C — K caminos más cortos (Yen's algorithm o variante simple)**

```
function k_shortest_paths(network, start, end, k) -> list[path]:
    # calcula el camino óptimo con Dijkstra, luego genera variantes
    # "casi óptimas" eliminando aristas/nodos del mejor camino y
    # recalculando, hasta tener k caminos distintos
```

*Pros:* te da de entrada varias rutas candidatas para repartir drones en
paralelo, útil si el grafo tiene bifurcaciones claras.
*Contras:* más complejo de implementar e innecesario si el scheduler ya sabe
recalcular con Dijkstra "bajo demanda" cuando detecta que un camino está
saturado (ver Capítulo 5). Es fácil caer en over-engineering aquí.

**Mi recomendación:** implementa **Dijkstra (B)** como la única pieza de
pathfinding "puro", y deja que la distribución entre múltiples caminos la
resuelva el *scheduler* recalculando o penalizando dinámicamente (ahí es
donde de verdad se gana o se pierde eficiencia en turnos, no en el cálculo
de un único camino). Empieza por B; si al medir turnos contra los
benchmarks del subject ves que un solo camino óptimo compartido por todos
los drones genera cuellos de botella, entonces vale la pena mirar C.

### Checkpoint
- Sobre el mapa de ejemplo del PDF, calcula el camino óptimo con Dijkstra y
  verifica a mano que su coste coincide con lo esperado (cuenta los turnos
  tú mismo sobre el diagrama del subject).
- Prueba con un mapa donde el camino más corto en saltos pase por una zona
  `restricted` y exista una alternativa más larga en saltos pero más barata
  en turnos — confirma que Dijkstra elige la segunda.
- Prueba que una zona `blocked` en medio del único camino existente hace que
  la función devuelva "sin camino" en vez de crashear.

---

## Capítulo 5 — Motor de simulación / Scheduler

### Objetivo
Esta es la pieza central del proyecto: mover **varios drones a la vez**,
turno a turno, respetando capacidades de zona y conexión, gestionando el
caso especial de las zonas `restricted`, y evitando deadlocks.

### Diseño

**Estado de un drone** — modélalo explícitamente como máquina de estados,
no como una simple posición:

```
enum DroneState: AT_ZONE, IN_TRANSIT, DELIVERED

class Drone:
    id, state
    current_zone: Zone | None          # válido si AT_ZONE
    transit_connection: Connection | None   # válido si IN_TRANSIT
    transit_turns_remaining: int       # para el caso restricted (2 turnos)
    path: list[Zone]                   # ruta objetivo calculada por Dijkstra
    path_index: int                    # posición actual dentro de path
```

**Por qué hace falta el estado `IN_TRANSIT` con contador:** el subject es
explícito en que, al entrar en una conexión hacia una zona `restricted`, el
drone **debe** llegar exactamente 2 turnos después, sin poder esperar a
mitad de camino. Eso significa que una vez que un drone "compromete" ese
movimiento, no es libre de cambiar de decisión hasta que llegue — es
distinto de un movimiento normal de 1 turno, que se decide de nuevo cada vez.

**Bucle principal de simulación (turno a turno):**

```
function simulate(network, drones) -> list[turn_log]:
    turn = 0
    logs = []

    while not all(drone.state == DELIVERED for drone in drones):
        turn += 1
        moves_this_turn = []

        # 1. Resolver primero los drones que ya estaban IN_TRANSIT
        #    (su movimiento ya estaba comprometido en el turno anterior)
        for drone in drones_in_transit:
            drone.transit_turns_remaining -= 1
            if drone.transit_turns_remaining == 0:
                complete_transit(drone)   # ahora AT_ZONE en el destino
                moves_this_turn.append((drone, destination_zone))
            # si remaining > 0, no genera línea de output este turno
            # (regla: el drone no está "llegando" a nada nuevo todavía)

        # 2. Decidir movimientos para drones AT_ZONE, en algún orden de prioridad
        reserved_zone_capacity = snapshot_of(network capacities, minus drones leaving)
        reserved_link_capacity = snapshot_of(connection capacities)

        for drone in drones_at_zone_ordered_by_priority:
            next_zone = drone.path[drone.path_index + 1]
            connection = network.connection_between(drone.current_zone, next_zone)

            if not capacity_available(next_zone, reserved_zone_capacity):
                continue  # el drone espera este turno (stay in place)
            if not capacity_available(connection, reserved_link_capacity):
                continue

            commit_move(drone, connection, next_zone, reserved_*)
            if next_zone.zone_type == RESTRICTED:
                drone.state = IN_TRANSIT
                drone.transit_turns_remaining = 2
                moves_this_turn.append((drone, connection))  # reporta la conexión, no la zona
            else:
                drone.current_zone = next_zone
                drone.path_index += 1
                moves_this_turn.append((drone, next_zone))
                if next_zone.is_end:
                    drone.state = DELIVERED

        logs.append(format_turn(moves_this_turn))

    return logs
```

**Puntos de diseño que hay que decidir explícitamente (no los dejes implícitos):**

1. **Orden de prioridad entre drones en el mismo turno.** Si dos drones
   compiten por la misma plaza en una zona con `max_drones=1`, ¿quién gana?
   Opciones razonables: por ID de drone (determinista y simple), o por
   "menor coste restante hasta el final" (más eficiente pero más complejo).
   Empieza por orden de ID — es determinista, fácil de depurar, y puedes
   optimizar después si no llegas a los benchmarks.

2. **Liberar capacidad en el mismo turno.** El subject dice explícitamente
   que un drone que sale de una zona libera espacio *ese mismo turno* para
   que otro pueda entrar. Esto implica que necesitas calcular primero
   "quién se va" antes de decidir "quién puede entrar" — de ahí el
   `reserved_zone_capacity` como snapshot que vas actualizando dentro del
   mismo turno, no el estado real de `Network` hasta que el turno termine.

3. **Evitar deadlocks.** Un deadlock típico: dos drones en zonas adyacentes,
   cada uno queriendo entrar en la zona del otro, ninguno puede moverse
   porque la zona de destino "parece ocupada" aunque en realidad se
   liberaría si ambos se movieran a la vez. La resolución típica es
   permitir el **swap simultáneo**: si A quiere ir a la zona de B y B
   quiere ir a la zona de A en el mismo turno, y ambos movimientos son
   válidos si se ejecutan juntos, permítelo como caso especial. Decide
   explícitamente si tu proyecto lo soporta o si prefieres detectarlo y
   forzar espera de uno de los dos (más simple, pero puede generar
   deadlocks reales en topologías con cuellos de botella estrechos).

4. **Recalcular rutas si un camino está saturado.** Si el pathfinder
   (Capítulo 4) le dio a todos los drones el mismo camino óptimo, es
   probable que se atasquen entre sí. Aquí es donde decides si el
   scheduler recalcula con Dijkstra "penalizando" conexiones ya muy
   ocupadas (súmales un coste extra proporcional a su ocupación actual) o
   si reparte manualmente los drones entre las k mejores rutas calculadas
   de antemano. Esta es la decisión que más va a impactar tu resultado en
   los benchmarks de mapas "hard".

### Checkpoint
- Simula el mapa de ejemplo del PDF con 5 drones y cuenta manualmente cuántos
  turnos debería tardar el mejor caso — compara con tu output.
- Fuerza un caso de dos drones compitiendo por una zona `max_drones=1`:
  confirma que uno espera (aparece omitido en la línea de turno) y no hay
  crash ni violación de capacidad.
- Prueba una zona `restricted`: confirma que el drone aparece como
  `D<id>-<connection>` en el turno de entrada y como `D<id>-<zone>` recién
  en el turno siguiente, nunca antes.
- Fuerza deliberadamente una topología con posible deadlock (dos únicas
  rutas que se cruzan en un cuello de botella de capacidad 1) y confirma
  que la simulación termina, no se cuelga en bucle infinito.

---

## Capítulo 6 — Formateo de salida

### Objetivo
Convertir los `moves_this_turn` que ya genera el scheduler en las líneas de
texto exactas que pide el subject.

### Diseño

```
function format_turn(moves: list[(Drone, Zone|Connection)]) -> str:
    tokens = []
    for drone, destination in moves:
        tokens.append(f"D{drone.id}-{destination.name}")
    return " ".join(tokens)
```

Nota: si en un turno **ningún** drone se mueve (todos esperan o todos ya
entregados), ¿esa línea se omite del todo o se imprime vacía? El subject no
lo dice explícitamente — decide un criterio y documéntalo en el README. Mi
sugerencia: omite turnos completamente vacíos del log final (no aportan
información y no afectan al conteo de turnos, que se calcula por el turno en
que el último drone llega, no por número de líneas impresas).

### Checkpoint
- Con el log de moves del Capítulo 5, genera el output y compara línea a
  línea con el ejemplo del subject (Capítulo VII.5 del PDF) usando un mapa
  equivalente.
- Confirma que un drone que llega a `end` en el turno N no vuelve a aparecer
  en ninguna línea posterior.

---

## Capítulo 7 — Visualización

### Objetivo
Dar feedback visual del estado de la simulación (terminal coloreado y/o
gráfico), sin acoplarlo a la lógica de simulación.

### Diseño

Mantén esto como una capa que **solo lee** el estado (`Network`, posiciones
de drones en cada turno), nunca lo modifica. Así puedes desarrollarlo en
paralelo o al final sin riesgo de romper la simulación.

```
function render_terminal_frame(network, drones, turn_number):
    for zone in network.zones:
        print colored(zone.name, color=zone.color or default_by_type(zone.zone_type))
    for drone in drones:
        print position of drone over its current zone / connection
```

Si el color de zona no está definido en el fichero (`color` es opcional),
ten un color por defecto por `zone_type` para que el feedback visual nunca
dependa de que el mapa lo especifique.

### Checkpoint
- Renderiza un turno intermedio de la simulación del Capítulo 5 y verifica a
  ojo que las posiciones de los drones coinciden con el log de texto de ese
  mismo turno.

---

## Capítulo 8 — Métricas y scoring

### Objetivo
Calcular y (opcionalmente) mostrar las métricas secundarias que menciona el
subject, para que tú mismo puedas comparar tu resultado contra los
benchmarks de la Sección VII.7 del PDF.

### Diseño

```
function compute_metrics(logs, drones) -> Metrics:
    total_turns = len(logs)
    drones_per_turn = [count of moving drones in each turn]
    avg_turns_per_drone = sum(turns until delivery per drone) / nb_drones
    total_path_cost = sum(weighted movement cost across all drones)
```

No es obligatorio automatizarlo (el subject lo marca como opcional), pero
mostrarlo al final de la simulación (`make run`) te da feedback inmediato de
si estás cerca o lejos de los targets del Capítulo VII.7.

### Checkpoint
- Corre las tres categorías de mapas (easy/medium/hard) de la Sección VII.7
  y anota tus turnos totales contra los targets publicados.

---

## Capítulo 9 — Testing global y edge cases

Antes de dar el proyecto por cerrado, revisa explícitamente:

- Mapa con drones = 0 (¿el subject lo prohíbe? confírmalo con "positive_integer").
- Mapa sin ningún camino posible entre `start` y `end` (todo bloqueado).
- Mapa con una única zona además de start/end.
- `max_link_capacity` mayor que el número de drones (no debería limitar nada).
- Ficheros mal formados: metadata con sintaxis inválida, coordenadas no
  enteras, tags desconocidos dentro de `[...]`.
- Excepciones no controladas: confirma que **nada** revienta con traceback
  crudo — todo pasa por `ParseError` o un manejo explícito.

---

## Capítulo 10 — README y checklist de entrega

Cuando el resto esté cerrado, arma el `README.md` con las secciones que pide
el subject (Capítulo VIII del PDF): primera línea itálica con los logins,
Descripción, Instrucciones, Resources (incluyendo cómo usaste IA), elección
de algoritmo/estrategia, documentación de la visualización, y un ejemplo de
input/output real de tu propio mapa.

Checklist final antes de subir:
- [ ] Todos los ficheros en la raíz del repo.
- [ ] `make lint` y `make lint-strict` sin errores.
- [ ] Los tres targets easy/medium/hard cumplen los benchmarks del subject.
- [ ] README completo en inglés.
- [ ] Puedes explicar cualquier función del proyecto sin mirar el código —
      este es literalmente un criterio de evaluación (Capítulo II del PDF).