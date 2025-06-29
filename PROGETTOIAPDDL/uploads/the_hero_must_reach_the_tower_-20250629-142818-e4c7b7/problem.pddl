(define (problem robot_map)
    (:domain robot_navigation)
    (:objects
      r1 - robot
      l1 l2 l3 l4 l5 l6 - location
      o1 o2 o3 - obstacle
      w1 w2 - wall)
    (:init
      (and (at r1 l1) (clear l1) (not (obstacle o1 l1)) (not (wall w1 l1)))
      (obstacle o1 l2)
      (obstacle o2 l3)
      (clear l4)
      (wall w1 l5)
      (wall w2 l6))
    (:goal (and (clear l2) (clear l3)))
  )