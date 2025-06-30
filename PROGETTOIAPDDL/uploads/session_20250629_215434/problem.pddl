(define (problem quest-against-ice)
    (:domain quest-of-fire)
    (:objects
      hero1 - hero
      tower-of-varnak cave - location
      ice-dragon - dragon
      sword-of-fire - sword
    )
    (:init
      (at hero1 cave)
      (on-ground sword-of-fire tower-of-varnak)
      (alive ice-dragon)
      (in ice-dragon cave)
    )
    (:goal (and (at hero1 tower-of-varnak) (has-object hero1 sword-of-fire) (defeated ice-dragon)))
  )