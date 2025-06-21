(define (problem city_journey)
    (:domain world_travel)
    (:objects
      agent1 - agent
      city1 city2 city3 - city
    )
    (:init
      (at agent1 city1)
      (connected city1 city2)
      (connected city2 city3)
    )
    (:goal (and (not (at agent1 city1)) (at agent1 city3)))
  )