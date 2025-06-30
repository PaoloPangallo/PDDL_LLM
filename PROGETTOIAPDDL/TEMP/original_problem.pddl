(define (problem hero-adventure-1)
     :domain hero-adventure
     :objects (hero sword-of-fire tower-of-varnak ice-dragon village)
     :init
       (at hero village)
       (on-ground sword-of-fire tower-of-varnak)
       (sleeping ice-dragon)
     :goal (and (not (sleeping ice-dragon)) (at hero tower-of-varnak) (carrying sword-of-fire)))