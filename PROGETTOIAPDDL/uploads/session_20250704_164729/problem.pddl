(define (problem varnack-problem))
(:domain varnack-problem)
(:objects hero - hero
          tower-of-varnak - location
          sword-of-fire - sword
          ice-dragon - dragon)
(:init 
   (at hero village)
   (sleeping ice-dragon))
(:goal (and (at hero tower-of-varnak)
            (carrying hero sword-of-fire)
            (defeated ice-dragon)))