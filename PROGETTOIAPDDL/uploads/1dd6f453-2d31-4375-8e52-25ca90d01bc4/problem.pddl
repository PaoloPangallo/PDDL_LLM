(define (problem la_spada_di_varnak))
  (:domain la_spada_di_varnak)
  (:objects hero village cave sword dragon)
  (:init
    (at hero village)
    (hidden sword cave)
    (asleep dragon))
  (:goal (and (has-item hero sword) (defeated dragon)))