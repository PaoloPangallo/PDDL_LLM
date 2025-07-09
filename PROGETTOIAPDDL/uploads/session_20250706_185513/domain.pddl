(define (domain SampleCollectDomain)
  (:requirements :strips :typing)
  (:types agent object location)
  (:predicates
    (at ?obj - object ?loc - location)
    (has ?a - agent ?o - object))
  (:action move_to
    :parameters (?obj - object ?from - location ?to - location)
    :precondition (and (at ?obj ?from))
    :effect (and (not (at ?obj ?from)) (at ?obj ?to)))
  (:action pickup
    :parameters (?a - agent ?o - object)
    :precondition (and (at ?a ?o) (at ?o ?a))
    :effect (has ?a ?o))
  (:action dropoff
    :parameters (?a - agent ?o - object)
    :precondition (and (at ?a ?o) (has ?a ?o))
    :effect (not (has ?a ?o))))