(define (problem simple_puzzle)
    (:domain simple_world)
    (:objects
      agent1 - agent
      startBox - location
      box1 - object
      goalBox - location
    )
    (:init
      (at agent1 startBox)
      (on box1 startBox)
    )
    (:goal (and (at agent1 goalBox) (not (on box1 goalBox))))
  )