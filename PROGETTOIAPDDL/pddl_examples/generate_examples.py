import os

BASE_DIR = "pddl_examples"

EXAMPLES = {
    "explore_ancient_temple": {
        "domain": """(define (domain temple)
    (:requirements :strips :typing)
    (:types agent room artifact)

    (:predicates
        (at ?a - agent ?r - room)
        (connected ?r1 - room ?r2 - room)
        (has ?a - agent ?o - artifact)
        (artifact_in ?o - artifact ?r - room)
        (door_open ?r1 - room ?r2 - room)
    )

    (:action move
        :parameters (?a - agent ?from - room ?to - room)
        :precondition (and (at ?a ?from) (connected ?from ?to) (door_open ?from ?to))
        :effect (and (not (at ?a ?from)) (at ?a ?to))
    )

    (:action pick
        :parameters (?a - agent ?o - artifact ?r - room)
        :precondition (and (at ?a ?r) (artifact_in ?o ?r))
        :effect (has ?a ?o)
    )

    (:action open-door
        :parameters (?a - agent ?r1 - room ?r2 - room)
        :precondition (at ?a ?r1)
        :effect (door_open ?r1 ?r2)
    )
)""",
        "problem": """(define (problem temple-exploration)
    (:domain temple)
    (:objects
        indiana - agent
        hall chamber treasure_room - room
        idol - artifact
    )
    (:init
        (at indiana hall)
        (connected hall chamber)
        (connected chamber treasure_room)
        (artifact_in idol treasure_room)
    )
    (:goal
        (and (has indiana idol))
    )
)"""
    },
    "rescue_trapped_villager": {
        "domain": """(define (domain rescue)
    (:requirements :strips :typing)
    (:types agent door villager room)

    (:predicates
        (at ?a - agent ?r - room)
        (door_locked ?d - door)
        (door_between ?d - door ?r1 - room ?r2 - room)
        (rescued ?v - villager)
        (villager_in ?v - villager ?r - room)
    )

    (:action unlock
        :parameters (?a - agent ?d - door)
        :precondition (door_locked ?d)
        :effect (not (door_locked ?d))
    )

    (:action move
        :parameters (?a - agent ?from - room ?to - room ?d - door)
        :precondition (and (at ?a ?from) (door_between ?d ?from ?to) (not (door_locked ?d)))
        :effect (and (not (at ?a ?from)) (at ?a ?to))
    )

    (:action rescue
        :parameters (?a - agent ?v - villager ?r - room)
        :precondition (and (at ?a ?r) (villager_in ?v ?r))
        :effect (rescued ?v)
    )
)""",
        "problem": """(define (problem rescue-mission)
    (:domain rescue)
    (:objects
        hero - agent
        d1 - door
        room1 room2 - room
        elsa - villager
    )
    (:init
        (at hero room1)
        (villager_in elsa room2)
        (door_locked d1)
        (door_between d1 room1 room2)
    )
    (:goal (rescued elsa))
)"""
    },
    "collect_magical_artifacts": {
        "domain": """(define (domain artifact-hunt)
    (:requirements :strips :typing)
    (:types agent item location)

    (:predicates
        (at ?a - agent ?l - location)
        (has ?a - agent ?i - item)
        (item_at ?i - item ?l - location)
    )

    (:action move
        :parameters (?a - agent ?from - location ?to - location)
        :precondition (at ?a ?from)
        :effect (and (not (at ?a ?from)) (at ?a ?to))
    )

    (:action collect
        :parameters (?a - agent ?i - item ?l - location)
        :precondition (and (at ?a ?l) (item_at ?i ?l))
        :effect (has ?a ?i)
    )
)""",
        "problem": """(define (problem artifact-hunt-problem)
    (:domain artifact-hunt)
    (:objects
        wizard - agent
        wand orb cloak - item
        cave forest tower - location
    )
    (:init
        (at wizard cave)
        (item_at wand forest)
        (item_at orb tower)
        (item_at cloak cave)
    )
    (:goal
        (and (has wizard wand) (has wizard orb) (has wizard cloak))
    )
)"""
    }
}


def create_example_files():
    os.makedirs(BASE_DIR, exist_ok=True)
    for name, files in EXAMPLES.items():
        example_dir = os.path.join(BASE_DIR, name)
        os.makedirs(example_dir, exist_ok=True)
        with open(os.path.join(example_dir, "domain.pddl"), "w", encoding="utf-8") as f:
            f.write(files["domain"])
        with open(os.path.join(example_dir, "problem.pddl"), "w", encoding="utf-8") as f:
            f.write(files["problem"])
        print(f"✅ Esempio creato: {name}")


if __name__ == "__main__":
    create_example_files()
