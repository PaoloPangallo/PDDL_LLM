(define (domain simple_world)
    (:requirements :strips)
    (:types agent location object)
    (:predicates
      (at ?a - agent ?l - location)
      (has-object ?a - agent ?o - object)
      (at-object ?o - object ?l - location)
    )

    (:action move_agent
      :parameters (?a - agent ?from - location ?to - location)
      :precondition (and (at ?a ?from))
      :effect (and (not (at ?a ?from)) (at ?a ?to)))

    (:action pickup
      :parameters (?a - agent ?o - object)
      :precondition (and (at ?a location) (at-object ?o location))
      :effect (has-object ?a ?o)))