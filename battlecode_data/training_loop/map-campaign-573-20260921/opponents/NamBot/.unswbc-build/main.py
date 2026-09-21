import helper as unswbc
from helper import Direction, EdgeType, Position, Team


ct: unswbc.Controller
game: unswbc.Game

DEBUG = False

# Each dragon is a separate process, so this memory belongs to one dragon only.
# A portal edge is recorded from both sides as (x, y, direction). Once the same
# directed side has been seen at both portal endpoints, its exit can be inferred.
portal_sides: dict[int, set[tuple[int, int, str]]] = {}
known_tiles: set[tuple[int, int]] = set()
known_edges: dict[tuple[int, int, str], EdgeType] = {}
known_portal_ids: dict[tuple[int, int, str], int] = {}
visit_counts: dict[tuple[int, int], int] = {}
recent_positions: list[tuple[int, int]] = []
tile_memory: dict[tuple[int, int], tuple[bool, int, int]] = {}
symmetry_candidates = {"x", "y", "xy"}
active_target: tuple[int, int] | None = None
active_target_kind: str | None = None
turn_area_cache: dict[tuple[int, int], tuple[int, int]] = {}
sonar_pearls: dict[tuple[int, int], int] = {}

MAX_REMEMBERED_SEARCH = 96
SONAR_MAGIC = 45
SONAR_PEARL = 1


def key(pos: Position) -> tuple[int, int]:
    return pos.x, pos.y


def dragon_role() -> int:
    """Stable role: scout, harvester, anchor, or breeder."""
    value = ct.get_id() * 0x45D9F3B
    if ct.get_team() == Team.B:
        value ^= 0x9E3779B9
    value ^= value >> 16
    return value & 3


def role_target_bonus(kind: str) -> int:
    # A lone dragon should retain the proven v1.4 policy. Roles become useful
    # only after the team actually has multiple agents to diversify.
    if ct.get_unit_count() < 2:
        return 0
    role = dragon_role()
    if kind in ("pearl", "sonar_pearl"):
        return (0, 55, 15, 25)[role]
    if kind == "frontier":
        return (45, -10, -25, -5)[role]
    return 0


def sonar_checksum(value: int) -> int:
    return ((value >> 2) ^ (value >> 13) ^ (value >> 24)) & 3


def encode_sonar(position: tuple[int, int]) -> int:
    team_bit = 1 if ct.get_team() == Team.B else 0
    value = (
        (SONAR_MAGIC << 26)
        | (team_bit << 25)
        | (SONAR_PEARL << 23)
        | ((position[0] & 63) << 17)
        | ((position[1] & 63) << 11)
        | ((game.get_round_num() & 511) << 2)
    )
    return value | sonar_checksum(value)


def receive_sonar() -> None:
    round_num = game.get_round_num()
    team_bit = 1 if ct.get_team() == Team.B else 0
    for message in ct.get_sonar_messages():
        value = int(message)
        if (value & 3) != sonar_checksum(value & ~3):
            continue
        if (value >> 26) != SONAR_MAGIC or ((value >> 25) & 1) != team_bit:
            continue
        if ((value >> 23) & 3) != SONAR_PEARL:
            continue
        age = (round_num - ((value >> 2) & 511)) & 511
        position = ((value >> 17) & 63, (value >> 11) & 63)
        width, height = game.get_map_size()
        if age <= 8 and position[0] < width and position[1] < height:
            sonar_pearls[position] = round_num

    for position, seen_round in list(sonar_pearls.items()):
        if round_num - seen_round > 8:
            del sonar_pearls[position]


def maybe_send_sonar(tiles: list[unswbc.Tile]) -> None:
    if ct.get_unit_count() < 2 or (game.get_round_num() + ct.get_id() * 3) % 8:
        return
    pearls = [key(tile.position) for tile in tiles if tile.has_pearl()]
    if not pearls:
        return
    here = key(ct.get_position())
    target = min(
        pearls,
        key=lambda position: (
            visit_counts.get(position, 0),
            wrapped_distance(here, position),
        ),
    )
    ct.send_sonar(encode_sonar(target))


