(define (problem varnack-problem))
(:domain varnack-problem)
(:objects hero - hero
          tower-of-varnak - location
          sword-of-fire - sword
          ice-dragon - dragon
          robot - robot
          charging-station - charging-station
          battery - battery
          obstacle - obstacle)
(:init 
   (at hero village)
   (on-ground sword-of-fire tower-of-varnak)
   (sleeping ice-dragon)
   (at robot charging-station)
   (on-ground battery charging-station)
   (blocked obstacle charging-station))
(:goal (and (at hero tower-of-varnak)
            (carrying hero sword-of-fire)
            (defeated ice-dragon)))