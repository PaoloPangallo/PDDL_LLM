(define (problem tower-challenge)
    (:domain world-exploration)
    (:objects
      hero1 - hero
      tower-of-varnak mountain-pass cave - location
      ice-dragon - dragon
      sword-of-fire - object
    )
    (:init
      (at hero1 cave)
      (on-ground sword-of-fire cave)
      (in ice-dragon mountain-pass)
      (alive ice-dragon)
    )
    (:goal (and (at hero1 tower-of-varnak) (has-object hero1 sword-of-fire) (defeated ice-dragon)))
  )