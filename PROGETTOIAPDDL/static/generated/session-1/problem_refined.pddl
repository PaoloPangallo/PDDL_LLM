(define (problem quest-problem)
  (:domain quest-domain)
  (:objects 
    ; comment: define all objects used in the problem
    (hero - agent)
    (tower-of-varnak - location)
    (sword-of-fire - object)
    (ice-dragon - monster)
    (village - location)
  )
  (:init
    ; comment: initial state of the world
    (and (at hero village) 
         (on-ground sword-of-fire tower-of-varnak) 
         (sleeping ice-dragon))
  )
  (:goal 
    ; comment: desired final state of the world
    (and (at hero tower-of-varnak) 
         (carrying hero sword-of-fire) 
         (defeated ice-dragon))
  )
)