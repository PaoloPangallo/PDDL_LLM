(define (domain robot-world)
    (:requirements :strips)
    (:types robot location block)
    (:predicates
      (at ?r - robot ?l - location)
      (on ?r - robot ?b - block)
      (clear ?l - location)
    )

    (:action move-robot
      :parameters (?r - robot ?from - location ?to - location)
      :precondition (and (at ?r ?from) (clear ?to))
      :effect (and (not (at ?r ?from)) (at ?r ?to) (clear ?from))
    )

    (:action pick-up
      :parameters (?r - robot ?b - block)
      :precondition (and (at ?r ?l) (on ?l ?b))
      :effect (and (not (on ?l ?b)) (on ?r ?b))
    )

    (:action put-down
      :parameters (?r - robot ?b - block)
      :precondition (and (at ?r ?l) (on ?r ?b))
      :effect (and (not (on ?r ?b)) (on ?l ?b))
    )
  )