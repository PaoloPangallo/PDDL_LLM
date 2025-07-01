(define (problem robot1)
  (:domain robot)
  (:objects
    robot1 - robot
    box1 - box
    table1 - table
    wall1 - wall
    wall2 - wall
    wall3 - wall
  )
  (:init
    (at robot1 table1)
    (on-table box1 table1)
    (on-wall box1 wall1)
    (on-wall box1 wall2)
    (on-wall box1 wall3)
  )
  (:goal
    (at robot1 wall2)
    (on-table box1 wall2)
  )
)