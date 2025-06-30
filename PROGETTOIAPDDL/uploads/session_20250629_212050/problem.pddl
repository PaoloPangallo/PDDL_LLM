(define (problem dragon-slaying)
    (:domain world-quest)
    (:objects
      hero1 - hero
      tower-of-varnak - location
      sword-of-fire - object
      ice-dragon - dragon
    )
    (:init
      (at hero1 tower-of-varnak)
      (on-ground sword-of-fire)
      (alive ice-dragon)
    )
    (:goal (and (at hero1 tower-of-varnak) (has-object hero1 sword-of-fire) (defeated ice-dragon)))
  )