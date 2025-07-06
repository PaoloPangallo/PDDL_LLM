(define (problem ice-dragon)
  (:domain hero-adventure)
  (:objects
    hero - location
    sword-of-fire - object
    tower-of-varnak - location
    ice-dragon - object
    village - location
  )
  (:init
    (at hero village)
    (on-ground sword-of-fire tower-of-varnak)
    (sleeping ice-dragon)
    (at ice-dragon village)
  )
  (:goal
    (and (at hero tower-of-varnak)
         (carrying hero sword-of-fire)
         (at hero tower-of-varnak)
         (carrying hero sword-of-fire)
         (defeated ice-dragon))
  )
)