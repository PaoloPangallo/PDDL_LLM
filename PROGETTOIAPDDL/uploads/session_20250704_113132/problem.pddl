(define (problem hero-quest))
(:domain hero)

(:objects hero - hero sword-of-fire - sword tower-of-varnak - tower ice-dragon - dragon)

(:init (at hero village)
       (carrying hero sword-of-fire)
       (awake ice-dragon))

(:goal (and (at hero tower-of-varnak)
            (carrying hero sword-of-fire)
            (defeated ice-dragon)))