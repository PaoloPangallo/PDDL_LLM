(define (problem reach-tower)
  (:domain tower-of-varnak)
  (:objects
    hero - :object
    sword-of-fire - :object
    tower-of-varnak - :location
    ice-dragon - :dragon
    village - :location
  )
  (:init
    (at hero village)
    (on-ground sword-of-fire tower-of-varnak)
    (sleeping ice-dragon)
  )
  (:goal
    (and (at hero tower-of-varnak)
         (carrying hero sword-of-fire)
         (defeated ice-dragon))))