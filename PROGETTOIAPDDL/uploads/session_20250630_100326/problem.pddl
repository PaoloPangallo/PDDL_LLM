(define (problem hero-adventure-problem)
     :domain hero-adventure
     :objects (hero tower-of-varnak sword-of-fire ice-dragon village)
     :init
       (and (at hero village)
            (on-ground sword-of-fire tower-of-varnak)
            (sleeping ice-dragon))
     :goal (and (at hero tower-of-varnak) (awake ice-dragon)))