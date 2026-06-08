# Cognitive Module Extension Guide

This guide explains how to extend the cognitive modules to add custom behaviors, new action types, or modified decision-making for agents.

## Architecture Overview

The cognitive pipeline processes each agent's turn in the following order:

```
Perceive → Retrieve → Plan → Reflect → Execute → Converse
```

Each module can be extended independently or in combination.

## Module Extension Points

### 1. Perceive (`perceive.py`)

**Purpose**: Determine what the agent notices in their environment.

**Extension Points**:

```python
# Add custom event types to perception
def custom_perceive_filter(persona, event):
    """
    Filter or modify perceived events before storing.
    
    Args:
        persona: The agent perceiving
        event: A dict with {subject, predicate, object, description}
    
    Returns:
        event (modified) or None to filter out
    """
    # Example: Prioritize events involving certain keywords
    if 'emergency' in event.get('description', '').lower():
        event['priority'] = 'high'
    return event

# Hook into generate_poig_score() to customize importance scoring
def custom_poignancy_scorer(persona, event_type, description):
    """
    Score how important/memorable an event is (1-10).
    
    Higher scores = more likely to be remembered and influence behavior.
    """
    base_score = run_gpt_prompt_event_poignancy(persona, description)[0]
    
    # Boost score for events involving friends
    if persona.scratch.friends and any(f in description for f in persona.scratch.friends):
        base_score = min(10, base_score + 2)
    
    return base_score
```

### 2. Retrieve (`retrieve.py`)

**Purpose**: Select relevant memories to inform current decisions.

**Extension Points**:

```python
# Customize memory retrieval weighting
def custom_memory_retrieval(persona, query, top_k=5):
    """
    Retrieve relevant memories based on current context.
    
    The default uses recency + importance + relevance weighting.
    You can modify weights or add new factors.
    """
    # Default weights
    recency_weight = 1.0
    importance_weight = 1.0
    relevance_weight = 1.0
    
    # Custom: Add social relevance weight
    social_weight = 0.5
    
    # Retrieve and re-rank
    memories = persona.a_mem.retrieve(query)
    for mem in memories:
        if is_social_memory(mem):
            mem.score += social_weight
    
    return sorted(memories, key=lambda m: m.score, reverse=True)[:top_k]
```

### 3. Plan (`plan.py`)

**Purpose**: Determine what the agent should do next.

**Extension Points**:

```python
# Add new action types
ACTION_TYPES = {
    'standard': ['eat', 'sleep', 'work', 'socialize'],
    'custom': ['investigate', 'broadcast', 'coordinate']  # Add your own
}

# Hook into daily planning
def inject_custom_goals(persona, daily_schedule):
    """
    Modify the agent's daily schedule.
    
    Called after initial schedule generation.
    Check for pending whispers/goals and inject them.
    """
    # Check for external goal injections
    whispers = load_pending_whispers(persona.name)
    for whisper in whispers:
        if whisper['type'] == 'goal':
            daily_schedule.insert(0, {
                'task': whisper['content'],
                'priority': 'high',
                'injected': True
            })
    
    return daily_schedule

# Add custom planning prompts
def custom_plan_prompt(persona, context):
    """
    Generate a custom planning prompt for specific scenarios.
    
    Returns modified prompt string or None to use default.
    """
    if persona.scratch.current_goal == 'coordinate':
        return f"""
        {persona.scratch.name} needs to coordinate with others.
        Current goal: {persona.scratch.currently}
        Nearby agents: {context['nearby_agents']}
        
        What should {persona.scratch.name} do to coordinate effectively?
        """
    return None
```

### 4. Reflect (`reflect.py`)

**Purpose**: Synthesize experiences into insights and update beliefs.

**Extension Points**:

```python
# Customize reflection triggers
def should_reflect(persona):
    """
    Determine if the agent should reflect on recent experiences.
    
    Default triggers on accumulated importance score threshold.
    Add custom triggers for specific events.
    """
    # Default threshold
    if persona.scratch.importance_trigger_curr >= 150:
        return True
    
    # Custom: Trigger on significant social events
    recent_chats = persona.a_mem.get_recent_chats(hours=2)
    if len(recent_chats) >= 3:
        return True
    
    return False

# Add custom insight generation
def generate_custom_insights(persona, focal_points):
    """
    Generate insights from recent experiences.
    
    focal_points: List of important memory items to reflect on
    """
    insights = []
    
    # Generate relationship insights
    for person in get_interacted_people(focal_points):
        insight = {
            'type': 'relationship_update',
            'subject': persona.name,
            'object': person,
            'content': analyze_relationship(persona, person, focal_points)
        }
        insights.append(insight)
    
    return insights
```

### 5. Execute (`execute.py`)

**Purpose**: Translate plans into world actions.

**Extension Points**:

```python
# Add new executable action types
CUSTOM_ACTIONS = {
    'broadcast': execute_broadcast,
    'coordinate': execute_coordinate,
    'investigate': execute_investigate,
}

def execute_broadcast(persona, action_params):
    """
    Execute a broadcast action - announce something to nearby agents.
    """
    message = action_params.get('message')
    radius = action_params.get('radius', persona.scratch.vision_r)
    
    # Get nearby agents
    nearby = get_agents_in_radius(persona.scratch.curr_tile, radius)
    
    # Create event for each nearby agent to perceive
    for agent in nearby:
        create_perceived_event(
            agent=agent,
            subject=persona.name,
            predicate='announced',
            object=message,
            description=f'{persona.name} announced: "{message}"'
        )
    
    return {'success': True, 'agents_reached': len(nearby)}

# Hook into movement execution
def custom_path_modifier(persona, planned_path):
    """
    Modify the agent's movement path.
    
    Called before movement execution.
    """
    # Example: Avoid certain areas
    if persona.scratch.avoiding:
        planned_path = reroute_avoiding(planned_path, persona.scratch.avoiding)
    
    return planned_path
```

