"""
File: social_network.py
Description: Defines the social network and relationship tracking for generative agents.

This module handles:
- Relationship tracking between agents
- Relationship strength scoring
- Relationship type classification
- Social influence modeling
"""
import sys
import datetime
import json
import math
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

sys.path.append('../../')

from global_methods import *


class RelationshipType(Enum):
    """Types of relationships between agents."""
    STRANGER = "stranger"           # No prior interaction
    ACQUAINTANCE = "acquaintance"   # Some familiarity
    FRIEND = "friend"               # Positive relationship
    CLOSE_FRIEND = "close_friend"   # Strong friendship
    COLLEAGUE = "colleague"         # Work relationship
    FAMILY = "family"               # Family member
    ROMANTIC = "romantic"           # Romantic relationship
    RIVAL = "rival"                 # Competitive relationship


@dataclass
class Relationship:
    """
    Represents a relationship between two agents.
    
    Attributes:
        agent_a: First agent's name
        agent_b: Second agent's name
        type: The type of relationship
        strength: Relationship strength (0.0 to 1.0)
        sentiment: Overall sentiment (-1.0 to 1.0)
        last_interaction: When they last interacted
        interaction_count: Total number of interactions
        shared_memories: Node IDs of shared memories
        relationship_history: List of relationship changes
        trust_level: How much they trust each other (0.0 to 1.0)
    """
    agent_a: str
    agent_b: str
    type: RelationshipType = RelationshipType.STRANGER
    strength: float = 0.0
    sentiment: float = 0.0
    last_interaction: Optional[datetime.datetime] = None
    interaction_count: int = 0
    shared_memories: List[str] = field(default_factory=list)
    relationship_history: List[Dict] = field(default_factory=list)
    trust_level: float = 0.5
    
    def __post_init__(self):
        # Ensure strength and sentiment are in valid ranges
        self.strength = max(0.0, min(1.0, self.strength))
        self.sentiment = max(-1.0, min(1.0, self.sentiment))
        self.trust_level = max(0.0, min(1.0, self.trust_level))

    def update_interaction(self, 
                          interaction_type: str,
                          sentiment_delta: float,
                          curr_time: datetime.datetime,
                          memory_node_id: Optional[str] = None):
        """
        Update the relationship after an interaction.
        
        Args:
            interaction_type: Type of interaction (e.g., "chat", "cooperation", "conflict")
            sentiment_delta: Change in sentiment from this interaction
            curr_time: Current time
            memory_node_id: Optional memory node to associate
        """
        self.last_interaction = curr_time
        self.interaction_count += 1
        
        # Update sentiment with decay towards neutral
        self.sentiment = self.sentiment * 0.9 + sentiment_delta * 0.1
        self.sentiment = max(-1.0, min(1.0, self.sentiment))
        
        # Update strength based on interaction frequency
        strength_gain = 0.05  # Base gain per interaction
        if interaction_type == "cooperation":
            strength_gain = 0.1
        elif interaction_type == "conflict":
            strength_gain = -0.05
        elif interaction_type == "chat":
            strength_gain = 0.03
            
        self.strength = max(0.0, min(1.0, self.strength + strength_gain))
        
        # Update trust based on interaction type
        if interaction_type == "cooperation":
            self.trust_level = min(1.0, self.trust_level + 0.05)
        elif interaction_type == "conflict":
            self.trust_level = max(0.0, self.trust_level - 0.1)
        elif interaction_type == "chat":
            self.trust_level = min(1.0, self.trust_level + 0.01)
        
        # Add memory reference
        if memory_node_id:
            self.shared_memories.append(memory_node_id)
            
        # Log to history
        self.relationship_history.append({
            "time": curr_time.strftime("%B %d, %Y, %H:%M:%S"),
            "type": interaction_type,
            "sentiment_delta": sentiment_delta,
            "new_strength": self.strength,
            "new_sentiment": self.sentiment
        })
        
        # Auto-update relationship type based on strength and sentiment
        self._update_type()

    def _update_type(self):
        """Update relationship type based on current metrics."""
        if self.interaction_count == 0:
            self.type = RelationshipType.STRANGER
        elif self.strength < 0.2:
            self.type = RelationshipType.ACQUAINTANCE
        elif self.strength < 0.5:
            if self.sentiment >= 0:
                self.type = RelationshipType.FRIEND
            else:
                self.type = RelationshipType.RIVAL
        elif self.strength < 0.8:
            if self.sentiment >= 0.3:
                self.type = RelationshipType.CLOSE_FRIEND
            elif self.sentiment >= 0:
                self.type = RelationshipType.FRIEND
            else:
                self.type = RelationshipType.RIVAL
        else:
            if self.sentiment >= 0.5:
                self.type = RelationshipType.CLOSE_FRIEND
            else:
                self.type = RelationshipType.FRIEND

    def get_influence_weight(self) -> float:
        """
        Calculate how much influence one agent has on the other.
        
        Based on relationship strength, trust, and sentiment.
        
        Returns:
            Float representing influence weight (0.0 to 1.0)
        """
        # Base influence from strength
        influence = self.strength * 0.5
        
        # Trust contribution
        influence += self.trust_level * 0.3
        
        # Sentiment contribution (positive relationships have more influence)
        if self.sentiment > 0:
            influence += self.sentiment * 0.2
        else:
            influence += abs(self.sentiment) * 0.1  # Negative sentiment has less influence
            
        return max(0.0, min(1.0, influence))

    def apply_decay(self, curr_time: datetime.datetime, decay_rate: float = 0.001):
        """
        Apply time-based decay to the relationship.
        
        Relationships that aren't maintained will weaken over time.
        
        Args:
            curr_time: Current time
            decay_rate: Rate of decay per day
        """
        if self.last_interaction:
            days_since = (curr_time - self.last_interaction).days
            decay = decay_rate * days_since
            self.strength = max(0.0, self.strength - decay)
            # Sentiment decays towards neutral
            self.sentiment *= (1 - decay * 0.5)

    def to_dict(self) -> Dict:
        """Convert relationship to dictionary for serialization."""
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "type": self.type.value,
            "strength": self.strength,
            "sentiment": self.sentiment,
            "last_interaction": self.last_interaction.strftime("%B %d, %Y, %H:%M:%S") if self.last_interaction else None,
            "interaction_count": self.interaction_count,
            "shared_memories": self.shared_memories,
            "relationship_history": self.relationship_history[-10:],  # Keep last 10 entries
            "trust_level": self.trust_level
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Relationship':
        """Create a Relationship from dictionary data."""
        return cls(
            agent_a=data["agent_a"],
            agent_b=data["agent_b"],
            type=RelationshipType(data["type"]),
            strength=data["strength"],
            sentiment=data["sentiment"],
            last_interaction=datetime.datetime.strptime(data["last_interaction"], "%B %d, %Y, %H:%M:%S") if data.get("last_interaction") else None,
            interaction_count=data.get("interaction_count", 0),
            shared_memories=data.get("shared_memories", []),
            relationship_history=data.get("relationship_history", []),
            trust_level=data.get("trust_level", 0.5)
        )


