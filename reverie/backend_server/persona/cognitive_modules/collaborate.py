"""
File: collaborate.py
Description: Defines the collaboration and goal sharing module for generative agents.

This module handles:
- Shared goal structures
- Task delegation
- Progress tracking for collaborative objectives
- Sub-task completion and merging
"""
import sys
import datetime
import uuid
import json
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

sys.path.append('../../')

from global_methods import *


class GoalStatus(Enum):
    """Status of a shared goal."""
    PENDING = "pending"         # Not yet started
    IN_PROGRESS = "in_progress" # Currently being worked on
    BLOCKED = "blocked"         # Cannot proceed
    COMPLETED = "completed"     # Successfully completed
    FAILED = "failed"           # Failed to complete
    CANCELLED = "cancelled"     # Cancelled


class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SharedTask:
    """
    A task that can be assigned to one or more agents.
    
    Attributes:
        id: Unique task identifier
        description: What needs to be done
        assigned_to: List of agents assigned to this task
        status: Current status
        priority: Task priority
        parent_goal_id: ID of parent goal
        dependencies: List of task IDs this depends on
        created_at: When task was created
        due_by: Optional deadline
        completed_at: When task was completed
        progress: Progress percentage (0-100)
        notes: Additional notes or updates
    """
    id: str
    description: str
    assigned_to: List[str]
    status: GoalStatus = GoalStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_goal_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: Optional[datetime.datetime] = None
    due_by: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    progress: int = 0
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.datetime.now()
        self.progress = max(0, min(100, self.progress))

    def assign(self, agent_name: str):
        """Assign an agent to this task."""
        if agent_name not in self.assigned_to:
            self.assigned_to.append(agent_name)

    def unassign(self, agent_name: str):
        """Unassign an agent from this task."""
        if agent_name in self.assigned_to:
            self.assigned_to.remove(agent_name)

    def update_progress(self, new_progress: int, note: Optional[str] = None):
        """Update task progress."""
        self.progress = max(0, min(100, new_progress))
        if note:
            self.notes.append(f"[{datetime.datetime.now().strftime('%H:%M')}] {note}")
        if self.progress >= 100 and self.status != GoalStatus.COMPLETED:
            self.complete()

    def start(self):
        """Start working on the task."""
        if self.status == GoalStatus.PENDING:
            self.status = GoalStatus.IN_PROGRESS

    def complete(self):
        """Mark task as completed."""
        self.status = GoalStatus.COMPLETED
        self.progress = 100
        self.completed_at = datetime.datetime.now()

    def fail(self, reason: Optional[str] = None):
        """Mark task as failed."""
        self.status = GoalStatus.FAILED
        if reason:
            self.notes.append(f"Failed: {reason}")

    def block(self, reason: Optional[str] = None):
        """Mark task as blocked."""
        self.status = GoalStatus.BLOCKED
        if reason:
            self.notes.append(f"Blocked: {reason}")

    def can_start(self, completed_task_ids: Set[str]) -> bool:
        """Check if all dependencies are met."""
        return all(dep in completed_task_ids for dep in self.dependencies)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "priority": self.priority.value,
            "parent_goal_id": self.parent_goal_id,
            "dependencies": self.dependencies,
            "created_at": self.created_at.strftime("%B %d, %Y, %H:%M:%S") if self.created_at else None,
            "due_by": self.due_by.strftime("%B %d, %Y, %H:%M:%S") if self.due_by else None,
            "completed_at": self.completed_at.strftime("%B %d, %Y, %H:%M:%S") if self.completed_at else None,
            "progress": self.progress,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SharedTask':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            assigned_to=data["assigned_to"],
            status=GoalStatus(data["status"]),
            priority=TaskPriority(data["priority"]),
            parent_goal_id=data.get("parent_goal_id"),
            dependencies=data.get("dependencies", []),
            created_at=datetime.datetime.strptime(data["created_at"], "%B %d, %Y, %H:%M:%S") if data.get("created_at") else None,
            due_by=datetime.datetime.strptime(data["due_by"], "%B %d, %Y, %H:%M:%S") if data.get("due_by") else None,
            completed_at=datetime.datetime.strptime(data["completed_at"], "%B %d, %Y, %H:%M:%S") if data.get("completed_at") else None,
            progress=data.get("progress", 0),
            notes=data.get("notes", [])
        )


