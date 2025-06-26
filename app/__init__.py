import os
import uuid

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash

from .models import Base, File, User, Progress

DB_PATH = os.environ.get('COURSE_DB', 'course.db')
FILES_DIR = os.environ.get('COURSE_DIR', 'files')

tokens = {}

def create_app():
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    engine = create_engine(f"sqlite:///{DB_PATH}")
    Base.metadata.create_all(engine)

    def get_db():
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    def scan():
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

    scan()

    def ensure_user():
        db = Session(engine)
        if not db.query(User).filter_by(username="admin").first():
            db.add(User(username="admin", password_hash=generate_password_hash("admin")))
            db.commit()
        db.close()

    ensure_user()

    async def get_current_user(request: Request):
        token = request.headers.get("Authorization")
        if not token or token not in tokens:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return tokens[token]

    @app.post("/api/login")
    def login(data: dict, db: Session = Depends(get_db)):
        username = data.get("username")
        password = data.get("password")
        user = db.query(User).filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = str(uuid.uuid4())
        tokens[token] = user.id
        return {"token": token}

    def build_tree(db: Session, parent_id=None):
        nodes = db.query(File).filter_by(parent_id=parent_id).order_by(File.order).all()
        result = []
        for node in nodes:
            item = {"id": node.id, "name": node.name, "is_dir": node.is_dir, "path": node.path}
            if node.is_dir:
                item["children"] = build_tree(db, node.id)
            result.append(item)
        return result

    @app.get("/api/files")
    def get_files(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
        return build_tree(db)

    @app.get("/api/progress")
    def get_progress(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
        progress = db.query(Progress).filter_by(user_id=user_id).first()
        return {"file_id": progress.file_id if progress else None}

    @app.post("/api/progress")
    def set_progress(data: dict, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
        file_id = data.get("file_id")
        progress = db.query(Progress).filter_by(user_id=user_id).first()
        if progress:
            progress.file_id = file_id
        else:
            progress = Progress(user_id=user_id, file_id=file_id)
            db.add(progress)
        db.commit()
        return {"status": "ok"}



    @app.get("/api/next/{file_id}")
    def next_file(file_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
        current = db.query(File).filter_by(id=file_id).first()
        if not current:
            return {"file_id": None}
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
        return {"file_id": next_id}

    app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")
    app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

    return app
