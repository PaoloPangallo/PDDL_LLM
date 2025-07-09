(define (problem hero-quest-problem)
  (:domain hero-quest)
  (:objects
    hero - agent
    tower - location
    sword - object ; Resolved error: sword added to :objects
    ice_dragon - monster
    village - location
  )
  (:init
    (at hero village)
    (on_ground sword village)
    (sleeping ice_dragon)
  )
  (:goal
    (and (at hero tower) (carrying hero sword) (defeated ice_dragon))
  )
)