@dataclass
class SharedGoal:
    """
    A shared goal that multiple agents work towards together.
    
    Attributes:
        id: Unique goal identifier
        description: What the goal is
        participants: Agents involved in the goal
        initiator: Who started the goal
        tasks: Subtasks for this goal
        status: Current status
        priority: Goal priority
        created_at: When goal was created
        target_completion: Target completion time
        completed_at: When goal was completed
        outcome: Description of outcome when completed
        shared_context: Information shared among participants
    """
    id: str
    description: str
    participants: List[str]
    initiator: str
    tasks: List[SharedTask] = field(default_factory=list)
    status: GoalStatus = GoalStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: Optional[datetime.datetime] = None
    target_completion: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    outcome: Optional[str] = None
    shared_context: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.datetime.now()

    def add_participant(self, agent_name: str):
        """Add a participant to the goal."""
        if agent_name not in self.participants:
            self.participants.append(agent_name)

    def remove_participant(self, agent_name: str):
        """Remove a participant from the goal."""
        if agent_name in self.participants and agent_name != self.initiator:
            self.participants.remove(agent_name)
            # Unassign from any tasks
            for task in self.tasks:
                task.unassign(agent_name)

    def add_task(self, 
                description: str, 
                assigned_to: List[str] = None,
                priority: TaskPriority = TaskPriority.MEDIUM,
                dependencies: List[str] = None) -> SharedTask:
        """Add a new task to this goal."""
        task = SharedTask(
            id=f"task_{uuid.uuid4().hex[:8]}",
            description=description,
            assigned_to=assigned_to or [],
            priority=priority,
            parent_goal_id=self.id,
            dependencies=dependencies or []
        )
        self.tasks.append(task)
        return task

    def get_task(self, task_id: str) -> Optional[SharedTask]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_tasks_for_agent(self, agent_name: str) -> List[SharedTask]:
        """Get all tasks assigned to an agent."""
        return [t for t in self.tasks if agent_name in t.assigned_to]

    def get_pending_tasks(self) -> List[SharedTask]:
        """Get all pending tasks."""
        return [t for t in self.tasks if t.status == GoalStatus.PENDING]

    def get_in_progress_tasks(self) -> List[SharedTask]:
        """Get all in-progress tasks."""
        return [t for t in self.tasks if t.status == GoalStatus.IN_PROGRESS]

    def get_completed_task_ids(self) -> Set[str]:
        """Get IDs of completed tasks."""
        return {t.id for t in self.tasks if t.status == GoalStatus.COMPLETED}

    def calculate_progress(self) -> int:
        """Calculate overall goal progress based on tasks."""
        if not self.tasks:
            return 0
        total_progress = sum(t.progress for t in self.tasks)
        return total_progress // len(self.tasks)

    def update_status(self):
        """Update goal status based on tasks."""
        if not self.tasks:
            return
            
        all_completed = all(t.status == GoalStatus.COMPLETED for t in self.tasks)
        any_failed = any(t.status == GoalStatus.FAILED for t in self.tasks)
        any_in_progress = any(t.status == GoalStatus.IN_PROGRESS for t in self.tasks)
        
        if all_completed:
            self.status = GoalStatus.COMPLETED
            self.completed_at = datetime.datetime.now()
        elif any_failed:
            self.status = GoalStatus.FAILED
        elif any_in_progress:
            self.status = GoalStatus.IN_PROGRESS
        else:
            self.status = GoalStatus.PENDING

    def start(self):
        """Start working on the goal."""
        if self.status == GoalStatus.PENDING:
            self.status = GoalStatus.IN_PROGRESS
            # Start any tasks without dependencies
            completed_ids = self.get_completed_task_ids()
            for task in self.tasks:
                if task.status == GoalStatus.PENDING and task.can_start(completed_ids):
                    task.start()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "participants": self.participants,
            "initiator": self.initiator,
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.strftime("%B %d, %Y, %H:%M:%S") if self.created_at else None,
            "target_completion": self.target_completion.strftime("%B %d, %Y, %H:%M:%S") if self.target_completion else None,
            "completed_at": self.completed_at.strftime("%B %d, %Y, %H:%M:%S") if self.completed_at else None,
            "outcome": self.outcome,
            "shared_context": self.shared_context
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SharedGoal':
        """Create from dictionary."""
        goal = cls(
            id=data["id"],
            description=data["description"],
            participants=data["participants"],
            initiator=data["initiator"],
            status=GoalStatus(data["status"]),
            priority=TaskPriority(data["priority"]),
            created_at=datetime.datetime.strptime(data["created_at"], "%B %d, %Y, %H:%M:%S") if data.get("created_at") else None,
            target_completion=datetime.datetime.strptime(data["target_completion"], "%B %d, %Y, %H:%M:%S") if data.get("target_completion") else None,
            completed_at=datetime.datetime.strptime(data["completed_at"], "%B %d, %Y, %H:%M:%S") if data.get("completed_at") else None,
            outcome=data.get("outcome"),
            shared_context=data.get("shared_context", {})
        )
        goal.tasks = [SharedTask.from_dict(t) for t in data.get("tasks", [])]
        return goal


