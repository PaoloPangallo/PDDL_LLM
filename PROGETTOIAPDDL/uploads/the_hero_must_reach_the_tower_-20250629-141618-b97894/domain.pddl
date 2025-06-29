(define (domain robot-world)
    (:requirements :strips)
    (:types robot wall block goal)
    (:predicates
      (at ?r - robot ?l - location)
      (on ?b - block ?r - robot)
      (clear ?r - robot)
      (at-goal ?r - robot)
    )

    (:action move
      :parameters (?r - robot ?from - location ?to - location)
      :precondition (and (at ?r ?from) (clear ?r))
      :effect (and (not (at ?r ?from)) (at ?r ?to))
    )

    (:action pick-up
      :parameters (?r - robot ?b - block)
      :precondition (and (on ?b ?r) (clear ?r))
      :effect (not (on ?b ?r))
    )

    (:action put-down
      :parameters (?r - robot ?b - block)
      :precondition (and (not (on ?b ?r)))
      :effect (on ?b ?r)
    )

    (:action move-to-goal
      :parameters (?r - robot)
      :precondition (and (at ?r goal))
      :effect (and (at-goal ?r))
    )
  )