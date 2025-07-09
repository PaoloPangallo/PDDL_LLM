(define (problem make-pizza-prob)
  (:domain pizza-making)
  (:objects
    robot - agent
    flour tomato - ingredient
    dough - dough
    sauce - sauce
    pizza - food
    mixer oven - machine
    table kitchen - place
  )
  (:init
    (at robot kitchen)
    (at flour table)
    (at tomato table)
    (empty dough)
    (empty sauce)
    (empty pizza)
  )
  (:goal (and
    (cooked pizza)
    (at robot kitchen)
  ))
)
