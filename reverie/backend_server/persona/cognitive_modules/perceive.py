"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: perceive.py
Description: This defines the "Perceive" module for generative agents. 
"""
import sys
sys.path.append('../../')

from operator import itemgetter
from global_methods import *
from persona.prompt_template.gpt_structure import *
from persona.prompt_template.run_gpt_prompt import *

def generate_poig_score(persona, event_type, description): 
  if "is idle" in description: 
    return 1

  if event_type == "event": 
    return run_gpt_prompt_event_poignancy(persona, description)[0]
  elif event_type == "chat": 
    return run_gpt_prompt_chat_poignancy(persona, 
                           persona.scratch.act_description)[0]

def perceive(persona, maze): 
  """
  Perceives events around the persona and saves it to the memory, both events 
  and spaces. 

  We first perceive the events nearby the persona, as determined by its 
  <vision_r>. If there are a lot of events happening within that radius, we 
  take the <att_bandwidth> of the closest events. Finally, we check whether
  any of them are new, as determined by <retention>. If they are new, then we
  save those and return the <ConceptNode> instances for those events. 

  INPUT: 
    persona: An instance of <Persona> that represents the current persona. 
    maze: An instance of <Maze> that represents the current maze in which the 
          persona is acting in. 
  OUTPUT: 
    ret_events: a list of <ConceptNode> that are perceived and new. 
  """
  # PERCEIVE SPACE
  # We get the nearby tiles given our current tile and the persona's vision
  # radius. 
  nearby_tiles = maze.get_nearby_tiles(persona.scratch.curr_tile, 
                                       persona.scratch.vision_r)

  # We then store the perceived space. Note that the s_mem of the persona is
  # in the form of a tree constructed using dictionaries. 
  for i in nearby_tiles: 
    i = maze.access_tile(i)
    if i["world"]: 
      if (i["world"] not in persona.s_mem.tree): 
        persona.s_mem.tree[i["world"]] = {}
    if i["sector"]: 
      if (i["sector"] not in persona.s_mem.tree[i["world"]]): 
        persona.s_mem.tree[i["world"]][i["sector"]] = {}
    if i["arena"]: 
      if (i["arena"] not in persona.s_mem.tree[i["world"]]
                                              [i["sector"]]): 
        persona.s_mem.tree[i["world"]][i["sector"]][i["arena"]] = []
    if i["game_object"]: 
      if (i["game_object"] not in persona.s_mem.tree[i["world"]]
                                                    [i["sector"]]
                                                    [i["arena"]]): 
        persona.s_mem.tree[i["world"]][i["sector"]][i["arena"]] += [
                                                             i["game_object"]]

  # PERCEIVE EVENTS. 
  # We will perceive events that take place in the same arena as the
  # persona's current arena. 
  curr_arena_path = maze.get_tile_path(persona.scratch.curr_tile, "arena")
  # We do not perceive the same event twice (this can happen if an object is
  # extended across multiple tiles).
  percept_events_set = set()
  # We will order our percept based on the distance, with the closest ones
  # getting priorities. 
  percept_events_list = []
  # First, we put all events that are occuring in the nearby tiles into the
  # percept_events_list
  for tile in nearby_tiles: 
    tile_details = maze.access_tile(tile)
    if tile_details["events"]: 
      if maze.get_tile_path(tile, "arena") == curr_arena_path:  
        # This calculates the distance between the persona's current tile, 
        # and the target tile.
        dist = math.dist([tile[0], tile[1]], 
                         [persona.scratch.curr_tile[0], 
                          persona.scratch.curr_tile[1]])
        # Add any relevant events to our temp set/list with the distant info. 
        for event in tile_details["events"]: 
          if event not in percept_events_set: 
            percept_events_list += [[dist, event]]
            percept_events_set.add(event)

  # We sort, and perceive only persona.scratch.att_bandwidth of the closest
  # events. If the bandwidth is larger, then it means the persona can perceive
  # more elements within a small area. 
  percept_events_list = sorted(percept_events_list, key=itemgetter(0))
  perceived_events = []
  for dist, event in percept_events_list[:persona.scratch.att_bandwidth]: 
    perceived_events += [event]

  # Storing events. 
  # <ret_events> is a list of <ConceptNode> instances from the persona's 
  # associative memory. 
  ret_events = []
  for p_event in perceived_events: 
    s, p, o, desc = p_event
    if not p: 
      # If the object is not present, then we default the event to "idle".
      p = "is"
      o = "idle"
      desc = "idle"
    desc = f"{s.split(':')[-1]} is {desc}"
    p_event = (s, p, o)

    # We retrieve the latest persona.scratch.retention events. If there is  
    # something new that is happening (that is, p_event not in latest_events),
    # then we add that event to the a_mem and return it. 
    latest_events = persona.a_mem.get_summarized_latest_events(
                                    persona.scratch.retention)
    if p_event not in latest_events:
      # We start by managing keywords. 
      keywords = set()
      sub = p_event[0]
      obj = p_event[2]
      if ":" in p_event[0]: 
        sub = p_event[0].split(":")[-1]
      if ":" in p_event[2]: 
        obj = p_event[2].split(":")[-1]
      keywords.update([sub, obj])

      # Get event embedding
      desc_embedding_in = desc
      if "(" in desc: 
        desc_embedding_in = (desc_embedding_in.split("(")[1]
                                              .split(")")[0]
                                              .strip())
      if desc_embedding_in in persona.a_mem.embeddings: 
        event_embedding = persona.a_mem.embeddings[desc_embedding_in]
      else: 
        event_embedding = get_embedding(desc_embedding_in)
      event_embedding_pair = (desc_embedding_in, event_embedding)
      
      # Get event poignancy. 
      event_poignancy = generate_poig_score(persona, 
                                            "event", 
                                            desc_embedding_in)

      # If we observe the persona's self chat, we include that in the memory
      # of the persona here. 
      chat_node_ids = []
      if p_event[0] == f"{persona.name}" and p_event[1] == "chat with": 
        curr_event = persona.scratch.act_event
        if persona.scratch.act_description in persona.a_mem.embeddings: 
          chat_embedding = persona.a_mem.embeddings[
                             persona.scratch.act_description]
        else: 
          chat_embedding = get_embedding(persona.scratch
                                                .act_description)
        chat_embedding_pair = (persona.scratch.act_description, 
                               chat_embedding)
        chat_poignancy = generate_poig_score(persona, "chat", 
                                             persona.scratch.act_description)
        chat_node = persona.a_mem.add_chat(persona.scratch.curr_time, None,
                      curr_event[0], curr_event[1], curr_event[2], 
                      persona.scratch.act_description, keywords, 
                      chat_poignancy, chat_embedding_pair, 
                      persona.scratch.chat)
        chat_node_ids = [chat_node.node_id]

      # Finally, we add the current event to the agent's memory. 
      ret_events += [persona.a_mem.add_event(persona.scratch.curr_time, None,
                           s, p, o, desc, keywords, event_poignancy, 
                           event_embedding_pair, chat_node_ids)]
      persona.scratch.importance_trigger_curr -= event_poignancy
      persona.scratch.importance_ele_n += 1

  return ret_events


def detect_agent_clusters(persona, maze, nearby_tiles, min_group_size=3, cluster_radius=2):
  """
  Detects clusters of agents nearby that could form a group.
  
  INPUT:
    persona: An instance of <Persona> that represents the current persona.
    maze: An instance of <Maze> that represents the current maze.
    nearby_tiles: List of nearby tile coordinates.
    min_group_size: Minimum number of agents to form a group (default 3).
    cluster_radius: Maximum tile distance between agents in a cluster.
  OUTPUT:
    clusters: List of agent name clusters, e.g., [["Agent1", "Agent2", "Agent3"], ...]
  """
  # Find all nearby agents and their positions
  agent_positions = {}  # {agent_name: (x, y)}
  
  for tile in nearby_tiles:
    tile_details = maze.access_tile(tile)
    if tile_details["events"]:
      for event in tile_details["events"]:
        s, p, o, desc = event
        # Check if this is an agent (subject contains a colon for personas)
        if ":" in s and "persona" in s.lower():
          agent_name = s.split(":")[-1]
          if agent_name != persona.name:  # Don't include self
            agent_positions[agent_name] = tile
  
  if len(agent_positions) < min_group_size - 1:  # -1 because we might join
    return []
  
  # Cluster agents based on proximity using simple clustering
  clusters = []
  visited = set()
  
  for agent_name, pos in agent_positions.items():
    if agent_name in visited:
      continue
    
    # Start a new cluster
    cluster = [agent_name]
    visited.add(agent_name)
    
    # Find all agents close to this cluster
    to_check = [agent_name]
    while to_check:
      current = to_check.pop()
      current_pos = agent_positions[current]
      
      for other_name, other_pos in agent_positions.items():
        if other_name in visited:
          continue
        
        # Check if within cluster radius
        dist = math.dist([current_pos[0], current_pos[1]], 
                         [other_pos[0], other_pos[1]])
        if dist <= cluster_radius:
          cluster.append(other_name)
          visited.add(other_name)
          to_check.append(other_name)
    
    # Only keep clusters that meet minimum size
    if len(cluster) >= min_group_size - 1:  # -1 because persona might join
      clusters.append(cluster)
  
  return clusters


def perceive_groups(persona, maze, nearby_tiles):
  """
  Perceives group interactions happening nearby and updates persona's
  group awareness.
  
  INPUT:
    persona: An instance of <Persona>
    maze: An instance of <Maze>
    nearby_tiles: List of nearby tile coordinates
  OUTPUT:
    group_events: List of perceived group events/activities
  """
  group_events = []
  
  # Detect nearby agent clusters
  clusters = detect_agent_clusters(persona, maze, nearby_tiles)
  
  # Update persona's awareness of nearby group members
  all_nearby_members = []
  for cluster in clusters:
    all_nearby_members.extend(cluster)
  persona.scratch.nearby_group_members = all_nearby_members
  
  # Check if persona should join any cluster
  curr_pos = persona.scratch.curr_tile
  for cluster in clusters:
    # Calculate cluster center
    cluster_positions = []
    for tile in nearby_tiles:
      tile_details = maze.access_tile(tile)
      if tile_details["events"]:
        for event in tile_details["events"]:
          s = event[0]
          if ":" in s:
            agent_name = s.split(":")[-1]
            if agent_name in cluster:
              cluster_positions.append(tile)
              break
    
    if cluster_positions:
      # Calculate average position of cluster
      avg_x = sum(p[0] for p in cluster_positions) / len(cluster_positions)
      avg_y = sum(p[1] for p in cluster_positions) / len(cluster_positions)
      
      # Check if persona is close to this cluster
      dist_to_cluster = math.dist([curr_pos[0], curr_pos[1]], [avg_x, avg_y])
      
      if dist_to_cluster <= 3:  # Close enough to be considered part of group
        # Create a group event description
        if len(cluster) == 2:
          group_desc = f"{cluster[0]} and {cluster[1]} are talking together"
        else:
          group_desc = f"{cluster[0]}, {cluster[1]}, and {len(cluster)-2} others are gathered"
        
        group_events.append({
          "type": "group_gathering",
          "members": cluster,
          "description": group_desc,
          "distance": dist_to_cluster,
          "center": (avg_x, avg_y)
        })
  
  return group_events


def perceive_with_groups(persona, maze):
  """
  Extended perceive function that includes group detection.
  Wraps the standard perceive() with additional group awareness.
  
  INPUT:
    persona: An instance of <Persona>
    maze: An instance of <Maze>
  OUTPUT:
    ret_events: List of <ConceptNode> instances (from standard perceive)
    group_events: List of perceived group activities
  """
  # Get nearby tiles first (needed for both perception types)
  nearby_tiles = maze.get_nearby_tiles(persona.scratch.curr_tile, 
                                       persona.scratch.vision_r)
  
  # Run standard perception
  ret_events = perceive(persona, maze)
  
  # Also perceive groups
  group_events = perceive_groups(persona, maze, nearby_tiles)
  
  return ret_events, group_events











