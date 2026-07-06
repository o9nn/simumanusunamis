"""
File: group_dynamics.py
Description: Defines the group dynamics module for generative agents.

This module handles:
- Group detection and formation
- Group state management
- Role emergence within groups
- Group behavior coordination
"""
import sys
import datetime
import uuid
import math
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

sys.path.append('../../')

from global_methods import *


class GroupPurpose(Enum):
    """Types of group formations."""
    CASUAL = "casual"           # Spontaneous gathering
    MEETING = "meeting"         # Formal meeting
    EVENT = "event"             # Scheduled event
    COLLABORATION = "collaboration"  # Working together
    SOCIAL = "social"           # Social gathering (party, dinner)


class GroupRole(Enum):
    """Roles that emerge in group dynamics."""
    LEADER = "leader"           # Drives decisions
    FACILITATOR = "facilitator" # Keeps conversation flowing
    CONTRIBUTOR = "contributor" # Active participant
    OBSERVER = "observer"       # Passive participant
    HARMONIZER = "harmonizer"   # Resolves conflicts


@dataclass
class Group:
    """
    Represents an active group of agents.
    
    Attributes:
        id: Unique identifier for the group
        members: List of agent names in the group
        purpose: Why the group formed
        location: Current tile location of the group
        leader: Optional leader of the group
        created_at: When the group was formed
        conversation_log: History of group conversation
        shared_context: Shared information among group members
        roles: Mapping of member names to their roles
        is_active: Whether the group is still active
    """
    id: str
    members: List[str]
    purpose: GroupPurpose
    location: Tuple[int, int]
    created_at: datetime.datetime
    leader: Optional[str] = None
    conversation_log: List[Tuple[str, str]] = field(default_factory=list)
    shared_context: Dict = field(default_factory=dict)
    roles: Dict[str, GroupRole] = field(default_factory=dict)
    is_active: bool = True
    last_activity: datetime.datetime = None
    
    def __post_init__(self):
        if self.last_activity is None:
            self.last_activity = self.created_at
        # Initialize default roles for all members
        for member in self.members:
            if member not in self.roles:
                if member == self.leader:
                    self.roles[member] = GroupRole.LEADER
                else:
                    self.roles[member] = GroupRole.CONTRIBUTOR

    def add_member(self, member_name: str, role: GroupRole = GroupRole.CONTRIBUTOR):
        """Add a new member to the group."""
        if member_name not in self.members:
            self.members.append(member_name)
            self.roles[member_name] = role
            self.last_activity = datetime.datetime.now()

    def remove_member(self, member_name: str):
        """Remove a member from the group."""
        if member_name in self.members:
            self.members.remove(member_name)
            self.roles.pop(member_name, None)
            self.last_activity = datetime.datetime.now()
            
            # If the leader left, assign a new one
            if member_name == self.leader and self.members:
                self.leader = self.members[0]
                self.roles[self.leader] = GroupRole.LEADER
            
            # Disband if fewer than 2 members
            if len(self.members) < 2:
                self.is_active = False

    def add_utterance(self, speaker: str, utterance: str):
        """Add a conversation utterance to the group log."""
        self.conversation_log.append((speaker, utterance))
        self.last_activity = datetime.datetime.now()

    def get_member_count(self) -> int:
        """Return the number of members in the group."""
        return len(self.members)

    def get_conversation_summary(self, last_n: int = 5) -> str:
        """Get a summary of recent conversation."""
        recent = self.conversation_log[-last_n:]
        return "\n".join([f"{speaker}: {utt}" for speaker, utt in recent])

    def to_dict(self) -> Dict:
        """Convert group to dictionary for serialization."""
        return {
            "id": self.id,
            "members": self.members,
            "purpose": self.purpose.value,
            "location": self.location,
            "leader": self.leader,
            "created_at": self.created_at.strftime("%B %d, %Y, %H:%M:%S"),
            "conversation_log": self.conversation_log,
            "shared_context": self.shared_context,
            "roles": {k: v.value for k, v in self.roles.items()},
            "is_active": self.is_active,
            "last_activity": self.last_activity.strftime("%B %d, %Y, %H:%M:%S") if self.last_activity else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Group':
        """Create a Group from dictionary data."""
        return cls(
            id=data["id"],
            members=data["members"],
            purpose=GroupPurpose(data["purpose"]),
            location=tuple(data["location"]),
            created_at=datetime.datetime.strptime(data["created_at"], "%B %d, %Y, %H:%M:%S"),
            leader=data.get("leader"),
            conversation_log=[(t[0], t[1]) for t in data.get("conversation_log", [])],
            shared_context=data.get("shared_context", {}),
            roles={k: GroupRole(v) for k, v in data.get("roles", {}).items()},
            is_active=data.get("is_active", True),
            last_activity=datetime.datetime.strptime(data["last_activity"], "%B %d, %Y, %H:%M:%S") if data.get("last_activity") else None
        )


class GroupManager:
    """
    Manages all active groups in the simulation.
    
    This class handles:
    - Group creation and dissolution
    - Group detection based on agent proximity
    - Group state tracking
    - Coordination between groups and individual agents
    """
    
    # Minimum number of agents to form a group
    MIN_GROUP_SIZE = 3
    
    # Maximum distance (in tiles) for agents to be considered part of the same cluster
    CLUSTER_RADIUS = 2
    
    # Time after which an inactive group is disbanded (in minutes)
    INACTIVITY_TIMEOUT = 30
    
    def __init__(self):
        self.groups: Dict[str, Group] = {}
        self.agent_to_group: Dict[str, str] = {}  # Maps agent name to group id
        
    def generate_group_id(self) -> str:
        """Generate a unique group ID."""
        return f"group_{uuid.uuid4().hex[:8]}"

    def create_group(self, 
                     members: List[str], 
                     location: Tuple[int, int],
                     purpose: GroupPurpose = GroupPurpose.CASUAL,
                     leader: Optional[str] = None,
                     curr_time: Optional[datetime.datetime] = None) -> Group:
        """
        Create a new group with the given members.
        
        Args:
            members: List of agent names to include in the group
            location: The tile location where the group forms
            purpose: The purpose of the group formation
            leader: Optional designated leader
            curr_time: Current simulation time
            
        Returns:
            The newly created Group instance
        """
        group_id = self.generate_group_id()
        
        if curr_time is None:
            curr_time = datetime.datetime.now()
            
        # If no leader specified, pick the first member
        if leader is None and members:
            leader = members[0]
        
        group = Group(
            id=group_id,
            members=members.copy(),
            purpose=purpose,
            location=location,
            created_at=curr_time,
            leader=leader
        )
        
        self.groups[group_id] = group
        
        # Update agent-to-group mapping
        for member in members:
            self.agent_to_group[member] = group_id
            
        return group

    def disband_group(self, group_id: str):
        """
        Disband a group and clean up references.
        
        Args:
            group_id: The ID of the group to disband
        """
        if group_id in self.groups:
            group = self.groups[group_id]
            group.is_active = False
            
            # Remove agent-to-group mappings
            for member in group.members:
                if self.agent_to_group.get(member) == group_id:
                    del self.agent_to_group[member]
                    
            del self.groups[group_id]

    def get_agent_group(self, agent_name: str) -> Optional[Group]:
        """
        Get the group that an agent belongs to.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            The Group instance if the agent is in a group, None otherwise
        """
        group_id = self.agent_to_group.get(agent_name)
        if group_id and group_id in self.groups:
            return self.groups[group_id]
        return None

    def is_agent_in_group(self, agent_name: str) -> bool:
        """Check if an agent is currently in a group."""
        return agent_name in self.agent_to_group

    def detect_agent_clusters(self, 
                              personas_tiles: Dict[str, Tuple[int, int]],
                              vision_r: int = None) -> List[Set[str]]:
        """
        Detect clusters of agents that could form groups.
        
        Uses proximity-based clustering to identify agents that are
        close enough to potentially form groups.
        
        Args:
            personas_tiles: Dictionary mapping agent names to their tile positions
            vision_r: Override the cluster radius if provided
            
        Returns:
            List of sets, where each set contains agent names in a cluster
        """
        radius = vision_r if vision_r is not None else self.CLUSTER_RADIUS
        clusters = []
        assigned = set()
        
        agent_names = list(personas_tiles.keys())
        
        for i, agent_a in enumerate(agent_names):
            if agent_a in assigned:
                continue
                
            pos_a = personas_tiles[agent_a]
            cluster = {agent_a}
            
            for agent_b in agent_names[i+1:]:
                if agent_b in assigned:
                    continue
                    
                pos_b = personas_tiles[agent_b]
                distance = math.dist(pos_a, pos_b)
                
                if distance <= radius:
                    cluster.add(agent_b)
                    
            # Only consider as a cluster if it has minimum size
            if len(cluster) >= self.MIN_GROUP_SIZE:
                clusters.append(cluster)
                assigned.update(cluster)
                
        return clusters

    def update_from_agent_positions(self, 
                                    personas_tiles: Dict[str, Tuple[int, int]],
                                    curr_time: datetime.datetime,
                                    personas: Dict = None) -> List[Group]:
        """
        Update groups based on current agent positions.
        
        This method:
        1. Detects new potential groups from clusters
        2. Updates existing groups (members who left, etc.)
        3. Creates new groups when appropriate
        4. Disbands groups that are no longer valid
        
        Args:
            personas_tiles: Dictionary mapping agent names to their positions
            curr_time: Current simulation time
            personas: Dictionary of Persona objects (optional, for personality-based leadership)
            
        Returns:
            List of newly formed groups
        """
        new_groups = []
        
        # First, check existing groups for disbanded members
        groups_to_disband = []
        for group_id, group in self.groups.items():
            # Remove members who have moved away
            members_to_remove = []
            group_center = group.location
            
            for member in group.members:
                if member not in personas_tiles:
                    members_to_remove.append(member)
                    continue
                    
                member_pos = personas_tiles[member]
                distance = math.dist(group_center, member_pos)
                
                if distance > self.CLUSTER_RADIUS * 2:  # Allow some margin
                    members_to_remove.append(member)
                    
            for member in members_to_remove:
                group.remove_member(member)
                if member in self.agent_to_group:
                    del self.agent_to_group[member]
                    
            # Check if group should be disbanded
            if len(group.members) < 2:
                groups_to_disband.append(group_id)
            # Check for inactivity timeout
            elif (curr_time - group.last_activity).total_seconds() / 60 > self.INACTIVITY_TIMEOUT:
                groups_to_disband.append(group_id)
                
        # Disband invalid groups
        for group_id in groups_to_disband:
            self.disband_group(group_id)
            
        # Detect new clusters from agents not in groups
        ungrouped_agents = {
            name: pos for name, pos in personas_tiles.items()
            if not self.is_agent_in_group(name)
        }
        
        clusters = self.detect_agent_clusters(ungrouped_agents)
        
        # Create new groups from valid clusters
        for cluster in clusters:
            cluster_list = list(cluster)
            
            # Calculate cluster center
            positions = [ungrouped_agents[agent] for agent in cluster_list]
            center_x = sum(p[0] for p in positions) // len(positions)
            center_y = sum(p[1] for p in positions) // len(positions)
            
            # Determine leader (could be enhanced with personality traits)
            leader = cluster_list[0]
            if personas:
                # Choose leader based on some traits (e.g., extraversion)
                for agent in cluster_list:
                    if agent in personas:
                        # Simple heuristic: first agent with specific traits
                        if "outgoing" in personas[agent].scratch.innate.lower():
                            leader = agent
                            break
            
            group = self.create_group(
                members=cluster_list,
                location=(center_x, center_y),
                purpose=GroupPurpose.CASUAL,
                leader=leader,
                curr_time=curr_time
            )
            new_groups.append(group)
            
        return new_groups

    def get_nearby_groups(self, 
                          location: Tuple[int, int], 
                          radius: int) -> List[Group]:
        """
        Get all groups within a certain radius of a location.
        
        Args:
            location: The center point to search from
            radius: The search radius
            
        Returns:
            List of groups within the radius
        """
        nearby = []
        for group in self.groups.values():
            if group.is_active:
                distance = math.dist(location, group.location)
                if distance <= radius:
                    nearby.append(group)
        return nearby

    def join_group(self, 
                   agent_name: str, 
                   group_id: str, 
                   role: GroupRole = GroupRole.CONTRIBUTOR) -> bool:
        """
        Add an agent to an existing group.
        
        Args:
            agent_name: Name of the agent joining
            group_id: ID of the group to join
            role: The role the agent will take
            
        Returns:
            True if successful, False otherwise
        """
        if group_id not in self.groups:
            return False
            
        # Leave current group if in one
        current_group = self.get_agent_group(agent_name)
        if current_group:
            current_group.remove_member(agent_name)
            
        group = self.groups[group_id]
        group.add_member(agent_name, role)
        self.agent_to_group[agent_name] = group_id
        
        return True

    def leave_group(self, agent_name: str) -> bool:
        """
        Remove an agent from their current group.
        
        Args:
            agent_name: Name of the agent leaving
            
        Returns:
            True if successful, False if agent wasn't in a group
        """
        group = self.get_agent_group(agent_name)
        if not group:
            return False
            
        group.remove_member(agent_name)
        if agent_name in self.agent_to_group:
            del self.agent_to_group[agent_name]
            
        return True

    def get_all_active_groups(self) -> List[Group]:
        """Get all currently active groups."""
        return [g for g in self.groups.values() if g.is_active]

    def get_group_by_id(self, group_id: str) -> Optional[Group]:
        """Get a specific group by its ID."""
        return self.groups.get(group_id)

    def to_dict(self) -> Dict:
        """Serialize all groups to a dictionary."""
        return {
            "groups": {gid: g.to_dict() for gid, g in self.groups.items()},
            "agent_to_group": self.agent_to_group.copy()
        }

    def load_from_dict(self, data: Dict):
        """Load groups from a dictionary."""
        self.groups = {}
        self.agent_to_group = data.get("agent_to_group", {}).copy()
        
        for gid, gdata in data.get("groups", {}).items():
            self.groups[gid] = Group.from_dict(gdata)


def detect_group_context(persona, maze, personas, personas_tiles):
    """
    Detect the group context around a persona.
    
    This function analyzes the persona's surroundings to identify:
    - Nearby agents
    - Potential group formations
    - Whether the persona should join/form a group
    
    Args:
        persona: The current Persona instance
        maze: The current Maze instance
        personas: Dictionary of all personas
        personas_tiles: Dictionary mapping persona names to positions
        
    Returns:
        Dictionary containing group context information
    """
    context = {
        "nearby_agents": [],
        "potential_group_members": [],
        "in_group_area": False,
        "group_conversation_opportunity": False
    }
    
    curr_tile = persona.scratch.curr_tile
    vision_r = persona.scratch.vision_r
    
    # Find nearby agents
    for name, pos in personas_tiles.items():
        if name == persona.scratch.name:
            continue
            
        distance = math.dist(curr_tile, pos)
        if distance <= vision_r:
            context["nearby_agents"].append({
                "name": name,
                "position": pos,
                "distance": distance
            })
    
    # Sort by distance
    context["nearby_agents"].sort(key=lambda x: x["distance"])
    
    # Check for potential group (3+ nearby agents including self)
    close_agents = [a for a in context["nearby_agents"] if a["distance"] <= 2]
    if len(close_agents) >= 2:  # 2 nearby + self = 3+ for a group
        context["potential_group_members"] = [a["name"] for a in close_agents]
        context["group_conversation_opportunity"] = True
        
    return context


def select_next_speaker(group: Group, 
                        personas: Dict, 
                        curr_chat: List[Tuple[str, str]],
                        last_speaker: Optional[str] = None) -> str:
    """
    Select the next speaker in a group conversation.
    
    Uses a combination of:
    - Role-based priority (leaders speak more)
    - Conversation context (who hasn't spoken recently)
    - Random variation
    
    Args:
        group: The current group
        personas: Dictionary of persona objects
        curr_chat: The current conversation log
        last_speaker: The last person who spoke
        
    Returns:
        Name of the next speaker
    """
    import random
    
    members = [m for m in group.members if m != last_speaker]
    if not members:
        members = group.members.copy()
        
    # Count recent utterances per member
    recent_speakers = {}
    for speaker, _ in curr_chat[-6:]:  # Look at last 6 utterances
        recent_speakers[speaker] = recent_speakers.get(speaker, 0) + 1
        
    # Weight members inversely by recent speaking frequency
    weights = []
    for member in members:
        recent_count = recent_speakers.get(member, 0)
        role = group.roles.get(member, GroupRole.CONTRIBUTOR)
        
        # Base weight
        weight = 1.0
        
        # Reduce weight for frequent recent speakers
        weight *= 1.0 / (1 + recent_count)
        
        # Boost weight for leader/facilitator roles
        if role == GroupRole.LEADER:
            weight *= 1.5
        elif role == GroupRole.FACILITATOR:
            weight *= 1.3
        elif role == GroupRole.OBSERVER:
            weight *= 0.5
            
        weights.append(weight)
        
    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]
    
    # Select based on weights
    return random.choices(members, weights=weights, k=1)[0]


