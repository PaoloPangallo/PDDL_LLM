(define (problem move-problem)
  (:domain move-agent)
  (:objects location1 location2)
  (:init
    (at location1)
    (connected location1 location2)
  )
  (:goal (at location2))
)