class SocialNetwork:
    """
    Manages the social network of relationships between all agents.
    
    This class handles:
    - Creating and tracking relationships
    - Querying relationship information
    - Social influence calculations
    - Information propagation modeling
    """
    
    def __init__(self):
        # Relationships stored as {(agent_a, agent_b): Relationship}
        # Always stored with alphabetically first name first for consistency
        self.relationships: Dict[Tuple[str, str], Relationship] = {}
        
        # Cache for quick agent lookups
        self.agent_relationships: Dict[str, Set[str]] = {}  # agent -> set of connected agents

    def _normalize_key(self, agent_a: str, agent_b: str) -> Tuple[str, str]:
        """Ensure consistent key ordering."""
        return tuple(sorted([agent_a, agent_b]))

    def get_or_create_relationship(self, agent_a: str, agent_b: str) -> Relationship:
        """
        Get an existing relationship or create a new one.
        
        Args:
            agent_a: First agent's name
            agent_b: Second agent's name
            
        Returns:
            The Relationship instance
        """
        key = self._normalize_key(agent_a, agent_b)
        
        if key not in self.relationships:
            self.relationships[key] = Relationship(
                agent_a=key[0],
                agent_b=key[1]
            )
            # Update cache
            if key[0] not in self.agent_relationships:
                self.agent_relationships[key[0]] = set()
            if key[1] not in self.agent_relationships:
                self.agent_relationships[key[1]] = set()
            self.agent_relationships[key[0]].add(key[1])
            self.agent_relationships[key[1]].add(key[0])
            
        return self.relationships[key]

    def record_interaction(self,
                          agent_a: str,
                          agent_b: str,
                          interaction_type: str,
                          sentiment_delta: float,
                          curr_time: datetime.datetime,
                          memory_node_id: Optional[str] = None):
        """
        Record an interaction between two agents.
        
        Args:
            agent_a: First agent's name
            agent_b: Second agent's name
            interaction_type: Type of interaction
            sentiment_delta: Sentiment change from this interaction
            curr_time: Current simulation time
            memory_node_id: Optional associated memory
        """
        relationship = self.get_or_create_relationship(agent_a, agent_b)
        relationship.update_interaction(
            interaction_type=interaction_type,
            sentiment_delta=sentiment_delta,
            curr_time=curr_time,
            memory_node_id=memory_node_id
        )

    def get_relationship(self, agent_a: str, agent_b: str) -> Optional[Relationship]:
        """
        Get the relationship between two agents.
        
        Args:
            agent_a: First agent's name
            agent_b: Second agent's name
            
        Returns:
            The Relationship if it exists, None otherwise
        """
        key = self._normalize_key(agent_a, agent_b)
        return self.relationships.get(key)

    def get_relationship_strength(self, agent_a: str, agent_b: str) -> float:
        """
        Get the strength of relationship between two agents.
        
        Returns 0.0 if no relationship exists.
        """
        relationship = self.get_relationship(agent_a, agent_b)
        return relationship.strength if relationship else 0.0

    def get_all_relationships(self, agent_name: str) -> List[Relationship]:
        """
        Get all relationships for an agent.
        
        Args:
            agent_name: The agent's name
            
        Returns:
            List of all relationships involving this agent
        """
        relationships = []
        connected = self.agent_relationships.get(agent_name, set())
        
        for other in connected:
            key = self._normalize_key(agent_name, other)
            if key in self.relationships:
                relationships.append(self.relationships[key])
                
        return relationships

    def get_friends(self, agent_name: str, min_strength: float = 0.3) -> List[str]:
        """
        Get list of friends for an agent.
        
        Args:
            agent_name: The agent's name
            min_strength: Minimum relationship strength to qualify as friend
            
        Returns:
            List of friend names
        """
        friends = []
        for rel in self.get_all_relationships(agent_name):
            if rel.strength >= min_strength and rel.sentiment >= 0:
                other = rel.agent_b if rel.agent_a == agent_name else rel.agent_a
                friends.append(other)
        return friends

    def get_close_friends(self, agent_name: str) -> List[str]:
        """Get list of close friends (high strength, high sentiment)."""
        return self.get_friends(agent_name, min_strength=0.6)

    def get_social_influence_ranking(self, agent_name: str) -> List[Tuple[str, float]]:
        """
        Get agents ranked by their influence on the given agent.
        
        Args:
            agent_name: The agent to get influences for
            
        Returns:
            List of (agent_name, influence_weight) tuples, sorted by influence
        """
        influences = []
        for rel in self.get_all_relationships(agent_name):
            other = rel.agent_b if rel.agent_a == agent_name else rel.agent_a
            influence = rel.get_influence_weight()
            influences.append((other, influence))
            
        return sorted(influences, key=lambda x: x[1], reverse=True)

    def calculate_social_proof(self, 
                               agent_name: str, 
                               opinion: str, 
                               agents_with_opinion: List[str]) -> float:
        """
        Calculate social proof pressure for an opinion.
        
        If many influential friends hold an opinion, it's more likely
        to influence the agent.
        
        Args:
            agent_name: The agent being influenced
            opinion: Description of the opinion
            agents_with_opinion: List of agents who hold this opinion
            
        Returns:
            Social proof score (0.0 to 1.0)
        """
        if not agents_with_opinion:
            return 0.0
            
        total_influence = 0.0
        max_possible_influence = 0.0
        
        for other in agents_with_opinion:
            rel = self.get_relationship(agent_name, other)
            if rel:
                total_influence += rel.get_influence_weight()
        
        # Get total possible influence from all relationships
        for rel in self.get_all_relationships(agent_name):
            max_possible_influence += rel.get_influence_weight()
            
        if max_possible_influence == 0:
            return 0.0
            
        return min(1.0, total_influence / max_possible_influence)

    def get_common_friends(self, agent_a: str, agent_b: str) -> List[str]:
        """
        Get mutual friends between two agents.
        
        Args:
            agent_a: First agent
            agent_b: Second agent
            
        Returns:
            List of agent names who are friends with both
        """
        friends_a = set(self.get_friends(agent_a))
        friends_b = set(self.get_friends(agent_b))
        return list(friends_a.intersection(friends_b))

    def get_cliques(self, min_size: int = 3) -> List[Set[str]]:
        """
        Find cliques (fully connected subgroups) in the social network.
        
        Args:
            min_size: Minimum clique size
            
        Returns:
            List of cliques (each is a set of agent names)
        """
        cliques = []
        all_agents = list(self.agent_relationships.keys())
        
        # Simple clique detection (Bron-Kerbosch algorithm simplified)
        for agent in all_agents:
            friends = set(self.get_friends(agent))
            
            if len(friends) < min_size - 1:
                continue
                
            # Check for fully connected subsets
            for friend1 in friends:
                potential_clique = {agent, friend1}
                
                for friend2 in friends:
                    if friend2 == friend1:
                        continue
                    # Check if friend2 is connected to all in potential_clique
                    connected_to_all = True
                    for member in potential_clique:
                        if friend2 != member:
                            rel = self.get_relationship(friend2, member)
                            if not rel or rel.strength < 0.3:
                                connected_to_all = False
                                break
                    if connected_to_all:
                        potential_clique.add(friend2)
                        
                if len(potential_clique) >= min_size:
                    # Check if this clique is not a subset of existing clique
                    is_subset = False
                    for existing in cliques:
                        if potential_clique.issubset(existing):
                            is_subset = True
                            break
                    if not is_subset:
                        # Remove any subsets
                        cliques = [c for c in cliques if not c.issubset(potential_clique)]
                        cliques.append(potential_clique)
                        
        return cliques

    def apply_global_decay(self, curr_time: datetime.datetime):
        """Apply decay to all relationships."""
        for relationship in self.relationships.values():
            relationship.apply_decay(curr_time)

    def get_network_summary(self, agent_name: str) -> Dict:
        """
        Get a summary of an agent's social network.
        
        Args:
            agent_name: The agent to summarize
            
        Returns:
            Dictionary with network statistics
        """
        relationships = self.get_all_relationships(agent_name)
        
        return {
            "total_connections": len(relationships),
            "friends": len(self.get_friends(agent_name)),
            "close_friends": len(self.get_close_friends(agent_name)),
            "average_strength": sum(r.strength for r in relationships) / len(relationships) if relationships else 0,
            "average_sentiment": sum(r.sentiment for r in relationships) / len(relationships) if relationships else 0,
            "most_influential": self.get_social_influence_ranking(agent_name)[:5]
        }

    def to_dict(self) -> Dict:
        """Serialize the social network to a dictionary."""
        return {
            "relationships": [r.to_dict() for r in self.relationships.values()],
            "agent_relationships": {k: list(v) for k, v in self.agent_relationships.items()}
        }

    def load_from_dict(self, data: Dict):
        """Load social network from a dictionary."""
        self.relationships = {}
        self.agent_relationships = {}
        
        for rdata in data.get("relationships", []):
            rel = Relationship.from_dict(rdata)
            key = self._normalize_key(rel.agent_a, rel.agent_b)
            self.relationships[key] = rel
            
        for agent, others in data.get("agent_relationships", {}).items():
            self.agent_relationships[agent] = set(others)

    def save(self, filepath: str):
        """Save social network to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def load(self, filepath: str):
        """Load social network from a JSON file."""
        if check_if_file_exists(filepath):
            with open(filepath) as f:
                self.load_from_dict(json.load(f))


# Global social network instance
_social_network = None

def get_social_network() -> SocialNetwork:
    """Get or create the global SocialNetwork instance."""
    global _social_network
    if _social_network is None:
        _social_network = SocialNetwork()
    return _social_network

def reset_social_network():
    """Reset the global SocialNetwork (useful for testing)."""
    global _social_network
    _social_network = SocialNetwork()


def analyze_relationship_from_memories(agent_a, agent_b, shared_events: List) -> Dict:
    """
    Analyze relationship characteristics from shared memory events.
    
    Args:
        agent_a: First agent name
        agent_b: Second agent name
        shared_events: List of memory nodes involving both agents
        
    Returns:
        Dictionary with relationship analysis
    """
    if not shared_events:
        return {
            "familiarity": "strangers",
            "interaction_type": "none",
            "sentiment": "neutral"
        }
    
    positive_count = 0
    negative_count = 0
    chat_count = 0
    cooperation_count = 0
    
    for event in shared_events:
        if hasattr(event, 'poignancy'):
            if event.poignancy > 5:
                positive_count += 1
            elif event.poignancy < 3:
                negative_count += 1
                
        if hasattr(event, 'type'):
            if event.type == 'chat':
                chat_count += 1
                
        # Check for cooperation keywords
        if hasattr(event, 'description'):
            desc = event.description.lower()
            if any(kw in desc for kw in ['help', 'together', 'cooperat', 'assist']):
                cooperation_count += 1
                
    # Determine familiarity
    total_interactions = len(shared_events)
    if total_interactions > 10:
        familiarity = "well acquainted"
    elif total_interactions > 5:
        familiarity = "familiar"
    elif total_interactions > 0:
        familiarity = "acquaintances"
    else:
        familiarity = "strangers"
        
    # Determine interaction type
    if cooperation_count > chat_count:
        interaction_type = "collaborative"
    elif chat_count > 0:
        interaction_type = "social"
    else:
        interaction_type = "minimal"
        
    # Determine sentiment
    if positive_count > negative_count * 2:
        sentiment = "positive"
    elif negative_count > positive_count * 2:
        sentiment = "negative"
    else:
        sentiment = "neutral"
        
    return {
        "familiarity": familiarity,
        "interaction_type": interaction_type,
        "sentiment": sentiment,
        "total_interactions": total_interactions,
        "positive_interactions": positive_count,
        "negative_interactions": negative_count
    }
