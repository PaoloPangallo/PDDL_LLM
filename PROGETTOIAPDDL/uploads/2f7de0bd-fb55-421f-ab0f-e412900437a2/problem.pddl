(define (problem la-spada-di-varnak-problem))
  (:domain la-spada-di-varnak)
  (:objects
    hero - hero
    village cave cave1 - location
    sword - sword
    dragon - monster)
  (:init
    (at hero village)
    (hidden sword cave)
    (sleeping dragon))
  (:goal (and (has hero sword) (defeated dragon)))