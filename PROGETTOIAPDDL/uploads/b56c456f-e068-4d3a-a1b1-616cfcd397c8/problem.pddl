(define (problem la-spada-di-varnak-1))
  (:domain la-spada-di-varnak)
  (:objects hero village cave sleeping-dragon)
  (:init
    (at hero village)
    (hidden sword cave)
    (asleep sleeping-dragon)
  )
  (:goal (and (has hero sword) (defeated sleeping-dragon)))