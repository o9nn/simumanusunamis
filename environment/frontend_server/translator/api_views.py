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

def sanitize_path_component(value):
    """
    Sanitize a path component to prevent path traversal attacks.
    
    Removes or replaces dangerous characters and patterns:
    - Path separators (/, backslash)
    - Parent directory references (..)
    - Null bytes
    - Other dangerous characters
    
    Returns sanitized string safe for use in file paths.
    """
    if not value:
        return ""
    
    # Convert to string and strip whitespace
    value = str(value).strip()
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Remove path separators and parent directory references
    value = value.replace('/', '').replace('\\', '')
    value = value.replace('..', '')
    
    # Only allow safe characters: alphanumeric, space, underscore, hyphen
    value = re.sub(r'[^a-zA-Z0-9\s_-]', '', value)
    
    return value


def validate_simulation_code(sim_code):
    """
    Validate that a simulation code exists and is safe.
    Returns sanitized sim_code if valid, None otherwise.
    """
    if not sim_code:
        return None
    
    sanitized = sanitize_path_component(sim_code)
    if not sanitized:
        return None
    
    # Check that simulation exists
    storage_path = os.path.join("storage", sanitized)
    if not os.path.isdir(storage_path):
        return None
    
    return sanitized


def validate_persona_name(sim_code, persona_name):
    """
    Validate that a persona exists in the simulation.
    Returns sanitized persona name if valid, None otherwise.
    """
    if not sim_code or not persona_name:
        return None
    
    sanitized_sim = sanitize_path_component(sim_code)
    sanitized_name = sanitize_path_component(persona_name)
    
    if not sanitized_sim or not sanitized_name:
        return None
    
    # Handle underscore vs space in name
    persona_name_clean = sanitized_name.replace("_", " ")
    
    # Check that persona exists
    persona_path = os.path.join("storage", sanitized_sim, "personas", persona_name_clean)
    if not os.path.isdir(persona_path):
        return None
    
    return persona_name_clean


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
    # Validate and sanitize inputs
    sanitized_sim = sanitize_path_component(sim_code)
    persona_name_clean = validate_persona_name(sim_code, persona_name)
    
    if not sanitized_sim or not persona_name_clean:
        return None
    
    memory_path = os.path.join("storage", sanitized_sim, "personas", 
                               persona_name_clean, "bootstrap_memory")
    
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
    
    # Get simulation metadata (sim_code is already validated by get_current_simulation)
    sanitized_sim = sanitize_path_component(sim_code)
    meta_path = os.path.join("storage", sanitized_sim, "reverie", "meta.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    
    # Count agents
    persona_path = os.path.join("storage", sanitized_sim, "personas")
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
    
    sanitized_sim = sanitize_path_component(sim_code)
    
    # Get current positions
    env_path = os.path.join("storage", sanitized_sim, "environment", f"{step}.json")
    positions = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            positions = json.load(f)
    
    agents = []
    persona_path = os.path.join("storage", sanitized_sim, "personas")
    
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
    sanitized_sim = sanitize_path_component(sim_code)
    
    # Get current position
    env_path = os.path.join("storage", sanitized_sim, "environment", f"{step}.json")
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
    # Use sanitized name for the filename
    sanitized_name = sanitize_path_component(validated_name)
    whisper_dir = "temp_storage/whispers"
    os.makedirs(whisper_dir, exist_ok=True)
    
    whisper_file = os.path.join(whisper_dir, f"{sanitized_name}.json")
    
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
    
    sanitized_sim = sanitize_path_component(sim_code)
    
    # Load metadata
    meta_path = os.path.join("storage", sanitized_sim, "reverie", "meta.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    
    # Load current environment
    env_path = os.path.join("storage", sanitized_sim, "environment", f"{step}.json")
    environment = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            environment = json.load(f)
    
    # Load all agent states (summary only)
    agents = {}
    persona_path = os.path.join("storage", sanitized_sim, "personas")
    
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
