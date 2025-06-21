(define (domain robot-world)
    (:requirements :strips)
    (:types robot block goal position)
    (:predicates
      (at ?r - robot ?p - position)
      (has-block ?r - robot)
      (on ?b - block ?g - goal)
      (goal-reached ?g - goal)
    )

    (:action move
      :parameters (?r - robot ?from - position ?to - position)
      :precondition (and (at ?r ?from) (not (= ?from ?to)))
      :effect (and (not (at ?r ?from)) (at ?r ?to))
    )

    (:action pick-up
      :parameters (?r - robot ?b - block)
      :precondition (and (at ?r (position ?b)) (not (has-block ?r)))
      :effect (and (not (on ?b (position ?r))) (has-block ?r))
    )

    (:action place
      :parameters (?r - robot ?b - block ?g - goal)
      :precondition (and (has-block ?r) (at ?r (position ?g)))
      :effect (and (not (has-block ?r)) (on ?b ?g))
    )
  )

  (:action reach-goal
    :parameters (?r - robot ?g - goal)
    :precondition (and (at ?r (position ?g)) (goal-reached ?g))
    :effect (not (goal-reached ?g))
  )