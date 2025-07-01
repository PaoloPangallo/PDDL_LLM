(define (domain warehouse)
  (:requirements :strips :typing)
  (:types
    warehouse
    box
    worker
  )
  (:predicates
    (at ?worker ?warehouse)
    (has_box ?worker ?box)
    (in ?box ?warehouse)
  )
  (:action move
    :parameters (?worker ?from ?to)
    :precondition (and (at ?worker ?from) (has_box ?worker ?box))
    :effect (and (not (at ?worker ?from)) (at ?worker ?to))
  )
  (:action pick
    :parameters (?worker ?box)
    :precondition (and (at ?worker ?warehouse) (in ?box ?warehouse))
    :effect (and (has_box ?worker ?box) (not (in ?box ?warehouse)))
  )
  (:action drop
    :parameters (?worker ?box)
    :precondition (and (at ?worker ?warehouse) (has_box ?worker ?box))
    :effect (and (not (has_box ?worker ?box)) (in ?box ?warehouse))
  )
)