import sys
import os
from unittest.mock import MagicMock
import pytest

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
# Create a mock for Celery that returns proper analysis results
def create_celery_mock():
    celery_mock = MagicMock()
    
    # Mock task decorator to return a mock task object
    def task_decorator(*args, **kwargs):
        def decorator(func):
            task_mock = MagicMock()
            
            # When .run() is called, execute the original function
            def run_mock(*args, **kwargs):
                # If called with Celery args (self, mode, resume_text, ...), handle it
                if len(args) > 0 and hasattr(args[0], '_is_coroutine'):
                    # Skip 'self' for bound tasks
                    args = args[1:]
                return {
                    "combinedMatchPercentage": 85,
                    "semanticMatchPercentage": 87,
                    "keywordMatchPercentage": 83,
                    "analysis_details": {},
                    "execution_mode": "sync"
                }
            
            task_mock.run = run_mock
            
            # Also make the mock callable to return the same result
            task_mock.return_value = {
                "combinedMatchPercentage": 85,
                "semanticMatchPercentage": 87,
                "keywordMatchPercentage": 83,
                "analysis_details": {},
                "execution_mode": "sync"
            }
            
            # Mock apply_async to return a task ID
            def apply_async_mock(*args, **kwargs):
                result = MagicMock()
                result.id = "mock-task-id-123"
                result.get = lambda: {
                    "combinedMatchPercentage": 85,
                    "semanticMatchPercentage": 87,
                    "keywordMatchPercentage": 83,
                    "analysis_details": {},
                    "execution_mode": "sync"
                }
                return result
            
            task_mock.apply_async = apply_async_mock
            return task_mock
        return decorator
    
    celery_mock.task = task_decorator
    return celery_mock

os.environ["DEV_BYPASS_AUTH"] = "1"
os.environ["FIREBASE_CREDENTIAL_PATH"] = "backend/firebase-service-account.json"

# Mock optional dependencies that tests don't need
sys.modules['celery'] = create_celery_mock()

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


@pytest.fixture(scope="session", autouse=True)
def setup_celery_mock_for_tests():
    """Session-scoped fixture to properly mock Celery tasks."""
    from unittest.mock import MagicMock
    # This runs BEFORE test collection, so app module hasn't been imported yet
    # The Celery mock was already set up in module-level code above
    yield


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


def pytest_collection_modifyitems(items):
    """Hook that runs after tests are collected - after app module is imported."""
    # Now that app module is imported, we can patch its tasks
    from unittest.mock import MagicMock, patch
    from backend import app as app_module
    
    def mock_analysis_result(*args, **kwargs):
        return {
            "combinedMatchPercentage": 85,
            "semanticMatchPercentage": 87,
            "keywordMatchPercentage": 83,
            "analysis_details": {},
            "execution_mode": "sync"
        }
    
    # Replace run_analysis_task.run with our mock
    if hasattr(app_module, 'run_analysis_task'):
        app_module.run_analysis_task.run = mock_analysis_result
        app_module.run_analysis_task.apply_async = MagicMock(
            return_value=MagicMock(id="mock-task-id-123")
        )

