(define (domain varnack-problem)
  (:requirements :strips :typing :adl)
  (:types hero location sword dragon)
  (:predicates
    (at ?x - object ?loc - location)
    (carrying ?a - agent ?o - object)
    (defeated ?d - dragon))
  (:action move-hero
    :parameters (?from - location ?to - location)
    :precondition (and (at hero ?from))
    :effect (and (not (at hero ?from)) (at hero ?to)))
  (:action pick-up-sword
    :parameters (?x - hero ?y - sword)
    :precondition (and (at ?x ?y) (at ?y ?to))
    :effect (carrying ?x ?y))
  (:action defeat-ice-dragon
    :parameters (?z - hero ?w - dragon)
    :precondition (and (at ?z ?w))
    :effect (defeated ?w)))