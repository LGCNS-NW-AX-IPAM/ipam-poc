import os
import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.candidate_service import CandidateService

router = APIRouter()

def _default_batch_id() -> str:
    now = datetime.now()
    return f"BATCH-{now.year:04d}-{now.month:02d}-{now.day}"


@router.post("/candidate/upload")
async def upload_candidates_by_context(
    file: UploadFile = File(...),
    history: str = Form(default="[]"),
    usage_threshold: float = Form(default=float(os.getenv("CANDIDATE_USAGE_THRESHOLD", "30"))),
    extraction_batch_id: str = Form(default=""),
    default_owner_email: str = Form(default=os.getenv("CANDIDATE_DEFAULT_OWNER_EMAIL", "no-reply@ipam.local")),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx/.xlsm)만 업로드할 수 있습니다.")

    try:
        parsed_history = json.loads(history) if history else []
    except Exception:
        parsed_history = []

    content = await file.read()
    service = CandidateService()
    mode = service.infer_upload_mode_from_history(parsed_history)

    if mode == "finalize":
        batch_id = extraction_batch_id.strip() or _default_batch_id()
        try:
            result = service.finalize_candidates_from_excel(
                db=db,
                file_bytes=content,
                extraction_batch_id=batch_id,
                usage_threshold=usage_threshold,
                default_owner_email=default_owner_email,
            )
            message = service.build_finalize_response_message(result)
            return {**result, "content": message, "mode": "finalize"}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"후보 확정 중 오류가 발생했습니다: {str(e)}")

    batch_id = extraction_batch_id.strip() or _default_batch_id()
    try:
        result = service.extract_candidates_from_excel(
            db=db,
            file_bytes=content,
            extraction_batch_id=batch_id,
            usage_threshold=usage_threshold,
            default_owner_email=default_owner_email,
        )
        message = service.build_extract_response_message(result)
        review_excel_base64 = service.build_review_excel_base64(result.get("selected_ips") or [])
        return {**result, "content": message, "mode": "extract", "review_excel_base64": review_excel_base64}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"후보 추출 중 오류가 발생했습니다: {str(e)}")


@router.post("/candidate/extract")
async def extract_candidates_from_excel(
    file: UploadFile = File(...),
    usage_threshold: float = Form(default=float(os.getenv("CANDIDATE_USAGE_THRESHOLD", "30"))),
    extraction_batch_id: str = Form(default=""),
    default_owner_email: str = Form(default=os.getenv("CANDIDATE_DEFAULT_OWNER_EMAIL", "no-reply@ipam.local")),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx/.xlsm)만 업로드할 수 있습니다.")

    batch_id = extraction_batch_id.strip() or _default_batch_id()
    content = await file.read()

    try:
        service = CandidateService()
        result = service.extract_candidates_from_excel(
            db=db,
            file_bytes=content,
            extraction_batch_id=batch_id,
            usage_threshold=usage_threshold,
            default_owner_email=default_owner_email,
        )
        message = service.build_extract_response_message(result)
        review_excel_base64 = service.build_review_excel_base64(result.get("selected_ips") or [])
        return {**result, "content": message, "review_excel_base64": review_excel_base64}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"후보 추출 중 오류가 발생했습니다: {str(e)}")


@router.post("/candidate/finalize")
async def finalize_candidates_from_excel(
    file: UploadFile = File(...),
    usage_threshold: float = Form(default=float(os.getenv("CANDIDATE_USAGE_THRESHOLD", "30"))),
    extraction_batch_id: str = Form(default=""),
    default_owner_email: str = Form(default=os.getenv("CANDIDATE_DEFAULT_OWNER_EMAIL", "no-reply@ipam.local")),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        raise HTTPException(status_code=400, detail="엑셀 파일(.xlsx/.xlsm)만 업로드할 수 있습니다.")

    batch_id = extraction_batch_id.strip() or _default_batch_id()
    content = await file.read()

    try:
        service = CandidateService()
        result = service.finalize_candidates_from_excel(
            db=db,
            file_bytes=content,
            extraction_batch_id=batch_id,
            usage_threshold=usage_threshold,
            default_owner_email=default_owner_email,
        )
        message = service.build_finalize_response_message(result)
        return {**result, "content": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"후보 확정 중 오류가 발생했습니다: {str(e)}")

