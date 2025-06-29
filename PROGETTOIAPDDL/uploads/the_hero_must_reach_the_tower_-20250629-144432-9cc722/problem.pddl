(define (problem treasure-hunt)
    (:domain world-exploration)
    (:objects
      agent1 - agent
      cave door chest - location
      key gold - item
    )
    (:init
      (at agent1 cave)
      (open cave)
      (contains chest gold)
      (open door)
      (and (not (contains chest agent1)) (not (has-item agent1 key)))
    )
    (:goal (and (has-item agent1 gold) (open door)))
  )