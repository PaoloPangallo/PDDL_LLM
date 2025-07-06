(define (domain varnack-problem)
  (:requirements :strips :typing :adl)
  (:types agent object location vehicle)
  (:predicates
    (at ?x - agent ?y - location)
    (has ?a - agent ?o - object))
  (:action move
    :parameters (?r - agent ?from - location ?to - location)
    :precondition (and (at ?r ?from))
    :effect (and (not (at ?r ?from)) (at ?r ?to)))
  (:action pickup
    :parameters (?r - agent ?p - object ?loc - location)
    :precondition (and (at ?r ?loc) (at ?p ?loc))
    :effect (has ?r ?p)))