def mirrored_key(position: tuple[int, int], symmetry: str) -> tuple[int, int]:
    x, y = position
    width, height = game.get_map_size()
    if "x" in symmetry:
        x = width - 1 - x
    if "y" in symmetry:
        y = height - 1 - y
    return x, y


def mirrored_direction(direction: Direction, symmetry: str) -> Direction:
    if "x" in symmetry:
        if direction == Direction.EAST:
            direction = Direction.WEST
        elif direction == Direction.WEST:
            direction = Direction.EAST
    if "y" in symmetry:
        if direction == Direction.NORTH:
            direction = Direction.SOUTH
        elif direction == Direction.SOUTH:
            direction = Direction.NORTH
    return direction


def update_symmetry_candidates(tiles: list[unswbc.Tile]) -> None:
    for symmetry in list(symmetry_candidates):
        contradicted = False
        for tile in tiles:
            mirrored_position = mirrored_key(key(tile.position), symmetry)
            for direction in Direction.get_direction_list():
                mirrored_dir = mirrored_direction(direction, symmetry)
                other = known_edges.get((*mirrored_position, mirrored_dir.value))
                if other is not None and other != tile.get_edge(direction).get_edge_type():
                    contradicted = True
                    break
            if contradicted:
                break
        if contradicted:
            symmetry_candidates.discard(symmetry)


def apply_inferred_symmetry(tiles: list[unswbc.Tile]) -> None:
    # Delay prediction until the dragon has collected enough real observations.
    # Early symmetry guesses changed routes too aggressively on sparse maps.
    if len(symmetry_candidates) != 1 or game.get_round_num() < 50:
        return
    symmetry = next(iter(symmetry_candidates))
    round_num = game.get_round_num()
    for tile in tiles:
        mirrored_position = mirrored_key(key(tile.position), symmetry)
        known_tiles.add(mirrored_position)
        tile_memory[mirrored_position] = (
            tile.has_pearl(), tile.get_pearl_time(), round_num
        )
        for direction in Direction.get_direction_list():
            mirrored_dir = mirrored_direction(direction, symmetry)
            known_edges[(*mirrored_position, mirrored_dir.value)] = (
                tile.get_edge(direction).get_edge_type()
            )


def remember_world(tiles: list[unswbc.Tile]) -> None:
    round_num = game.get_round_num()
    for tile in tiles:
        tile_key = key(tile.position)
        known_tiles.add(tile_key)
        tile_memory[tile_key] = (tile.has_pearl(), tile.get_pearl_time(), round_num)
        for direction in Direction.get_direction_list():
            edge = tile.get_edge(direction)
            edge_key = (tile.position.x, tile.position.y, direction.value)
            known_edges[edge_key] = edge.get_edge_type()
            if edge.get_edge_type() != EdgeType.PORTAL:
                continue
            known_portal_ids[edge_key] = edge.get_portal_id()
            sides = portal_sides.setdefault(edge.get_portal_id(), set())
            sides.add((tile.position.x, tile.position.y, direction.value))
    if round_num % 4 == 1:
        update_symmetry_candidates(tiles)
        apply_inferred_symmetry(tiles)


def portal_destination(here: Position, direction: Direction, portal_id: int) -> Position | None:
    """Return a known portal exit, or None until the other endpoint is known."""
    candidates = [
        side for side in portal_sides.get(portal_id, ())
        if side[2] == direction.value and (side[0], side[1]) != key(here)
    ]
    if len(candidates) != 1:
        return None
    x, y, _ = candidates[0]
    return Position(x, y).add_dir(direction)


def remembered_neighbours(
    pos: Position,
    blocked: set[tuple[int, int]],
) -> tuple[list[Position], int]:
    """Return traversable remembered neighbours and unexplored exits."""
    neighbours: list[Position] = []
    frontier_exits = 0

    for direction in Direction.get_direction_list():
        edge_key = (pos.x, pos.y, direction.value)
        edge_type = known_edges.get(edge_key)
        if edge_type is None:
            frontier_exits += 1
            continue
        if edge_type == EdgeType.KELP:
            continue
        if edge_type == EdgeType.PORTAL:
            portal_id = known_portal_ids.get(edge_key)
            if portal_id is None:
                frontier_exits += 1
                continue
            destination = portal_destination(pos, direction, portal_id)
            if destination is None:
                frontier_exits += 1
                continue
        else:
            destination = pos.add_dir(direction)

        destination_key = key(destination)
        if destination_key in blocked:
            continue
        if destination_key not in known_tiles:
            frontier_exits += 1
            continue
        neighbours.append(destination)

    return neighbours, frontier_exits


