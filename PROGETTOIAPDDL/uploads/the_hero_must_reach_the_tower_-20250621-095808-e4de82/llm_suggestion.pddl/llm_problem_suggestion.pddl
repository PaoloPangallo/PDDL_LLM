(define (problem robot-labyrinth)
       (:domain robot-world)
       (:objects
         robot1 - robot
         start block1 goal1 - goal
         position1 position2 - position
       )
       (:goal (and (goal-reached goal1)))
       (:action reach-goal
         :parameters (?g - goal)
         :precondition (goal-reached ?g)
         :effect (not (goal-reached ?g))
       )
   )