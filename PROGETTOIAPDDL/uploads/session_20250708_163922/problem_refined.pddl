(define (problem reach-and-defeat)
  (:domain heroic-mission)
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
    (carrying hero sword_of_fire)
    (defeated ice_dragon)
  ))
)