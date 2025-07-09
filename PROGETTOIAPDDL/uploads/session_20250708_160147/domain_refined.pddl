(define (domain heroic-quest)
  (:requirements :strips :typing)
  (:types agent location object monster)
  (:predicates
    (at ?h - agent ?l - location)
    (on_ground ?o - object ?l - location)
    (sleeping ?m - monster)
    (defeated ?m - monster)
    (carrying ?h - agent ?s - object)) ; Added predicate carrying
  (:action move
    :parameters (?h - agent ?from - location ?to - location)
    :precondition (and (at ?h ?from))
    :effect (and (not (at ?h ?from)) (at ?h ?to))
  )
  (:action pickup
    :parameters (?h - agent ?s - object ?l - location)
    :precondition (and (at ?h ?l) (on_ground ?s ?l))
    :effect (and (carrying ?h ?s) (not (on_ground ?s ?l)))
  )
  (:action defeat
    :parameters (?h - agent ?d - monster ?l - location)
    :precondition (and (at ?h ?l) (carrying ?h sword_of_fire) (sleeping ?d))
    :effect (and (defeated ?d) (not (sleeping ?d)))
  )
)