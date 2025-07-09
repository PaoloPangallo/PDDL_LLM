(define (domain collect_sample)
  (:requirements :strips :typing)
  (:types agent object location)
  (:predicates
    (at ?x - object ?loc - location)
    (has ?a - agent ?o - object))
  (:action move
    :parameters (?r - agent ?from - location ?to - location)
    :precondition (and (at ?r ?from) (at ?r ?from))
    :effect (and (not (at ?r ?from)) (at ?r ?to)))
  (:action pickup
    :parameters (?r - agent ?p - object ?loc - location)
    :precondition (and (at ?r ?loc) (at ?p ?loc))
    :effect (has ?r ?p)))