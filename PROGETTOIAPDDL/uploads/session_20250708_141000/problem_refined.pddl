(define (problem hero-mission-problem)
  (:domain hero-mission)
  (:objects
    hero - agent
    tower_of_varnak - location
    sword_of_fire - object
    ice_dragon - monster
    village - location
  )
  (:init
    (at hero village)
    (on_ground sword_of_fire tower_of_varnak)
    (sleeping ice_dragon)
  )
  (:goal (and
    (at hero tower_of_varnak)
    (carrying hero sword_of_fire)
    (defeated ice_dragon)
  ))
)