def remembered_area(
    start: Position,
    blocked: set[tuple[int, int]],
) -> tuple[int, int]:
    """Bounded flood fill over all terrain remembered by this dragon."""
    start_key = key(start)
    cached = turn_area_cache.get(start_key)
    if cached is not None:
        return cached
    if start_key in blocked or start_key not in known_tiles:
        return 0, 0

    queue = [start]
    seen = {start_key}
    frontier_exits = 0
    index = 0

    while index < len(queue) and len(seen) < MAX_REMEMBERED_SEARCH:
        pos = queue[index]
        index += 1
        neighbours, frontier = remembered_neighbours(pos, blocked)
        frontier_exits += frontier
        for neighbour in neighbours:
            neighbour_key = key(neighbour)
            if neighbour_key in seen:
                continue
            seen.add(neighbour_key)
            queue.append(neighbour)

    # Reaching the search cap means the area is large enough not to be treated
    # as a local dead end, even if no unexplored edge was encountered yet.
    if len(seen) >= MAX_REMEMBERED_SEARCH:
        frontier_exits += 1
    result = (len(seen), frontier_exits)
    for position in seen:
        turn_area_cache[position] = result
    return result


def remembered_mobility_score(
    destination: Position,
    occupied: set[tuple[int, int]],
) -> int:
    """Penalise revisits and remembered corridors with no viable exit."""
    destination_key = key(destination)
    blocked = set(occupied)
    blocked.discard(destination_key)
    area, frontier_exits = remembered_area(destination, blocked)

    # Geometry memory is primarily a safety layer. Moderate weights let it
    # break loops and prefer exits without overpowering visible pearls.
    score = min(area, 60) + min(frontier_exits, 8) * 10
    score -= min(visit_counts.get(destination_key, 0), 8) * 12

    # A short recency penalty breaks oscillations without forbidding necessary
    # backtracking in narrow corridors.
    for age, position in enumerate(reversed(recent_positions[-12:]), start=1):
        if position == destination_key:
            score -= max(0, 65 - age * 5)
            break

    required_room = min(max(ct.get_length() + 2, 8), 30)
    if frontier_exits == 0 and area < required_room:
        score -= 650
    if frontier_exits == 0 and area < ct.get_length():
        score -= 450
    if area <= 4:
        score -= 220
    return score


def wrapped_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    width, height = game.get_map_size()
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return min(dx, width - dx) + min(dy, height - dy)


def is_frontier(position: tuple[int, int]) -> bool:
    pos = Position(*position)
    for direction in Direction.get_direction_list():
        edge_type = known_edges.get((*position, direction.value))
        if edge_type == EdgeType.EMPTY and key(pos.add_dir(direction)) not in known_tiles:
            return True
    return False


def target_candidate_score(
    position: tuple[int, int],
    kind: str,
    here: tuple[int, int],
) -> int | None:
    distance = wrapped_distance(here, position)
    visits = visit_counts.get(position, 0)
    memory = tile_memory.get(position)

    if kind == "pearl":
        if memory is None:
            return None
        has_pearl, _, seen_round = memory
        age = game.get_round_num() - seen_round
        if not has_pearl or age > 6:
            return None
        return 1100 - distance * 24 - age * 45 - visits * 8 + role_target_bonus(kind)

    if kind == "sonar_pearl":
        seen_round = sonar_pearls.get(position)
        if seen_round is None:
            return None
        age = game.get_round_num() - seen_round
        if age > 8:
            return None
        return 830 - distance * 22 - age * 50 - visits * 8 + role_target_bonus(kind)

    if kind == "spawn":
        if memory is None:
            return None
        has_pearl, pearl_time, seen_round = memory
        age = game.get_round_num() - seen_round
        remaining = pearl_time - age
        if has_pearl or pearl_time < 0 or remaining <= 0 or remaining > 12:
            return None
        arrival_error = abs(distance - remaining)
        return 360 - arrival_error * 18 - remaining * 3 - visits * 5

    if kind == "frontier":
        if not is_frontier(position):
            return None
        return 230 - distance * 9 - visits * 12 + role_target_bonus(kind)

    return None


