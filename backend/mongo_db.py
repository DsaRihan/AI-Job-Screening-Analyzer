# DATABASE LAYER: MongoDB integration for persisting user analysis history and coaching version data with graceful fallback
import certifi
import logging
import os
from pathlib import Path
from dotenv import load_dotenv


def _load_backend_env() -> None:
    """Load backend/.env early so Mongo can read configuration on import.

    mongo_db.py is imported before backend.config in app.py, so this module
    must load its own environment values.
    """
    backend_dir = Path(__file__).resolve().parent
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


_load_backend_env()

logger = logging.getLogger("resume_analyzer")

# Lazy connection — only connect when actually needed
_client = None
_db = None
analysis_collection = None
users_collection = None
audit_collection = None

MONGO_AVAILABLE = False


def get_db():
    """Lazily connect to MongoDB. Returns (db, True) or (None, False)."""
    global _client, _db, analysis_collection, users_collection, audit_collection, MONGO_AVAILABLE
    if _db is not None:
        return _db, MONGO_AVAILABLE

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        logger.warning("MONGO_URI not set — database features disabled")
        return None, False
    try:
        from pymongo import MongoClient
        # Enable TLS only when the URI indicates a secure/Atlas connection.
        # Local docker mongo instances typically do not use TLS, and passing
        # a tlsCAFile causes an SSL handshake attempt that fails.
        client_kwargs = {"serverSelectionTimeoutMS": 5000}
        uri_lower = mongo_uri.lower()
        if uri_lower.startswith("mongodb+srv://") or "tls=true" in uri_lower or "ssl=true" in uri_lower:
            client_kwargs["tlsCAFile"] = certifi.where()
        _client = MongoClient(mongo_uri, **client_kwargs)
        _client.admin.command("ping")  # verify connection
        _db = _client["resumeAnalyzer"]
        analysis_collection = _db["analysis_results"]
        users_collection = _db["users"]
        audit_collection = _db["audit_logs"]
        MONGO_AVAILABLE = True
        logger.info("mongo.connected database=resumeAnalyzer collections=analysis_results,audit_logs")
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e} — database features disabled")
        MONGO_AVAILABLE = False
    return _db, MONGO_AVAILABLE


def save_analysis(user_id, mode, result, resume_excerpt="", job_desc_excerpt=""):
    """Save an analysis result to MongoDB."""
    from datetime import datetime
    db, available = get_db()
    if not available or analysis_collection is None:
        return None
    try:
        doc = {
            "userId": user_id,
            "mode": mode,
            "result": result,
            "resumeExcerpt": resume_excerpt[:500],
            "jobDescExcerpt": job_desc_excerpt[:500],
            "createdAt": datetime.utcnow(),
        }
        inserted = analysis_collection.insert_one(doc)
        logger.info(f"mongo.save_analysis_ok id={inserted.inserted_id} user={user_id} mode={mode}")
        return str(inserted.inserted_id)
    except Exception as e:
        logger.error(f"mongo.save_analysis_error: {e}")
        return None


def save_audit_event(entry):
    """Persist an audit event to MongoDB."""
    from datetime import datetime
    db, available = get_db()
    if not available or audit_collection is None:
        return None
    try:
        doc = {
            "ts": entry.get("ts") or datetime.utcnow().isoformat() + "Z",
            "userId": entry.get("user"),
            "action": entry.get("action"),
            "meta": entry.get("meta") or {},
            "createdAt": datetime.utcnow(),
        }
        inserted = audit_collection.insert_one(doc)
        logger.info(f"mongo.save_audit_ok id={inserted.inserted_id} user={doc['userId']} action={doc['action']}")
        return str(inserted.inserted_id)
    except Exception as e:
        logger.error(f"mongo.save_audit_error: {e}")
        return None


def get_user_history(user_id, limit=20):
    """Retrieve past analyses for a user."""
    db, available = get_db()
    if not available or analysis_collection is None:
        return []
    try:
        cursor = (
            analysis_collection.find({"userId": user_id}, {"resumeExcerpt": 0})
            .sort("createdAt", -1)
            .limit(limit)
        )
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "createdAt" in doc:
                doc["createdAt"] = doc["createdAt"].isoformat() + "Z"
            results.append(doc)
        return results
    except Exception as e:
        logger.error(f"mongo.get_history_error: {e}")
        return []


def save_user_role(user_id, role):
    """Save or update user role in MongoDB."""
    from datetime import datetime
    db, available = get_db()
    if not available or users_collection is None:
        return False
    try:
        users_collection.update_one(
            {"userId": user_id},
            {"$set": {"role": role, "updatedAt": datetime.utcnow()}},
            upsert=True
        )
        logger.info(f"mongo.save_user_role_ok user={user_id} role={role}")
        return True
    except Exception as e:
        logger.error(f"mongo.save_user_role_error: {e}")
        return False


def get_user_role_mongo(user_id):
    """Retrieve user role from MongoDB."""
    db, available = get_db()
    if not available or users_collection is None:
        return None
    try:
        doc = users_collection.find_one({"userId": user_id})
        return doc.get("role") if doc else None
    except Exception as e:
        logger.error(f"mongo.get_user_role_error: {e}")
        return None
