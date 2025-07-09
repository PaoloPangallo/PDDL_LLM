(define (problem hero-to-tower)
  (:domain hero-journey)
  (:objects hero sword_of_fire ice_dragon tower_of_varnak village) ; Resolved error: sword_of_fire added to :objects
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
; Resolved error: sword_of_fire added to :objects