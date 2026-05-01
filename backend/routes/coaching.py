from flask import Blueprint, request, jsonify

coaching_bp = Blueprint('coaching', __name__)

# Plain handler functions (no decorators here). We'll register them from app.py
# to reuse app-level decorators (`auth_required`, `rate_limit`) without circular imports.

def coaching_save_version(user_info):
    # Local imports to avoid circular import at module load time
    from backend.app import (
        extract_text_from_pdf,
        extract_bullets,
        detect_skills,
        detect_skill_gaps,
        compute_basic_metrics,
        parse_resume_sections,
        add_version,
        write_audit,
        dispatch_event,
        build_study_pack,
    )

    # auth is applied by app.py when registering the route
    user_id = user_info.get('uid') if user_info else 'anonymous'

    resume_file = request.files.get("resume")
    if not resume_file:
        return jsonify({"error": "Resume file is required"}), 400

    resume_text = extract_text_from_pdf(resume_file) or ""
    resume_text = resume_text[:6000]

    job_desc_text = ""
    if "jobDescription" in request.form:
        job_desc_text = request.form.get("jobDescription", "")[:4000]
    elif request.files.get("job_description"):
        job_desc_text = extract_text_from_pdf(request.files["job_description"]) or ""
        job_desc_text = job_desc_text[:4000]

    bullets = extract_bullets(resume_text)
    skills = detect_skills(resume_text)
    gaps = detect_skill_gaps(skills, job_desc_text)
    metrics = compute_basic_metrics(resume_text, bullets, skills, gaps)
    sections = parse_resume_sections(resume_text)

    record = {
        "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z",
        "metrics": metrics,
        "skills": skills,
        "skillGaps": gaps,
        "studyPack": build_study_pack(gaps),
        "bullets": bullets[:30],
        "resumeExcerpt": resume_text[:1200],
        "sections": sections,
    }

    # add_version & write_audit are provided by app.py
    saved = add_version(user_id, record)
    write_audit(user_id, 'coaching.save_version', {'version': saved['version']})
    dispatch_event('version.saved', {'userId': user_id, 'version': saved['version']})
    return jsonify({"saved": saved})


def coaching_progress(user_info):
    from backend.app import list_versions, write_audit
    user_id = user_info.get('uid') if user_info else 'anonymous'
    versions = list_versions(user_id)
    write_audit(user_id, 'coaching.progress', {'count': len(versions)})
    return jsonify({"versions": versions})


def coaching_study_pack(user_info):
    from backend.app import list_versions, write_audit
    user_id = user_info.get('uid') if user_info else 'anonymous'
    versions = list_versions(user_id)
    if not versions:
        return jsonify({
            "skillGaps": [],
            "studyPack": []
        })
    latest = versions[-1]
    write_audit(user_id, 'coaching.study_pack', {'gaps': len(latest.get('skillGaps', []))})
    return jsonify({
        "skillGaps": latest.get("skillGaps", []),
        "studyPack": latest.get("studyPack", [])
    })


def coaching_interview_questions(user_info):
    from backend.app import list_versions, write_audit, _generate_interview_questions_for_role
    user_id = user_info.get('uid') if user_info else 'anonymous'
    target_role = request.args.get("targetRole", "Software Engineer")[:100]
    versions = list_versions(user_id)
    if not versions:
        return jsonify({
            "targetRole": target_role,
            "questions": ["Please save a resume version first to generate tailored questions."]
        })
    latest = versions[-1]
    questions = _generate_interview_questions_for_role(latest.get("resumeExcerpt", ""), target_role, latest.get("skills", [])[:10])
    write_audit(user_id, 'coaching.interview_questions', {'role': target_role, 'count': len(questions)})
    return jsonify({
        "targetRole": target_role,
        "questions": questions
    })


def coaching_diff(user_info):
    from backend.app import list_versions, write_audit
    user_id = user_info.get('uid') if user_info else 'anonymous'
    versions = list_versions(user_id)
    if len(versions) < 2:
        return jsonify({'error': 'Need at least 2 versions'}), 400
    try:
        prev_idx = int(request.args.get('prev', len(versions)-1)) - 1
        curr_idx = int(request.args.get('curr', len(versions))) - 1
    except ValueError:
        return jsonify({'error': 'Invalid indices'}), 400
    if not (0 <= prev_idx < len(versions) and 0 <= curr_idx < len(versions)):
        return jsonify({'error': 'Index out of range'}), 400
    if prev_idx == curr_idx:
        return jsonify({'error': 'prev and curr must differ'}), 400
    prev = versions[prev_idx]
    curr = versions[curr_idx]
    prev_sk = set(prev.get('skills', []))
    curr_sk = set(curr.get('skills', []))
    added = sorted(list(curr_sk - prev_sk))
    removed = sorted(list(prev_sk - curr_sk))
    metrics_prev = prev.get('metrics', {})
    metrics_curr = curr.get('metrics', {})
    metric_deltas = {}
    for k in set(metrics_prev.keys()).union(metrics_curr.keys()):
        v0 = metrics_prev.get(k)
        v1 = metrics_curr.get(k)
        if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
            metric_deltas[k] = round(v1 - v0, 2)
    result = {
        'prevVersion': prev.get('version'),
        'currVersion': curr.get('version'),
        'addedSkills': added,
        'removedSkills': removed,
        'metricDeltas': metric_deltas,
        'currMetrics': metrics_curr,
        'prevMetrics': metrics_prev
    }
    write_audit(user_id, 'coaching.diff', {'prev': prev.get('version'), 'curr': curr.get('version')})
    return jsonify(result)
