"""
File: create_sim.py
Description: Bootstrap script for creating a new simulation from a scenario
definition. This replaces the manual workflow of copying a base-simulation
folder and editing meta.json by hand.

Usage:
  python create_sim.py --scenario <scenario_name_or_path> --name <new_sim_name>

Example:
  python create_sim.py --scenario base_the_ville_isabella_maria_klaus --name my_sim

The --scenario argument accepts either:
  - A bare scenario name (looked up in static_dirs/assets/scenarios/)
  - A path to a scenario JSON file

Run from the reverie/backend_server directory, the same place you run reverie.py.
"""
import argparse
import json
import os
import shutil
import sys


# ---------------------------------------------------------------------------
# Import the path constants from utils.py (same as reverie.py does).
# utils.py is not committed to the repo; each user creates it themselves.
# ---------------------------------------------------------------------------
try:
    from utils import maze_assets_loc, fs_storage
except ImportError:
    print("ERROR: utils.py not found.")
    print("Please create reverie/backend_server/utils.py as described in README.md.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Derived asset paths (mirrors what utils.py would normally provide)
# ---------------------------------------------------------------------------
AGENT_TEMPLATES_DIR = os.path.join(maze_assets_loc, "agent_templates")
ARENAS_DIR          = os.path.join(maze_assets_loc, "arenas")
SCENARIOS_DIR       = os.path.join(maze_assets_loc, "scenarios")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_scenario(scenario_arg):
    """
    Load and return a scenario dict.

    Accepts either a bare name (looked up in SCENARIOS_DIR) or a file path.
    """
    # Treat as a path if it ends with .json or contains a directory separator
    if os.path.sep in scenario_arg or scenario_arg.endswith(".json"):
        scenario_path = scenario_arg
    else:
        scenario_path = os.path.join(SCENARIOS_DIR, f"{scenario_arg}.json")

    if not os.path.isfile(scenario_path):
        print(f"ERROR: Scenario file not found: {scenario_path}")
        sys.exit(1)

    with open(scenario_path) as f:
        return json.load(f)


def load_arena_config(arena_name):
    """Return the arena config dict for the given arena name."""
    config_path = os.path.join(ARENAS_DIR, arena_name, "config.json")
    if not os.path.isfile(config_path):
        print(f"ERROR: Arena config not found: {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)


def _build_scratch_from_template(template_data):
    """
    Merge a scratch_template.json with the ephemeral runtime fields that the
    Scratch class expects to find in a freshly-bootstrapped scratch.json.

    The template holds only stable identity / personality fields; this
    function adds back the ephemeral fields initialised to their zero values.
    """
    agent_name = template_data["name"]
    scratch = dict(template_data)  # copy all personality fields

    # Runtime / ephemeral state — initialised exactly as the Scratch class
    # would on a brand-new persona
    scratch.update({
        "curr_time": None,
        "curr_tile": None,
        "daily_req": [],
        "f_daily_schedule": [],
        "f_daily_schedule_hourly_org": [],
        "act_address": None,
        "act_start_time": None,
        "act_duration": None,
        "act_description": None,
        "act_pronunciatio": None,
        "act_event": [agent_name, None, None],
        "act_obj_description": None,
        "act_obj_pronunciatio": None,
        "act_obj_event": [None, None, None],
        "chatting_with": None,
        "chat": None,
        "chatting_with_buffer": {},
        "chatting_end_time": None,
        "act_path_set": False,
        "planned_path": [],
    })
    return scratch


def create_simulation(scenario, sim_name):
    """
    Build a complete simulation folder at fs_storage/<sim_name>/ from the
    given scenario dict.

    Folder layout created:
        <sim_name>/
            reverie/meta.json
            environment/0.json
            personas/<agent_name>/bootstrap_memory/
                scratch.json
                spatial_memory.json
                associative_memory/
            movement/          (empty; written by the server at runtime)
    """
    sim_folder = os.path.join(fs_storage, sim_name)

    if os.path.exists(sim_folder):
        print(f"ERROR: Simulation folder already exists: {sim_folder}")
        print("Choose a different name or delete the existing folder first.")
        sys.exit(1)

    arena_name   = scenario["arena"]
    start_date   = scenario["start_date"]
    sec_per_step = scenario.get("sec_per_step", 10)
    agents       = scenario["agents"]

    arena_config = load_arena_config(arena_name)
    maze_name    = arena_config["maze_name"]

    # --- Create directory skeleton ----------------------------------------
    os.makedirs(os.path.join(sim_folder, "reverie"))
    os.makedirs(os.path.join(sim_folder, "environment"))
    os.makedirs(os.path.join(sim_folder, "movement"))

    # --- reverie/meta.json ------------------------------------------------
    persona_names = [a["template"] for a in agents]
    meta = {
        "fork_sim_code": sim_name,   # self-referential for a fresh sim
        "start_date": start_date,
        "curr_time": f"{start_date}, 00:00:00",
        "sec_per_step": sec_per_step,
        "maze_name": maze_name,
        "persona_names": persona_names,
        "step": 0,
    }
    with open(os.path.join(sim_folder, "reverie", "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # --- environment/0.json  (initial agent tile positions) ---------------
    env_0 = {}
    for agent_entry in agents:
        name  = agent_entry["template"]
        spawn = agent_entry.get("spawn",
                                arena_config["default_spawn_points"]["default"])
        env_0[name] = {"maze": maze_name, "x": spawn[0], "y": spawn[1]}

    with open(os.path.join(sim_folder, "environment", "0.json"), "w") as f:
        json.dump(env_0, f, indent=2)

    # --- personas/<Name>/bootstrap_memory/ --------------------------------
    for agent_entry in agents:
        name          = agent_entry["template"]
        template_dir  = os.path.join(AGENT_TEMPLATES_DIR, name)

        if not os.path.isdir(template_dir):
            print(f"ERROR: Agent template not found: {template_dir}")
            shutil.rmtree(sim_folder)   # clean up partial work
            sys.exit(1)

        bootstrap_dir = os.path.join(
            sim_folder, "personas", name, "bootstrap_memory")
        os.makedirs(bootstrap_dir)

        # scratch.json — merge template with ephemeral runtime fields
        scratch_template_path = os.path.join(
            template_dir, "scratch_template.json")
        with open(scratch_template_path) as f:
            template_data = json.load(f)
        scratch = _build_scratch_from_template(template_data)
        with open(os.path.join(bootstrap_dir, "scratch.json"), "w") as f:
            json.dump(scratch, f, indent=2)

        # spatial_memory.json
        shutil.copy(
            os.path.join(template_dir, "spatial_memory.json"),
            os.path.join(bootstrap_dir, "spatial_memory.json"))

        # associative_memory/ directory
        shutil.copytree(
            os.path.join(template_dir, "associative_memory"),
            os.path.join(bootstrap_dir, "associative_memory"))

    print(f"Simulation '{sim_name}' created successfully at:")
    print(f"  {sim_folder}")
    print()
    print("To run it, start reverie.py and enter:")
    print(f"  Fork simulation : {sim_name}")
    print(f"  New simulation  : <choose a run name>")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Create a new Reverie simulation from a scenario file.")
    parser.add_argument(
        "--scenario", "-s", required=True,
        help=("Scenario name (looked up in assets/scenarios/) "
              "or path to a scenario JSON file."))
    parser.add_argument(
        "--name", "-n", required=True,
        help="Name of the new simulation to create (must not already exist).")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    create_simulation(scenario, args.name)


if __name__ == "__main__":
    main()
