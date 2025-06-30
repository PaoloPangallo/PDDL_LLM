(define (problem fire-dragon-slayer)
    (:domain quest-fantasy)
    (:objects
      hero1 - hero
      tower-of-varnak mountain-cave - location
      ice-dragon - dragon
      sword-of-fire - weapon
    )
    (:init
      (at hero1 tower-of-varnak)
      (in ice-dragon mountain-cave)
      (alive ice-dragon)
    )
    (:goal (and (at hero1 tower-of-varnak) (has-object hero1 sword-of-fire) (defeated ice-dragon)))
  )