"""
API Views for External Agent Integration.

This module provides REST API endpoints for external autonomous agents
to interact with the Reverie simulation.

Endpoints:
- GET /api/v1/simulation/status - Get current simulation status
- GET /api/v1/agents - List all agents in simulation
- GET /api/v1/agents/<name>/state - Get specific agent state
- POST /api/v1/agents/<name>/whisper - Inject goal/memory into agent
- GET /api/v1/world/snapshot - Export full world state
- POST /api/v1/simulation/step - Advance simulation
- GET /api/v1/agents/<name>/memory - Get agent memory stream
"""
import json
import os
import re
import datetime
from functools import wraps

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from global_methods import check_if_file_exists, find_filenames


# =============================================================================
# Security: Path Sanitization
# =============================================================================

def normalize_input(value):
    """
    Normalize a user input value for comparison.
    
    Removes dangerous characters and normalizes to lowercase for safe comparison.
    This function is only used to create a comparison key, NOT for file paths.
    """
    if not value:
        return ""
    
    # Convert to string and strip whitespace
    value = str(value).strip().lower()
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Remove path separators and parent directory references
    value = value.replace('/', '').replace('\\', '')
    value = value.replace('..', '')
    
    # Only allow safe characters: alphanumeric, space, underscore, hyphen
    value = re.sub(r'[^a-z0-9\s_-]', '', value)
    
    # Normalize underscores to spaces for comparison
    value = value.replace('_', ' ')
    
    return value


def get_allowed_simulations():
    """
    Get list of valid simulation directories from storage.
    Returns a dict mapping normalized names to actual directory names.
    """
    allowed = {}
    storage_dir = "storage"
    
    if not os.path.isdir(storage_dir):
        return allowed
    
    for name in os.listdir(storage_dir):
        path = os.path.join(storage_dir, name)
        if os.path.isdir(path) and not name.startswith('.'):
            # Map normalized name to actual directory name
            allowed[normalize_input(name)] = name
    
    return allowed


def validate_simulation_code(sim_code):
    """
    Validate that a simulation code exists by checking against allowlist.
    Returns the actual directory name if valid, None otherwise.
    
    Uses allowlist approach to break taint chain - returns value from
    filesystem listing, not from user input.
    """
    if not sim_code:
        return None
    
    normalized = normalize_input(sim_code)
    if not normalized:
        return None
    
    allowed = get_allowed_simulations()
    
    # Return the actual directory name from allowlist, not user input
    return allowed.get(normalized)


def get_allowed_personas(sim_dir):
    """
    Get list of valid persona directories for a simulation.
    Returns a dict mapping normalized names to actual directory names.
    """
    allowed = {}
    personas_dir = os.path.join("storage", sim_dir, "personas")
    
    if not os.path.isdir(personas_dir):
        return allowed
    
    for name in os.listdir(personas_dir):
        path = os.path.join(personas_dir, name)
        if os.path.isdir(path) and not name.startswith('.'):
            # Map normalized name to actual directory name
            allowed[normalize_input(name)] = name
    
    return allowed


def validate_persona_name(sim_code, persona_name):
    """
    Validate that a persona exists in the simulation by checking against allowlist.
    Returns the actual persona directory name if valid, None otherwise.
    
    Uses allowlist approach to break taint chain - returns value from
    filesystem listing, not from user input.
    """
    if not sim_code or not persona_name:
        return None
    
    # First validate the simulation code
    sim_dir = validate_simulation_code(sim_code)
    if not sim_dir:
        return None
    
    normalized = normalize_input(persona_name)
    if not normalized:
        return None
    
    allowed = get_allowed_personas(sim_dir)
    
    # Return the actual directory name from allowlist, not user input
    return allowed.get(normalized)


# =============================================================================
# API Authentication Decorator
# =============================================================================

