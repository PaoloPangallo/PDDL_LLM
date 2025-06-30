(define (problem tower-quest)
    (:domain quest)
    (:objects
      hero - hero
      tower - location
      ice-dragon - dragon
      fire-sword - weapon
    )
    (:init
      (at hero tower)
      (in ice-dragon tower)
      (alive ice-dragon)
      (not (has-weapon hero fire-sword))
    )
    (:goal (and (at hero tower) (has-object hero fire-sword) (defeated ice-dragon)))
  )