(define (problem varnak-adventure)
     (:objects (hero sword dragon) (village cave))
     (:init
      (and (at hero village) (hidden sword cave) (sleeping (location dragon)))
     )
     (:goal (and (has hero sword) (not (sleeping (location dragon))))
   )