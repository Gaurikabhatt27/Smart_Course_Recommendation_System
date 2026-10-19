"""
database.py
-----------
MongoDB connection manager and client lifecycle handling.
Uses PyMongo and python-dotenv to support both local MongoDB
and MongoDB Atlas configurations safely.
"""

import os
import re
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError

# Load environment variables from .env file
load_dotenv()

DEFAULT_URI = "mongodb://localhost:27017/"
DEFAULT_DB_NAME = "course_recommendation"

_client: Optional[MongoClient] = None


def get_connection_uri() -> str:
    """Retrieve MongoDB URI from environment variables or default."""
    return os.getenv("MONGODB_URI", DEFAULT_URI)


def get_db_name() -> str:
    """Retrieve target MongoDB database name."""
    return os.getenv("MONGODB_DB_NAME", DEFAULT_DB_NAME)


def mask_uri(uri: str) -> str:
    """
    Mask credentials in a MongoDB connection URI for safe UI/logging display.
    Example: mongodb+srv://admin:pass123@cluster0.net -> mongodb+srv://admin:****@cluster0.net
    """
    # Pattern to match username:password@
    pattern = r"://([^:]+):([^@]+)@"
    return re.sub(pattern, r"://\1:****@", uri)


def get_client(uri: Optional[str] = None, timeout_ms: int = 3000) -> MongoClient:
    """
    Get or initialize the shared MongoClient singleton.
    Configured with a reasonable timeout so the application never hangs.
    """
    global _client
    if _client is None:
        target_uri = uri or get_connection_uri()
        _client = MongoClient(
            target_uri,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms,
            appname="CourseRecommendationSystem"
        )
    return _client


def get_db(db_name: Optional[str] = None) -> Database:
    """Get the database instance."""
    client = get_client()
    target_db = db_name or get_db_name()
    return client[target_db]


def get_collection(collection_name: str) -> Collection:
    """Get a specific collection reference by name."""
    db = get_db()
    return db[collection_name]


def check_connection() -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verify MongoDB connection using the admin ping command.
    Returns:
        (is_connected, message, metadata)
    """
    try:
        client = get_client()
        # The ping command is cheap and does not require auth on admin DB in typical setups
        server_info = client.admin.command("ping")
        build_info = client.admin.command("buildinfo")
        version = build_info.get("version", "unknown")
        db = get_db()
        colls = db.list_collection_names()
        
        info = {
            "version": version,
            "masked_uri": mask_uri(get_connection_uri()),
            "database": get_db_name(),
            "collections": colls,
            "collection_count": len(colls),
        }
        return True, f"Connected to MongoDB v{version} successfully.", info
    except ServerSelectionTimeoutError:
        return False, f"Server selection timeout. Ensure MongoDB is running at {mask_uri(get_connection_uri())}.", {}
    except ConnectionFailure as e:
        return False, f"Failed to connect to MongoDB: {str(e)}", {}
    except PyMongoError as e:
        return False, f"MongoDB error: {str(e)}", {}
    except Exception as e:
        return False, f"Unexpected error during MongoDB check: {str(e)}", {}


def close_connection() -> None:
    """Gracefully close the MongoClient connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
