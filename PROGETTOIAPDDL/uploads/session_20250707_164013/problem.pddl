(define (problem reach-the-tower-problem)
  (:domain reach-the-tower)
  (:objects hero sword_of_fire ice_dragon tower_of_varnak village) ; Added object to this list
  (:init
    (at hero village)
    (on_ground sword_of_fire tower_of_varnak)
    (sleeping ice_dragon)
    (at hero tower_of_varnak)) ; Resolved error: fact moved/removed
  (:goal
    (and (carrying hero sword_of_fire) (defeated ice_dragon))) ; Resolved error: fact moved/removed
)