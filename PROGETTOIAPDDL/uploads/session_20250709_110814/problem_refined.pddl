(define (problem hero-quest-problem)
  (:domain hero-quest)
  (:objects
    hero tower sword_of_fire ice_dragon village
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