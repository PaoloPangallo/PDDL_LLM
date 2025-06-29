(define (domain simple-robot)
    (:requirements :strips)
    (:types robot location block)
    (:predicates
      (at ?r - robot ?l - location)
      (on ?r - robot ?b - block)
      (clear ?l - location)
    )

    (:action pickup
      :parameters (?r - robot ?b - block)
      :precondition (and (at ?r ?l) (on ?b nil) (clear ?l))
      :effect (not (clear ?l)) (on ?r ?b)
    )

    (:action putdown
      :parameters (?r - robot ?b - block)
      :precondition (and (at ?r ?l) (on ?r ?b))
      :effect (on ?b nil) (clear ?l)
    )

    (:action move-to
      :parameters (?r - robot ?from - location ?to - location)
      :precondition (and (at ?r ?from) (clear ?to))
      :effect (not (at ?r ?from)) (at ?r ?to)
    )
  )