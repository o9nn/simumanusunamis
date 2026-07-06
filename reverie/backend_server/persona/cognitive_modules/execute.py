"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: execute.py
Description: This defines the "Act" module for generative agents. 
"""
import sys
import random
sys.path.append('../../')

from global_methods import *
from path_finder import *
from utils import *

def execute(persona, maze, personas, plan): 
  """
  Given a plan (action's string address), we execute the plan (actually 
  outputs the tile coordinate path and the next coordinate for the 
  persona). 

  INPUT:
    persona: Current <Persona> instance.  
    maze: An instance of current <Maze>.
    personas: A dictionary of all personas in the world. 
    plan: This is a string address of the action we need to execute. 
       It comes in the form of "{world}:{sector}:{arena}:{game_objects}". 
       It is important that you access this without doing negative 
       indexing (e.g., [-1]) because the latter address elements may not be 
       present in some cases. 
       e.g., "dolores double studio:double studio:bedroom 1:bed"
    
  OUTPUT: 
    execution
  """
  if "<random>" in plan and persona.scratch.planned_path == []: 
    persona.scratch.act_path_set = False

  # <act_path_set> is set to True if the path is set for the current action. 
  # It is False otherwise, and means we need to construct a new path. 
  if not persona.scratch.act_path_set: 
    # <target_tiles> is a list of tile coordinates where the persona may go 
    # to execute the current action. The goal is to pick one of them.
    target_tiles = None

    print ('aldhfoaf/????')
    print (plan)

    if "<persona>" in plan: 
      # Executing persona-persona interaction.
      target_p_tile = (personas[plan.split("<persona>")[-1].strip()]
                       .scratch.curr_tile)
      potential_path = path_finder(maze.collision_maze, 
                                   persona.scratch.curr_tile, 
                                   target_p_tile, 
                                   collision_block_id)
      if len(potential_path) <= 2: 
        target_tiles = [potential_path[0]]
      else: 
        potential_1 = path_finder(maze.collision_maze, 
                                persona.scratch.curr_tile, 
                                potential_path[int(len(potential_path)/2)], 
                                collision_block_id)
        potential_2 = path_finder(maze.collision_maze, 
                                persona.scratch.curr_tile, 
                                potential_path[int(len(potential_path)/2)+1], 
                                collision_block_id)
        if len(potential_1) <= len(potential_2): 
          target_tiles = [potential_path[int(len(potential_path)/2)]]
        else: 
          target_tiles = [potential_path[int(len(potential_path)/2+1)]]
    
    elif "<waiting>" in plan: 
      # Executing interaction where the persona has decided to wait before 
      # executing their action.
      x = int(plan.split()[1])
      y = int(plan.split()[2])
      target_tiles = [[x, y]]

    elif "<random>" in plan: 
      # Executing a random location action.
      plan = ":".join(plan.split(":")[:-1])
      target_tiles = maze.address_tiles[plan]
      target_tiles = random.sample(list(target_tiles), 1)

    else: 
      # This is our default execution. We simply take the persona to the
      # location where the current action is taking place. 
      # Retrieve the target addresses. Again, plan is an action address in its
      # string form. <maze.address_tiles> takes this and returns candidate 
      # coordinates. 
      if plan not in maze.address_tiles: 
        maze.address_tiles["Johnson Park:park:park garden"] #ERRORRRRRRR
      else: 
        target_tiles = maze.address_tiles[plan]

    # There are sometimes more than one tile returned from this (e.g., a tabe
    # may stretch many coordinates). So, we sample a few here. And from that 
    # random sample, we will take the closest ones. 
    if len(target_tiles) < 4: 
      target_tiles = random.sample(list(target_tiles), len(target_tiles))
    else:
      target_tiles = random.sample(list(target_tiles), 4)
    # If possible, we want personas to occupy different tiles when they are 
    # headed to the same location on the maze. It is ok if they end up on the 
    # same time, but we try to lower that probability. 
    # We take care of that overlap here.  
    persona_name_set = set(personas.keys())
    new_target_tiles = []
    for i in target_tiles: 
      curr_event_set = maze.access_tile(i)["events"]
      pass_curr_tile = False
      for j in curr_event_set: 
        if j[0] in persona_name_set: 
          pass_curr_tile = True
      if not pass_curr_tile: 
        new_target_tiles += [i]
    if len(new_target_tiles) == 0: 
      new_target_tiles = target_tiles
    target_tiles = new_target_tiles

    # Now that we've identified the target tile, we find the shortest path to
    # one of the target tiles. 
    curr_tile = persona.scratch.curr_tile
    collision_maze = maze.collision_maze
    closest_target_tile = None
    path = None
    for i in target_tiles: 
      # path_finder takes a collision_mze and the curr_tile coordinate as 
      # an input, and returns a list of coordinate tuples that becomes the
      # path. 
      # e.g., [(0, 1), (1, 1), (1, 2), (1, 3), (1, 4)...]
      curr_path = path_finder(maze.collision_maze, 
                              curr_tile, 
                              i, 
                              collision_block_id)
      if not closest_target_tile: 
        closest_target_tile = i
        path = curr_path
      elif len(curr_path) < len(path): 
        closest_target_tile = i
        path = curr_path

    # Actually setting the <planned_path> and <act_path_set>. We cut the 
    # first element in the planned_path because it includes the curr_tile. 
    persona.scratch.planned_path = path[1:]
    persona.scratch.act_path_set = True
  
  # Setting up the next immediate step. We stay at our curr_tile if there is
  # no <planned_path> left, but otherwise, we go to the next tile in the path.
  ret = persona.scratch.curr_tile
  if persona.scratch.planned_path: 
    ret = persona.scratch.planned_path[0]
    persona.scratch.planned_path = persona.scratch.planned_path[1:]

  description = f"{persona.scratch.act_description}"
  description += f" @ {persona.scratch.act_address}"

  execution = ret, persona.scratch.act_pronunciatio, description
  return execution


# =============================================================================
# GROUP MOVEMENT SYSTEM
# =============================================================================

def execute_group_movement(persona, maze, personas, plan, group_members=None):
  """
  Extended execute function that handles group movement coordination.
  Ensures group members move together and maintain formation.
  
  INPUT:
    persona: Current <Persona> instance.
    maze: An instance of current <Maze>.
    personas: A dictionary of all personas in the world.
    plan: Action string address.
    group_members: List of persona names in the group (optional)
  OUTPUT:
    execution: (tile, pronunciatio, description) tuple
  """
  # If not in a group, use standard execution
  if not persona.scratch.current_group and not group_members:
    return execute(persona, maze, personas, plan)
  
  # Get group members from scratch if not provided
  if not group_members:
    group_members = persona.scratch.nearby_group_members or []
    if persona.scratch.name not in group_members:
      group_members.append(persona.scratch.name)
  
  # Check if this is a group plan (indicated by <group> prefix)
  if "<group>" in plan:
    # Extract member names from plan
    member_part = plan.split("<group>")[-1].strip()
    target_members = [m.strip() for m in member_part.split(",")]
    
    # Find the group's target location (use first member's location)
    target_p = None
    for member_name in target_members:
      if member_name in personas:
        target_p = personas[member_name]
        break
    
    if target_p:
      target_tile = target_p.scratch.curr_tile
      
      # Calculate path with group formation offset
      group_index = group_members.index(persona.scratch.name) if persona.scratch.name in group_members else 0
      
      # Apply offset based on position in group
      offset_x = (group_index % 3) - 1
      offset_y = (group_index // 3)
      
      adjusted_target = (
        target_tile[0] + offset_x,
        target_tile[1] + offset_y
      )
      
      # Ensure adjusted target is valid
      if maze.collision_maze[adjusted_target[1]][adjusted_target[0]] == collision_block_id:
        adjusted_target = target_tile
      
      # Calculate path to adjusted target
      if not persona.scratch.act_path_set:
        path = path_finder(maze.collision_maze,
                          persona.scratch.curr_tile,
                          adjusted_target,
                          collision_block_id)
        
        if path:
          persona.scratch.planned_path = path[1:]
          persona.scratch.act_path_set = True
  
  # Standard path following with group awareness
  ret = persona.scratch.curr_tile
  
  # Check if we should wait for other group members
  should_wait = False
  if group_members and len(group_members) > 1:
    # Calculate average distance of group members
    group_positions = []
    for member_name in group_members:
      if member_name in personas and member_name != persona.scratch.name:
        member_pos = personas[member_name].scratch.curr_tile
        group_positions.append(member_pos)
    
    if group_positions:
      # Calculate distance to nearest group member
      min_dist = float('inf')
      for pos in group_positions:
        dist = ((persona.scratch.curr_tile[0] - pos[0])**2 + 
                (persona.scratch.curr_tile[1] - pos[1])**2)**0.5
        min_dist = min(min_dist, dist)
      
      # Wait if too far ahead (more than 3 tiles from nearest member)
      if min_dist > 3:
        should_wait = True
  
  if should_wait:
    # Stay in place to wait for group
    ret = persona.scratch.curr_tile
  elif persona.scratch.planned_path:
    ret = persona.scratch.planned_path[0]
    persona.scratch.planned_path = persona.scratch.planned_path[1:]
  
  description = f"{persona.scratch.act_description}"
  description += f" @ {persona.scratch.act_address}"
  
  # Add group context to description
  if persona.scratch.current_group:
    description += f" (with group)"
  
  execution = ret, persona.scratch.act_pronunciatio, description
  return execution


def wait_for_group(persona, group_members, personas, max_wait_time=5):
  """
  Determines if persona should wait for group members to catch up.
  
  INPUT:
    persona: The persona considering waiting
    group_members: List of persona names in the group
    personas: Dictionary of all personas
    max_wait_time: Maximum time willing to wait (in simulation minutes)
  OUTPUT:
    should_wait: Boolean
    wait_reason: String explanation
  """
  if not group_members or len(group_members) < 2:
    return False, "No group members"
  
  curr_tile = persona.scratch.curr_tile
  stragglers = []
  
  for member_name in group_members:
    if member_name == persona.scratch.name:
      continue
    
    if member_name not in personas:
      continue
    
    member = personas[member_name]
    member_tile = member.scratch.curr_tile
    
    # Calculate distance
    dist = ((curr_tile[0] - member_tile[0])**2 + 
            (curr_tile[1] - member_tile[1])**2)**0.5
    
    # If member is more than 3 tiles away, consider them a straggler
    if dist > 3:
      stragglers.append(member_name)
  
  if stragglers:
    return True, f"Waiting for {', '.join(stragglers)}"
  
  return False, "Group is together"


def coordinate_group_arrival_execution(group_members, target_location, maze, personas):
  """
  Coordinates the arrival of a group at a location.
  Ensures all members arrive and positions them appropriately.
  
  INPUT:
    group_members: List of persona names
    target_location: Target tile coordinates
    maze: The maze instance
    personas: Dictionary of all personas
  OUTPUT:
    arrival_status: Dict with each member's arrival status
  """
  arrival_status = {}
  
  # Calculate formation positions around target
  formation_positions = calculate_group_formation(len(group_members), target_location)
  
  for i, member_name in enumerate(group_members):
    if member_name not in personas:
      arrival_status[member_name] = {
        "status": "unknown",
        "reason": "Persona not found"
      }
      continue
    
    member = personas[member_name]
    member_tile = member.scratch.curr_tile
    
    # Assign formation position
    formation_pos = formation_positions[i] if i < len(formation_positions) else target_location
    
    # Check distance to assigned position
    dist = ((member_tile[0] - formation_pos[0])**2 + 
            (member_tile[1] - formation_pos[1])**2)**0.5
    
    if dist <= 1:
      arrival_status[member_name] = {
        "status": "arrived",
        "position": member_tile,
        "formation_position": formation_pos
      }
    else:
      arrival_status[member_name] = {
        "status": "en_route",
        "position": member_tile,
        "target": formation_pos,
        "distance": dist
      }
  
  return arrival_status


def calculate_group_formation(group_size, center_position):
  """
  Calculates formation positions for group members around a center point.
  
  INPUT:
    group_size: Number of members in the group
    center_position: (x, y) center position
  OUTPUT:
    positions: List of (x, y) positions for each member
  """
  positions = []
  cx, cy = center_position
  
  if group_size == 1:
    return [center_position]
  elif group_size == 2:
    return [(cx, cy), (cx + 1, cy)]
  elif group_size == 3:
    return [(cx, cy), (cx + 1, cy), (cx, cy + 1)]
  elif group_size == 4:
    return [(cx, cy), (cx + 1, cy), (cx, cy + 1), (cx + 1, cy + 1)]
  else:
    # For larger groups, use a circular formation
    import math
    for i in range(group_size):
      angle = (2 * math.pi * i) / group_size
      radius = min(2, group_size // 4 + 1)
      px = int(cx + radius * math.cos(angle))
      py = int(cy + radius * math.sin(angle))
      positions.append((px, py))
  
  return positions


def update_group_movement_state(persona, group_members, personas):
  """
  Updates the persona's movement state based on group dynamics.
  
  INPUT:
    persona: The persona to update
    group_members: List of group member names
    personas: Dictionary of all personas
  """
  if not group_members:
    persona.scratch.nearby_group_members = []
    return
  
  # Update nearby group members
  nearby = []
  curr_tile = persona.scratch.curr_tile
  
  for member_name in group_members:
    if member_name == persona.scratch.name:
      continue
    
    if member_name not in personas:
      continue
    
    member = personas[member_name]
    member_tile = member.scratch.curr_tile
    
    # Calculate distance
    dist = ((curr_tile[0] - member_tile[0])**2 + 
            (curr_tile[1] - member_tile[1])**2)**0.5
    
    # Consider nearby if within vision radius (typically 4-8 tiles)
    if dist <= persona.scratch.vision_r:
      nearby.append(member_name)
  
  persona.scratch.nearby_group_members = nearby
  
  # Check if group has dispersed
  if len(nearby) < len(group_members) // 2:
    # Group has scattered - may need to clear group state
    if persona.scratch.current_group:
      print(f"{persona.scratch.name}: Group appears to have dispersed")











