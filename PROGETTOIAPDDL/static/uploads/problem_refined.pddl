(define (problem quest-problem)
  (:domain quest)
  (:objects
    hero - Hero
    tower_of_varnak - Location
    sword_of_fire - Object
    ice_dragon - Monster
    village - Location
  )

  (:init
    ; initial state
    (at hero village)
    (on-ground sword_of_fire tower_of_varnak)
    (sleeping ice_dragon)
  )

  ; Add the missing tuples in the :init section as per the validation report.
  (:goal
    ; goal conditions
    (and
      (at hero tower_of_varnak)
      (carrying hero sword_of_fire)
      (defeated ice_dragon)
    )
  )
)