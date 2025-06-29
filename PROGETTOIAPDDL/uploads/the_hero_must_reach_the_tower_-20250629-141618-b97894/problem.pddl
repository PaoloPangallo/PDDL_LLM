(define (problem maze-solution)
    (:domain robot-world)
    (:objects
      rover - robot
      start-point goal - location
      block1 block2 - block
    )
    (:init
      (at rover start-point)
      (on block1 start-point)
      (clear start-point)
      (not (at-goal rover))
    )
    (:goal (and (at-goal rover)))
  )