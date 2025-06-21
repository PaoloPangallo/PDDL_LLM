(define (problem initial-state goal)
  :domain blocks-world

  ;; Initial State
  (:init
    (and (clear block1) (holding nil block1)
         (clear block2) (holding nil block2)
         (on block3 block4)
         (clear block5)))

  ;; Goal
  (:goal (and (clear block1) (clear block2) (on block1 block2) (clear block4) (clear block5)))
  )