def choose_long_term_target(here: Position) -> tuple[tuple[int, int] | None, str | None]:
    """Choose a stable remembered pearl, spawn timing, or exploration target."""
    global active_target, active_target_kind
    here_key = key(here)

    if active_target is not None and active_target_kind is not None:
        active_score = target_candidate_score(active_target, active_target_kind, here_key)
        if active_score is not None and game.get_round_num() % 4 != 1:
            return active_target, active_target_kind
        if active_score is None:
            active_target = None
            active_target_kind = None

    # The local planner is sufficient during the opening and between global
    # refreshes. This keeps Python comfortably below the judge budget.
    if game.get_round_num() % 4 != 1:
        return active_target, active_target_kind

    best_target: tuple[int, int] | None = None
    best_kind: str | None = None
    best_score = -10**9
    round_num = game.get_round_num()

    # Scan remembered resource information once. Avoiding three helper calls
    # per tile saves a substantial number of Python sandbox instructions.
    for position, memory in tile_memory.items():
        has_pearl, pearl_time, seen_round = memory
        age = round_num - seen_round
        distance = wrapped_distance(here_key, position)
        visits = visit_counts.get(position, 0)

        if has_pearl and age <= 4:
            score = (
                1100 - distance * 24 - age * 45 - visits * 8
                + role_target_bonus("pearl")
            )
            kind = "pearl"
        else:
            continue

        if score > best_score:
            best_score = score
            best_target = position
            best_kind = kind

    # A teammate's recent sighting is weaker than direct memory, but stronger
    # than wandering towards an arbitrary frontier.
    if best_score < 800:
        for position, seen_round in sonar_pearls.items():
            age = round_num - seen_round
            score = (
                830
                - wrapped_distance(here_key, position) * 22
                - age * 50
                - visit_counts.get(position, 0) * 8
                + role_target_bonus("sonar_pearl")
            )
            if age <= 8 and score > best_score:
                best_score = score
                best_target = position
                best_kind = "sonar_pearl"

    # Frontier selection is a fallback when no strong resource target exists.
    if best_score < 200:
        for position in known_tiles:
            if not is_frontier(position):
                continue
            score = (
                230
                - wrapped_distance(here_key, position) * 9
                - visit_counts.get(position, 0) * 12
                + role_target_bonus("frontier")
            )
            if score > best_score:
                best_score = score
                best_target = position
                best_kind = "frontier"

    if active_target is not None and active_target_kind is not None:
        active_score = target_candidate_score(active_target, active_target_kind, here_key)
        if active_score is not None and active_score >= best_score - 80:
            return active_target, active_target_kind

    active_target = best_target
    active_target_kind = best_kind
    return active_target, active_target_kind


def visible_neighbours(
    pos: Position,
    visible: dict[tuple[int, int], unswbc.Tile],
    occupied: set[tuple[int, int]],
) -> list[Position]:
    """Safe, non-portal neighbours used by the local flood fill."""
    tile = visible.get(key(pos))
    if tile is None:
        return []

    result: list[Position] = []
    for direction in Direction.get_direction_list():
        if tile.get_edge(direction).get_edge_type() != EdgeType.EMPTY:
            continue
        neighbour = pos.add_dir(direction)
        neighbour_key = key(neighbour)
        if neighbour_key in visible and neighbour_key not in occupied:
            result.append(neighbour)
    return result


