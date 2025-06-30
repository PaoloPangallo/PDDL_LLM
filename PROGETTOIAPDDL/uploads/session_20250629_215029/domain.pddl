(define (domain robot_world)
    (:requirements :strips)
    (:types robot block goal)
    (:predicates
      (at ?r - robot ?l - location)
      (has-block ?r - robot)
      (on ?b - block ?r - robot)
      (at_goal ?g - goal)
    )

    (:action move
      :parameters (?r - robot ?from - location ?to - location)
      :precondition (and (at ?r ?from) (not (on ?b ?r)))
      :effect (and (not (at ?r ?from)) (at ?r ?to))
    )

    (:action pick_block
      :parameters (?r - robot ?b - block)
      :precondition (and (at ?r ?l) (on ?b ?r))
      :effect (has-block ?r)
    )

    (:action place_block
      :parameters (?r - robot ?b - block ?g - goal)
      :precondition (and (has-block ?r) (at ?r ?l) (at_goal ?g))
      :effect (and (not (has-block ?r)) (on ?b ?g))
    )
  )