(define (domain world_travel)
    (:requirements :strips)
    (:types city agent)
    (:predicates
      (at ?a - agent ?c - city)
      (connected ?c1 - city ?c2 - city)
    )

    (:action travel
      :parameters (?a - agent ?c1 - city ?c2 - city)
      :precondition (and (at ?a ?c1) (connected ?c1 ?c2))
      :effect (and (not (at ?a ?c1)) (at ?a ?c2))
    )
  )