def local_metrics(
    start: Position,
    visible: dict[tuple[int, int], unswbc.Tile],
    occupied: set[tuple[int, int]],
) -> tuple[int, int | None, int]:
    """Return reachable space, nearest pearl distance, and spawn opportunity."""
    start_key = key(start)
    if start_key not in visible or start_key in occupied:
        return 0, None, 0

    queue: list[tuple[Position, int]] = [(start, 0)]
    seen = {start_key}
    nearest_pearl: int | None = None
    spawn_opportunity = 0
    index = 0

    while index < len(queue):
        pos, distance = queue[index]
        index += 1
        tile = visible[key(pos)]

        if tile.has_pearl() and nearest_pearl is None:
            nearest_pearl = distance

        if not tile.has_pearl() and 0 <= tile.get_pearl_time() <= 3:
            # Prefer being near a soon-to-spawn pearl, but not standing on it
            # when its countdown is 1 because our body would block the spawn.
            value = (4 - tile.get_pearl_time()) * 14 - distance * 5
            if distance == 0 and tile.get_pearl_time() == 1:
                value -= 45
            spawn_opportunity = max(spawn_opportunity, value)

        for neighbour in visible_neighbours(pos, visible, occupied):
            neighbour_key = key(neighbour)
            if neighbour_key in seen:
                continue
            seen.add(neighbour_key)
            queue.append((neighbour, distance + 1))

    return len(seen), nearest_pearl, spawn_opportunity


def reconstruct_own_body(
    visible: dict[tuple[int, int], unswbc.Tile],
) -> tuple[list[Position], bool, set[tuple[int, int]]]:
    """Reconstruct the visible body prefix from head towards tail.

    Body directions point towards the head. If the tail leaves vision or crosses
    a portal, the reconstruction is incomplete and the unseen remainder is
    treated conservatively as stationary during lookahead.
    """
    my_id = ct.get_id()
    own_parts: dict[tuple[int, int], unswbc.DragonPart] = {}
    all_occupied: set[tuple[int, int]] = set()

    for position, tile in visible.items():
        part = tile.get_dragon()
        if part is not None:
            all_occupied.add(position)
            if part.get_id() == my_id:
                own_parts[position] = part

    predecessor: dict[tuple[int, int], Position] = {}
    for position, part in own_parts.items():
        if part.is_head():
            continue
        body_pos = Position(position[0], position[1])
        towards_head = body_pos.add_dir(part.get_dir())
        predecessor[key(towards_head)] = body_pos

    body = [ct.get_position()]
    seen = {key(body[0])}
    while key(body[-1]) in predecessor:
        next_part = predecessor[key(body[-1])]
        if key(next_part) in seen:
            break
        body.append(next_part)
        seen.add(key(next_part))

    complete = len(body) == ct.get_length()
    fixed_occupied = all_occupied - {key(pos) for pos in body}
    return body, complete, fixed_occupied


def should_split(
    here: Position,
    visible: dict[tuple[int, int], unswbc.Tile],
    occupied: set[tuple[int, int]],
) -> bool:
    """Create a small wingman only when the parent has ample room and length."""
    round_num = game.get_round_num()
    if dragon_role() != 3 or ct.get_length() < 14 or not ct.can_split(2):
        return False
    if round_num < 70 or round_num > 360 or (round_num + ct.get_id() * 7) % 43:
        return False
    for tile in visible.values():
        part = tile.get_dragon()
        if part is not None and part.is_head() and part.get_team() != ct.get_team():
            return False
    open_space, pearl_distance, _ = local_metrics(
        here, visible, occupied - {key(here)}
    )
    return open_space >= 26 and (pearl_distance is None or pearl_distance > 2)


def advance_body(
    body: list[Position],
    destination: Position,
    grows: bool,
    complete: bool,
) -> list[Position]:
    if grows or not complete:
        return [destination, *body]
    return [destination, *body[:-1]]


def simulated_options(
    body: list[Position],
    complete: bool,
    fixed_occupied: set[tuple[int, int]],
    visible: dict[tuple[int, int], unswbc.Tile],
    consumed_pearls: frozenset[tuple[int, int]],
) -> list[tuple[list[Position], frozenset[tuple[int, int]]]]:
    """Generate conservative, non-portal moves for short lookahead."""
    head = body[0]
    head_tile = visible.get(key(head))
    if head_tile is None:
        return []

    body_occupied = {key(pos) for pos in body}
    occupied = fixed_occupied | body_occupied
    options: list[tuple[list[Position], frozenset[tuple[int, int]]]] = []

    for direction in Direction.get_direction_list():
        # Portal paths require far-side state that may be stale, so they do not
        # count as reliable escape branches in the anti-trap search.
        if head_tile.get_edge(direction).get_edge_type() != EdgeType.EMPTY:
            continue

        destination = head.add_dir(direction)
        destination_key = key(destination)
        destination_tile = visible.get(destination_key)
        if destination_tile is None or destination_key in occupied:
            continue

        grows = destination_tile.has_pearl() and destination_key not in consumed_pearls
        next_consumed = consumed_pearls
        if grows:
            next_consumed = consumed_pearls | {destination_key}
        next_body = advance_body(body, destination, grows, complete)
        options.append((next_body, next_consumed))

    return options


