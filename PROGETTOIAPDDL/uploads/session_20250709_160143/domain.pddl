(define (domain my-domain)
  (:requirements :strips :typing :conditional-effects)
  (:types agent location monster object)

  (:constants
    sword_of_fire - object
    ice_dragon    - monster
    bandit        - monster
    goblin        - monster
    village       - location
    forest        - location
    dark_cave     - location
    tower         - location
  )

  (:predicates
    (at ?h - agent ?l - location)
    (on_ground ?o - object ?l - location)
    (sleeping ?d - monster)
    (explored ?l - location)
    (rested ?h - agent)
    (visited-forest)
    (visited-cave)
    (defeated ?m - monster)
    (ice_dragon ?x - monster)
    (bandit ?x - monster)
    (goblin ?x - monster)
  )

  (:action move
    :parameters (?h    - agent ?from - location ?to   - location)
    :precondition (and (at ?h ?from))
    :effect       (and (not (at ?h ?from)) (at ?h ?to))
  )

  (:action carry-and-move
    :parameters (?h    - agent ?o    - object ?from - location ?to   - location)
    :precondition (and (at ?h ?from) (on_ground ?o ?from))
    :effect       (and (not (at ?h ?from)) (at ?h ?to) (not (on_ground ?o ?from)) (on_ground ?o ?to))
  )

  (:action explore
    :parameters (?h - agent ?l - location)
    :precondition (and (at ?h ?l))
    :effect       (and (explored ?l) (when (and (at ?h forest) (explored forest)) (visited-forest)) (when (and (at ?h dark_cave) (explored dark_cave)) (visited-cave)))
  )

  (:action rest
    :parameters (?h - agent ?l - location)
    :precondition (and (at ?h ?l))
    :effect       (and (rested ?h))
  )

  (:action defeat-forest
    :parameters (?h - agent ?b - monster ?l - location)
    :precondition (and (at ?h ?l) (bandit ?b))
    :effect       (and (defeated ?b))
  )

  (:action defeat-cave
    :parameters (?h - agent ?g - monster ?l - location)
    :precondition (and (at ?h ?l) (goblin ?g))
    :effect       (and (defeated ?g))
  )

  (:action defeat-dragon-via-forest
    :parameters (?h - agent ?d - monster ?l - location)
    :precondition (and (at ?h ?l) (on_ground sword_of_fire ?l) (sleeping ?d) (visited-forest))
    :effect       (and (defeated ?d) (not (sleeping ?d)))
  )

  (:action defeat-dragon-via-cave
    :parameters (?h - agent ?d - monster ?l - location)
    :precondition (and (at ?h ?l) (on_ground sword_of_fire ?l) (sleeping ?d) (visited-cave))
    :effect       (and (defeated ?d) (not (sleeping ?d)))
  )
)