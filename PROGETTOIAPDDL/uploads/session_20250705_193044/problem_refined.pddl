(define (problem varnack-problem)
  (:domain varnack-problem)
  (:objects hero - hero
            tower-of-varnak - location
            sword-of-fire - sword
            ice-dragon - dragon)
  (:init
    (at astronaut base)
    (at rover base)
    (at sample crater))
  (:goal
    (and (at astronaut base)
         (has astronaut sample))))