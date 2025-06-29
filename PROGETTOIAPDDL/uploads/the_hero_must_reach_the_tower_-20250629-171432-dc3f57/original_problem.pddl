(define (problem blocked-room)
    (:domain robot-world)
    (:objects
      rover - robot
      room1 room2 room3 - location
      blockA blockB blockC - block
    )
    (:init
      (and (at rover room1) (clear room1) (on blockA room1))
      (clear room2)
      (not (clear room3))
    )
    (:goal (clear room3))
  )