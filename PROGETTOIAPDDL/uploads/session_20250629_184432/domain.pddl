(define (domain simple_world)
    (:requirements :strips)
    (:types agent location object)
    (:predicates
      (at ?a - agent ?l - location)
      (has ?a - agent ?o - object)
      (on ?o - object ?l - location)
    )

    (:action move_agent
      :parameters (?a - agent ?from - location ?to - location)
      :precondition (and (at ?a ?from) (not (on any ?to)))
      :effect (and (not (at ?a ?from)) (at ?a ?to))
    )

    (:action pickup
      :parameters (?a - agent ?o - object)
      :precondition (and (at ?a location) (on ?o location))
      :effect (and (not (on ?o location)) (has ?a ?o))
    )

    (:action place
      :parameters (?a - agent ?o - object ?l - location)
      :precondition (and (has ?a ?o) (not (on any ?l)))
      :effect (and (not (has ?a ?o)) (on ?o ?l))
    )
  )