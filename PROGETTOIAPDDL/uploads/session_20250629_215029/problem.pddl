(define (problem robots_puzzle)
    (:domain robot_world)
    (:objects
      robot1 - robot
      block1 block2 block3 goal - location
    )
    (:init
      (at robot1 start)
      (on block1 start)
      (at_goal goal)
    )
    (:goal (and (or (not (on block1 start)) (or (on block2 start) (on block3 start))) (at_goal goal)))
  )