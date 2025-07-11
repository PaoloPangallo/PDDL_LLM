(define (problem hero-quest-problem)
  (:domain hero-quest)
  
  ; Objects
  (:objects
    hero tower_of_varnak sword_of_fire ice_dragon village
  )
  
  ; Initial State
  (:init
    (at hero village)
    (on-ground sword_of_fire tower_of_varnak)
    (sleeping ice_dragon)
  )
  
  ; Goal Conditions
  (:goal
    (and (at hero tower_of_varnak)
         (carrying hero sword_of_fire)
         (defeated ice_dragon))
  )
)