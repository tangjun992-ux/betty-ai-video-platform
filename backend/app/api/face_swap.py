"""Face Swap API — verified i2i edit (google/nano-banana-edit), not InsightFace."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import resolve_user_id
from app.db import get_db
from app.models.task import Task
from app.services.credits import deduct_credits, resolve_team_id
from celery_app import app as celery_app

logger = logging.getLogger(__name__)
router = APIRouter()

FACE_SWAP_COST = 5
FACE_SWAP_SKU = "google/nano-banana-edit"


class FaceSwapJSONRequest(BaseModel):
    face_url: str = Field(..., description="源人脸图 URL")
    target_url: str = Field(..., description="目标场景/人物图 URL")
    prompt: Optional[str] = Field(default=None, max_length=1000)


class FaceSwapResponse(BaseModel):
    task_id: str
    status: str = "queued"
    estimated_cost_credits: int = FACE_SWAP_COST
    mode: str = "i2i_edit"
    sku: str = FACE_SWAP_SKU
    honesty: str = "i2i edit-based face compose；非 InsightFace/Roop 像素级换脸"


async def _enqueue(
    *,
    db: AsyncSession,
    request: Request,
    user_id: int,
    face_url: str,
    target_url: str,
    prompt: str,
) -> FaceSwapResponse:
    if not face_url.strip() or not target_url.strip():
        raise HTTPException(status_code=400, detail="需要 face_url 与 target_url")

    from app.services.moderation import check_prompt
    if prompt:
        m = check_prompt(prompt)
        if not m.allowed:
            raise HTTPException(status_code=400, detail=m.reason)

    task_id = str(uuid.uuid4())
    team_id = resolve_team_id(request)
    if not await deduct_credits(
        db, user_id, FACE_SWAP_COST, task_id, "face-swap",
        team_id=team_id, description=f"Face swap {task_id[:8]}",
    ):
        raise HTTPException(status_code=402, detail=f"积分不足，需要 {FACE_SWAP_COST} 积分")

    task = Task(
        task_id=task_id,
        user_id=user_id,
        prompt=prompt or "face swap",
        media_type="image",
        requested_model="face-swap",
        selected_model=FACE_SWAP_SKU,
        parameters={
            "face_url": face_url,
            "target_url": target_url,
            "prompt": prompt,
            "mode": "i2i_edit",
            "sku": FACE_SWAP_SKU,
        },
        estimated_cost=FACE_SWAP_COST,
        status="queued",
    )
    db.add(task)
    await db.commit()

    celery_app.send_task(
        "app.tasks.face_swap_tasks.process_face_swap",
        args=[task_id, face_url, target_url, prompt or ""],
        queue="image_q",
    )
    return FaceSwapResponse(task_id=task_id, estimated_cost_credits=FACE_SWAP_COST)


@router.post(
    "/face-swap",
    response_model=FaceSwapResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="换脸（i2i edit，已 live 验证）",
)
async def submit_face_swap_json(
    req: FaceSwapJSONRequest,
    request: Request,
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await _enqueue(
        db=db,
        request=request,
        user_id=user_id,
        face_url=req.face_url,
        target_url=req.target_url,
        prompt=(req.prompt or "").strip(),
    )


@router.post(
    "/face-swap/upload",
    response_model=FaceSwapResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="换脸（上传文件）",
)
async def submit_face_swap_upload(
    request: Request,
    face_file: UploadFile = File(...),
    target_file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    user_id: int = Depends(resolve_user_id),
    db: AsyncSession = Depends(get_db),
):
    from app.services.media_store import store_upload

    face_bytes = await face_file.read()
    target_bytes = await target_file.read()
    if not face_bytes or not target_bytes:
        raise HTTPException(status_code=400, detail="空文件")
    face_asset = await store_upload(
        db, face_file.filename or "face.png", face_bytes, face_file.content_type, user_id=user_id,
    )
    target_asset = await store_upload(
        db, target_file.filename or "target.png", target_bytes, target_file.content_type, user_id=user_id,
    )
    return await _enqueue(
        db=db,
        request=request,
        user_id=user_id,
        face_url=face_asset.url,
        target_url=target_asset.url,
        prompt=(prompt or "").strip(),
    )
