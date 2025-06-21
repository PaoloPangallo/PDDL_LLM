(define (problem la-spada-di-varnak))
  (:domain la-spada-di-varnak)
  (:objects hero village cave sword dragon)
  (:init
    (at hero village)
    (hidden sword cave)
    (asleep dragon)
  )
  (:goal (and (has hero sword) (defeated dragon)))