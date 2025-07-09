(define (problem reach-tower-problem)
  (:domain reach-tower)
  (:objects
    hero - agent
    tower - location
    sword_of_fire - object
    ice_dragon - monster
    village - location
  )
  (:init
    (at hero village)
    (on_ground sword_of_fire village)
    (sleeping ice_dragon)
  )
  (:goal (and
    (at hero tower)
    (on_ground sword_of_fire tower)
    (defeated ice_dragon)
  ))
)