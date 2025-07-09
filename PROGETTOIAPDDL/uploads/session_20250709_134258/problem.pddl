(define (problem journey-to-tower)
  (:domain hero-journey)
  (:objects
    hero village forest dark_cave tower sword_of_fire ice_dragon bandit goblin
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