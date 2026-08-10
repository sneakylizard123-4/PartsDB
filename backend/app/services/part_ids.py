from sqlalchemy.orm import Session

from app.models.part import Part

CATEGORY_PREFIXES = {
    "resistor": "RES",
    "capacitor": "CAP",
    "capacitor ceramic": "CAP",
    "capacitor electrolytic": "CAP",
    "inductor": "IND",
    "diode": "DIO",
    "led": "LED",
    "transistor": "TR",
    "optoelectronic": "OPT",
    "ic": "IC",
    "connector": "CONN",
    "header": "CONN",
    "terminal block": "CONN",
    "switch": "SW",
    "relay": "REL",
    "fuse": "FUSE",
    "crystal": "XTAL",
    "oscillator": "XTAL",
    "battery": "BAT",
    "module": "MOD",
    "sensor": "SEN",
    "mounting": "HW",
    "hardware": "HW",
    "screw": "HW",
    "standoff": "HW",
    "spacer": "HW",
    "wire": "WIRE",
    "cable": "CABLE",
    "pads": "PAD",
    "adapter": "ADP",
    "other": "PART",
}

DEFAULT_PREFIX = "PART"


def generate_internal_id(db: Session, category: str | None = None) -> str:
    """Generate a unique, human-readable internal ID, e.g. RES-000042.

    The prefix comes from the part category (falling back to PART); the
    numeric suffix is the next free sequence number for that prefix.
    """
    label = (category or "").strip().lower()
    prefix = DEFAULT_PREFIX
    for key, value in CATEGORY_PREFIXES.items():
        if key in label:
            prefix = value
            break

    existing = db.query(Part.internal_id).filter(
        Part.internal_id.like(f"{prefix}-%")
    ).all()

    max_n = 0
    for (iid,) in existing:
        if not iid:
            continue
        tail = iid[len(prefix) + 1 :]
        if tail.isdigit():
            max_n = max(max_n, int(tail))

    for n in range(max_n + 1, max_n + 1000):
        candidate = f"{prefix}-{n:06d}"
        if db.query(Part.id).filter(Part.internal_id == candidate).first() is None:
            return candidate
    raise RuntimeError("Could not allocate an internal ID for prefix {prefix}")
