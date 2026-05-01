from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import time
import json

# Import helpers from app and resume modules. These imports rely on app.py
# having defined decorators and task objects before registering this blueprint.
from backend.app import (
    auth_required,
    rate_limit,
    ASYNC_TASKS_ENABLED,
    estimate_salary_task,
    tailor_resume_task,
    generate_career_path_task,
    run_analysis_task,
    write_audit,
    save_analysis,
    dispatch_event,
    get_user_role,
    logger,
    _metrics,
)
from backend.resume import extract_text_from_pdf

resume_bp = Blueprint('resume', __name__)


@resume_bp.route("/analyze", methods=["POST"])
@cross_origin()
@rate_limit(40, 60)
@auth_required
def analyze(user_info):
    _metrics['requests'] += 1
    start = time.time()

    # Support JSON request
    if request.is_json:
        data = request.json
        mode = data.get("mode")
        if mode not in ["jobSeeker", "recruiter"]:
            return jsonify({"error": "Invalid mode; must be 'jobSeeker' or 'recruiter'"}), 400
        resume_text = data.get("resume", "")
        if not resume_text or len(resume_text.strip()) < 40:
            return jsonify({"error": "Resume text is required and must be at least 40 characters"}), 400
        resume_text = resume_text[:3000]
        job_desc_text = ""
        recruiter_email = ""
        if mode == "jobSeeker":
            job_desc_text = data.get("job_description", "").strip()[:2000]
        elif mode == "recruiter":
            recruiter_email = data.get("recruiterEmail", "").strip()
            job_desc_text = data.get("job_description", "").strip()[:2000]
            if not job_desc_text or not recruiter_email:
                return jsonify({"error": "Job description and recruiterEmail are required"}), 400
    else:
        mode = request.form.get("mode")
        if mode not in ["jobSeeker", "recruiter"]:
            return jsonify({"error": "Invalid mode; must be 'jobSeeker' or 'recruiter'"}), 400
        resume_file = request.files.get("resume")
        if not resume_file:
            return jsonify({"error": "Resume file is required"}), 400
        resume_text = extract_text_from_pdf(resume_file)
        if not resume_text:
            return jsonify({"error": "Could not extract text from resume PDF"}), 400
        resume_text = resume_text[:3000]
        job_desc_text = ""
        recruiter_email = ""
        if mode == "jobSeeker":
            job_desc_text = request.form.get("jobDescription", "").strip()[:2000]
        elif mode == "recruiter":
            job_desc_file = request.files.get("job_description")
            recruiter_email = request.form.get("recruiterEmail", "").strip()
            if job_desc_file:
                job_desc_text = extract_text_from_pdf(job_desc_file) or ""
                job_desc_text = job_desc_text[:2000]
            if not job_desc_text or not recruiter_email:
                return jsonify({"error": "Job description file and recruiterEmail are required"}), 400
        write_audit(user_info.get('uid'), 'resume.upload', {
            'mode': mode,
            'filename': resume_file.filename,
            'hasJobDescriptionFile': bool(request.files.get("job_description"))
        })

    if mode == "recruiter":
        role = get_user_role(user_info.get("uid"))
        if role not in ["recruiter", "admin"]:
            return jsonify({"error": "Forbidden: recruiter role required"}), 403

    if ASYNC_TASKS_ENABLED:
        try:
            task = run_analysis_task.apply_async(
                args=[mode, resume_text, job_desc_text, recruiter_email, user_info],
                timeout=600,
            )
            return jsonify({"status": "queued", "job_id": task.id, "mode": mode}), 202
        except Exception as e:
            logger.warning(f"Async queue unavailable ({e}), executing synchronously")

    result = run_analysis_task.run(mode, resume_text, job_desc_text, recruiter_email, user_info)

    save_analysis(
        user_id=user_info.get("uid", "anonymous"),
        mode=mode,
        result=result,
        resume_excerpt=resume_text[:500],
        job_desc_excerpt=job_desc_text[:500],
    )

    elapsed = round((time.time() - start) * 1000)
    _metrics['analyze']['count'] += 1
    _metrics['analyze']['avgMs'] = round((
        _metrics['analyze']['avgMs'] * (_metrics['analyze']['count'] - 1) + elapsed
    ) / _metrics['analyze']['count'], 1)
    write_audit(user_info.get('uid'), 'analyze', {'mode': mode, 'ms': elapsed})
    dispatch_event('analysis.completed', {
        'mode': mode,
        'userId': user_info.get('uid'),
        'matchPercentage': result.get('combinedMatchPercentage') or result.get('semanticMatchPercentage'),
        'notifyEmail': request.form.get('recruiterEmail') if not request.is_json else (request.json or {}).get('recruiterEmail')
    })

    if isinstance(result, dict):
        result.setdefault("execution_mode", "sync")
    return jsonify(result)


