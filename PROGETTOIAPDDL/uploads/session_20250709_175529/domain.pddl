(define (domain my-domain)
  (:requirements :strips :typing :conditional-effects)
  (:types entity agent monster location object)
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
    (at         ?e - entity   ?l - location)
    (on_ground  ?o - object   ?l - location)
    (sleeping   ?d - monster)
    (explored   ?l - location)
    (visited    ?l - location)
    (visited-forest)
    (visited-cave)
    (rested     ?h - agent)
    (connected  ?f - location ?t - location)
    (defeated   ?m - monster)
  )

  (:action move
    :parameters (?h - agent ?from - location ?to - location)
    :precondition (and (at ?h ?from) (connected ?from ?to))
    :effect       (and (not (at ?h ?from)) (at ?h ?to))
  )

  (:action carry-and-move
    :parameters (?h - agent ?o - object ?from - location ?to - location)
    :precondition (and (at ?h ?from) (on_ground ?o ?from) (connected ?from ?to))
    :effect       (and (not (at ?h ?from)) (at ?h ?to) (not (on_ground ?o ?from)) (on_ground ?o ?to))
  )

  (:action explore
    :parameters (?h - agent ?l - location)
    :precondition (and (at ?h ?l) (not (visited ?l)))
    :effect       (and (explored ?l) (visited ?l) (when (and (at ?h forest)    (explored forest))   (visited-forest)) (when (and (at ?h dark_cave) (explored dark_cave))(visited-cave)))
  )

  (:action rest
    :parameters (?h - agent ?l - location)
    :precondition (and (at ?h ?l))
    :effect       (and (rested ?h))
  )

  (:action defeat-forest
    :parameters (?h - agent ?b - monster)
    :precondition (and (at ?h forest) (at ?b forest))
    :effect       (and (defeated ?b))
  )

  (:action defeat-cave
    :parameters (?h - agent ?g - monster)
    :precondition (and (at ?h dark_cave) (at ?g dark_cave))
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