def api_auth_required(view_func):
    """
    Decorator to require API authentication.
    Checks for X-API-Key header or api_key query parameter.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        # Check if auth is required (configurable)
        require_auth = getattr(settings, 'REQUIRE_API_AUTH', False)
        if not require_auth:
            return view_func(request, *args, **kwargs)
        
        # Get API key from header or query param
        api_key = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')
        
        if not api_key:
            return JsonResponse({
                'error': 'Missing API key',
                'detail': 'Provide X-API-Key header or api_key query parameter'
            }, status=401)
        
        # Validate API key
        valid_keys = getattr(settings, 'API_KEYS', [])
        if api_key not in valid_keys:
            return JsonResponse({
                'error': 'Invalid API key',
                'detail': 'The provided API key is not valid'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapped


# =============================================================================
# Utility Functions
# =============================================================================

def get_current_simulation():
    """Get the current active simulation code and step."""
    sim_code_file = "temp_storage/curr_sim_code.json"
    
    if not check_if_file_exists(sim_code_file):
        return None, None
    
    with open(sim_code_file) as f:
        data = json.load(f)
        sim_code = data.get('sim_code')
        # Validate the simulation code from config
        if sim_code:
            sim_code = validate_simulation_code(sim_code)
        return sim_code, data.get('step', 0)


def load_persona_state(sim_code, persona_name):
    """Load the full state of a persona from storage."""
    # Validate inputs using allowlist - returns actual directory names
    validated_sim = validate_simulation_code(sim_code)
    validated_persona = validate_persona_name(sim_code, persona_name)
    
    if not validated_sim or not validated_persona:
        return None
    
    # Use validated names from allowlist (not user input)
    memory_path = os.path.join("storage", validated_sim, "personas", 
                               validated_persona, "bootstrap_memory")
    
    if not os.path.exists(memory_path):
        return None
    
    state = {}
    
    # Load scratch (short-term state)
    scratch_path = os.path.join(memory_path, "scratch.json")
    if os.path.exists(scratch_path):
        with open(scratch_path) as f:
            state['scratch'] = json.load(f)
    
    # Load spatial memory
    spatial_path = os.path.join(memory_path, "spatial_memory.json")
    if os.path.exists(spatial_path):
        with open(spatial_path) as f:
            state['spatial_memory'] = json.load(f)
    
    # Load associative memory
    assoc_path = os.path.join(memory_path, "associative_memory", "nodes.json")
    if os.path.exists(assoc_path):
        with open(assoc_path) as f:
            state['associative_memory'] = json.load(f)
    
    return state


# =============================================================================
# API Endpoints
# =============================================================================

@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_simulation_status(request):
    """
    GET /api/v1/simulation/status
    
    Returns the current simulation status including:
    - Simulation code/name
    - Current step
    - Current simulation time
    - Number of active agents
    """
    sim_code, step = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({
            'status': 'inactive',
            'detail': 'No active simulation. Start the backend server first.'
        })
    
    # sim_code is already validated by get_current_simulation() using allowlist
    # It returns the actual directory name from the filesystem, not user input
    meta_path = os.path.join("storage", sim_code, "reverie", "meta.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    
    # Count agents
    persona_path = os.path.join("storage", sim_code, "personas")
    agent_count = 0
    if os.path.exists(persona_path):
        agent_count = len([d for d in os.listdir(persona_path) 
                          if os.path.isdir(os.path.join(persona_path, d)) and not d.startswith('.')])
    
    return JsonResponse({
        'status': 'active',
        'sim_code': sim_code,
        'step': step,
        'start_date': meta.get('start_date'),
        'curr_time': meta.get('curr_time'),
        'sec_per_step': meta.get('sec_per_step', 10),
        'maze_name': meta.get('maze_name'),
        'agent_count': agent_count,
        'persona_names': meta.get('persona_names', [])
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_list_agents(request):
    """
    GET /api/v1/agents
    
    List all agents in the current simulation with their basic info.
    """
    sim_code, step = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({
            'error': 'No active simulation',
            'agents': []
        }, status=404)
    
    # sim_code is already validated by get_current_simulation() using allowlist
    # Get current positions
    env_path = os.path.join("storage", sim_code, "environment", f"{step}.json")
    positions = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            positions = json.load(f)
    
    agents = []
    persona_path = os.path.join("storage", sim_code, "personas")
    
    if os.path.exists(persona_path):
        for name in os.listdir(persona_path):
            if name.startswith('.'):
                continue
            full_path = os.path.join(persona_path, name)
            if not os.path.isdir(full_path):
                continue
            
            agent_info = {
                'name': name,
                'name_underscore': name.replace(' ', '_'),
                'position': positions.get(name, {})
            }
            
            # Load scratch for basic info
            scratch_path = os.path.join(full_path, "bootstrap_memory", "scratch.json")
            if os.path.exists(scratch_path):
                with open(scratch_path) as f:
                    scratch = json.load(f)
                    agent_info.update({
                        'first_name': scratch.get('first_name'),
                        'age': scratch.get('age'),
                        'innate': scratch.get('innate'),
                        'currently': scratch.get('currently'),
                        'current_action': scratch.get('act_description')
                    })
            
            agents.append(agent_info)
    
    return JsonResponse({
        'sim_code': sim_code,
        'step': step,
        'agent_count': len(agents),
        'agents': agents
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_agent_state(request, agent_name):
    """
    GET /api/v1/agents/<name>/state
    
    Get detailed state of a specific agent including:
    - Current plan/schedule
    - Location
    - Memory summary
    - Current action
    """
    sim_code, step = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({'error': 'No active simulation'}, status=404)
    
    # Validate agent name
    validated_name = validate_persona_name(sim_code, agent_name)
    if not validated_name:
        return JsonResponse({
            'error': f'Agent not found: {agent_name}'
        }, status=404)
    
    state = load_persona_state(sim_code, agent_name)
    
    if not state:
        return JsonResponse({
            'error': f'Agent not found: {agent_name}'
        }, status=404)
    
    scratch = state.get('scratch', {})
    
    # sim_code is already validated by get_current_simulation() using allowlist
    # Get current position
    env_path = os.path.join("storage", sim_code, "environment", f"{step}.json")
    position = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            env = json.load(f)
            position = env.get(validated_name, {})
    
    # Count memory items
    assoc = state.get('associative_memory', {})
    event_count = sum(1 for n in assoc.values() if n.get('type') == 'event')
    thought_count = sum(1 for n in assoc.values() if n.get('type') == 'thought')
    chat_count = sum(1 for n in assoc.values() if n.get('type') == 'chat')
    
    return JsonResponse({
        'name': validated_name,
        'position': position,
        'identity': {
            'first_name': scratch.get('first_name'),
            'last_name': scratch.get('last_name'),
            'age': scratch.get('age'),
            'innate': scratch.get('innate'),
            'learned': scratch.get('learned'),
            'currently': scratch.get('currently'),
            'lifestyle': scratch.get('lifestyle'),
            'living_area': scratch.get('living_area')
        },
        'current_state': {
            'curr_time': scratch.get('curr_time'),
            'curr_tile': scratch.get('curr_tile'),
            'act_description': scratch.get('act_description'),
            'act_address': scratch.get('act_address'),
            'act_pronunciatio': scratch.get('act_pronunciatio'),
            'chatting_with': scratch.get('chatting_with'),
            'planned_path': scratch.get('planned_path', [])[:5]  # First 5 steps
        },
        'daily_schedule': scratch.get('f_daily_schedule', []),
        'memory_summary': {
            'total_events': event_count,
            'total_thoughts': thought_count,
            'total_chats': chat_count
        },
        'cognitive_params': {
            'vision_r': scratch.get('vision_r'),
            'att_bandwidth': scratch.get('att_bandwidth'),
            'retention': scratch.get('retention')
        }
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_agent_memory(request, agent_name):
    """
    GET /api/v1/agents/<name>/memory
    
    Get agent's memory stream with filtering options.
    
    Query params:
    - type: event|thought|chat (filter by type)
    - limit: max items to return (default 50)
    - since: only memories after this node_id
    """
    sim_code, _ = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({'error': 'No active simulation'}, status=404)
    
    # Validate agent name
    validated_name = validate_persona_name(sim_code, agent_name)
    if not validated_name:
        return JsonResponse({
            'error': f'Agent not found: {agent_name}'
        }, status=404)
    
    state = load_persona_state(sim_code, agent_name)
    
    if not state:
        return JsonResponse({
            'error': f'Agent not found: {agent_name}'
        }, status=404)
    
    # Get query parameters
    memory_type = request.GET.get('type')
    try:
        limit = min(int(request.GET.get('limit', 50)), 500)  # Cap at 500
    except ValueError:
        limit = 50
    since = request.GET.get('since')
    
    assoc = state.get('associative_memory', {})
    memories = []
    
    # Sort by node count (most recent first)
    sorted_keys = sorted(assoc.keys(), 
                        key=lambda x: assoc[x].get('node_count', 0), 
                        reverse=True)
    
    for key in sorted_keys:
        node = assoc[key]
        
        # Filter by type
        if memory_type and node.get('type') != memory_type:
            continue
        
        # Filter by since
        if since:
            try:
                since_count = int(since.replace('node_', ''))
                if node.get('node_count', 0) <= since_count:
                    continue
            except ValueError:
                pass
        
        memories.append({
            'node_id': key,
            'type': node.get('type'),
            'created': node.get('created'),
            'subject': node.get('subject'),
            'predicate': node.get('predicate'),
            'object': node.get('object'),
            'description': node.get('description'),
            'poignancy': node.get('poignancy'),
            'keywords': node.get('keywords', [])
        })
        
        if len(memories) >= limit:
            break
    
    return JsonResponse({
        'agent': validated_name,
        'count': len(memories),
        'memories': memories
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["POST"])
def api_agent_whisper(request, agent_name):
    """
    POST /api/v1/agents/<name>/whisper
    
    Inject a goal or memory into an agent's mind.
    This simulates the "whisper" functionality.
    
    Request body:
    {
        "content": "Remember to go to the park at 3pm",
        "type": "thought" | "goal"
    }
    """
    sim_code, _ = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({'error': 'No active simulation'}, status=404)
    
    # Validate agent name
    validated_name = validate_persona_name(sim_code, agent_name)
    if not validated_name:
        return JsonResponse({
            'error': f'Agent not found: {agent_name}'
        }, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    
    content = data.get('content')
    whisper_type = data.get('type', 'thought')
    
    if not content:
        return JsonResponse({'error': 'Missing content field'}, status=400)
    
    # Validate whisper_type
    if whisper_type not in ('thought', 'goal'):
        whisper_type = 'thought'
    
    # Write whisper to a file that the backend will pick up
    # validated_name is already from allowlist (validate_persona_name returns 
    # actual directory name from filesystem, not user input)
    whisper_dir = "temp_storage/whispers"
    os.makedirs(whisper_dir, exist_ok=True)
    
    # Replace spaces with underscores for safe filename
    safe_filename = validated_name.replace(' ', '_')
    whisper_file = os.path.join(whisper_dir, f"{safe_filename}.json")
    
    # Append to existing whispers
    whispers = []
    if os.path.exists(whisper_file):
        with open(whisper_file) as f:
            whispers = json.load(f)
    
    whispers.append({
        'content': content,
        'type': whisper_type,
        'timestamp': datetime.datetime.now().isoformat()
    })
    
    with open(whisper_file, 'w') as f:
        json.dump(whispers, f, indent=2)
    
    return JsonResponse({
        'status': 'success',
        'agent': validated_name,
        'whisper': content,
        'type': whisper_type,
        'pending_whispers': len(whispers)
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_world_snapshot(request):
    """
    GET /api/v1/world/snapshot
    
    Export full world state as JSON including:
    - All agent positions
    - All agent states (summary)
    - Current simulation metadata
    """
    sim_code, step = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({'error': 'No active simulation'}, status=404)
    
    # sim_code is already validated by get_current_simulation() using allowlist
    # Load metadata
    meta_path = os.path.join("storage", sim_code, "reverie", "meta.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    
    # Load current environment
    env_path = os.path.join("storage", sim_code, "environment", f"{step}.json")
    environment = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            environment = json.load(f)
    
    # Load all agent states (summary only)
    agents = {}
    persona_path = os.path.join("storage", sim_code, "personas")
    
    if os.path.exists(persona_path):
        for name in os.listdir(persona_path):
            if name.startswith('.'):
                continue
            full_path = os.path.join(persona_path, name)
            if not os.path.isdir(full_path):
                continue
            
            scratch_path = os.path.join(full_path, "bootstrap_memory", "scratch.json")
            if os.path.exists(scratch_path):
                with open(scratch_path) as f:
                    scratch = json.load(f)
                    agents[name] = {
                        'position': environment.get(name, {}),
                        'currently': scratch.get('currently'),
                        'act_description': scratch.get('act_description'),
                        'act_address': scratch.get('act_address')
                    }
    
    return JsonResponse({
        'sim_code': sim_code,
        'step': step,
        'metadata': meta,
        'agents': agents,
        'exported_at': datetime.datetime.now().isoformat()
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_list_simulations(request):
    """
    GET /api/v1/simulations
    
    List all available simulations (saved states).
    """
    storage_path = "storage"
    simulations = []
    
    if os.path.exists(storage_path):
        for name in os.listdir(storage_path):
            sim_path = os.path.join(storage_path, name)
            if not os.path.isdir(sim_path):
                continue
            if name.startswith('.'):
                continue
            
            meta_path = os.path.join(sim_path, 'reverie', 'meta.json')
            meta = {}
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
            
            simulations.append({
                'sim_code': name,
                'start_date': meta.get('start_date'),
                'curr_time': meta.get('curr_time'),
                'step': meta.get('step'),
                'persona_count': len(meta.get('persona_names', []))
            })
    
    return JsonResponse({
        'count': len(simulations),
        'simulations': simulations
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_list_scenarios(request):
    """
    GET /api/v1/scenarios
    
    List available scenario templates.
    """
    scenarios_path = "static_dirs/assets/scenarios"
    scenarios = []
    
    if os.path.exists(scenarios_path):
        for filename in os.listdir(scenarios_path):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(scenarios_path, filename)
            with open(filepath) as f:
                data = json.load(f)
                scenarios.append({
                    'name': filename.replace('.json', ''),
                    'arena': data.get('arena'),
                    'start_date': data.get('start_date'),
                    'sec_per_step': data.get('sec_per_step'),
                    'agent_count': len(data.get('agents', []))
                })
    
    return JsonResponse({
        'count': len(scenarios),
        'scenarios': scenarios
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_list_agent_templates(request):
    """
    GET /api/v1/agent-templates
    
    List available agent templates.
    """
    templates_path = "static_dirs/assets/agent_templates"
    templates = []
    
    if os.path.exists(templates_path):
        for name in os.listdir(templates_path):
            template_path = os.path.join(templates_path, name)
            if not os.path.isdir(template_path):
                continue
            if name.startswith('.'):
                continue
            
            scratch_path = os.path.join(template_path, 'scratch_template.json')
            if os.path.exists(scratch_path):
                with open(scratch_path) as f:
                    scratch = json.load(f)
                    templates.append({
                        'name': name,
                        'first_name': scratch.get('first_name'),
                        'age': scratch.get('age'),
                        'innate': scratch.get('innate'),
                        'currently': scratch.get('currently')
                    })
    
    return JsonResponse({
        'count': len(templates),
        'templates': templates
    })


# =============================================================================
# Health Check Endpoints
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def api_health(request):
    """
    GET /health or GET /api/v1/health
    
    Basic health check endpoint for load balancers and monitoring.
    Returns service status and basic diagnostics.
    
    No authentication required - designed for infrastructure monitoring.
    """
    health_status = {
        'status': 'healthy',
        'service': 'reverie-frontend',
        'timestamp': datetime.datetime.now().isoformat(),
        'checks': {}
    }
    
    # Check storage directory accessibility
    storage_ok = os.path.isdir("storage") and os.access("storage", os.R_OK | os.W_OK)
    health_status['checks']['storage'] = 'ok' if storage_ok else 'error'
    
    # Check temp_storage directory
    temp_ok = os.path.isdir("temp_storage") and os.access("temp_storage", os.R_OK | os.W_OK)
    health_status['checks']['temp_storage'] = 'ok' if temp_ok else 'error'
    
    # Check if simulation is active
    sim_code, step = get_current_simulation()
    health_status['checks']['simulation'] = 'active' if sim_code else 'inactive'
    
    # Check database connectivity (simple check)
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['checks']['database'] = 'ok'
    except Exception:
        health_status['checks']['database'] = 'error'
    
    # Determine overall health
    critical_checks = ['storage', 'temp_storage', 'database']
    if any(health_status['checks'].get(c) == 'error' for c in critical_checks):
        health_status['status'] = 'unhealthy'
        return JsonResponse(health_status, status=503)
    
    return JsonResponse(health_status)


@csrf_exempt
@require_http_methods(["GET"])
def api_health_detailed(request):
    """
    GET /api/v1/health/detailed
    
    Detailed health check with system metrics.
    Requires API authentication.
    """
    # Get basic health first
    basic_health = api_health(request)
    health_data = json.loads(basic_health.content)
    
    # Add detailed metrics
    health_data['details'] = {}
    
    # Count simulations
    storage_path = "storage"
    if os.path.isdir(storage_path):
        sim_count = len([d for d in os.listdir(storage_path) 
                        if os.path.isdir(os.path.join(storage_path, d)) 
                        and not d.startswith('.')])
        health_data['details']['simulation_count'] = sim_count
    
    # Check for active simulation details
    sim_code, step = get_current_simulation()
    if sim_code:
        health_data['details']['active_simulation'] = {
            'sim_code': sim_code,
            'step': step
        }
        # Count active agents
        persona_path = os.path.join("storage", sim_code, "personas")
        if os.path.exists(persona_path):
            agent_count = len([d for d in os.listdir(persona_path) 
                              if os.path.isdir(os.path.join(persona_path, d)) 
                              and not d.startswith('.')])
            health_data['details']['active_simulation']['agent_count'] = agent_count
    
    # Check pending whispers
    whispers_dir = "temp_storage/whispers"
    if os.path.isdir(whispers_dir):
        pending_whispers = len([f for f in os.listdir(whispers_dir) if f.endswith('.json')])
        health_data['details']['pending_whispers'] = pending_whispers
    
    return JsonResponse(health_data)


# =============================================================================
# Multi-Agent Interaction Features
# =============================================================================

@csrf_exempt
@api_auth_required
@require_http_methods(["POST"])
def api_broadcast_goal(request):
    """
    POST /api/v1/broadcast
    
    Broadcast a goal or announcement to multiple agents at once.
    Useful for event injection, world events, or coordinated scenarios.
    
    Request body:
    {
        "content": "There's a party at the town square at 5pm!",
        "type": "event" | "announcement",
        "target_agents": ["agent1", "agent2"] | "all"
    }
    """
    sim_code, _ = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({'error': 'No active simulation'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    
    content = data.get('content')
    broadcast_type = data.get('type', 'event')
    target_agents = data.get('target_agents', 'all')
    
    if not content:
        return JsonResponse({'error': 'Missing content field'}, status=400)
    
    # Validate broadcast_type
    if broadcast_type not in ('event', 'announcement', 'goal'):
        broadcast_type = 'event'
    
    # Get all agents if target is "all"
    if target_agents == 'all':
        allowed = get_allowed_personas(sim_code)
        target_agents = list(allowed.values())
    else:
        # Validate each agent name
        validated_targets = []
        for agent in target_agents:
            validated = validate_persona_name(sim_code, agent)
            if validated:
                validated_targets.append(validated)
        target_agents = validated_targets
    
    if not target_agents:
        return JsonResponse({'error': 'No valid target agents'}, status=400)
    
    # Create whispers for all target agents
    whisper_dir = "temp_storage/whispers"
    os.makedirs(whisper_dir, exist_ok=True)
    
    broadcast_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    success_count = 0
    
    for agent_name in target_agents:
        safe_filename = agent_name.replace(' ', '_')
        whisper_file = os.path.join(whisper_dir, f"{safe_filename}.json")
        
        whispers = []
        if os.path.exists(whisper_file):
            with open(whisper_file) as f:
                whispers = json.load(f)
        
        whispers.append({
            'content': content,
            'type': broadcast_type,
            'broadcast_id': broadcast_id,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        with open(whisper_file, 'w') as f:
            json.dump(whispers, f, indent=2)
        
        success_count += 1
    
    return JsonResponse({
        'status': 'success',
        'broadcast_id': broadcast_id,
        'content': content,
        'type': broadcast_type,
        'agents_notified': success_count,
        'target_agents': target_agents
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_agent_relationships(request, agent_name):
    """
    GET /api/v1/agents/<name>/relationships
    
    Get an agent's social network - who they know and relationship strengths.
    Analyzes chat history to infer relationships.
    """
    sim_code, _ = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({'error': 'No active simulation'}, status=404)
    
    validated_name = validate_persona_name(sim_code, agent_name)
    if not validated_name:
        return JsonResponse({'error': f'Agent not found: {agent_name}'}, status=404)
    
    state = load_persona_state(sim_code, agent_name)
    if not state:
        return JsonResponse({'error': f'Agent not found: {agent_name}'}, status=404)
    
    # Analyze associative memory for relationships
    assoc = state.get('associative_memory', {})
    relationships = {}
    
    for node_id, node in assoc.items():
        # Look for chat memories
        if node.get('type') == 'chat':
            # Extract other person from chat
            subject = node.get('subject', '')
            obj = node.get('object', '')
            desc = node.get('description', '')
            
            # Find other agents mentioned
            for other_agent in get_allowed_personas(sim_code).values():
                if other_agent != validated_name:
                    if other_agent.lower() in desc.lower() or other_agent in subject or other_agent in obj:
                        if other_agent not in relationships:
                            relationships[other_agent] = {
                                'name': other_agent,
                                'interactions': 0,
                                'recent_topics': [],
                                'sentiment_score': 0
                            }
                        relationships[other_agent]['interactions'] += 1
                        
                        # Track recent topics
                        keywords = node.get('keywords', [])
                        for kw in keywords[:3]:
                            if kw not in relationships[other_agent]['recent_topics']:
                                relationships[other_agent]['recent_topics'].append(kw)
                                if len(relationships[other_agent]['recent_topics']) > 5:
                                    relationships[other_agent]['recent_topics'].pop(0)
                        
                        # Simple sentiment from poignancy
                        poignancy = node.get('poignancy', 5)
                        relationships[other_agent]['sentiment_score'] += poignancy - 5
    
    # Calculate relationship strength
    for rel in relationships.values():
        interactions = rel['interactions']
        rel['strength'] = 'strong' if interactions > 10 else 'moderate' if interactions > 3 else 'weak'
        # Normalize sentiment
        rel['sentiment'] = 'positive' if rel['sentiment_score'] > 5 else 'negative' if rel['sentiment_score'] < -5 else 'neutral'
    
    return JsonResponse({
        'agent': validated_name,
        'relationship_count': len(relationships),
        'relationships': list(relationships.values())
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_interaction_history(request):
    """
    GET /api/v1/interactions
    
    Get recent interactions between agents across the simulation.
    Useful for understanding social dynamics.
    
    Query params:
    - limit: max interactions to return (default 50)
    - agent: filter to interactions involving a specific agent
    """
    sim_code, _ = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({'error': 'No active simulation'}, status=404)
    
    try:
        limit = min(int(request.GET.get('limit', 50)), 200)
    except ValueError:
        limit = 50
    
    filter_agent = request.GET.get('agent')
    if filter_agent:
        filter_agent = validate_persona_name(sim_code, filter_agent)
    
    interactions = []
    
    # Gather chat memories from all agents
    for agent_name in get_allowed_personas(sim_code).values():
        state = load_persona_state(sim_code, agent_name)
        if not state:
            continue
        
        assoc = state.get('associative_memory', {})
        for node_id, node in assoc.items():
            if node.get('type') == 'chat':
                # Apply filter if specified
                if filter_agent and filter_agent != agent_name:
                    desc = node.get('description', '').lower()
                    if filter_agent.lower() not in desc:
                        continue
                
                interactions.append({
                    'agent': agent_name,
                    'node_id': node_id,
                    'created': node.get('created'),
                    'description': node.get('description'),
                    'subject': node.get('subject'),
                    'object': node.get('object'),
                    'poignancy': node.get('poignancy'),
                    'keywords': node.get('keywords', [])
                })
    
    # Sort by creation time (most recent first)
    interactions.sort(key=lambda x: x.get('created', ''), reverse=True)
    interactions = interactions[:limit]
    
    return JsonResponse({
        'sim_code': sim_code,
        'count': len(interactions),
        'filter_agent': filter_agent,
        'interactions': interactions
    })


@csrf_exempt
@api_auth_required
@require_http_methods(["GET"])
def api_social_network(request):
    """
    GET /api/v1/social-network
    
    Get the full social network graph of agent relationships.
    Returns nodes (agents) and edges (relationships based on interactions).
    """
    sim_code, _ = get_current_simulation()
    
    if not sim_code:
        return JsonResponse({'error': 'No active simulation'}, status=404)
    
    agents = list(get_allowed_personas(sim_code).values())
    
    # Build nodes
    nodes = []
    for agent_name in agents:
        state = load_persona_state(sim_code, agent_name)
        scratch = state.get('scratch', {}) if state else {}
        nodes.append({
            'id': agent_name,
            'label': agent_name,
            'type': 'agent',
            'currently': scratch.get('currently', ''),
            'innate': scratch.get('innate', '')
        })
    
    # Build edges by analyzing interactions
    edges = []
    edge_weights = {}
    
    for agent_name in agents:
        state = load_persona_state(sim_code, agent_name)
        if not state:
            continue
        
        assoc = state.get('associative_memory', {})
        for node in assoc.values():
            if node.get('type') == 'chat':
                desc = node.get('description', '').lower()
                for other_agent in agents:
                    if other_agent != agent_name and other_agent.lower() in desc:
                        # Create sorted edge key for deduplication
                        edge_key = tuple(sorted([agent_name, other_agent]))
                        if edge_key not in edge_weights:
                            edge_weights[edge_key] = 0
                        edge_weights[edge_key] += 1
    
    # Convert to edge list
    for (source, target), weight in edge_weights.items():
        edges.append({
            'source': source,
            'target': target,
            'weight': weight,
            'strength': 'strong' if weight > 10 else 'moderate' if weight > 3 else 'weak'
        })
    
    return JsonResponse({
        'sim_code': sim_code,
        'nodes': nodes,
        'edges': edges,
        'node_count': len(nodes),
        'edge_count': len(edges)
    })
