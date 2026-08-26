from src.domain.zone import Zone, ZoneType

class ParseError(Exception):
    """Raised when the map file does not follow the expected syntax.
        Attributes:
            line_number: The line in the source file where the error occurred.
            message: A short description of what went wrong.
    """
    def __init__(self, line_number: int, message: str) -> None:
        self.line_number = line_number
        self.message = message
        super().__init__(f"Line {self.line_number}: {self.message}")


def strip_comment_and_whitespace(raw_line: str) -> str:
    """Remove trailing comments and surrounding whitespace from a line.
    Args:
        raw_line: A raw line as read from the map file.

    Returns:
        The line with any '#' comment removed and whitespace stripped.
        Returns an empty string if the line is blank or fully commented.
    """
    line_without_comment = raw_line.split("#", 1)[0]
    return line_without_comment.strip()


def parse_nb_drones(line: str, line_number: int) -> int:
    """Parse the 'nb_drones: <positive_integer>' line.
    Args:
        line: The already-cleaned line (no comments, no surrounding whitespace).
        line_number: The 1-indexed line number, used for error reporting.
    Returns:
        The number of drones declared in the map file.

    Raises:
        ParseError: If the line is malformed or the value is not a positive
            integer.
    """

    value_str = line.split(":", 1)[1].strip()
    try:
        value = int(value_str)
    except ValueError:
        raise ParseError(line_number, f"Invalid nb_drones value: "
                         f"'{value_str}'")
    if value <= 0:
        raise ParseError(line_number, f"nb_drones must be positive, "
                         f"got {value}")
    return value


def parse_metadata_block(raw: str, line_number: int) -> dict[str, str]:
    """Parse a metadata block into a dictionary of tag values.
    Args:
        raw: The content between brackets, e.g. "zone=restricted color=red".
            An empty string means no metadata was present.
        line_number: The 1-indexed line number, used for error reporting.

    Returns:
        A dictionary mapping each tag name to its raw string value. Empty
        if raw is blank.

    Raises:
        ParseError: If any token is not in the form "key=value".
    """

    metadata: dict[str, str] = {}
    if raw.strip() == "":
        return metadata

    for token in raw.split():
        if "=" not in token:
            raise ParseError(line_number, f"Invalid metadata tag:"
                             f"'{token}'")
        key, value = token.split("=", 1)
        if key == "" or value == "":
            raise ParseError(line_number, f"Invalid metadata tag:"
                             f"'{token}'")
        metadata[key] = value

    return metadata



def parse_zone_line(line: str, line_number: int) -> Zone:
    """Parse a 'start_hub:', 'end_hub:', or 'hub:' line into a Zone.
    Args:
        line: The already-cleaned line (no comments, no surrounding whitespace).
        line_number: The 1-indexed line number, used for error reporting.

    Returns:
        The Zone described by this line, with metadata defaults applied.

    Raises:
        ParseError: If the line is malformed, has an invalid zone type,
            non-integer coordinates, or an invalid capacity value.
    """

    prefix, rest_of_line = line.split(":", 1)
    prefix = prefix.strip()
    rest_of_line = rest_of_line.strip()

    if prefix not in ["start_hub", "end_hub", "hub"]:
        raise ParseError(line_number, f"Invalid zone line prefix: '{prefix}'")

    if prefix == "start_hub":
        is_start = True
        is_end = False
    elif prefix == "end_hub":
        is_start = False
        is_end = True
    else:  # prefix == "hub"
        is_start = False
        is_end = False

    bracket_index = rest_of_line.find("[")
    if bracket_index == -1:
        fixed_part = rest_of_line
        metadata_raw = ""
    else:
        fixed_part = rest_of_line[:bracket_index]
        closing_index = rest_of_line.find("]", bracket_index)
        if closing_index == -1:
            raise ParseError(line_number, "missing closing ']' "
                             "in metadata block")
        metadata_raw = rest_of_line[bracket_index + 1:closing_index]

    fixed_tokens = fixed_part.split()
    if len(fixed_tokens) != 3:
        raise ParseError(line_number, f"expected 'name x y', "
                         f"got: '{fixed_part}'")
    name, x_str, y_str = fixed_tokens

    metadata = parse_metadata_block(metadata_raw, line_number)

    try:
        x = int(x_str)
        y = int(y_str)
    except ValueError:
        raise ParseError(line_number, f"invalid coordinates: "
                         f"'{x_str}', '{y_str}'")

    zone_type_str = metadata.get("zone", "normal")
    try:
        zone_type = ZoneType(zone_type_str)
    except ValueError:
        raise ParseError(line_number, f"invalid zone type: '{zone_type_str}'")

    color = metadata.get("color", None)
    max_drones = metadata.get("max_drones", "1")
    try:
        max_drones_int = int(max_drones)
    except ValueError:
        raise ParseError(line_number, f"invalid max_drones value: "
                         f"'{max_drones}'")
    if max_drones_int <= 0:
        raise ParseError(line_number, f"max_drones must be positive, "
                         f"got {max_drones_int}")

    return Zone(name=name, x=x, y=y, zone_type=zone_type,
                max_drones=max_drones_int,
                is_start=is_start, is_end=is_end, color=color)


def parse_connection_line():