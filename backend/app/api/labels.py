import base64
import html
import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.organizer import Organizer, OrganizerCompartment
from app.models.user import User

router = APIRouter(prefix="/api/labels", tags=["labels"])


def _qr_png_bytes(content: str) -> bytes:
    img = qrcode.make(content)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _qr_data_uri(content: str) -> str:
    return "data:image/png;base64," + base64.b64encode(_qr_png_bytes(content)).decode()


def _compartment_payload(c: OrganizerCompartment) -> str:
    return f"partsdb:organizer:{c.organizer_id}:compartment:{c.id}"


@router.get("/compartment/{compartment_id}/qr.png")
def compartment_qr(
    compartment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.get(OrganizerCompartment, compartment_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Compartment not found")
    return Response(
        content=_qr_png_bytes(_compartment_payload(c)),
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="compartment-{c.id}.png"'
        },
    )


@router.get("/organizer/{organizer_id}/qr.png")
def organizer_qr(
    organizer_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    o = db.get(Organizer, organizer_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Organizer not found")
    return Response(
        content=_qr_png_bytes(f"partsdb:organizer:{o.id}"),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="organizer-{o.id}.png"'},
    )


@router.get("/organizer/{organizer_id}/print-sheet")
def organizer_print_sheet(
    organizer_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    o = db.get(Organizer, organizer_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Organizer not found")

    cards = []
    for c in o.compartments:
        part = c.part
        location_path = c.location.full_path() if c.location else ""
        info_lines = []
        if part:
            if part.value:
                info_lines.append(f"<b>{html.escape(str(part.value))}</b>")
            meta = " · ".join(
                x
                for x in (
                    part.package or "",
                    part.mpn or "",
                    part.manufacturer or "",
                )
                if x
            )
            if meta:
                info_lines.append(f'<span class="meta">{html.escape(meta)}</span>')
        if location_path:
            info_lines.append(f'<span class="loc">{html.escape(location_path)}</span>')
        title = html.escape(c.label or f"R{c.row}C{c.col}")
        qr = _qr_data_uri(_compartment_payload(c))
        cards.append(
            f"""
            <div class="label">
              <img class="qr" src="{qr}" alt="">
              <div class="body">
                <div class="t">{title}</div>
                {" ".join(info_lines) if info_lines else '<span class="meta">empty</span>'}
              </div>
            </div>
            """
        )

    title = html.escape(o.name or "Organizer")
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Labels · {title}</title>
<style>
  @page {{ margin: 8mm; size: A4; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, Helvetica, sans-serif; margin: 0; }}
  h1 {{ font-size: 14px; margin: 4mm 2mm 6mm; }}
  .sheet {{ display: grid; grid-template-columns: repeat(3, 63.5mm);
             gap: 2mm; justify-content: start; }}
  .label {{ width: 63.5mm; height: 25.4mm; border: 1px solid #333;
            display: flex; align-items: center; gap: 2mm; padding: 1.5mm;
            break-inside: avoid; }}
  .qr {{ width: 20mm; height: 20mm; flex: none; }}
  .body {{ flex: 1; min-width: 0; overflow: hidden; font-size: 9px; line-height: 1.3; }}
  .t {{ font-size: 11px; font-weight: bold; margin-bottom: 1mm; }}
  .meta {{ display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .loc {{ display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #555; }}
</style>
</head>
<body>
  <h1>Labels · {title}</h1>
  <div class="sheet">{"".join(cards)}</div>
</body>
</html>"""
    return Response(
        content=html_body,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="labels-{title}.html"'},
    )