(define (domain collect_sample)
  (:requirements :strips :typing)
  (:types agent object location vehicle) ; Adding 'vehicle' type as suggested by the validator
  (:predicates
    (at ?x - object ?loc - location)
    (has ?a - agent ?o - object)
    (is-vehicle ?v - vehicle)) ; Declaring a new predicate for vehicles
  (:action move
    :parameters (?r - agent ?from - location ?to - location)
    :precondition (and (at ?r ?from) (is-vehicle ?r) (or (is-rover ?r) (is-car ?r))) ; Added for completeness, adjust as needed
    :effect (and (not (at ?r ?from)) (at ?r ?to)))
  (:action pickup
    :parameters (?r - agent ?p - object ?loc - location)
    :precondition (and (at ?r ?loc) (is-vehicle ?r) (at ?p ?loc)) ; Added for completeness, adjust as needed
    :effect (has ?r ?p)))