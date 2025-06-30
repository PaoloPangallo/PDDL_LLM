(define (problem world-battle)
    (:domain world-conquest)
    (:objects
      hero1 - hero
      tower-of-varnak castle - location
      ice-dragon - dragon
      sword-of-fire - object
    )
    (:init
      (at hero1 tower-of-varnak)
      (in ice-dragon castle)
      (alive ice-dragon)
      (not (has-object hero1 sword-of-fire))
    )
    (:goal (and (at hero1 castle) (has-object hero1 sword-of-fire) (defeated ice-dragon)))
  )