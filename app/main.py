from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.config import settings
from app.database import Base, engine, get_db
from app.models import Organisation, User, Department, WorkItem, Risk, WatchEvent, EvidenceRecord, Approval, AuditLog
from app.schemas import RegisterIn, LoginIn, DepartmentIn, WorkIn, RiskIn, WatchIn, EvidenceIn, ApprovalIn, DecisionIn
from app.security import hash_password, verify_password, make_token, current_user, require_roles

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ORBIT API", version="0.1.0", description="Organisational Risk & Business Intelligence Technology")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def log(db, user, action, kind, oid=None):
    db.add(AuditLog(organisation_id=user.organisation_id, actor_id=user.id, action=action, object_type=kind, object_id=oid))

def org_query(db, model, user):
    return db.query(model).filter(model.organisation_id == user.organisation_id)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ORBIT API", "version": "0.1.0"}

@app.post("/api/auth/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    org = Organisation(name=data.organisation_name.strip())
    db.add(org); db.flush()
    user = User(organisation_id=org.id, email=email, full_name=data.full_name.strip(), password_hash=hash_password(data.password), role="owner")
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": make_token(user), "token_type": "bearer", "user": {"id": user.id, "name": user.full_name, "email": user.email, "role": user.role}, "organisation": {"id": org.id, "name": org.name}}

@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower(), User.active == True).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return {"access_token": make_token(user), "token_type": "bearer", "user": {"id": user.id, "name": user.full_name, "email": user.email, "role": user.role}, "organisation_id": user.organisation_id}

@app.get("/api/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.query(Organisation).filter(Organisation.id == user.organisation_id).first()
    return {"id": user.id, "name": user.full_name, "email": user.email, "role": user.role, "organisation": org.name if org else None}

@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        "open_tasks": org_query(db, WorkItem, user).filter(WorkItem.status != "completed").count(),
        "overdue_tasks": org_query(db, WorkItem, user).filter(WorkItem.status != "completed", WorkItem.due_date < datetime.now().date().isoformat()).count(),
        "open_risks": org_query(db, Risk, user).filter(Risk.status != "closed").count(),
        "critical_risks": org_query(db, Risk, user).filter((Risk.likelihood * Risk.impact) >= 16, Risk.status != "closed").count(),
        "new_events": org_query(db, WatchEvent, user).filter(WatchEvent.status == "new").count(),
        "pending_approvals": org_query(db, Approval, user).filter(Approval.status == "pending").count()
    }

@app.get("/api/departments")
def list_departments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": x.id, "name": x.name} for x in org_query(db, Department, user).order_by(Department.name).all()]

@app.post("/api/departments")
def create_department(data: DepartmentIn, user: User = Depends(require_roles("owner","admin")), db: Session = Depends(get_db)):
    item = Department(organisation_id=user.organisation_id, name=data.name.strip())
    db.add(item); db.flush(); log(db,user,"created","department",item.id); db.commit()
    return {"id": item.id, "name": item.name}

@app.get("/api/tasks")
def list_tasks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = org_query(db, WorkItem, user).order_by(WorkItem.created_at.desc()).limit(300).all()
    return [{"id":x.id,"title":x.title,"description":x.description,"status":x.status,"priority":x.priority,"due_date":x.due_date,"department_id":x.department_id} for x in rows]

