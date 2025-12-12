"""
Rotas para consulta de status de jobs RQ
"""

from flask import Blueprint, jsonify, current_app
from meu_app.decorators import login_obrigatorio

bp = Blueprint('jobs', __name__, url_prefix='/jobs')


@bp.route('/<job_id>/status', methods=['GET'])
@login_obrigatorio
def get_job_status(job_id):
    """
    Consulta o status de um job assíncrono
    
    GET /jobs/<job_id>/status
    
    Returns:
        {
            "job_id": "abc123",
            "status": "queued|started|finished|failed",
            "progress": 50,  # 0-100 (quando started)
            "result": {...},  # quando finished
            "error": "...",   # quando failed
            "created_at": "2025-10-08T12:00:00",
            "started_at": "2025-10-08T12:00:05",
            "ended_at": "2025-10-08T12:00:30"
        }
    
    ---
    tags:
      - Jobs
    parameters:
      - name: job_id
        in: path
        type: string
        required: true
        description: ID do job
    responses:
      200:
        description: Status do job
      404:
        description: Job não encontrado
    """
    from meu_app.queue import get_job_status as _get_status
    
    try:
        status = _get_status(job_id)
        
        if status.get('status') == 'error':
            return jsonify(status), 404
        
        return jsonify(status), 200
        
    except Exception as e:
        current_app.logger.error(f"Erro ao consultar job {job_id}: {e}")
        return jsonify({
            'error': True,
            'message': f'Erro ao consultar job: {str(e)}'
        }), 500
