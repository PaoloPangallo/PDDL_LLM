(define (problem quest-title)
  (:domain world-context)
  (:objects
    hero - agent
    village - location
    sword-of-fire - sword
    tower-of-varnak - location
    ice-dragon - dragon
  )
  (:init
    (at hero village)
    (on-ground sword-of-fire tower-of-varnak)
    (sleeping ice-dragon)
  )
  (:goal
    (and (at hero tower-of-varnak)
         (on hero sword-of-fire)
         (sleeping ice-dragon))
  )
)