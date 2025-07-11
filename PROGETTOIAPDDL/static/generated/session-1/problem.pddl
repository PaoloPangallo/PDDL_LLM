(define (problem quest-problem)
  (:domain quest-domain)
  
  (:objects 
    hero - agent
    tower-of-varnak - location
    sword-of-fire - object
    ice-dragon - monster
    village - location
  )

  (:init 
    (at hero village)
    (on-ground sword-of-fire tower-of-varnak)
    (sleeping ice-dragon)
  )

  (:goal 
    (and (at hero tower-of-varnak)
         (carrying hero sword-of-fire)
         (defeated ice-dragon))
  )
)