(define (problem varnak)
     (:objects hero sword dragon village cave)
     (:init
       (and (health hero positive)
            (at hero village)
            (hidden sword cave)
            (sleeping dragon)))
     (:goal (and (has hero sword) (defeated dragon))))