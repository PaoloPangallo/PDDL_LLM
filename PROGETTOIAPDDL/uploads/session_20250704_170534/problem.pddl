(define (problem varnack-problem))
(:domain varnack-problem)
(:objects hero - hero
          tower-of-varnak - location
          sword-of-fire - sword
          ice-dragon - dragon)
(:init 
   (at hero village)
   (on-ground sword-of-fire tower-of-varnak)
   (sleeping ice-dragon))
(:goal (and (at hero tower-of-varnak)
            (carrying hero sword-of-fire)
            (defeated ice-dragon)))