"""
File: consensus.py
Description: Defines the collective decision-making module for generative agents.

This module handles:
- Voting and consensus mechanisms
- Debate and discussion modeling
- Compromise detection and generation
- Deadlock resolution
"""
import sys
import datetime
import uuid
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import random

sys.path.append('../../')

from global_methods import *


class DecisionType(Enum):
    """Types of group decisions."""
    MAJORITY_VOTE = "majority_vote"           # Simple majority wins
    UNANIMOUS = "unanimous"                    # Everyone must agree
    WEIGHTED_VOTE = "weighted_vote"            # Votes weighted by role/influence
    CONSENSUS = "consensus"                    # Discussion until agreement
    LEADER_DECIDES = "leader_decides"          # Leader makes final call


class VoteOption(Enum):
    """Possible vote values."""
    STRONGLY_AGREE = "strongly_agree"
    AGREE = "agree"
    NEUTRAL = "neutral"
    DISAGREE = "disagree"
    STRONGLY_DISAGREE = "strongly_disagree"
    ABSTAIN = "abstain"


# Vote weights for different options
VOTE_WEIGHTS = {
    VoteOption.STRONGLY_AGREE: 2,
    VoteOption.AGREE: 1,
    VoteOption.NEUTRAL: 0,
    VoteOption.DISAGREE: -1,
    VoteOption.STRONGLY_DISAGREE: -2,
    VoteOption.ABSTAIN: 0
}


