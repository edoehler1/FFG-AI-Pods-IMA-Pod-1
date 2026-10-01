from fastapi import APIRouter

from app.services.taxonomy import load_taxonomy

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


@router.get("")
def get_taxonomy():
    taxonomy = load_taxonomy()
    return {k: v for k, v in taxonomy.items() if not k.startswith("_")}