def determine_group_role(persona, group: Group, personas: Dict) -> GroupRole:
    """
    Determine the appropriate role for a persona in a group.
    
    Based on personality traits and group composition.
    
    Args:
        persona: The persona to assign a role to
        group: The group context
        personas: Dictionary of all personas
        
    Returns:
        The appropriate GroupRole
    """
    innate = persona.scratch.innate.lower() if persona.scratch.innate else ""
    
    # Check for leadership traits
    leadership_traits = ["outgoing", "confident", "assertive", "leader"]
    has_leadership = any(trait in innate for trait in leadership_traits)
    
    # Check for facilitator traits
    facilitator_traits = ["friendly", "social", "communicative", "empathetic"]
    has_facilitator = any(trait in innate for trait in facilitator_traits)
    
    # Check for harmonizer traits
    harmonizer_traits = ["peaceful", "calm", "diplomatic", "understanding"]
    has_harmonizer = any(trait in innate for trait in harmonizer_traits)
    
    # Check current role distribution in group
    current_roles = list(group.roles.values())
    has_leader = GroupRole.LEADER in current_roles
    has_facilitator = GroupRole.FACILITATOR in current_roles
    
    # Assign role based on traits and group needs
    if has_leadership and not has_leader:
        return GroupRole.LEADER
    elif has_facilitator and not has_facilitator:
        return GroupRole.FACILITATOR
    elif has_harmonizer:
        return GroupRole.HARMONIZER
    else:
        return GroupRole.CONTRIBUTOR


# Global group manager instance
_group_manager = None

def get_group_manager() -> GroupManager:
    """Get or create the global GroupManager instance."""
    global _group_manager
    if _group_manager is None:
        _group_manager = GroupManager()
    return _group_manager

def reset_group_manager():
    """Reset the global GroupManager (useful for testing)."""
    global _group_manager
    _group_manager = GroupManager()
