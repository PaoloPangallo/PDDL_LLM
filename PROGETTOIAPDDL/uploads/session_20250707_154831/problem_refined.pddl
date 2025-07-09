(define (problem hero-tower-of-varnak)
  (:domain hero-quest)
  (:objects hero sword_of_fire ice_dragon tower_of_varnak village) ; Removed erroneous declaration of `sword_of_fire` from :types.
  (:init
    (at hero village)
    (on_ground sword_of_fire tower_of_varnak)
    (sleeping ice_dragon))
  (:goal
    (and (at hero tower_of_varnak)
         (carrying hero sword_of_fire)
         (defeated ice_dragon)))
)