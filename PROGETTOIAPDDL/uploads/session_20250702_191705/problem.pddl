(define (problem ice-dragon)
  (:domain hero)
  (:objects
    hero - hero
    sword-of-fire - sword
    tower-of-varnak - tower
    ice-dragon - dragon
    village - village
  )
  (:init
    (at hero village)
    (on-ground sword-of-fire tower-of-varnak)
    (sleeping ice-dragon)
  )
  (:goal
    (at hero tower-of-varnak)
    (carrying hero sword-of-fire)
    (defeated ice-dragon)
  )
)