@dataclass
class Vote:
    """A single vote on a decision."""
    voter: str
    option: VoteOption
    reasoning: Optional[str] = None
    weight: float = 1.0  # For weighted voting
    timestamp: Optional[datetime.datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()
            
    def get_weighted_value(self) -> float:
        """Get the weighted vote value."""
        return VOTE_WEIGHTS[self.option] * self.weight

    def to_dict(self) -> Dict:
        return {
            "voter": self.voter,
            "option": self.option.value,
            "reasoning": self.reasoning,
            "weight": self.weight,
            "timestamp": self.timestamp.strftime("%B %d, %Y, %H:%M:%S") if self.timestamp else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Vote':
        return cls(
            voter=data["voter"],
            option=VoteOption(data["option"]),
            reasoning=data.get("reasoning"),
            weight=data.get("weight", 1.0),
            timestamp=datetime.datetime.strptime(data["timestamp"], "%B %d, %Y, %H:%M:%S") if data.get("timestamp") else None
        )


@dataclass
class DecisionOption:
    """An option being considered in a decision."""
    id: str
    description: str
    proposed_by: str
    votes: List[Vote] = field(default_factory=list)
    supporting_arguments: List[str] = field(default_factory=list)
    opposing_arguments: List[str] = field(default_factory=list)
    
    def add_vote(self, vote: Vote):
        """Add a vote for this option."""
        # Remove previous vote from same voter
        self.votes = [v for v in self.votes if v.voter != vote.voter]
        self.votes.append(vote)
        
    def get_vote_count(self) -> int:
        """Count positive votes."""
        return sum(1 for v in self.votes if v.option in [VoteOption.AGREE, VoteOption.STRONGLY_AGREE])
    
    def get_weighted_score(self) -> float:
        """Get weighted vote score."""
        return sum(v.get_weighted_value() for v in self.votes)
    
    def get_support_percentage(self) -> float:
        """Get percentage of voters who support this option."""
        if not self.votes:
            return 0.0
        positive = sum(1 for v in self.votes if v.option in [VoteOption.AGREE, VoteOption.STRONGLY_AGREE])
        return positive / len(self.votes)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "proposed_by": self.proposed_by,
            "votes": [v.to_dict() for v in self.votes],
            "supporting_arguments": self.supporting_arguments,
            "opposing_arguments": self.opposing_arguments
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DecisionOption':
        option = cls(
            id=data["id"],
            description=data["description"],
            proposed_by=data["proposed_by"],
            supporting_arguments=data.get("supporting_arguments", []),
            opposing_arguments=data.get("opposing_arguments", [])
        )
        option.votes = [Vote.from_dict(v) for v in data.get("votes", [])]
        return option


class DecisionStatus(Enum):
    """Status of a group decision."""
    PROPOSED = "proposed"           # Just proposed
    DISCUSSING = "discussing"       # Under discussion
    VOTING = "voting"              # Voting in progress
    DECIDED = "decided"            # Decision made
    DEADLOCKED = "deadlocked"      # Cannot reach consensus
    CANCELLED = "cancelled"        # Decision cancelled


@dataclass
class GroupDecision:
    """
    Represents a group decision-making process.
    
    Attributes:
        id: Unique decision identifier
        question: What is being decided
        group_id: The group making the decision
        participants: Who can vote
        decision_type: How the decision will be made
        options: Available options
        status: Current status
        deadline: When voting ends
        result: The chosen option (if decided)
        discussion_log: Record of discussion
    """
    id: str
    question: str
    group_id: str
    participants: List[str]
    decision_type: DecisionType = DecisionType.MAJORITY_VOTE
    options: List[DecisionOption] = field(default_factory=list)
    status: DecisionStatus = DecisionStatus.PROPOSED
    created_at: Optional[datetime.datetime] = None
    deadline: Optional[datetime.datetime] = None
    decided_at: Optional[datetime.datetime] = None
    result: Optional[str] = None  # Option ID
    discussion_log: List[Tuple[str, str, datetime.datetime]] = field(default_factory=list)
    leader: Optional[str] = None  # For LEADER_DECIDES type
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.datetime.now()

    def add_option(self, description: str, proposed_by: str) -> DecisionOption:
        """Add a new option to consider."""
        option = DecisionOption(
            id=f"opt_{uuid.uuid4().hex[:6]}",
            description=description,
            proposed_by=proposed_by
        )
        self.options.append(option)
        self.add_discussion(proposed_by, f"Proposed option: {description}")
        return option

    def cast_vote(self, voter: str, option_id: str, vote_option: VoteOption, 
                  reasoning: Optional[str] = None, weight: float = 1.0) -> bool:
        """Cast a vote for an option."""
        if voter not in self.participants:
            return False
            
        if self.status != DecisionStatus.VOTING:
            return False
            
        for option in self.options:
            if option.id == option_id:
                vote = Vote(
                    voter=voter,
                    option=vote_option,
                    reasoning=reasoning,
                    weight=weight
                )
                option.add_vote(vote)
                self.add_discussion(voter, f"Voted {vote_option.value} on '{option.description}'")
                return True
        return False

    def add_argument(self, speaker: str, option_id: str, argument: str, is_supporting: bool):
        """Add an argument for or against an option."""
        for option in self.options:
            if option.id == option_id:
                if is_supporting:
                    option.supporting_arguments.append(f"{speaker}: {argument}")
                else:
                    option.opposing_arguments.append(f"{speaker}: {argument}")
                self.add_discussion(speaker, argument)
                return True
        return False

    def add_discussion(self, speaker: str, message: str):
        """Add to the discussion log."""
        self.discussion_log.append((speaker, message, datetime.datetime.now()))

    def start_voting(self):
        """Transition to voting phase."""
        if self.status == DecisionStatus.DISCUSSING:
            self.status = DecisionStatus.VOTING

    def start_discussion(self):
        """Transition to discussion phase."""
        if self.status == DecisionStatus.PROPOSED:
            self.status = DecisionStatus.DISCUSSING

    def check_deadline(self, curr_time: datetime.datetime) -> bool:
        """Check if deadline has passed."""
        if self.deadline and curr_time >= self.deadline:
            return True
        return False

    def evaluate(self, curr_time: Optional[datetime.datetime] = None) -> Optional[str]:
        """
        Evaluate the decision based on current votes.
        
        Returns the winning option ID if decision is made, None otherwise.
        """
        if not self.options:
            return None
            
        if self.decision_type == DecisionType.MAJORITY_VOTE:
            return self._evaluate_majority()
        elif self.decision_type == DecisionType.UNANIMOUS:
            return self._evaluate_unanimous()
        elif self.decision_type == DecisionType.WEIGHTED_VOTE:
            return self._evaluate_weighted()
        elif self.decision_type == DecisionType.CONSENSUS:
            return self._evaluate_consensus()
        elif self.decision_type == DecisionType.LEADER_DECIDES:
            return self._evaluate_leader()
        return None

    def _evaluate_majority(self) -> Optional[str]:
        """Simple majority vote evaluation."""
        if not all(self._all_voted()):
            return None
            
        best_option = max(self.options, key=lambda o: o.get_vote_count())
        if best_option.get_vote_count() > len(self.participants) / 2:
            return best_option.id
        return None

    def _evaluate_unanimous(self) -> Optional[str]:
        """Unanimous vote evaluation."""
        for option in self.options:
            if option.get_support_percentage() == 1.0 and len(option.votes) == len(self.participants):
                return option.id
        return None

    def _evaluate_weighted(self) -> Optional[str]:
        """Weighted vote evaluation."""
        if not all(self._all_voted()):
            return None
            
        best_option = max(self.options, key=lambda o: o.get_weighted_score())
        if best_option.get_weighted_score() > 0:
            return best_option.id
        return None

    def _evaluate_consensus(self) -> Optional[str]:
        """Consensus evaluation - needs high agreement."""
        for option in self.options:
            if option.get_support_percentage() >= 0.8:  # 80% agreement
                return option.id
        return None

    def _evaluate_leader(self) -> Optional[str]:
        """Leader decides evaluation."""
        if not self.leader:
            return None
            
        for option in self.options:
            for vote in option.votes:
                if vote.voter == self.leader and vote.option in [VoteOption.AGREE, VoteOption.STRONGLY_AGREE]:
                    return option.id
        return None

    def _all_voted(self) -> List[bool]:
        """Check which participants have voted."""
        voted = set()
        for option in self.options:
            for vote in option.votes:
                voted.add(vote.voter)
        return [p in voted for p in self.participants]

    def finalize(self, curr_time: Optional[datetime.datetime] = None):
        """Finalize the decision."""
        result = self.evaluate(curr_time)
        if result:
            self.result = result
            self.status = DecisionStatus.DECIDED
            self.decided_at = curr_time or datetime.datetime.now()
        elif all(self._all_voted()) and result is None:
            self.status = DecisionStatus.DEADLOCKED

    def get_winning_option(self) -> Optional[DecisionOption]:
        """Get the winning option."""
        if self.result:
            for option in self.options:
                if option.id == self.result:
                    return option
        return None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "question": self.question,
            "group_id": self.group_id,
            "participants": self.participants,
            "decision_type": self.decision_type.value,
            "options": [o.to_dict() for o in self.options],
            "status": self.status.value,
            "created_at": self.created_at.strftime("%B %d, %Y, %H:%M:%S") if self.created_at else None,
            "deadline": self.deadline.strftime("%B %d, %Y, %H:%M:%S") if self.deadline else None,
            "decided_at": self.decided_at.strftime("%B %d, %Y, %H:%M:%S") if self.decided_at else None,
            "result": self.result,
            "discussion_log": [(s, m, t.strftime("%H:%M:%S")) for s, m, t in self.discussion_log[-20:]],
            "leader": self.leader
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GroupDecision':
        decision = cls(
            id=data["id"],
            question=data["question"],
            group_id=data["group_id"],
            participants=data["participants"],
            decision_type=DecisionType(data["decision_type"]),
            status=DecisionStatus(data["status"]),
            created_at=datetime.datetime.strptime(data["created_at"], "%B %d, %Y, %H:%M:%S") if data.get("created_at") else None,
            deadline=datetime.datetime.strptime(data["deadline"], "%B %d, %Y, %H:%M:%S") if data.get("deadline") else None,
            decided_at=datetime.datetime.strptime(data["decided_at"], "%B %d, %Y, %H:%M:%S") if data.get("decided_at") else None,
            result=data.get("result"),
            leader=data.get("leader")
        )
        decision.options = [DecisionOption.from_dict(o) for o in data.get("options", [])]
        return decision


class ConsensusManager:
    """
    Manages group decision-making processes.
    
    Handles:
    - Creating and tracking decisions
    - Managing voting processes
    - Resolving deadlocks
    - Generating compromises
    """
    
    def __init__(self):
        self.decisions: Dict[str, GroupDecision] = {}
        self.group_decisions: Dict[str, List[str]] = {}  # group_id -> decision_ids

    def create_decision(self,
                       question: str,
                       group_id: str,
                       participants: List[str],
                       decision_type: DecisionType = DecisionType.MAJORITY_VOTE,
                       deadline: Optional[datetime.datetime] = None,
                       leader: Optional[str] = None) -> GroupDecision:
        """
        Create a new group decision.
        
        Args:
            question: What is being decided
            group_id: The group making the decision
            participants: Who can vote
            decision_type: How to decide
            deadline: Optional voting deadline
            leader: Optional leader for leader_decides type
            
        Returns:
            The created GroupDecision
        """
        decision_id = f"dec_{uuid.uuid4().hex[:8]}"
        
        decision = GroupDecision(
            id=decision_id,
            question=question,
            group_id=group_id,
            participants=participants,
            decision_type=decision_type,
            deadline=deadline,
            leader=leader
        )
        
        self.decisions[decision_id] = decision
        
        if group_id not in self.group_decisions:
            self.group_decisions[group_id] = []
        self.group_decisions[group_id].append(decision_id)
        
        return decision

    def get_decision(self, decision_id: str) -> Optional[GroupDecision]:
        """Get a decision by ID."""
        return self.decisions.get(decision_id)

    def get_group_decisions(self, group_id: str) -> List[GroupDecision]:
        """Get all decisions for a group."""
        decision_ids = self.group_decisions.get(group_id, [])
        return [self.decisions[did] for did in decision_ids if did in self.decisions]

    def get_active_decisions(self, group_id: str) -> List[GroupDecision]:
        """Get active (non-finalized) decisions for a group."""
        return [d for d in self.get_group_decisions(group_id)
                if d.status not in [DecisionStatus.DECIDED, DecisionStatus.CANCELLED]]

    def propose_option(self, 
                      decision_id: str, 
                      proposer: str, 
                      description: str) -> Optional[DecisionOption]:
        """Propose a new option for a decision."""
        decision = self.get_decision(decision_id)
        if not decision or proposer not in decision.participants:
            return None
        return decision.add_option(description, proposer)

    def vote(self,
            decision_id: str,
            voter: str,
            option_id: str,
            vote_option: VoteOption,
            reasoning: Optional[str] = None) -> bool:
        """Cast a vote on a decision."""
        decision = self.get_decision(decision_id)
        if not decision:
            return False
            
        # Calculate vote weight based on role (could be enhanced)
        weight = 1.0
        if decision.leader == voter:
            weight = 1.5
            
        return decision.cast_vote(voter, option_id, vote_option, reasoning, weight)

    def add_argument(self,
                    decision_id: str,
                    speaker: str,
                    option_id: str,
                    argument: str,
                    is_supporting: bool) -> bool:
        """Add an argument for or against an option."""
        decision = self.get_decision(decision_id)
        if not decision or speaker not in decision.participants:
            return False
        return decision.add_argument(speaker, option_id, argument, is_supporting)

    def advance_decision(self, decision_id: str, curr_time: Optional[datetime.datetime] = None):
        """
        Advance a decision through its phases.
        
        Handles transitions between proposed -> discussing -> voting -> decided
        """
        decision = self.get_decision(decision_id)
        if not decision:
            return
            
        if decision.status == DecisionStatus.PROPOSED:
            decision.start_discussion()
        elif decision.status == DecisionStatus.DISCUSSING:
            # Check if enough discussion has happened
            if len(decision.discussion_log) >= len(decision.participants) * 2:
                decision.start_voting()
        elif decision.status == DecisionStatus.VOTING:
            # Check if deadline passed or all voted
            should_finalize = False
            if curr_time and decision.check_deadline(curr_time):
                should_finalize = True
            elif all(decision._all_voted()):
                should_finalize = True
            if should_finalize:
                decision.finalize(curr_time)

    def generate_compromise(self, decision_id: str) -> Optional[str]:
        """
        Generate a compromise option when deadlocked.
        
        Analyzes existing options and generates a middle-ground option.
        
        Returns description of compromise option, or None if not possible.
        """
        decision = self.get_decision(decision_id)
        if not decision or len(decision.options) < 2:
            return None
            
        # Find the top 2 options by votes
        sorted_options = sorted(decision.options, 
                               key=lambda o: o.get_weighted_score(), 
                               reverse=True)[:2]
        
        if len(sorted_options) < 2:
            return None
            
        opt1, opt2 = sorted_options
        
        # Simple compromise: combine elements from both
        compromise_desc = f"Compromise: combining elements from '{opt1.description[:30]}...' and '{opt2.description[:30]}...'"
        
        return compromise_desc

    def resolve_deadlock(self, 
                        decision_id: str, 
                        resolution_method: str = "compromise") -> Optional[str]:
        """
        Attempt to resolve a deadlocked decision.
        
        Args:
            decision_id: The decision to resolve
            resolution_method: How to resolve ("compromise", "leader", "random", "postpone")
            
        Returns:
            The result, or None if not resolved
        """
        decision = self.get_decision(decision_id)
        if not decision or decision.status != DecisionStatus.DEADLOCKED:
            return None
            
        if resolution_method == "compromise":
            compromise = self.generate_compromise(decision_id)
            if compromise:
                # Add compromise as new option and auto-accept
                option = decision.add_option(compromise, "system")
                decision.result = option.id
                decision.status = DecisionStatus.DECIDED
                return option.id
                
        elif resolution_method == "leader" and decision.leader:
            # Leader breaks the tie
            sorted_options = sorted(decision.options, 
                                   key=lambda o: o.get_weighted_score(), 
                                   reverse=True)
            if sorted_options:
                decision.result = sorted_options[0].id
                decision.status = DecisionStatus.DECIDED
                decision.add_discussion(decision.leader, "Leader broke the tie")
                return sorted_options[0].id
                
        elif resolution_method == "random":
            # Random selection weighted by votes
            weights = [max(0.1, o.get_weighted_score() + 5) for o in decision.options]
            total = sum(weights)
            weights = [w/total for w in weights]
            chosen = random.choices(decision.options, weights=weights, k=1)[0]
            decision.result = chosen.id
            decision.status = DecisionStatus.DECIDED
            decision.add_discussion("system", "Random selection was used to break deadlock")
            return chosen.id
            
        elif resolution_method == "postpone":
            # Reset to discussing phase with extended deadline
            decision.status = DecisionStatus.DISCUSSING
            if decision.deadline:
                decision.deadline += datetime.timedelta(hours=1)
            decision.add_discussion("system", "Decision postponed for more discussion")
            return None
            
        return None

    def get_agent_pending_votes(self, agent_name: str) -> List[Tuple[GroupDecision, List[DecisionOption]]]:
        """Get decisions where the agent hasn't voted yet."""
        pending = []
        
        for decision in self.decisions.values():
            if decision.status != DecisionStatus.VOTING:
                continue
            if agent_name not in decision.participants:
                continue
                
            # Check which options need votes
            unvoted_options = []
            for option in decision.options:
                has_voted = any(v.voter == agent_name for v in option.votes)
                if not has_voted:
                    unvoted_options.append(option)
                    
            if unvoted_options:
                pending.append((decision, unvoted_options))
                
        return pending

    def to_dict(self) -> Dict:
        return {
            "decisions": {did: d.to_dict() for did, d in self.decisions.items()},
            "group_decisions": {k: list(v) for k, v in self.group_decisions.items()}
        }

    def load_from_dict(self, data: Dict):
        self.decisions = {}
        self.group_decisions = {}
        
        for did, ddata in data.get("decisions", {}).items():
            self.decisions[did] = GroupDecision.from_dict(ddata)
            
        for gid, decision_ids in data.get("group_decisions", {}).items():
            self.group_decisions[gid] = list(decision_ids)


# Global consensus manager instance
_consensus_manager = None

def get_consensus_manager() -> ConsensusManager:
    """Get or create the global ConsensusManager instance."""
    global _consensus_manager
    if _consensus_manager is None:
        _consensus_manager = ConsensusManager()
    return _consensus_manager

def reset_consensus_manager():
    """Reset the global ConsensusManager."""
    global _consensus_manager
    _consensus_manager = ConsensusManager()


def generate_vote_reasoning(persona, option: DecisionOption, context: str) -> Tuple[VoteOption, str]:
    """
    Generate a vote and reasoning based on persona's characteristics.
    
    This is a simplified version - in production, this would use LLM prompts.
    
    Args:
        persona: The persona voting
        option: The option to vote on
        context: Current context
        
    Returns:
        Tuple of (vote option, reasoning)
    """
    # Simple heuristic based on persona traits and option description
    innate = persona.scratch.innate.lower() if persona.scratch.innate else ""
    currently = persona.scratch.currently.lower() if persona.scratch.currently else ""
    option_desc = option.description.lower()
    
    # Check for alignment
    alignment_score = 0
    
    # Check trait alignment
    positive_traits = ["cooperative", "agreeable", "friendly", "open"]
    negative_traits = ["stubborn", "contrarian", "skeptical"]
    
    for trait in positive_traits:
        if trait in innate:
            alignment_score += 1
            
    for trait in negative_traits:
        if trait in innate:
            alignment_score -= 1
            
    # Check goal alignment
    current_words = set(currently.split())
    option_words = set(option_desc.split())
    overlap = current_words.intersection(option_words)
    alignment_score += len(overlap) * 0.5
    
    # Determine vote
    if alignment_score >= 2:
        vote = VoteOption.STRONGLY_AGREE
        reasoning = "This aligns strongly with my current goals and values"
    elif alignment_score >= 1:
        vote = VoteOption.AGREE
        reasoning = "This seems reasonable and worth supporting"
    elif alignment_score <= -2:
        vote = VoteOption.STRONGLY_DISAGREE
        reasoning = "This conflicts with my values and current priorities"
    elif alignment_score <= -1:
        vote = VoteOption.DISAGREE
        reasoning = "I have concerns about this approach"
    else:
        vote = VoteOption.NEUTRAL
        reasoning = "I don't have strong feelings either way"
        
    return vote, reasoning
