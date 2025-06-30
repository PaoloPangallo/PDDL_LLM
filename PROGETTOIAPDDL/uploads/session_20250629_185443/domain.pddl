(define (domain robot-world)
    (:requirements :strips)
    (:types room block goal_block empty)
    (:predicates
      (at ?r - room)
      (on ?b - block ?r - room)
      (goal_location ?g - goal_block)
      (empty ?r - room)
      (connected ?r1 - room ?r2 - room)
    )

    (:action move-robot
      :parameters (?r1 - room ?r2 - room)
      :precondition (and (at ?r1) (empty ?r1) (connected ?r1 ?r2))
      :effect (not (empty ?r1))
      (and (at ?r2) (empty ?r2))
    )

    (:action pick-block
      :parameters (?b - block ?r - room)
      :precondition (and (at ?r) (on ?b ?r))
      :effect (not (on ?b ?r))
      (and (empty ?r) (and (or (= ?b goal_location) (not (= ?b goal_location))) (not (empty ?b))))
    )

    (:action place-block
      :parameters (?b - block ?r - room)
      :precondition (and (not (empty ?b)) (not (on ?b ?r)))
      :effect (not (not (on ?b ?r)))
      (and (empty ?r) (or (= ?b goal_location) (not (= ?b goal_location))))
    )
  )