class CollaborationManager:
    """
    Manages collaborative goals and tasks across agents.
    
    This class handles:
    - Creating and tracking shared goals
    - Task assignment and delegation
    - Progress monitoring
    - Coordination between collaborating agents
    """
    
    def __init__(self):
        self.goals: Dict[str, SharedGoal] = {}
        self.agent_goals: Dict[str, Set[str]] = {}  # agent -> set of goal IDs
        
    def generate_goal_id(self) -> str:
        """Generate a unique goal ID."""
        return f"goal_{uuid.uuid4().hex[:8]}"

    def create_goal(self,
                   description: str,
                   initiator: str,
                   participants: List[str] = None,
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   target_completion: Optional[datetime.datetime] = None) -> SharedGoal:
        """
        Create a new shared goal.
        
        Args:
            description: What the goal is
            initiator: Who is starting the goal
            participants: Initial participants (includes initiator)
            priority: Goal priority
            target_completion: Optional target completion time
            
        Returns:
            The created SharedGoal
        """
        goal_id = self.generate_goal_id()
        
        if participants is None:
            participants = [initiator]
        elif initiator not in participants:
            participants = [initiator] + participants
            
        goal = SharedGoal(
            id=goal_id,
            description=description,
            participants=participants,
            initiator=initiator,
            priority=priority,
            target_completion=target_completion
        )
        
        self.goals[goal_id] = goal
        
        # Update agent-to-goal mapping
        for participant in participants:
            if participant not in self.agent_goals:
                self.agent_goals[participant] = set()
            self.agent_goals[participant].add(goal_id)
            
        return goal

    def get_goal(self, goal_id: str) -> Optional[SharedGoal]:
        """Get a goal by ID."""
        return self.goals.get(goal_id)

    def get_agent_goals(self, agent_name: str) -> List[SharedGoal]:
        """Get all goals an agent is participating in."""
        goal_ids = self.agent_goals.get(agent_name, set())
        return [self.goals[gid] for gid in goal_ids if gid in self.goals]

    def get_agent_active_goals(self, agent_name: str) -> List[SharedGoal]:
        """Get active (not completed/failed/cancelled) goals for an agent."""
        return [g for g in self.get_agent_goals(agent_name) 
                if g.status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS, GoalStatus.BLOCKED]]

    def get_agent_pending_tasks(self, agent_name: str) -> List[Tuple[SharedGoal, SharedTask]]:
        """Get all pending tasks for an agent across all goals."""
        pending = []
        for goal in self.get_agent_active_goals(agent_name):
            for task in goal.get_tasks_for_agent(agent_name):
                if task.status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]:
                    pending.append((goal, task))
        return pending

    def add_participant(self, goal_id: str, agent_name: str) -> bool:
        """Add a participant to a goal."""
        goal = self.get_goal(goal_id)
        if not goal:
            return False
            
        goal.add_participant(agent_name)
        
        if agent_name not in self.agent_goals:
            self.agent_goals[agent_name] = set()
        self.agent_goals[agent_name].add(goal_id)
        
        return True

    def remove_participant(self, goal_id: str, agent_name: str) -> bool:
        """Remove a participant from a goal."""
        goal = self.get_goal(goal_id)
        if not goal:
            return False
            
        goal.remove_participant(agent_name)
        
        if agent_name in self.agent_goals:
            self.agent_goals[agent_name].discard(goal_id)
            
        return True

    def delegate_task(self,
                     goal_id: str,
                     task_description: str,
                     from_agent: str,
                     to_agents: List[str],
                     priority: TaskPriority = TaskPriority.MEDIUM,
                     dependencies: List[str] = None) -> Optional[SharedTask]:
        """
        Delegate a task from one agent to others.
        
        Args:
            goal_id: The goal this task belongs to
            task_description: What needs to be done
            from_agent: Who is delegating
            to_agents: Who will do the task
            priority: Task priority
            dependencies: Task dependencies
            
        Returns:
            The created task, or None if goal not found
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return None
            
        task = goal.add_task(
            description=task_description,
            assigned_to=to_agents,
            priority=priority,
            dependencies=dependencies
        )
        task.notes.append(f"Delegated by {from_agent}")
        
        return task

    def update_task_progress(self,
                            goal_id: str,
                            task_id: str,
                            agent_name: str,
                            progress: int,
                            note: Optional[str] = None) -> bool:
        """
        Update progress on a task.
        
        Args:
            goal_id: The goal ID
            task_id: The task ID
            agent_name: Who is reporting
            progress: New progress percentage
            note: Optional progress note
            
        Returns:
            True if updated successfully
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return False
            
        task = goal.get_task(task_id)
        if not task or agent_name not in task.assigned_to:
            return False
            
        full_note = f"{agent_name}: {note}" if note else None
        task.update_progress(progress, full_note)
        goal.update_status()
        
        return True

    def complete_task(self, goal_id: str, task_id: str, agent_name: str) -> bool:
        """Complete a task."""
        return self.update_task_progress(goal_id, task_id, agent_name, 100)

    def get_coordination_summary(self, goal_id: str) -> Dict:
        """
        Get a summary of coordination status for a goal.
        
        Returns dictionary with:
        - Overall progress
        - Task breakdown by status
        - Per-agent progress
        - Blockers
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return {}
            
        # Count tasks by status
        status_counts = {s.value: 0 for s in GoalStatus}
        for task in goal.tasks:
            status_counts[task.status.value] += 1
            
        # Calculate per-agent progress
        agent_progress = {}
        for participant in goal.participants:
            tasks = goal.get_tasks_for_agent(participant)
            if tasks:
                agent_progress[participant] = sum(t.progress for t in tasks) // len(tasks)
            else:
                agent_progress[participant] = 0
                
        # Find blockers
        blockers = [
            {"task_id": t.id, "description": t.description, "notes": t.notes[-1] if t.notes else None}
            for t in goal.tasks if t.status == GoalStatus.BLOCKED
        ]
        
        return {
            "goal_id": goal_id,
            "description": goal.description,
            "overall_progress": goal.calculate_progress(),
            "status": goal.status.value,
            "task_counts": status_counts,
            "agent_progress": agent_progress,
            "blockers": blockers,
            "participants": goal.participants
        }

    def find_collaboration_opportunities(self,
                                        agent_name: str,
                                        agent_skills: List[str],
                                        agent_interests: List[str]) -> List[Dict]:
        """
        Find potential collaboration opportunities for an agent.
        
        Based on:
        - Goals that need help
        - Matching skills/interests
        - Agent's availability
        
        Args:
            agent_name: The agent looking for collaborations
            agent_skills: What the agent can do
            agent_interests: What the agent is interested in
            
        Returns:
            List of opportunities with relevance scores
        """
        opportunities = []
        
        for goal in self.goals.values():
            # Skip if already participating
            if agent_name in goal.participants:
                continue
                
            # Skip completed/failed goals
            if goal.status in [GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.CANCELLED]:
                continue
                
            # Calculate relevance
            relevance = 0.0
            matching_factors = []
            
            # Check skill match
            desc_lower = goal.description.lower()
            for skill in agent_skills:
                if skill.lower() in desc_lower:
                    relevance += 0.3
                    matching_factors.append(f"skill: {skill}")
                    
            # Check interest match
            for interest in agent_interests:
                if interest.lower() in desc_lower:
                    relevance += 0.2
                    matching_factors.append(f"interest: {interest}")
                    
            # Bonus for goals that need help (many pending tasks)
            pending_count = len(goal.get_pending_tasks())
            if pending_count > 0:
                relevance += 0.1 * min(pending_count, 5)
                matching_factors.append(f"{pending_count} tasks need help")
                
            if relevance > 0:
                opportunities.append({
                    "goal": goal,
                    "relevance": relevance,
                    "matching_factors": matching_factors,
                    "current_participants": goal.participants,
                    "pending_tasks": pending_count
                })
                
        # Sort by relevance
        opportunities.sort(key=lambda x: x["relevance"], reverse=True)
        
        return opportunities[:5]  # Return top 5

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "goals": {gid: g.to_dict() for gid, g in self.goals.items()},
            "agent_goals": {k: list(v) for k, v in self.agent_goals.items()}
        }

    def load_from_dict(self, data: Dict):
        """Load from dictionary."""
        self.goals = {}
        self.agent_goals = {}
        
        for gid, gdata in data.get("goals", {}).items():
            self.goals[gid] = SharedGoal.from_dict(gdata)
            
        for agent, goal_ids in data.get("agent_goals", {}).items():
            self.agent_goals[agent] = set(goal_ids)

    def save(self, filepath: str):
        """Save to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def load(self, filepath: str):
        """Load from JSON file."""
        if check_if_file_exists(filepath):
            with open(filepath) as f:
                self.load_from_dict(json.load(f))