@resume_bp.route('/estimate-salary', methods=['POST'])
@cross_origin()
@auth_required
@rate_limit(max_requests=10, per_seconds=60)
def estimate_salary(user_info):
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    resume_file = request.files['resume']
    job_description = request.form.get('jobDescription', '')
    write_audit(user_info.get('uid'), 'resume.upload', {
        'endpoint': 'estimate_salary',
        'filename': resume_file.filename,
        'hasJobDescription': bool(job_description)
    })
    resume_text = extract_text_from_pdf(resume_file)
    if ASYNC_TASKS_ENABLED:
        try:
            task = estimate_salary_task.apply_async(
                args=[resume_text, job_description, user_info.get("uid", "anonymous")],
                timeout=300
            )
            return jsonify({
                "status": "queued",
                "job_id": task.id,
                "mode": "salary_estimation"
            }), 202
        except Exception as e:
            logger.warning(f"Celery task queue failed: {e}, falling back to sync")
    result = estimate_salary_task.run(resume_text, job_description, user_info.get("uid", "anonymous"))
    write_audit(user_info.get('uid'), 'analysis.run', {'mode': 'salary_estimation'})
    return jsonify(result)


@resume_bp.route('/tailor-resume', methods=['POST'])
@cross_origin()
@auth_required
@rate_limit(max_requests=10, per_seconds=60)
def tailor_resume(user_info):
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    resume_file = request.files['resume']
    job_description = request.form.get('jobDescription', '')
    write_audit(user_info.get('uid'), 'resume.upload', {
        'endpoint': 'tailor_resume',
        'filename': resume_file.filename,
        'hasJobDescription': bool(job_description)
    })
    resume_text = extract_text_from_pdf(resume_file)
    if not resume_text:
        return jsonify({'error': 'Failed to extract resume text'}), 400
    if ASYNC_TASKS_ENABLED:
        try:
            task = tailor_resume_task.apply_async(
                args=[resume_text, job_description, user_info.get("uid", "anonymous")],
                timeout=300
            )
            return jsonify({"status": "queued", "job_id": task.id, "mode": "tailor_resume"}), 202
        except Exception as e:
            logger.warning(f"Celery task queue failed: {e}, falling back to sync")
    result = tailor_resume_task.run(resume_text, job_description, user_info.get("uid", "anonymous"))
    write_audit(user_info.get('uid'), 'analysis.run', {'mode': 'tailor_resume'})
    return jsonify(result)


@resume_bp.route('/generate-career-path', methods=['POST'])
@cross_origin()
@auth_required
@rate_limit(max_requests=10, per_seconds=60)
def generate_career_path(user_info):
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    resume_file = request.files['resume']
    resume_text = extract_text_from_pdf(resume_file)
    write_audit(user_info.get('uid'), 'resume.upload', {
        'endpoint': 'generate_career_path',
        'filename': resume_file.filename,
    })
    if not resume_text:
        return jsonify({'error': 'Failed to extract resume text'}), 400
    if ASYNC_TASKS_ENABLED:
        try:
            task = generate_career_path_task.apply_async(
                args=[resume_text, user_info.get("uid", "anonymous")],
                timeout=300
            )
            return jsonify({"status": "queued", "job_id": task.id, "mode": "career_path"}), 202
        except Exception as e:
            logger.warning(f"Celery task queue failed: {e}, falling back to sync")
    result = generate_career_path_task.run(resume_text, user_info.get("uid", "anonymous"))
    write_audit(user_info.get('uid'), 'analysis.run', {'mode': 'career_path'})
    return jsonify(result)