def survival_tree(
    body: list[Position],
    complete: bool,
    fixed_occupied: set[tuple[int, int]],
    visible: dict[tuple[int, int], unswbc.Tile],
    consumed_pearls: frozenset[tuple[int, int]],
    depth: int,
) -> tuple[int, int]:
    """Return maximum safe depth and number of safe leaves at that depth."""
    if depth == 0:
        return 0, 1

    options = simulated_options(body, complete, fixed_occupied, visible, consumed_pearls)
    if not options:
        return 0, 0

    best_depth = 0
    leaf_count = 0
    for next_body, next_consumed in options:
        child_depth, child_leaves = survival_tree(
            next_body,
            complete,
            fixed_occupied,
            visible,
            next_consumed,
            depth - 1,
        )
        reached = 1 + child_depth
        if reached > best_depth:
            best_depth = reached
            leaf_count = max(1, child_leaves)
        elif reached == best_depth:
            leaf_count += max(1, child_leaves)

    return best_depth, leaf_count


def future_mobility_score(
    destination: Position,
    destination_tile: unswbc.Tile | None,
    destination_known: bool,
    own_body: list[Position],
    body_complete: bool,
    fixed_occupied: set[tuple[int, int]],
    visible: dict[tuple[int, int], unswbc.Tile],
) -> int:
    """Simulate the body after this move and look two more moves ahead."""
    if not destination_known or destination_tile is None:
        return -100

    destination_key = key(destination)
    grows = destination_tile.has_pearl()
    consumed = frozenset({destination_key}) if grows else frozenset()
    next_body = advance_body(own_body, destination, grows, body_complete)
    immediate_options = simulated_options(
        next_body, body_complete, fixed_occupied, visible, consumed
    )
    if not immediate_options:
        return -700

    safe_depth, safe_leaves = survival_tree(
        next_body,
        body_complete,
        fixed_occupied,
        visible,
        consumed,
        depth=2,
    )

    score = len(immediate_options) * 35 + safe_depth * 100 + min(safe_leaves, 10) * 12
    if len(immediate_options) == 1:
        score -= 140
    if safe_depth < 2:
        score -= 260
    return score


def head_collision_risk(
    destination: Position,
    visible: dict[tuple[int, int], unswbc.Tile],
) -> int:
    """Estimate whether another head can enter our destination on its turn."""
    risk = 0
    my_id = ct.get_id()
    my_team = ct.get_team()

    for tile in visible.values():
        part = tile.get_dragon()
        if part is None or not part.is_head() or part.get_id() == my_id:
            continue

        for direction in Direction.get_direction_list():
            if tile.get_edge(direction).get_edge_type() == EdgeType.KELP:
                continue
            if tile.position.add_dir(direction) != destination:
                continue

            # A greater id has not acted yet this round and can immediately
            # collide with us. Friendly heads are dangerous too.
            if part.get_id() > my_id:
                risk += 420
            else:
                risk += 120
            if part.get_team() == my_team:
                risk += 40
            break

    return risk


