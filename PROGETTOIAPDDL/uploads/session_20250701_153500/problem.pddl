(define (problem warehouse_problem)
  (:domain warehouse)
  (:objects
    worker1 - worker
    worker2 - worker
    box1 - box
    box2 - box
    warehouse1 - warehouse
    warehouse2 - warehouse
    box3 - box
    box4 - box
  )
  (:init
    (at worker1 warehouse1)
    (at worker2 warehouse2)
    (has_box worker1 box1)
    (has_box worker2 box2)
    (in box1 warehouse1)
    (in box2 warehouse2)
    (at warehouse1 warehouse2)
    (at warehouse2 warehouse1)
  )
  (:goal
    (and (at worker1 warehouse2) (at worker2 warehouse1) (has_box worker1 box1) (has_box worker2 box2))
  )
)