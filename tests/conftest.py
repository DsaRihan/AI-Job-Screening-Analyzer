import sys
import os
from unittest.mock import MagicMock

print("\n" + "=" * 70)
print("TESTS/CONFTEST.PY EXECUTING")
print("=" * 70)

# ===== ABSOLUTE CRITICAL: Setup sys.path BEFORE anything else =====
# This code runs at conftest.py import time (earliest possible)
# Use os.path.realpath() for absolute path resolution, not relying on cwd
conftest_file = os.path.realpath(__file__)
conftest_dir = os.path.dirname(conftest_file)  # /path/to/tests
project_root = os.path.dirname(conftest_dir)   # /path/to/project

print(f"conftest_file: {conftest_file}")
print(f"conftest_dir: {conftest_dir}")
print(f"project_root: {project_root}")

# Verify project root is correct
backend_path = os.path.join(project_root, 'backend')
if not os.path.exists(backend_path):
    raise RuntimeError(
        f"backend not found at {backend_path}. "
        f"conftest.py at: {conftest_file}, "
        f"calculated project_root: {project_root}"
    )

print(f"backend verified at: {backend_path}")

# Force project root to be first in sys.path
while project_root in sys.path:
    sys.path.remove(project_root)
sys.path.insert(0, project_root)
print(f"sys.path[0] set to: {sys.path[0]}")

# Change to project root immediately
os.chdir(project_root)
print(f"Changed to cwd: {os.getcwd()}")

# Set environment variables BEFORE anything imports the app
os.environ["DEV_BYPASS_AUTH"] = "1"
os.environ["FIREBASE_CREDENTIAL_PATH"] = "backend/firebase-service-account.json"

# Mock optional dependencies that tests don't need
sys.modules['celery'] = MagicMock()
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.auth'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['firebase_admin.firestore'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['rq'] = MagicMock()
sys.modules['rq.job'] = MagicMock()
sys.modules['cohere'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['spacy'] = MagicMock()
sys.modules['tensorflow'] = MagicMock()

# Fix sklearn mocking - need to create nested structure
sklearn_mock = MagicMock()
sklearn_mock.metrics = MagicMock()
sklearn_mock.metrics.pairwise = MagicMock()
sklearn_mock.metrics.pairwise.cosine_similarity = MagicMock(return_value=0.5)
sklearn_mock.feature_extraction = MagicMock()
sklearn_mock.feature_extraction.text = MagicMock()
sklearn_mock.feature_extraction.text.TfidfVectorizer = MagicMock()
sys.modules['sklearn'] = sklearn_mock
sys.modules['sklearn.metrics'] = sklearn_mock.metrics
sys.modules['sklearn.metrics.pairwise'] = sklearn_mock.metrics.pairwise
sys.modules['sklearn.feature_extraction'] = sklearn_mock.feature_extraction
sys.modules['sklearn.feature_extraction.text'] = sklearn_mock.feature_extraction.text
print("Environment variables and mock modules set")

print("=" * 70)
print("TESTS/CONFTEST.PY SETUP COMPLETE")
print("=" * 70 + "\n")


def pytest_configure(config):
    """
    Pytest configuration hook - runs before test collection.
    Ensures sys.path is configured before pytest tries to collect test modules.
    """
    global project_root
    print("\n" + "=" * 70)
    print("pytest_configure HOOK (TESTS)")
    print("=" * 70)
    
    # Re-apply setup as extra insurance
    while project_root in sys.path:
        sys.path.remove(project_root)
    sys.path.insert(0, project_root)
    
    print(f"  Project root: {project_root}")
    print(f"  sys.path[0]: {sys.path[0]}")
    print(f"  cwd: {os.getcwd()}")
    print(f"  backend exists: {os.path.exists(os.path.join(project_root, 'backend'))}")
    print("=" * 70 + "\n")

