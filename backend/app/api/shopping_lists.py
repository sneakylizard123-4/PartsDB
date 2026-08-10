from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.project import Project
from app.models.shopping import ShoppingList, ShoppingListItem
from app.models.user import User
from app.schemas import ShoppingListCreate, ShoppingListOut, ShoppingListItemCreate, ShoppingListItemOut
from app.services.shopping import generate_shopping_list

router = APIRouter(prefix="/api/shopping-lists", tags=["shopping"])


def _to_out(sl: ShoppingList) -> ShoppingListOut:
    out = ShoppingListOut.model_validate(sl)
    for item in out.items:
        pass
    items = []
    for it in sl.items:
        item_out = ShoppingListItemOut.model_validate(it)
        if it.part:
            item_out.part_value = it.part.value
            item_out.part_internal_id = it.part.internal_id
        items.append(item_out)
    out.items = items
    return out


@router.get("", response_model=list[ShoppingListOut])
def list_shopping_lists(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_to_out(sl) for sl in db.query(ShoppingList).order_by(ShoppingList.created_at.desc()).all()]


@router.post("", response_model=ShoppingListOut, status_code=201)
def create_shopping_list(
    body: ShoppingListCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sl = ShoppingList(name=body.name)
    db.add(sl)
    db.commit()
    db.refresh(sl)
    return _to_out(sl)


@router.post("/generate", response_model=ShoppingListOut, status_code=201)
def generate(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = None
    if project_id:
        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
    sl = generate_shopping_list(db, project)
    db.refresh(sl)
    return _to_out(sl)


@router.get("/{shopping_list_id}", response_model=ShoppingListOut)
def get_shopping_list(
    shopping_list_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sl = db.get(ShoppingList, shopping_list_id)
    if sl is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return _to_out(sl)


@router.post("/{shopping_list_id}/items", response_model=ShoppingListOut, status_code=201)
def add_item(
    shopping_list_id: str,
    body: ShoppingListItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sl = db.get(ShoppingList, shopping_list_id)
    if sl is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    db.add(ShoppingListItem(shopping_list_id=shopping_list_id, **body.model_dump()))
    db.commit()
    db.refresh(sl)
    return _to_out(sl)


@router.delete("/{shopping_list_id}/items/{item_id}", status_code=204)
def remove_item(
    shopping_list_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.get(ShoppingListItem, item_id)
    if item is None or item.shopping_list_id != shopping_list_id:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()


@router.delete("/{shopping_list_id}", status_code=204)
def delete_shopping_list(
    shopping_list_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sl = db.get(ShoppingList, shopping_list_id)
    if sl is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    db.delete(sl)
    db.commit()
