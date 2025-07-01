(define (problem robot_quest_problem)
  (:domain robot_quest)
  (:objects
    robot1 - robot
    robot2 - robot
    battery1 - battery
    battery2 - battery
    object1 - object
    object2 - object
    location1 - location
    location2 - location
    location3 - location
  )
  (:init
    (at robot1 location1)
    (at robot2 location2)
    (has_battery robot1 battery1)
    (has_battery robot2 battery2)
    (in object1 location1)
    (in object2 location2)
  )
  (:goal
    (and (at robot1 location2) (at robot2 location3) (holds robot1 object1) (holds robot2 object2))
  )
)