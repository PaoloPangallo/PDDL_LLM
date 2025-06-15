(define (problem varnak-1)
   (:domain varnak)
   ; Oggetti e stato iniziale
   (:objects ?hero ?monster1 ?sword ?cave)
   (:init (and (in- ?hero village) (in- ?sword cave) (sleep-dragon ?monster1) (not (fight-dragon ?hero)) (not (has-sword ?hero))))
   ; Goal
   (:goal (and (not (sleep-dragon ?monster1)) (not (in- ?monster1 cave))) )
 )