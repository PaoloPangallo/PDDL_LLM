(define (problem castle-conquest)
    (:domain kingdom-conquest)
    (:objects
      hero1 - hero
      tower-of-varnak forest - location
      ice-dragon - dragon
      sword-of-fire - weapon
    )
    (:init
      (at hero1 tower-of-varnak)
      (in ice-dragon forest)
      (alive ice-dragon)
      (not (has-weapon hero1 sword-of-fire))
    )
    (:goal (and (at hero1 tower-of-varnak) (has-object hero1 sword-of-fire) (defeated ice-dragon)))
  )