@app.post("/api/tasks")
def create_task(data: WorkIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.department_id and not org_query(db, Department, user).filter(Department.id == data.department_id).first():
        raise HTTPException(400, "Department not found in your organisation")
    item = WorkItem(organisation_id=user.organisation_id, created_by=user.id, **data.model_dump())
    db.add(item); db.flush(); log(db,user,"created","task",item.id); db.commit()
    return {"id":item.id,"title":item.title,"status":item.status}

@app.patch("/api/tasks/{item_id}")
def update_task(item_id: int, data: WorkIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = org_query(db, WorkItem, user).filter(WorkItem.id == item_id).first()
    if not item: raise HTTPException(404, "Task not found")
    if data.department_id and not org_query(db, Department, user).filter(Department.id == data.department_id).first():
        raise HTTPException(400, "Department not found in your organisation")
    for k,v in data.model_dump().items(): setattr(item,k,v)
    log(db,user,"updated","task",item.id); db.commit()
    return {"id":item.id,"status":item.status}

@app.get("/api/risks")
def list_risks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = org_query(db, Risk, user).order_by(Risk.created_at.desc()).limit(300).all()
    return [{"id":x.id,"title":x.title,"description":x.description,"category":x.category,"likelihood":x.likelihood,"impact":x.impact,"score":x.likelihood*x.impact,"status":x.status,"mitigation":x.mitigation} for x in rows]

@app.post("/api/risks")
def create_risk(data: RiskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = Risk(organisation_id=user.organisation_id, created_by=user.id, **data.model_dump())
    db.add(item); db.flush(); log(db,user,"created","risk",item.id); db.commit()
    return {"id":item.id,"score":item.likelihood*item.impact}

@app.get("/api/watch")
def list_watch(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = org_query(db, WatchEvent, user).order_by(WatchEvent.created_at.desc()).limit(300).all()
    return [{"id":x.id,"title":x.title,"source":x.source,"severity":x.severity,"status":x.status,"details":x.details} for x in rows]

@app.post("/api/watch")
def create_watch(data: WatchIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = WatchEvent(organisation_id=user.organisation_id, created_by=user.id, **data.model_dump())
    db.add(item); db.flush(); log(db,user,"created","watch_event",item.id); db.commit()
    return {"id":item.id,"status":item.status}

@app.patch("/api/watch/{item_id}/acknowledge")
def acknowledge_watch(item_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = org_query(db, WatchEvent, user).filter(WatchEvent.id == item_id).first()
    if not item: raise HTTPException(404, "Event not found")
    item.status = "acknowledged"; log(db,user,"acknowledged","watch_event",item.id); db.commit()
    return {"id":item.id,"status":item.status}

@app.get("/api/evidence")
def list_evidence(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = org_query(db, EvidenceRecord, user).order_by(EvidenceRecord.created_at.desc()).limit(300).all()
    return [{"id":x.id,"title":x.title,"evidence_type":x.evidence_type,"reference":x.reference,"review_date":x.review_date,"notes":x.notes} for x in rows]

@app.post("/api/evidence")
def create_evidence(data: EvidenceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = EvidenceRecord(organisation_id=user.organisation_id, created_by=user.id, **data.model_dump())
    db.add(item); db.flush(); log(db,user,"created","evidence",item.id); db.commit()
    return {"id":item.id,"title":item.title}

@app.get("/api/approvals")
def list_approvals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = org_query(db, Approval, user).order_by(Approval.created_at.desc()).limit(300).all()
    return [{"id":x.id,"title":x.title,"request_details":x.request_details,"status":x.status,"decision_note":x.decision_note} for x in rows]

@app.post("/api/approvals")
def create_approval(data: ApprovalIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = Approval(organisation_id=user.organisation_id, requested_by=user.id, **data.model_dump())
    db.add(item); db.flush(); log(db,user,"submitted","approval",item.id); db.commit()
    return {"id":item.id,"status":item.status}

@app.post("/api/approvals/{item_id}/decision")
def decide_approval(item_id: int, data: DecisionIn, user: User = Depends(require_roles("owner","admin","manager")), db: Session = Depends(get_db)):
    item = org_query(db, Approval, user).filter(Approval.id == item_id).first()
    if not item: raise HTTPException(404, "Approval not found")
    if item.status != "pending": raise HTTPException(409, "This request has already been decided")
    item.status = data.decision; item.decision_note = data.decision_note; item.decided_by = user.id; item.decided_at = datetime.now(timezone.utc)
    log(db,user,data.decision,"approval",item.id); db.commit()
    return {"id":item.id,"status":item.status}

@app.get("/api/audit")
def audit(user: User = Depends(require_roles("owner","admin","auditor")), db: Session = Depends(get_db)):
    rows = org_query(db, AuditLog, user).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [{"id":x.id,"actor_id":x.actor_id,"action":x.action,"object_type":x.object_type,"object_id":x.object_id,"created_at":x.created_at.isoformat()} for x in rows]

@app.get("/")
def home():
    return FileResponse("app/static/index.html")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
