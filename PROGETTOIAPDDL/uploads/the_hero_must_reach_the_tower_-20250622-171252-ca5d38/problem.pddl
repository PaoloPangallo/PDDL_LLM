(define (problem lost_in_the_labyrinth)
    (:domain world_of_puzzles)
    (:objects
      hero - entity
      start - location
      end - location
      stone1 - object
      stone2 - object
      goal - goal
    )
    (:init
      (at hero start)
      (on stone1 nil start)
      (clear end)
      (not (at goal end))
    )
    (:goal (and (at goal end) (goal_reached goal)))
  )