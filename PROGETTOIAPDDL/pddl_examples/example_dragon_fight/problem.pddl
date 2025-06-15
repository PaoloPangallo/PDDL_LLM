(define (problem dragon-battle)
  (:domain dragon-quest)
  (:objects
    hero1 - hero
    cave forest - location
    smaug - dragon
  )
  (:init
    (at hero1 cave)
    (in smaug forest)
    (alive smaug)
  )
  (:goal (and (not (alive smaug))))
)