(define (domain astronaut_collect)
  (:requirements :strips :typing)
  (:types agent object location)
  (:predicates
    (at ?x - object ?loc - location)
    (has ?a - agent ?o - object))
  (:action move
    :parameters (?obj - object ?from - location ?to - location)
    :precondition (and (at ?obj ?from) (not (at ?obj ?to)))
    :effect (and (not (at ?obj ?from)) (at ?obj ?to)))
  (:action pickup
    :parameters (?a - agent ?o - object)
    :precondition (and (at ?a ?o) (at ?o ?a))
    :effect (has ?a ?o)))