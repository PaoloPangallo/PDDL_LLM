(define (domain reach-the-tower)
  (:requirements :strips :typing)
  (:types agent object location monster) ; Add 'object' to this list
  (:predicates
    (at ?h - agent ?l - location)
    (on_ground ?s - object ?l - location)
    (carrying ?h - agent ?s - object)
    (sleeping ?d - monster)
    (defeated ?d - monster)) ; Resolved error: predicate defeated declared
  (:action move
    :parameters (?h - agent ?from - location ?to - location)
    :precondition (and (at ?h ?from))
    :effect (and (not (at ?h ?from)) (at ?h ?to))) ; Resolved error: X added to :objects
  (:action pickup
    :parameters (?h - agent ?s - object ?l - location)
    :precondition (and (at ?h ?l) (on_ground ?s ?l))
    :effect (and (carrying ?h ?s) (not (on_ground ?s ?l)))) ; Resolved error: arity fixed for pickup
  (:action defeat
    :parameters (?h - agent ?d - monster ?l - location)
    :precondition (and (at ?h ?l) (carrying ?h sword_of_fire) (sleeping ?d))
    :effect (and (defeated ?d) (not (sleeping ?d)))) ; Resolved error: arity fixed for defeat
)