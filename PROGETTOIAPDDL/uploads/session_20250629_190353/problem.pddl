(define (problem ice-battle)
    (:domain ice-adventure)
    (:objects
      hero1 - hero
      tower-of-varnak mountain cave - location
      ice-dragon - monster
    )
    (:init
      (at hero1 tower-of-varnak)
      (in ice-dragon cave)
      (alive ice-dragon)
      (frozen ice-dragon)
    )
    (:goal (and (not (alive ice-dragon)) (at hero1 tower-of-varnak)))
  )