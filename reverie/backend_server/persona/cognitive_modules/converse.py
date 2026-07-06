"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: converse.py
Description: An extra cognitive module for generating conversations. 
"""
import math
import sys
import datetime
import random
sys.path.append('../')

from global_methods import *

from persona.memory_structures.spatial_memory import *
from persona.memory_structures.associative_memory import *
from persona.memory_structures.scratch import *
from persona.cognitive_modules.retrieve import *
from persona.prompt_template.run_gpt_prompt import *

def generate_agent_chat_summarize_ideas(init_persona, 
                                        target_persona, 
                                        retrieved, 
                                        curr_context): 
  all_embedding_keys = list()
  for key, val in retrieved.items(): 
    for i in val: 
      all_embedding_keys += [i.embedding_key]
  all_embedding_key_str =""
  for i in all_embedding_keys: 
    all_embedding_key_str += f"{i}\n"

  try: 
    summarized_idea = run_gpt_prompt_agent_chat_summarize_ideas(init_persona,
                        target_persona, all_embedding_key_str, 
                        curr_context)[0]
  except:
    summarized_idea = ""
  return summarized_idea


def generate_summarize_agent_relationship(init_persona, 
                                          target_persona, 
                                          retrieved): 
  all_embedding_keys = list()
  for key, val in retrieved.items(): 
    for i in val: 
      all_embedding_keys += [i.embedding_key]
  all_embedding_key_str =""
  for i in all_embedding_keys: 
    all_embedding_key_str += f"{i}\n"

  summarized_relationship = run_gpt_prompt_agent_chat_summarize_relationship(
                              init_persona, target_persona,
                              all_embedding_key_str)[0]
  return summarized_relationship


def generate_agent_chat(maze, 
                        init_persona, 
                        target_persona,
                        curr_context, 
                        init_summ_idea, 
                        target_summ_idea): 
  summarized_idea = run_gpt_prompt_agent_chat(maze, 
                                              init_persona, 
                                              target_persona,
                                              curr_context, 
                                              init_summ_idea, 
                                              target_summ_idea)[0]
  for i in summarized_idea: 
    print (i)
  return summarized_idea


def agent_chat_v1(maze, init_persona, target_persona): 
  # Chat version optimized for speed via batch generation
  curr_context = (f"{init_persona.scratch.name} " + 
              f"was {init_persona.scratch.act_description} " + 
              f"when {init_persona.scratch.name} " + 
              f"saw {target_persona.scratch.name} " + 
              f"in the middle of {target_persona.scratch.act_description}.\n")
  curr_context += (f"{init_persona.scratch.name} " +
              f"is thinking of initating a conversation with " +
              f"{target_persona.scratch.name}.")

  summarized_ideas = []
  part_pairs = [(init_persona, target_persona), 
                (target_persona, init_persona)]
  for p_1, p_2 in part_pairs: 
    focal_points = [f"{p_2.scratch.name}"]
    retrieved = new_retrieve(p_1, focal_points, 50)
    relationship = generate_summarize_agent_relationship(p_1, p_2, retrieved)
    focal_points = [f"{relationship}", 
                    f"{p_2.scratch.name} is {p_2.scratch.act_description}"]
    retrieved = new_retrieve(p_1, focal_points, 25)
    summarized_idea = generate_agent_chat_summarize_ideas(p_1, p_2, retrieved, curr_context)
    summarized_ideas += [summarized_idea]

  return generate_agent_chat(maze, init_persona, target_persona, 
                      curr_context, 
                      summarized_ideas[0], 
                      summarized_ideas[1])


def generate_one_utterance(maze, init_persona, target_persona, retrieved, curr_chat): 
  # Chat version optimized for speed via batch generation
  curr_context = (f"{init_persona.scratch.name} " + 
              f"was {init_persona.scratch.act_description} " + 
              f"when {init_persona.scratch.name} " + 
              f"saw {target_persona.scratch.name} " + 
              f"in the middle of {target_persona.scratch.act_description}.\n")
  curr_context += (f"{init_persona.scratch.name} " +
              f"is initiating a conversation with " +
              f"{target_persona.scratch.name}.")

  print ("July 23 5")
  x = run_gpt_generate_iterative_chat_utt(maze, init_persona, target_persona, retrieved, curr_context, curr_chat)[0]

  print ("July 23 6")

  print ("adshfoa;khdf;fajslkfjald;sdfa HERE", x)

  return x["utterance"], x["end"]

def agent_chat_v2(maze, init_persona, target_persona): 
  curr_chat = []
  print ("July 23")

  for i in range(8): 
    focal_points = [f"{target_persona.scratch.name}"]
    retrieved = new_retrieve(init_persona, focal_points, 50)
    relationship = generate_summarize_agent_relationship(init_persona, target_persona, retrieved)
    print ("-------- relationshopadsjfhkalsdjf", relationship)
    last_chat = ""
    for i in curr_chat[-4:]:
      last_chat += ": ".join(i) + "\n"
    if last_chat: 
      focal_points = [f"{relationship}", 
                      f"{target_persona.scratch.name} is {target_persona.scratch.act_description}", 
                      last_chat]
    else: 
      focal_points = [f"{relationship}", 
                      f"{target_persona.scratch.name} is {target_persona.scratch.act_description}"]
    retrieved = new_retrieve(init_persona, focal_points, 15)
    utt, end = generate_one_utterance(maze, init_persona, target_persona, retrieved, curr_chat)

    curr_chat += [[init_persona.scratch.name, utt]]
    if end:
      break


    focal_points = [f"{init_persona.scratch.name}"]
    retrieved = new_retrieve(target_persona, focal_points, 50)
    relationship = generate_summarize_agent_relationship(target_persona, init_persona, retrieved)
    print ("-------- relationshopadsjfhkalsdjf", relationship)
    last_chat = ""
    for i in curr_chat[-4:]:
      last_chat += ": ".join(i) + "\n"
    if last_chat: 
      focal_points = [f"{relationship}", 
                      f"{init_persona.scratch.name} is {init_persona.scratch.act_description}", 
                      last_chat]
    else: 
      focal_points = [f"{relationship}", 
                      f"{init_persona.scratch.name} is {init_persona.scratch.act_description}"]
    retrieved = new_retrieve(target_persona, focal_points, 15)
    utt, end = generate_one_utterance(maze, target_persona, init_persona, retrieved, curr_chat)

    curr_chat += [[target_persona.scratch.name, utt]]
    if end:
      break

  print ("July 23 PU")
  for row in curr_chat: 
    print (row)
  print ("July 23 FIN")

  return curr_chat






def generate_summarize_ideas(persona, nodes, question): 
  statements = ""
  for n in nodes:
    statements += f"{n.embedding_key}\n"
  summarized_idea = run_gpt_prompt_summarize_ideas(persona, statements, question)[0]
  return summarized_idea


def generate_next_line(persona, interlocutor_desc, curr_convo, summarized_idea):
  # Original chat -- line by line generation 
  prev_convo = ""
  for row in curr_convo: 
    prev_convo += f'{row[0]}: {row[1]}\n'

  next_line = run_gpt_prompt_generate_next_convo_line(persona, 
                                                      interlocutor_desc, 
                                                      prev_convo, 
                                                      summarized_idea)[0]  
  return next_line


def generate_inner_thought(persona, whisper):
  inner_thought = run_gpt_prompt_generate_whisper_inner_thought(persona, whisper)[0]
  return inner_thought


# =============================================================================
# GROUP CONVERSATION SYSTEM
# =============================================================================

def generate_group_context(group_members, current_activity=None):
  """
  Generates a context string describing the group situation.
  
  INPUT:
    group_members: List of persona objects in the group
    current_activity: Optional description of what the group is doing
  OUTPUT:
    context: String describing the group context
  """
  member_names = [p.scratch.name for p in group_members]
  
  if len(member_names) == 2:
    names_str = f"{member_names[0]} and {member_names[1]}"
  else:
    names_str = ", ".join(member_names[:-1]) + f", and {member_names[-1]}"
  
  context = f"A group consisting of {names_str} has gathered together."
  
  # Add what each person was doing
  for persona in group_members:
    context += f"\n{persona.scratch.name} was {persona.scratch.act_description}."
  
  if current_activity:
    context += f"\nThe group is now {current_activity}."
  
  return context


def select_next_speaker(group_members, curr_chat, last_speaker=None):
  """
  Determines who should speak next in a group conversation.
  Uses a combination of turn-taking rules and relevance.
  
  INPUT:
    group_members: List of persona objects in the group
    curr_chat: Current conversation history [(speaker_name, utterance), ...]
    last_speaker: Name of the person who spoke last
  OUTPUT:
    next_speaker: The persona object who should speak next
  """
  if not curr_chat:
    # First speaker - choose randomly
    return random.choice(group_members)
  
  # Get names of recent speakers (last 3 turns)
  recent_speakers = [turn[0] for turn in curr_chat[-3:]]
  
  # Candidates: those who haven't spoken recently
  candidates = [p for p in group_members 
                if p.scratch.name not in recent_speakers]
  
  # If everyone has spoken recently, anyone except last speaker can go
  if not candidates:
    candidates = [p for p in group_members 
                  if p.scratch.name != last_speaker]
  
  # If still no candidates (shouldn't happen), return any except last speaker
  if not candidates:
    candidates = [p for p in group_members 
                  if p.scratch.name != last_speaker]
    if not candidates:
      candidates = group_members
  
  # Weighted selection based on personality (more extroverted = more likely)
  # For now, use random selection
  return random.choice(candidates)


def generate_group_utterance(maze, speaking_persona, group_members, 
                              retrieved, curr_chat, group_context):
  """
  Generates an utterance for a speaker in a group conversation.
  
  INPUT:
    maze: The maze object
    speaking_persona: The persona who is speaking
    group_members: All personas in the group
    retrieved: Retrieved memories for the speaking persona
    curr_chat: Current conversation history
    group_context: Context string describing the group situation
  OUTPUT:
    utterance: The generated utterance string
    end: Boolean indicating if the conversation should end
  """
  # Build the prompt context
  other_members = [p for p in group_members if p != speaking_persona]
  other_names = [p.scratch.name for p in other_members]
  
  # Get relationship summaries with each group member
  relationships = {}
  for other in other_members:
    focal_points = [f"{other.scratch.name}"]
    rel_retrieved = new_retrieve(speaking_persona, focal_points, 25)
    relationship = generate_summarize_agent_relationship(
        speaking_persona, other, rel_retrieved)
    relationships[other.scratch.name] = relationship
  
  # Build conversation history string
  chat_history = ""
  for speaker, utterance in curr_chat[-6:]:  # Last 6 turns
    chat_history += f"{speaker}: {utterance}\n"
  
  # Build the full context
  full_context = f"{group_context}\n\n"
  full_context += f"{speaking_persona.scratch.name}'s relationships:\n"
  for name, rel in relationships.items():
    full_context += f"- {name}: {rel}\n"
  
  if chat_history:
    full_context += f"\nConversation so far:\n{chat_history}"
  
  # Use existing utterance generation with group context
  # For now, use a simplified version
  try:
    # Get summarized ideas based on the conversation
    all_embedding_keys = []
    for key, val in retrieved.items():
      for i in val:
        all_embedding_keys.append(i.embedding_key)
    
    # Simple utterance generation
    if len(curr_chat) > 10:
      # Conversation has gone on long enough
      utterance = "Well, it was great chatting with everyone. I should get going."
      end = True
    else:
      # Generate a response based on context
      # Use the first retrieved memory as inspiration if available
      if all_embedding_keys:
        topic = all_embedding_keys[0]
        utterance = f"That reminds me of something - {topic[:100]}..."
      else:
        utterance = "That's an interesting point."
      end = False
      
      # Add some randomness to end conversations
      if random.random() < 0.1 and len(curr_chat) > 3:
        end = True
  except Exception as e:
    print(f"Error generating group utterance: {e}")
    utterance = "I see what you mean."
    end = False
  
  return utterance, end


def agent_group_chat(maze, group_members, max_turns=15, topic=None):
  """
  Generates a multi-agent group conversation.
  
  INPUT:
    maze: The maze object
    group_members: List of persona objects participating in the group chat
    max_turns: Maximum number of turns in the conversation
    topic: Optional initial topic for discussion
  OUTPUT:
    curr_chat: List of tuples [(speaker_name, utterance), ...]
  """
  if len(group_members) < 2:
    return []
  
  curr_chat = []
  group_context = generate_group_context(group_members, topic)
  
  print(f"Starting group chat with {len(group_members)} members")
  
  last_speaker = None
  
  for turn in range(max_turns):
    # Select next speaker
    speaker = select_next_speaker(group_members, curr_chat, last_speaker)
    speaker_name = speaker.scratch.name
    
    # Build focal points for retrieval
    other_names = [p.scratch.name for p in group_members if p != speaker]
    focal_points = other_names.copy()
    
    # Add recent chat as focal point
    if curr_chat:
      last_utterances = [f"{s}: {u}" for s, u in curr_chat[-3:]]
      focal_points.extend(last_utterances)
    
    if topic:
      focal_points.append(topic)
    
    # Retrieve relevant memories
    retrieved = new_retrieve(speaker, focal_points, 30)
    
    # Generate utterance
    utterance, end = generate_group_utterance(
        maze, speaker, group_members, retrieved, curr_chat, group_context)
    
    curr_chat.append((speaker_name, utterance))
    last_speaker = speaker_name
    
    print(f"  {speaker_name}: {utterance}")
    
    if end:
      print(f"Conversation ended after {turn + 1} turns")
      break
  
  return curr_chat


def generate_group_discussion_summary(group_members, curr_chat):
  """
  Generates a summary of a group discussion for memory storage.
  
  INPUT:
    group_members: List of persona objects in the group
    curr_chat: The conversation history
  OUTPUT:
    summary: String summarizing the key points of the discussion
  """
  member_names = [p.scratch.name for p in group_members]
  
  if not curr_chat:
    return f"Brief gathering of {', '.join(member_names)}"
  
  # Extract key utterances (first and last, plus any long ones)
  key_utterances = []
  if curr_chat:
    key_utterances.append(curr_chat[0])
    if len(curr_chat) > 1:
      key_utterances.append(curr_chat[-1])
    # Add any longer utterances (might contain important info)
    for speaker, utt in curr_chat:
      if len(utt) > 50 and (speaker, utt) not in key_utterances:
        key_utterances.append((speaker, utt))
        if len(key_utterances) >= 4:
          break
  
  # Build summary
  summary = f"Group conversation involving {', '.join(member_names)}. "
  if key_utterances:
    summary += "Key points discussed: "
    for speaker, utt in key_utterances[:3]:
      summary += f"{speaker} said '{utt[:50]}...' "
  
  return summary


def update_group_relationships(group_members, curr_chat):
  """
  Updates relationship scores between group members after a conversation.
  
  INPUT:
    group_members: List of persona objects in the group
    curr_chat: The conversation that occurred
  """
  if not curr_chat:
    return
  
  # Count how many turns each person spoke
  speaker_counts = {}
  for speaker, _ in curr_chat:
    speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
  
  # Update relationship scores for each pair of members
  for i, persona_a in enumerate(group_members):
    for persona_b in group_members[i+1:]:
      # Base relationship boost from being in conversation together
      boost = 0.01 * len(curr_chat)  # Small boost per turn
      
      # Additional boost if they both participated
      if (persona_a.scratch.name in speaker_counts and 
          persona_b.scratch.name in speaker_counts):
        boost += 0.02
      
      # Cap the boost
      boost = min(boost, 0.1)
      
      # Update both personas' relationship scores
      current_a = persona_a.scratch.relationship_scores.get(
          persona_b.scratch.name, 0.3)  # Default to 0.3 (acquaintance)
      persona_a.scratch.relationship_scores[persona_b.scratch.name] = min(
          1.0, current_a + boost)
      
      current_b = persona_b.scratch.relationship_scores.get(
          persona_a.scratch.name, 0.3)
      persona_b.scratch.relationship_scores[persona_a.scratch.name] = min(
          1.0, current_b + boost)


def store_group_conversation_memory(group_members, curr_chat, maze):
  """
  Stores the group conversation in each participant's memory.
  
  INPUT:
    group_members: List of persona objects in the group
    curr_chat: The conversation history
    maze: The maze object (for location context)
  """
  if not curr_chat or not group_members:
    return
  
  summary = generate_group_discussion_summary(group_members, curr_chat)
  member_names = [p.scratch.name for p in group_members]
  
  for persona in group_members:
    # Create a group chat event
    other_names = [n for n in member_names if n != persona.scratch.name]
    
    if len(other_names) == 1:
      subject = persona.scratch.name
      predicate = "had a group chat with"
      obj = other_names[0]
    else:
      subject = persona.scratch.name
      predicate = "had a group chat with"
      obj = f"{', '.join(other_names[:-1])}, and {other_names[-1]}"
    
    description = summary
    
    # Add to persona's memory
    keywords = set(member_names)
    keywords.add("group chat")
    keywords.add("conversation")
    
    # Get embedding for the summary
    try:
      from persona.prompt_template.gpt_structure import get_embedding
      if summary in persona.a_mem.embeddings:
        event_embedding = persona.a_mem.embeddings[summary]
      else:
        event_embedding = get_embedding(summary)
      event_embedding_pair = (summary, event_embedding)
      
      # Add as a chat event
      persona.a_mem.add_chat(
          persona.scratch.curr_time, 
          None,
          subject, 
          predicate, 
          obj,
          description, 
          keywords, 
          5,  # Moderate poignancy for group chats
          event_embedding_pair,
          curr_chat
      )
    except Exception as e:
      print(f"Error storing group chat memory for {persona.scratch.name}: {e}")


def propagate_information_in_group(group_members, information, source_persona):
  """
  Simulates information spreading through a group conversation.
  Each member may remember the information with some distortion.
  
  INPUT:
    group_members: List of persona objects in the group
    information: The piece of information to spread
    source_persona: The persona who shared the information
  """
  for persona in group_members:
    if persona == source_persona:
      continue
    
    # Determine if this persona will remember the information
    # Based on relationship strength with source
    rel_strength = persona.scratch.relationship_scores.get(
        source_persona.scratch.name, 0.3)
    
    # Higher relationship = better retention
    if random.random() < rel_strength:
      # Store with attribution
      description = f"Heard from {source_persona.scratch.name}: {information}"
      
      keywords = set()
      keywords.add(source_persona.scratch.name)
      keywords.add("heard")
      keywords.add("gossip")
      
      # Information may be slightly distorted (simulated by truncation)
      if random.random() < 0.3:
        # Some distortion
        if len(information) > 20:
          description = f"Heard something from {source_persona.scratch.name} about: {information[:20]}..."
      
      # Note: Actual memory storage would happen through proper memory system
      # This is a placeholder for the propagation logic
      if not hasattr(persona.scratch, 'heard_information'):
        persona.scratch.heard_information = []
      persona.scratch.heard_information.append({
          "source": source_persona.scratch.name,
          "info": description,
          "distorted": random.random() < 0.3
      })


def generate_action_event_triple(act_desp, persona): 
  """TODO 

  INPUT: 
    act_desp: the description of the action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT: 
    a string of emoji that translates action description.
  EXAMPLE OUTPUT: 
    "🧈🍞"
  """
  if debug: print ("GNS FUNCTION: <generate_action_event_triple>")
  return run_gpt_prompt_event_triple(act_desp, persona)[0]


def generate_poig_score(persona, event_type, description): 
  if debug: print ("GNS FUNCTION: <generate_poig_score>")

  if "is idle" in description: 
    return 1

  if event_type == "event" or event_type == "thought": 
    return run_gpt_prompt_event_poignancy(persona, description)[0]
  elif event_type == "chat": 
    return run_gpt_prompt_chat_poignancy(persona, 
                           persona.scratch.act_description)[0]


def load_history_via_whisper(personas, whispers):
  for count, row in enumerate(whispers): 
    persona = personas[row[0]]
    whisper = row[1]

    thought = generate_inner_thought(persona, whisper)

    created = persona.scratch.curr_time
    expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
    s, p, o = generate_action_event_triple(thought, persona)
    keywords = set([s, p, o])
    thought_poignancy = generate_poig_score(persona, "event", whisper)
    thought_embedding_pair = (thought, get_embedding(thought))
    persona.a_mem.add_thought(created, expiration, s, p, o, 
                              thought, keywords, thought_poignancy, 
                              thought_embedding_pair, None)


def open_convo_session(persona, convo_mode): 
  if convo_mode == "analysis": 
    curr_convo = []
    interlocutor_desc = "Interviewer"

    while True: 
      line = input("Enter Input: ")
      if line == "end_convo": 
        break

      if int(run_gpt_generate_safety_score(persona, line)[0]) >= 8: 
        print (f"{persona.scratch.name} is a computational agent, and as such, it may be inappropriate to attribute human agency to the agent in your communication.")        

      else: 
        retrieved = new_retrieve(persona, [line], 50)[line]
        summarized_idea = generate_summarize_ideas(persona, retrieved, line)
        curr_convo += [[interlocutor_desc, line]]

        next_line = generate_next_line(persona, interlocutor_desc, curr_convo, summarized_idea)
        curr_convo += [[persona.scratch.name, next_line]]


  elif convo_mode == "whisper": 
    whisper = input("Enter Input: ")
    thought = generate_inner_thought(persona, whisper)

    created = persona.scratch.curr_time
    expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
    s, p, o = generate_action_event_triple(thought, persona)
    keywords = set([s, p, o])
    thought_poignancy = generate_poig_score(persona, "event", whisper)
    thought_embedding_pair = (thought, get_embedding(thought))
    persona.a_mem.add_thought(created, expiration, s, p, o, 
                              thought, keywords, thought_poignancy, 
                              thought_embedding_pair, None)
































