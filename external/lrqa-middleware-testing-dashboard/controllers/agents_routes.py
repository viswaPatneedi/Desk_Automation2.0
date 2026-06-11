"""
Flask Routes for AI Agent Framework Integration
Endpoints for managing, monitoring, and controlling all AI agents
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timezone
import logging

# Import agent functions
from agents import (
    get_orchestrator,
    get_memory_monitor,
    get_eta_device_lock_agent,
    get_screen_analyzer_agent,
    get_job_orchestrator_agent,
    get_recovery_agent
)

logger = logging.getLogger(__name__)

# Create Blueprint
agents_bp = Blueprint('agents', __name__, url_prefix='/api/agents')

# ============================================================
# ORCHESTRATOR ENDPOINTS
# ============================================================

@agents_bp.route('/orchestrator/start', methods=['POST'])
def start_orchestrator():
    """Start the orchestrator and all sub-agents"""
    try:
        orchestrator = get_orchestrator()
        orchestrator.start()
        
        return jsonify({
            'success': True,
            'message': 'Orchestrator started successfully',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error starting orchestrator: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/orchestrator/stop', methods=['POST'])
def stop_orchestrator():
    """Stop the orchestrator and all sub-agents"""
    try:
        orchestrator = get_orchestrator()
        orchestrator.stop()
        
        return jsonify({
            'success': True,
            'message': 'Orchestrator stopped successfully',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error stopping orchestrator: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/orchestrator/status', methods=['GET'])
def orchestrator_status():
    """Get orchestrator and all agents status"""
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting orchestrator status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# AGENT-SPECIFIC ENDPOINTS
# ============================================================

@agents_bp.route('/memory-monitor/status', methods=['GET'])
def memory_monitor_status():
    """Get MemoryMonitor agent status"""
    try:
        agent = get_memory_monitor()
        status = agent.get_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/memory-monitor/analyze', methods=['GET'])
def memory_monitor_analyze():
    """Analyze memory files for issues"""
    try:
        agent = get_memory_monitor()
        issues = agent.get_detected_issues()
        
        return jsonify({
            'success': True,
            'issues_count': len(issues),
            'issues': [i.to_dict() for i in issues],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/eta-device-lock/status', methods=['GET'])
def eta_device_lock_status():
    """Get ETA-DeviceLock agent status"""
    try:
        agent = get_eta_device_lock_agent()
        status = agent.get_agent_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/eta-device-lock/acquire-lock', methods=['POST'])
def acquire_device_lock():
    """Acquire a device lock"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        job_id = data.get('job_id')
        ttl = data.get('ttl', 3600)
        priority = data.get('priority', 5)
        
        agent = get_eta_device_lock_agent()
        result = agent.request_lock(device_id, job_id, ttl, priority)
        
        return jsonify({
            'success': result.get('success', False),
            'data': result,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200 if result.get('success') else 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/screen-analyzer/status', methods=['GET'])
def screen_analyzer_status():
    """Get ScreenAnalyzer agent status"""
    try:
        agent = get_screen_analyzer_agent()
        status = agent.get_agent_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/job-orchestrator/status', methods=['GET'])
def job_orchestrator_status():
    """Get JobOrchestrator queue status"""
    try:
        agent = get_job_orchestrator_agent()
        status = agent.get_agent_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/job-orchestrator/submit-job', methods=['POST'])
def submit_job():
    """Submit a new job for execution"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        method = data.get('method')
        iterations = data.get('iterations', 1)
        priority = data.get('priority', 5)
        
        if not device_id or not method:
            return jsonify({
                'success': False,
                'error': 'device_id and method are required'
            }), 400
        
        agent = get_job_orchestrator_agent()
        result = agent.submit_job(device_id, method, iterations, priority)
        
        return jsonify({
            'success': result.get('success', False),
            'data': result,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200 if result.get('success') else 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/job-orchestrator/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of a specific job"""
    try:
        agent = get_job_orchestrator_agent()
        status = agent.get_job_status(job_id)
        
        if not status or 'error' in status:
            return jsonify({
                'success': False,
                'error': f'Job not found: {job_id}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/recovery/status', methods=['GET'])
def recovery_status():
    """Get Recovery agent status"""
    try:
        agent = get_recovery_agent()
        status = agent.get_agent_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agents_bp.route('/recovery/recommendations', methods=['GET'])
def recovery_recommendations():
    """Get recovery recommendations based on failure patterns"""
    try:
        agent = get_recovery_agent()
        recommendations = agent.get_recommendations()
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# HEALTH CHECK ENDPOINTS
# ============================================================

@agents_bp.route('/health', methods=['GET'])
def agents_health_check():
    """Check overall agents framework health"""
    try:
        orchestrator = get_orchestrator()
        memory_monitor = get_memory_monitor()
        eta_lock = get_eta_device_lock_agent()
        screen_analyzer = get_screen_analyzer_agent()
        job_orchestrator = get_job_orchestrator_agent()
        recovery = get_recovery_agent()
        
        health = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'agents': {
                'orchestrator': {
                    'running': orchestrator.is_running,
                    'status': 'healthy' if orchestrator.is_running else 'stopped'
                },
                'memory-monitor': {
                    'running': memory_monitor.is_running,
                    'status': 'healthy' if memory_monitor.is_running else 'idle'
                },
                'eta-device-lock': {
                    'running': eta_lock.is_running,
                    'status': 'healthy' if eta_lock.is_running else 'idle'
                },
                'screen-analyzer': {
                    'running': screen_analyzer.is_running,
                    'status': 'healthy' if screen_analyzer.is_running else 'idle'
                },
                'job-orchestrator': {
                    'running': job_orchestrator.is_running,
                    'status': 'healthy' if job_orchestrator.is_running else 'idle'
                },
                'recovery': {
                    'running': recovery.is_running,
                    'status': 'healthy' if recovery.is_running else 'idle'
                }
            }
        }
        
        all_healthy = all(agent['status'] == 'healthy' for agent in health['agents'].values())
        
        return jsonify({
            'success': True,
            'overall_status': 'healthy' if all_healthy else 'degraded',
            'data': health
        }), 200
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'overall_status': 'error'
        }), 500


# ============================================================
# ERROR HANDLERS
# ============================================================

@agents_bp.errorhandler(400)
def bad_request(e):
    """Handle bad requests"""
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': str(e)
    }), 400


@agents_bp.errorhandler(404)
def not_found(e):
    """Handle not found errors"""
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': str(e)
    }), 404


@agents_bp.errorhandler(500)
def server_error(e):
    """Handle server errors"""
    logger.error(f"Server error: {e}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': str(e)
    }), 500


def register_agents_blueprint(app):
    """Register the agents blueprint with the Flask app"""
    app.register_blueprint(agents_bp)
    logger.info("✅ Agents blueprint registered")
