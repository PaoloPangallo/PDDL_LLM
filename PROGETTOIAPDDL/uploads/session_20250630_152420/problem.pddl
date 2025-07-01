(define (problem tower-of-varnak-problem)
       :domain tower-of-varnak
       :objects
         (hero village hero-sword tower-of-varnak sword ice-dragon north-tower south-tower)
       :init
         (and
           (at hero village)
           (on-ground hero-sword tower-of-varnak)
           (sleeping ice-dragon))
       :goal (and (at hero tower-of-varnak) (awake ice-dragon)))