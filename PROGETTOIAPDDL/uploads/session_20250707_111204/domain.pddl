(define (domain collect_sample)
  (:requirements :strips :typing)
  (:types agent object location vehicle)
  (:predicates
    (at ?x - object ?loc - location)
    (has ?a - agent ?o - object))
  (:action move
    :parameters (?r - vehicle ?from - location ?to - location)
    :precondition (and (at ?r ?from) (not (at ?r ?from)))
    :effect (and (not (at ?r ?from)) (at ?r ?to)))
  (:action pickup
    :parameters (?a - agent ?o - object ?loc - location)
    :precondition (and (at ?a ?loc) (at ?o ?loc))
    :effect (has ?a ?o)))