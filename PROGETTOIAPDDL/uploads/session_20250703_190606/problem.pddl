(define (problem adventure-problem)
  (:domain adventure-domain)

  (:objects 
    hero - agent
    dragon - agent
    sword-of-fire - item
    village - location
    tower-of-varnak - location)

  (:init
    (at hero village)  
    (on-ground sword-of-fire tower-of-varnak)  
    (sleeping dragon)  
    (not (carrying hero sword-of-fire)))

  (:goal
    (and 
      (at hero tower-of-varnak)
      (carrying hero sword-of-fire)))
)