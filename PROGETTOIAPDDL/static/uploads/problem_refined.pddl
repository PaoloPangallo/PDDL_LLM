(define (problem quest-problem) (:domain quest-domain)
  ; Problem declaration with name "quest-problem" that uses the domain "quest-domain"

  (:objects
    ; Define objects used in this problem, specifying their types
    hero - agent
    tower_of_varnak - location
    sword_of_fire - object
    ice_dragon - monster
    village - location
  )

  (:init
    ; Initial state of the world
    (at hero village)
    ; Hero starts at the village
    (on-ground sword_of_fire tower_of_varnak)
    ; Sword of Fire is on the ground in Tower of Varnak
    (sleeping ice_dragon)
    ; Ice Dragon is sleeping
  )

  (:goal
    ; Goal state to be achieved
    (and
      (at hero tower_of_varnak)
      ; Hero should be at Tower of Varnak
      (carrying hero sword_of_fire)
      ; Hero should be carrying the Sword of Fire
      (defeated ice_dragon)
      ; Ice Dragon should be defeated
    )
  )
)