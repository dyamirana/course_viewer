from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..models import File, Progress
from ..utils.core import get_db, build_tree

router = APIRouter()

DEFAULT_USER_ID = 1

@router.get('/files')
def get_files(db: Session = Depends(get_db)):
    return build_tree(db)

@router.get('/progress')
def get_progress(db: Session = Depends(get_db)):
    progress = db.query(Progress).filter_by(user_id=DEFAULT_USER_ID).first()
    return {'file_id': progress.file_id if progress else None}

@router.post('/progress')
def set_progress(data: dict, db: Session = Depends(get_db)):
    file_id = data.get('file_id')
    progress = db.query(Progress).filter_by(user_id=DEFAULT_USER_ID).first()
    if progress:
        progress.file_id = file_id
    else:
        progress = Progress(user_id=DEFAULT_USER_ID, file_id=file_id)
        db.add(progress)
    db.commit()
    return {'status': 'ok'}

@router.get('/next/{file_id}')
def next_file(file_id: int, db: Session = Depends(get_db)):
    current = db.query(File).filter_by(id=file_id).first()
    if not current:
        return {'file_id': None}
    siblings = (
        db.query(File)
        .filter_by(parent_id=current.parent_id, is_dir=False)
        .order_by(File.order)
        .all()
    )
    next_id = None
    for idx, s in enumerate(siblings):
        if s.id == current.id and idx + 1 < len(siblings):
            next_id = siblings[idx + 1].id
            break
    return {'file_id': next_id}