# Global collaboration manager instance
_collaboration_manager = None

def get_collaboration_manager() -> CollaborationManager:
    """Get or create the global CollaborationManager instance."""
    global _collaboration_manager
    if _collaboration_manager is None:
        _collaboration_manager = CollaborationManager()
    return _collaboration_manager

def reset_collaboration_manager():
    """Reset the global CollaborationManager."""
    global _collaboration_manager
    _collaboration_manager = CollaborationManager()


def generate_collaboration_proposal(persona, 
                                   target_name: str,
                                   goal_description: str,
                                   context: str) -> Dict:
    """
    Generate a collaboration proposal for conversation.
    
    Args:
        persona: The persona proposing
        target_name: Who they're proposing to
        goal_description: What they want to achieve
        context: Current context
        
    Returns:
        Dictionary with proposal details
    """
    return {
        "proposer": persona.scratch.name,
        "target": target_name,
        "goal": goal_description,
        "context": context,
        "proposed_tasks": [],
        "proposed_timeline": None,
        "requires_response": True
    }


def evaluate_collaboration_proposal(persona, proposal: Dict) -> Dict:
    """
    Evaluate a collaboration proposal from another agent.
    
    Args:
        persona: The persona evaluating
        proposal: The proposal to evaluate
        
    Returns:
        Dictionary with evaluation results
    """
    # Check alignment with persona's goals
    currently = persona.scratch.currently.lower() if persona.scratch.currently else ""
    goal_lower = proposal["goal"].lower()
    
    # Simple interest alignment check
    interest_alignment = 0.5  # Base neutral
    
    # Check for overlapping keywords
    current_words = set(currently.split())
    goal_words = set(goal_lower.split())
    overlap = current_words.intersection(goal_words)
    if overlap:
        interest_alignment += 0.1 * len(overlap)
        
    # Check schedule availability (simplified)
    has_time = True  # Would check actual schedule
    
    return {
        "interest_alignment": min(1.0, interest_alignment),
        "has_time": has_time,
        "recommendation": "accept" if interest_alignment > 0.4 and has_time else "decline",
        "reasoning": f"Interest alignment: {interest_alignment:.2f}, Schedule available: {has_time}"
    }
