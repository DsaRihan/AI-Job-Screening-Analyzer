from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger("resume_analyzer.auth")

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register_user():
    """Create a Firebase Auth user via server-side admin SDK.

    Expected JSON: { "email": str, "password": str, "displayName": str (optional) }
    """
    # FIREBASE_AVAILABLE is optional; import from app lazily to avoid circular imports
    try:
        from backend.app import FIREBASE_AVAILABLE
    except Exception:
        FIREBASE_AVAILABLE = False

    if not FIREBASE_AVAILABLE:
        return jsonify({'ok': False, 'error': 'firebase_unavailable', 'message': 'Server not configured with Firebase admin credentials.'}), 503

    payload = request.get_json(silent=True) or {}
    email = (payload.get('email') or '').strip()
    password = (payload.get('password') or '').strip()
    display_name = (payload.get('displayName') or '').strip()

    if not email or not password:
        return jsonify({'ok': False, 'error': 'invalid_input', 'message': 'Email and password are required.'}), 400

    try:
        # Import here to avoid hard import-time dependency if admin not configured
        import firebase_admin
        from firebase_admin import auth as firebase_auth

        user_record = firebase_auth.create_user(email=email, password=password, display_name=display_name or None)
        logger.info(f"Created new firebase user: {user_record.uid}")
        return jsonify({'ok': True, 'uid': user_record.uid, 'email': user_record.email}), 201
    except Exception as e:
        logger.exception("Failed to create firebase user")
        msg = str(e)
        return jsonify({'ok': False, 'error': 'create_failed', 'message': msg}), 400
