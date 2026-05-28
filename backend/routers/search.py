from fastapi import APIRouter, Request, Query

router = APIRouter()


@router.get("/search")
async def search(request: Request, q: str = Query(..., min_length=1)):
    prowlarr = request.app.state.prowlarr
    return await prowlarr.search(q)