### 6. Converse (`converse.py`)

**Purpose**: Handle agent-to-agent conversations.

**Extension Points**:

```python
# Add conversation initiators
CONVERSATION_TRIGGERS = {
    'greeting': should_greet,
    'task_request': should_request_help,
    'information_share': should_share_info,
    'custom': should_custom_converse,  # Add your own
}

def should_custom_converse(persona, other_agent):
    """
    Determine if a custom conversation should be initiated.
    """
    # Example: Initiate if have pending message for this agent
    pending = get_pending_messages(persona.name, other_agent.name)
    return len(pending) > 0

# Customize conversation content
def custom_conversation_prompt(persona, other_agent, context):
    """
    Generate custom conversation prompts.
    
    Returns conversation opening or None to use default.
    """
    # Check for coordinated tasks
    if has_shared_goal(persona, other_agent):
        return f"""
        {persona.name} and {other_agent.name} are working on: {get_shared_goal()}
        {persona.name} should discuss progress and coordinate next steps.
        """
    return None

# Add conversation conclusion handlers
def on_conversation_end(persona, other_agent, conversation_log):
    """
    Called when a conversation ends.
    
    Use to update relationships, schedule follow-ups, etc.
    """
    # Update relationship strength
    update_relationship_score(persona, other_agent, conversation_log)
    
    # Check for agreed-upon actions
    commitments = extract_commitments(conversation_log)
    for commitment in commitments:
        schedule_follow_up(persona, commitment)
```

## Integration Examples

### Example 1: Goal Broadcasting System

```python
# In your custom extension module
from persona.cognitive_modules.plan import inject_goals
from persona.cognitive_modules.execute import register_action

# Register the broadcast action
register_action('broadcast_goal', execute_goal_broadcast)

def execute_goal_broadcast(persona, params):
    """Announce a goal to coordinate with other agents."""
    goal = params['goal']
    
    # Store as announced goal
    persona.scratch.announced_goals.append({
        'goal': goal,
        'timestamp': get_current_time()
    })
    
    # Create perceivable event for nearby agents
    create_broadcast_event(persona, f"announced goal: {goal}")
    
    return {'success': True}
```

### Example 2: Social Network Tracking

```python
# Track relationship strengths dynamically
class RelationshipTracker:
    def __init__(self, persona):
        self.persona = persona
        self.relationships = {}
    
    def on_interaction(self, other_agent, interaction_type, sentiment):
        """Update relationship on any interaction."""
        if other_agent not in self.relationships:
            self.relationships[other_agent] = {
                'strength': 0,
                'sentiment': 'neutral',
                'last_interaction': None
            }
        
        rel = self.relationships[other_agent]
        rel['strength'] += get_strength_delta(interaction_type)
        rel['sentiment'] = update_sentiment(rel['sentiment'], sentiment)
        rel['last_interaction'] = get_current_time()
    
    def get_friends(self, threshold=50):
        """Get agents with relationship strength above threshold."""
        return [
            agent for agent, rel in self.relationships.items()
            if rel['strength'] >= threshold
        ]
```

### Example 3: Collaborative Task System

```python
# Enable multi-agent task completion
class CollaborativeTask:
    def __init__(self, task_id, description, required_agents):
        self.task_id = task_id
        self.description = description
        self.required_agents = required_agents
        self.assigned_agents = []
        self.status = 'pending'
    
    def assign_agent(self, agent):
        """Assign an agent to this task."""
        if agent.name in self.required_agents:
            self.assigned_agents.append(agent)
            inject_task_goal(agent, self)
            
            if set(a.name for a in self.assigned_agents) >= set(self.required_agents):
                self.status = 'ready'
                self.notify_all_agents()
    
    def notify_all_agents(self):
        """Notify all assigned agents that the task is ready."""
        for agent in self.assigned_agents:
            create_whisper(
                agent.name,
                f"Task '{self.description}' is ready to start!",
                type='goal'
            )
```

## Best Practices

1. **Minimal Invasive Changes**: Hook into existing extension points rather than modifying core modules directly.

2. **Preserve Agent Autonomy**: Extensions should guide behavior, not fully control it. Let the LLM maintain creative decision-making.

3. **Test Incrementally**: Test each extension in isolation before combining multiple extensions.

4. **Monitor Performance**: LLM calls are expensive. Cache results when possible and batch operations.

5. **Maintain Consistency**: Ensure extensions don't create contradictory behaviors or impossible states.

## File Structure for Extensions

```
persona/
├── cognitive_modules/
│   ├── perceive.py
│   ├── retrieve.py
│   ├── plan.py
│   ├── reflect.py
│   ├── execute.py
│   ├── converse.py
│   └── extensions/           # Your custom extensions
│       ├── __init__.py
│       ├── goal_broadcast.py
│       ├── social_network.py
│       └── collaborative_tasks.py
```

## API Integration

Extensions can interact with the external API via the whisper system:

```python
# External API writes whispers to temp_storage/whispers/
# Extensions can read and process these:

def process_external_commands(persona):
    """Check for and process external commands."""
    whisper_file = f"temp_storage/whispers/{persona.name.replace(' ', '_')}.json"
    
    if os.path.exists(whisper_file):
        with open(whisper_file) as f:
            whispers = json.load(f)
        
        for whisper in whispers:
            if whisper['type'] == 'goal':
                inject_goal(persona, whisper['content'])
            elif whisper['type'] == 'event':
                create_perceived_event(persona, whisper['content'])
        
        # Clear processed whispers
        os.remove(whisper_file)
```

This enables external systems (via the REST API) to influence agent behavior in a controlled way.
