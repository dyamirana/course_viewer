import os
from typing import Generator, List

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from ..models import Base, File, User, Progress

DB_PATH = os.environ.get('COURSE_DB', 'course.db')
FILES_DIR = os.environ.get('COURSE_DIR', 'files')

engine = create_engine(f"sqlite:///{DB_PATH}")
Base.metadata.create_all(engine)

tokens: dict[str, int] = {}

def get_db() -> Generator[Session, None, None]:
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

def scan() -> None:
    db = Session(engine)
    if db.query(File).first():
        db.close()
        return
    for root, dirs, files in os.walk(FILES_DIR):
        rel_root = os.path.relpath(root, FILES_DIR)
        parent = db.query(File).filter(File.path == rel_root).first()
        if not parent:
            parent_name = os.path.basename(root) or rel_root
            parent = File(name=parent_name, path=rel_root, parent_id=None, is_dir=True)
            db.add(parent)
            db.commit()
        for order, d in enumerate(sorted(dirs)):
            dir_path = os.path.join(rel_root, d)
            db.add(File(name=d, path=dir_path, parent_id=parent.id, is_dir=True, order=order))
        for order, f in enumerate(sorted(files)):
            file_path = os.path.join(rel_root, f)
            db.add(File(name=f, path=file_path, parent_id=parent.id, is_dir=False, order=order))
        db.commit()
    db.close()

def ensure_user() -> None:
    db = Session(engine)
    if not db.query(User).filter_by(username="admin").first():
        db.add(User(username="admin", password_hash=generate_password_hash("admin")))
        db.commit()
    db.close()

def build_tree(db: Session, parent_id: int | None = None) -> List[dict]:
    nodes = db.query(File).filter_by(parent_id=parent_id).order_by(File.order).all()
    result = []
    for node in nodes:
        item = {"id": node.id, "name": node.name, "is_dir": node.is_dir, "path": node.path}
        if node.is_dir:
            item["children"] = build_tree(db, node.id)
        result.append(item)
    return result
