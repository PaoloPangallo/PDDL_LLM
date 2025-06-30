(define (problem block-puzzle)
    (:domain robot-world)
    (:objects
      r1 r2 r3 r4 - room
      b1 b2 b3 b4 b5 - block
      g - goal_block
    )
    (:init
      (at r1) (empty r1) (connected r1 r2) (on b1 r1)
      (at r2) (empty r2) (connected r2 r3) (on b2 r2)
      (at r3) (empty r3) (connected r3 r4) (empty r4) (goal_location g)
      (not (on g r4))
    )
    (:goal (and (and (= b1 g) (at r4)) (and (= b2 g) (at r4)) (and (= b3 g) (at r4)) (and (= b4 g) (at r4))))
  )