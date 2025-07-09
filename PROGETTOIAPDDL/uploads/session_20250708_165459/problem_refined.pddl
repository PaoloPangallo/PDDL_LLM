(define (problem reach-tower-with-sword)
  (:domain tower-of-varnak)
  (:objects
    hero - agent
    tower village - location ; Ensure this is correctly typed if it's a location
    sword_of_fire - object ; Added type here
    ice_dragon - monster   ; Ensure all types are declared in objects if used
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