def evaluate_direction(
    direction: Direction,
    here: Position,
    here_tile: unswbc.Tile,
    visible: dict[tuple[int, int], unswbc.Tile],
    occupied: set[tuple[int, int]],
    own_body: list[Position],
    body_complete: bool,
    fixed_occupied: set[tuple[int, int]],
    long_target: tuple[int, int] | None,
) -> tuple[int, Position] | None:
    edge = here_tile.get_edge(direction)
    edge_type = edge.get_edge_type()
    if edge_type == EdgeType.KELP:
        return None

    portal_penalty = 0
    if edge_type == EdgeType.PORTAL:
        destination = portal_destination(here, direction, edge.get_portal_id())
        if destination is None:
            # Unknown exits are legal but deliberately unattractive. They stay
            # available as an escape when every ordinary move is blocked.
            destination = here.add_dir(direction)
            portal_penalty = 220
            destination_known = False
        else:
            destination_known = True
            if key(destination) not in visible:
                portal_penalty = 90
    else:
        destination = here.add_dir(direction)
        destination_known = True

    destination_tile = visible.get(key(destination)) if destination_known else None
    if destination_tile is not None and destination_tile.get_dragon() is not None:
        return None

    score = -portal_penalty

    if destination_tile is not None and destination_tile.has_pearl():
        score += 260

    space, pearl_distance, spawn_opportunity = local_metrics(destination, visible, occupied)
    score += min(space, 30) * 5
    score += spawn_opportunity

    if space <= 2 and destination_known:
        score -= 350
    elif space <= 5 and destination_known:
        score -= 100

    if pearl_distance is not None:
        score += max(0, 100 - pearl_distance * 18)

    if long_target is not None and destination_known:
        before = wrapped_distance(key(here), long_target)
        after = wrapped_distance(key(destination), long_target)
        score += (before - after) * 14
        if key(destination) == long_target:
            score += 40

    future_score = future_mobility_score(
        destination,
        destination_tile,
        destination_known,
        own_body,
        body_complete,
        fixed_occupied,
        visible,
    )
    score += future_score

    # Global remembered flood fill is considerably more expensive than the
    # 7x7 lookahead. Run it only for cramped, forced, or repeatedly visited
    # choices where long-corridor knowledge can actually change the decision.
    if destination_known and (
        space <= 14
        or future_score < 0
        or visit_counts.get(key(destination), 0) >= 2
    ):
        score += remembered_mobility_score(destination, occupied)
    score -= head_collision_risk(destination, visible)

    facing = ct.get_dir()
    if direction == facing:
        score += 14
    elif direction in (facing.get_left(), facing.get_right()):
        score += 5
    else:
        score -= 35

    return score, destination


def execute_turn() -> None:
    turn_area_cache.clear()
    tiles = ct.get_tiles()
    remember_world(tiles)
    receive_sonar()

    visible = {key(tile.position): tile for tile in tiles}
    occupied = {
        position for position, tile in visible.items()
        if tile.get_dragon() is not None
    }

    here = ct.get_position()
    here_key = key(here)
    visit_counts[here_key] = visit_counts.get(here_key, 0) + 1
    recent_positions.append(here_key)
    if len(recent_positions) > 20:
        del recent_positions[:-20]
    long_target, long_target_kind = choose_long_term_target(here)
    here_tile = visible[key(here)]
    own_body, body_complete, fixed_occupied = reconstruct_own_body(visible)

    if should_split(here, visible, occupied):
        ct.do_split(2)
        maybe_send_sonar(tiles)
        return

    candidates: list[tuple[int, int, Direction, Position]] = []
    direction_order = Direction.get_direction_list()

    # Rotate equal-score tie breaking by dragon and round so separate dragons
    # do not all follow the same deterministic pattern.
    tie_offset = (ct.get_id() + game.get_round_num()) % len(direction_order)

    for index, direction in enumerate(direction_order):
        evaluated = evaluate_direction(
            direction,
            here,
            here_tile,
            visible,
            occupied,
            own_body,
            body_complete,
            fixed_occupied,
            long_target,
        )
        if evaluated is None:
            continue
        score, destination = evaluated
        tie_rank = -((index - tie_offset) % len(direction_order))
        candidates.append((score, tie_rank, direction, destination))

    if candidates:
        score, _, direction, destination = max(candidates, key=lambda item: (item[0], item[1]))
        if DEBUG:
            ct.output_log("move", direction.value, "score", score)
            ct.draw_indicator_line(here, destination, 40, 220, 90)
            ct.set_indicator_string(
                f"{direction.value} {score} {long_target_kind or '-'}"
            )
        ct.make_move(direction)
        maybe_send_sonar(tiles)
        return

    # A valid action is still mandatory even when death is unavoidable.
    ct.make_move(Direction.NORTH)
    maybe_send_sonar(tiles)


def main() -> None:
    global ct, game
    ct, game = unswbc.init()
    while unswbc.update(ct, game):
        execute_turn()
        unswbc.end_turn()


if __name__ == "__main__":
    main()
