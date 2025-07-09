(define (problem my-problem)
  (:domain my-domain)
  (:objects
    hero - agent
    tower village - location
    sword_of_fire - object
    ice_dragon - monster
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