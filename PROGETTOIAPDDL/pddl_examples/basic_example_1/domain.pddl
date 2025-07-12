(define (domain move-agent)
  (:requirements :strips)
  (:predicates
    (at ?x)
    (connected ?from ?to)
  )

  (:action move
    :parameters (?from ?to)
    :precondition (and (at ?from) (connected ?from ?to))
    :effect (and (not (at ?from)) (at ?to))
  )
)