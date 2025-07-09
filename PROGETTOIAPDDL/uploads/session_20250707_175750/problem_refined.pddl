(define (problem lore-problem)
  (:domain lore-domain)
  (:objects hero - agent sword_of_fire - object tower_of_varnak - location ice_dragon - monster village - location) ; Added 'village' here
  ; Detected error: Undefined object Got: sword_of_fire
  ; Resolved error: sword_of_fire added to :objects
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