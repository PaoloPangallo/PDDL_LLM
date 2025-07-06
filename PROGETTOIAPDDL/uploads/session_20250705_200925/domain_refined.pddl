(define (domain astronaut_rover)
  (:requirements :strips :typing)
  (:types agent rover location sample)
  (:predicates
    (at ?x - object ?loc - location)
    (has ?a - agent ?o - object))
  (:action move
    :parameters (?r - rover ?from - location ?to - location)
    :precondition (and (at ?r ?from) (at ?r ?to))
    :effect (and (not (at ?r ?from)) (at ?r ?to)))
  (:action pickup
    :parameters (?a - agent ?s - sample ?loc - location)
    :precondition (and (at ?a ?loc) (at ?s ?loc))
    :effect (has ?a ?s)))