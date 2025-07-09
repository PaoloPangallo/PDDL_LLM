(define (problem hero-to-tower)
  (:domain hero-quest)
  (:objects hero tower_of_varnak sword_of_fire ice_dragon village)
  (:init
    (at hero village)
    (on_ground sword_of_fire tower_of_varnak)
    (sleeping ice_dragon))
  (:goal
    (and
      (at hero tower_of_varnak)
      (carrying hero sword_of_fire)
      (defeated ice_dragon)))
)