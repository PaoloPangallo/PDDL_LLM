(define (problem robot-labyrinth)
    (:domain robot-world)
    (:objects
      robot1 - robot
      start block1 goal1 - goal
      position1 position2 - position
    )
    (:init
      (at robot1 start)
      (on block1 goal1)
      (not (goal-reached goal1))
    )
    (:goal (and (goal-reached goal1)))
  )