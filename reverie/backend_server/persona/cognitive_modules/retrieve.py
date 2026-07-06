"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: retrieve.py
Description: This defines the "Retrieve" module for generative agents. 
"""
import sys
sys.path.append('../../')

from global_methods import *
from persona.prompt_template.gpt_structure import *

from numpy import dot
from numpy.linalg import norm

def retrieve(persona, perceived): 
  """
  This function takes the events that are perceived by the persona as input
  and returns a set of related events and thoughts that the persona would 
  need to consider as context when planning. 

  INPUT: 
    perceived: a list of event <ConceptNode>s that represent any of the events
    `         that are happening around the persona. What is included in here
              are controlled by the att_bandwidth and retention 
              hyper-parameters.
  OUTPUT: 
    retrieved: a dictionary of dictionary. The first layer specifies an event, 
               while the latter layer specifies the "curr_event", "events", 
               and "thoughts" that are relevant.
  """
  # We rerieve events and thoughts separately. 
  retrieved = dict()
  for event in perceived: 
    retrieved[event.description] = dict()
    retrieved[event.description]["curr_event"] = event
    
    relevant_events = persona.a_mem.retrieve_relevant_events(
                        event.subject, event.predicate, event.object)
    retrieved[event.description]["events"] = list(relevant_events)

    relevant_thoughts = persona.a_mem.retrieve_relevant_thoughts(
                          event.subject, event.predicate, event.object)
    retrieved[event.description]["thoughts"] = list(relevant_thoughts)
    
  return retrieved


def cos_sim(a, b): 
  """
  This function calculates the cosine similarity between two input vectors 
  'a' and 'b'. Cosine similarity is a measure of similarity between two 
  non-zero vectors of an inner product space that measures the cosine 
  of the angle between them.

  INPUT: 
    a: 1-D array object 
    b: 1-D array object 
  OUTPUT: 
    A scalar value representing the cosine similarity between the input 
    vectors 'a' and 'b'.
  
  Example input: 
    a = [0.3, 0.2, 0.5]
    b = [0.2, 0.2, 0.5]
  """
  return dot(a, b)/(norm(a)*norm(b))


def normalize_dict_floats(d, target_min, target_max):
  """
  This function normalizes the float values of a given dictionary 'd' between 
  a target minimum and maximum value. The normalization is done by scaling the
  values to the target range while maintaining the same relative proportions 
  between the original values.

  INPUT: 
    d: Dictionary. The input dictionary whose float values need to be 
       normalized.
    target_min: Integer or float. The minimum value to which the original 
                values should be scaled.
    target_max: Integer or float. The maximum value to which the original 
                values should be scaled.
  OUTPUT: 
    d: A new dictionary with the same keys as the input but with the float
       values normalized between the target_min and target_max.

  Example input: 
    d = {'a':1.2,'b':3.4,'c':5.6,'d':7.8}
    target_min = -5
    target_max = 5
  """
  min_val = min(val for val in d.values())
  max_val = max(val for val in d.values())
  range_val = max_val - min_val

  if range_val == 0: 
    for key, val in d.items(): 
      d[key] = (target_max - target_min)/2
  else: 
    for key, val in d.items():
      d[key] = ((val - min_val) * (target_max - target_min) 
                / range_val + target_min)
  return d


def top_highest_x_values(d, x):
  """
  This function takes a dictionary 'd' and an integer 'x' as input, and 
  returns a new dictionary containing the top 'x' key-value pairs from the 
  input dictionary 'd' with the highest values.

  INPUT: 
    d: Dictionary. The input dictionary from which the top 'x' key-value pairs 
       with the highest values are to be extracted.
    x: Integer. The number of top key-value pairs with the highest values to
       be extracted from the input dictionary.
  OUTPUT: 
    A new dictionary containing the top 'x' key-value pairs from the input 
    dictionary 'd' with the highest values.
  
  Example input: 
    d = {'a':1.2,'b':3.4,'c':5.6,'d':7.8}
    x = 3
  """
  top_v = dict(sorted(d.items(), 
                      key=lambda item: item[1], 
                      reverse=True)[:x])
  return top_v


def extract_recency(persona, nodes):
  """
  Gets the current Persona object and a list of nodes that are in a 
  chronological order, and outputs a dictionary that has the recency score
  calculated.

  INPUT: 
    persona: Current persona whose memory we are retrieving. 
    nodes: A list of Node object in a chronological order. 
  OUTPUT: 
    recency_out: A dictionary whose keys are the node.node_id and whose values
                 are the float that represents the recency score. 
  """
  recency_vals = [persona.scratch.recency_decay ** i 
                  for i in range(1, len(nodes) + 1)]
  
  recency_out = dict()
  for count, node in enumerate(nodes): 
    recency_out[node.node_id] = recency_vals[count]

  return recency_out


def extract_importance(persona, nodes):
  """
  Gets the current Persona object and a list of nodes that are in a 
  chronological order, and outputs a dictionary that has the importance score
  calculated.

  INPUT: 
    persona: Current persona whose memory we are retrieving. 
    nodes: A list of Node object in a chronological order. 
  OUTPUT: 
    importance_out: A dictionary whose keys are the node.node_id and whose 
                    values are the float that represents the importance score.
  """
  importance_out = dict()
  for count, node in enumerate(nodes): 
    importance_out[node.node_id] = node.poignancy

  return importance_out


def extract_relevance(persona, nodes, focal_pt): 
  """
  Gets the current Persona object, a list of nodes that are in a 
  chronological order, and the focal_pt string and outputs a dictionary 
  that has the relevance score calculated.

  INPUT: 
    persona: Current persona whose memory we are retrieving. 
    nodes: A list of Node object in a chronological order. 
    focal_pt: A string describing the current thought of revent of focus.  
  OUTPUT: 
    relevance_out: A dictionary whose keys are the node.node_id and whose values
                 are the float that represents the relevance score. 
  """
  focal_embedding = get_embedding(focal_pt)

  relevance_out = dict()
  for count, node in enumerate(nodes): 
    node_embedding = persona.a_mem.embeddings[node.embedding_key]
    relevance_out[node.node_id] = cos_sim(node_embedding, focal_embedding)

  return relevance_out


def new_retrieve(persona, focal_points, n_count=30): 
  """
  Given the current persona and focal points (focal points are events or 
  thoughts for which we are retrieving), we retrieve a set of nodes for each
  of the focal points and return a dictionary. 

  INPUT: 
    persona: The current persona object whose memory we are retrieving. 
    focal_points: A list of focal points (string description of the events or
                  thoughts that is the focus of current retrieval).
  OUTPUT: 
    retrieved: A dictionary whose keys are a string focal point, and whose 
               values are a list of Node object in the agent's associative 
               memory.

  Example input:
    persona = <persona> object 
    focal_points = ["How are you?", "Jane is swimming in the pond"]
  """
  # <retrieved> is the main dictionary that we are returning
  retrieved = dict() 
  for focal_pt in focal_points: 
    # Getting all nodes from the agent's memory (both thoughts and events) and
    # sorting them by the datetime of creation.
    # You could also imagine getting the raw conversation, but for now. 
    nodes = [[i.last_accessed, i]
              for i in persona.a_mem.seq_event + persona.a_mem.seq_thought
              if "idle" not in i.embedding_key]
    nodes = sorted(nodes, key=lambda x: x[0])
    nodes = [i for created, i in nodes]

    # Calculating the component dictionaries and normalizing them.
    recency_out = extract_recency(persona, nodes)
    recency_out = normalize_dict_floats(recency_out, 0, 1)
    importance_out = extract_importance(persona, nodes)
    importance_out = normalize_dict_floats(importance_out, 0, 1)  
    relevance_out = extract_relevance(persona, nodes, focal_pt)
    relevance_out = normalize_dict_floats(relevance_out, 0, 1)

    # Computing the final scores that combines the component values. 
    # Note to self: test out different weights. [1, 1, 1] tends to work
    # decently, but in the future, these weights should likely be learned, 
    # perhaps through an RL-like process.
    # gw = [1, 1, 1]
    # gw = [1, 2, 1]
    gw = [0.5, 3, 2]
    master_out = dict()
    for key in recency_out.keys(): 
      master_out[key] = (persona.scratch.recency_w*recency_out[key]*gw[0] 
                     + persona.scratch.relevance_w*relevance_out[key]*gw[1] 
                     + persona.scratch.importance_w*importance_out[key]*gw[2])

    master_out = top_highest_x_values(master_out, len(master_out.keys()))
    for key, val in master_out.items(): 
      print (persona.a_mem.id_to_node[key].embedding_key, val)
      print (persona.scratch.recency_w*recency_out[key]*1, 
             persona.scratch.relevance_w*relevance_out[key]*1, 
             persona.scratch.importance_w*importance_out[key]*1)

    # Extracting the highest x values.
    # <master_out> has the key of node.id and value of float. Once we get the 
    # highest x values, we want to translate the node.id into nodes and return
    # the list of nodes.
    master_out = top_highest_x_values(master_out, n_count)
    master_nodes = [persona.a_mem.id_to_node[key] 
                    for key in list(master_out.keys())]

    for n in master_nodes: 
      n.last_accessed = persona.scratch.curr_time
      
    retrieved[focal_pt] = master_nodes

  return retrieved


# =============================================================================
# SOCIAL INFLUENCE RETRIEVAL SYSTEM
# =============================================================================

def extract_social_relevance(persona, nodes, focal_pt):
  """
  Calculates social relevance scores based on relationship strength.
  Memories involving people the persona has stronger relationships with
  are weighted higher.
  
  INPUT:
    persona: Current persona whose memory we are retrieving
    nodes: A list of Node objects
    focal_pt: String focal point for retrieval
  OUTPUT:
    social_relevance_out: Dictionary mapping node_id to social relevance score
  """
  social_relevance_out = dict()
  
  for node in nodes:
    # Default social relevance
    base_score = 0.5
    
    # Check if the node involves another persona
    subject = node.subject if hasattr(node, 'subject') else ""
    obj = getattr(node, 'object', "")
    
    # Get relationship scores for people mentioned in the node
    relationship_boost = 0
    
    for name in [subject, obj]:
      if name and name != persona.scratch.name:
        # Check relationship score
        rel_score = persona.scratch.relationship_scores.get(name, 0.3)
        relationship_boost = max(relationship_boost, rel_score)
    
    # Calculate final social relevance
    social_relevance_out[node.node_id] = base_score + relationship_boost * 0.5
  
  return social_relevance_out


def new_retrieve_with_social(persona, focal_points, n_count=30, social_weight=1.0):
  """
  Extended retrieval function that incorporates social relationship weights.
  Memories involving people with stronger relationships are prioritized.
  
  INPUT:
    persona: The current persona object whose memory we are retrieving
    focal_points: A list of focal points (string descriptions)
    n_count: Number of nodes to retrieve per focal point
    social_weight: Weight for social relevance component
  OUTPUT:
    retrieved: Dictionary mapping focal points to lists of relevant nodes
  """
  retrieved = dict()
  
  for focal_pt in focal_points:
    # Get all nodes from memory
    nodes = [[i.last_accessed, i]
              for i in persona.a_mem.seq_event + persona.a_mem.seq_thought
              if "idle" not in i.embedding_key]
    nodes = sorted(nodes, key=lambda x: x[0])
    nodes = [i for created, i in nodes]
    
    if not nodes:
      retrieved[focal_pt] = []
      continue
    
    # Calculate standard component scores
    recency_out = extract_recency(persona, nodes)
    recency_out = normalize_dict_floats(recency_out, 0, 1)
    importance_out = extract_importance(persona, nodes)
    importance_out = normalize_dict_floats(importance_out, 0, 1)
    relevance_out = extract_relevance(persona, nodes, focal_pt)
    relevance_out = normalize_dict_floats(relevance_out, 0, 1)
    
    # Calculate social relevance
    social_out = extract_social_relevance(persona, nodes, focal_pt)
    social_out = normalize_dict_floats(social_out, 0, 1)
    
    # Combine all scores with weights
    gw = [0.5, 3, 2, social_weight]  # Added social weight
    master_out = dict()
    
    for key in recency_out.keys():
      master_out[key] = (
        persona.scratch.recency_w * recency_out[key] * gw[0] +
        persona.scratch.relevance_w * relevance_out[key] * gw[1] +
        persona.scratch.importance_w * importance_out[key] * gw[2] +
        social_out.get(key, 0.5) * gw[3]
      )
    
    # Get top nodes
    master_out = top_highest_x_values(master_out, n_count)
    master_nodes = [persona.a_mem.id_to_node[key] 
                    for key in list(master_out.keys())]
    
    # Update last accessed
    for n in master_nodes:
      n.last_accessed = persona.scratch.curr_time
    
    retrieved[focal_pt] = master_nodes
  
  return retrieved


def retrieve_group_relevant_memories(persona, group_members, n_count=20):
  """
  Retrieves memories relevant to a specific group of people.
  
  INPUT:
    persona: Current persona
    group_members: List of persona names in the group
    n_count: Number of memories to retrieve
  OUTPUT:
    memories: List of relevant memory nodes
  """
  # Create focal points based on group members
  focal_points = []
  for member in group_members:
    if member != persona.scratch.name:
      focal_points.append(f"interactions with {member}")
      focal_points.append(member)
  
  if not focal_points:
    return []
  
  # Use social-aware retrieval
  retrieved = new_retrieve_with_social(persona, focal_points, n_count // len(focal_points) + 1)
  
  # Combine and deduplicate
  all_nodes = []
  seen_ids = set()
  
  for nodes in retrieved.values():
    for node in nodes:
      if node.node_id not in seen_ids:
        all_nodes.append(node)
        seen_ids.add(node.node_id)
  
  # Sort by recency and return top n_count
  all_nodes.sort(key=lambda x: x.last_accessed, reverse=True)
  return all_nodes[:n_count]


def get_shared_memories(persona_a, persona_b, n_count=10):
  """
  Finds memories that are shared between two personas.
  These are memories where both personas were involved.
  
  INPUT:
    persona_a: First persona
    persona_b: Second persona
    n_count: Number of shared memories to retrieve
  OUTPUT:
    shared: List of memory nodes involving both personas
  """
  shared = []
  
  # Check persona_a's memories for mentions of persona_b
  for node in persona_a.a_mem.seq_event + persona_a.a_mem.seq_thought:
    embedding_key = node.embedding_key.lower()
    if persona_b.scratch.name.lower() in embedding_key:
      shared.append(node)
  
  # Sort by creation time
  shared.sort(key=lambda x: x.created, reverse=True)
  
  return shared[:n_count]


def get_group_shared_context(personas, topic=None):
  """
  Builds a shared context for a group by finding common memories and knowledge.
  
  INPUT:
    personas: List of Persona objects in the group
    topic: Optional topic to focus the context on
  OUTPUT:
    shared_context: Dictionary with shared knowledge and experiences
  """
  shared_context = {
    "common_locations": set(),
    "shared_events": [],
    "relationship_network": {},
    "topic_relevant": []
  }
  
  if len(personas) < 2:
    return shared_context
  
  # Find common locations (places all personas have been)
  location_counts = {}
  for persona in personas:
    for node in persona.a_mem.seq_event:
      if hasattr(node, 'object') and node.object:
        loc = str(node.object)
        if loc not in location_counts:
          location_counts[loc] = set()
        location_counts[loc].add(persona.scratch.name)
  
  for loc, visitors in location_counts.items():
    if len(visitors) >= len(personas) // 2:
      shared_context["common_locations"].add(loc)
  
  # Build relationship network
  for i, persona_a in enumerate(personas):
    for persona_b in personas[i+1:]:
      rel_score_a = persona_a.scratch.relationship_scores.get(
          persona_b.scratch.name, 0.3)
      rel_score_b = persona_b.scratch.relationship_scores.get(
          persona_a.scratch.name, 0.3)
      avg_rel = (rel_score_a + rel_score_b) / 2
      
      key = f"{persona_a.scratch.name}-{persona_b.scratch.name}"
      shared_context["relationship_network"][key] = avg_rel
  
  # Find topic-relevant memories if topic provided
  if topic:
    for persona in personas:
      focal_points = [topic]
      retrieved = new_retrieve(persona, focal_points, 5)
      for nodes in retrieved.values():
        shared_context["topic_relevant"].extend([
          {"persona": persona.scratch.name, "memory": n.embedding_key}
          for n in nodes[:2]
        ])
  
  return shared_context


def apply_peer_influence(persona, group_members, decision_context):
  """
  Modifies a persona's decision based on peer influence from group members.
  
  INPUT:
    persona: The persona making a decision
    group_members: List of Persona objects in the group
    decision_context: String describing the decision being made
  OUTPUT:
    influence_modifier: Float modifier to apply to decision
    influenced_by: List of personas who influenced the decision
  """
  influence_modifier = 1.0
  influenced_by = []
  
  for member in group_members:
    if member.scratch.name == persona.scratch.name:
      continue
    
    # Get relationship strength
    rel_strength = persona.scratch.relationship_scores.get(
        member.scratch.name, 0.3)
    
    # Stronger relationships = more influence
    if rel_strength > 0.6:
      # Significant influence
      influence_modifier *= (1 + (rel_strength - 0.5) * 0.3)
      influenced_by.append(member.scratch.name)
    elif rel_strength > 0.4:
      # Moderate influence
      influence_modifier *= (1 + (rel_strength - 0.4) * 0.15)
      if len(influenced_by) < 3:
        influenced_by.append(member.scratch.name)
  
  return influence_modifier, influenced_by









