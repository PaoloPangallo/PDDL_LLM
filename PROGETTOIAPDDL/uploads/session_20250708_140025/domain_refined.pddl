(define (domain heroic-mission)
  (:requirements :strips :typing)
  (:types agent location object monster)
  (:predicates
    (at ?h - agent ?l - location)
    (on_ground ?s - object ?l - location)
    (sleeping ?d - monster)
    (defeated ?d - monster)
    (carrying ?h - agent ?s - object) ; Resolved error: predicate carrying declared
  )
  (:action move
    :parameters (?h - agent ?from - location ?to - location)
    :precondition (and (at ?h ?from)) ; Resolved error: ?h parameter added
    :effect (and (not (at ?h ?from)) (at ?h ?to))
  )
  (:action pickup
    :parameters (?h - agent ?s - object ?l - location)
    :precondition (and (at ?h ?l) (on_ground ?s ?l)) ; Resolved error: ?h parameter added
    :effect (and (carrying ?h ?s) (not (on_ground ?s ?l)))
  )
  (:action defeat
    :parameters (?h - agent ?d - monster ?l - location)
    :precondition (and (at ?h ?l) (carrying ?h sword_of_fire) (sleeping ?d)) ; Resolved error: ?h parameter added
    :effect (and (defeated ?d) (not (sleeping ?d)))
  )
)