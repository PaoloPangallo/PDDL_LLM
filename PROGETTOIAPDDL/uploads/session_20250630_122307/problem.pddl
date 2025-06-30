(define (problem hero-quest-1)
       (:domain hero-quest)
       (:objects hero tower-of-varnak ice-dragon sword-for-defeating village)
       (:init
        (at hero village)
        (on-ground sword-for-defeating tower-of-varnak)
        (sleeping ice-dragon))
       (:goal (and (defeated ice-dragon))))