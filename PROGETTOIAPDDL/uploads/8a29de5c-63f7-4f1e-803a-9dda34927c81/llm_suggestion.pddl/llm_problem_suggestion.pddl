(define (problem travel-problem))
  (domain travel-world)
  (:objects
    agent1 - travel-agent
    location1 - location
    location2 - location)
  (:init
    (at agent1 location1)
    (on-water location1)
    (on-path location1 location2))
  (:goal (and (reachable agent1))))